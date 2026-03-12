---
status: resolved
trigger: "wrong-namespace-prefix - All migrator files use CFSuite__ as the Salesforce namespace prefix, but the actual managed package namespace is cfsuite1__"
created: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - root cause is CFSuite__ prefix throughout. Additionally, migrator FIELDS lists include field names that don't exist on the org objects.
test: ran sf sobject describe for all 3 custom objects, compared against migrator field lists
expecting: all fields corrected to actual org field API names
next_action: applying fixes to all 7 files

## Symptoms

expected: Migration runs successfully against orgs with the CFSuite managed package (namespace: cfsuite1)
actual: "sObject type 'CFSuite__Request_Flow__c' is not supported" error. The correct name is cfsuite1__CFSuite_Request_Flow__c
errors: Malformed request - sObject type 'CFSuite__Request_Flow__c' is not supported
reproduction: Run migration from cos_uat to cos_support org via web UI
started: Always been wrong - the code was generated with incorrect namespace prefix

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-12T00:00:00Z
  checked: migrate/objects/request_flow.py
  found: SOBJECT = "cfsuite1__CFSuite_Request_Flow__c" - already correct; all fields use cfsuite1__ prefix
  implication: request_flow.py is already fully fixed

- timestamp: 2026-03-12T00:00:00Z
  checked: migrate/objects/community_request.py
  found: SOBJECT = "cfsuite1__Data_Settings__c" - already correct; all fields use cfsuite1__ prefix
  implication: community_request.py is already fully fixed

- timestamp: 2026-03-12T00:00:00Z
  checked: migrate/objects/preferred_comms.py
  found: SOBJECT = "CFSuite__Preferred_Comms_Config__c" - WRONG; fields use CFSuite__ prefix - WRONG
  implication: preferred_comms.py needs full namespace fix: object name AND all 4 field names

- timestamp: 2026-03-12T00:00:00Z
  checked: migrate/pipeline.py OBJECT_MIGRATORS
  found: "CFSuite__Request_Flow__c", "CFSuite__Data_Settings__c", "CFSuite__Preferred_Comms_Config__c" - all WRONG
  implication: pipeline.py needs all 3 API names corrected to cfsuite1__ prefix

- timestamp: 2026-03-12T00:00:00Z
  checked: migrate/web.py /api/objects
  found: Returns hardcoded list of display names - display names are fine as friendly strings
  implication: web.py /api/objects does not need changes (display names are correct)

## Resolution

root_cause: Three root causes combined: (1) preferred_comms.py was never updated from CFSuite__ prefix - wrong object name and all field names. (2) pipeline.py OBJECT_MIGRATORS had wrong API names for all 3 custom objects. (3) All three migrators had fabricated field names that do not exist on the actual org objects (Active__c, Description__c, Order__c, Question_Text__c, Response_Value__c, Entitlement_Name__c, Channel__c, Priority__c).
fix: preferred_comms.py - corrected object to cfsuite1__CFSuite_Preferred_Comms_Config__c, replaced non-existent Channel/Priority fields with real org fields; request_flow.py - removed non-existent Active/Description/Order fields, renamed Entitlement_Name__c -> Entitlement_Process_Name__c, added real org fields; community_request.py - removed non-existent Active/Description/Response_Value fields, Order__c -> Sort_Order__c, Question_Text__c -> Question__c, added real org fields; pipeline.py - all 3 API names corrected to cfsuite1__ prefix; all test files updated to match.
verification: 74/76 tests pass. 2 pre-existing test_auth.py failures unrelated to this fix (sf alias list command mismatch in test setup).
files_changed:
  - migrate/objects/preferred_comms.py
  - migrate/objects/request_flow.py
  - migrate/objects/community_request.py
  - migrate/pipeline.py
  - tests/test_preferred_comms.py
  - tests/test_request_flow.py
  - tests/test_community_request.py
  - tests/test_pipeline.py
