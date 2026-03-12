---
created: 2026-03-12T04:40:26.892Z
title: Fix cfsuite1 namespace in all migrators
area: etl
files:
  - migrate/objects/entitlement.py
  - migrate/objects/request_flow.py
  - migrate/objects/community_request.py
  - migrate/objects/preferred_comms.py
  - migrate/etl.py
  - tests/test_entitlement.py
  - tests/test_request_flow.py
  - tests/test_community_request.py
  - tests/test_preferred_comms.py
---

## Problem

All four object migrators use incorrect Salesforce API names. The managed package namespace is `cfsuite1__` (not `CFSuite__`), and object names use underscores instead of spaces (e.g., `cfsuite1__CFSuite_Request_Flow__c` not `CFSuite__Request_Flow__c`).

Confirmed from `sf sobject list --target-org cos_uat`:
- `cfsuite1__CFSuite_Request_Flow__c` (not `CFSuite__Request_Flow__c`)
- `cfsuite1__CFSuite_Preferred_Comms_Config__c` (not `CFSuite__Preferred_Comms_Config__c`)
- `Entitlement` (standard object — may be correct already)
- **Community Request object not found** — no `cfsuite1__*Community_Request*` object exists. Need to identify the correct object (possibly `cfsuite1__CFSuite_Categories__c` or another object).

All field names on these objects will also need the `cfsuite1__` prefix (e.g., `cfsuite1__Display_Category__c` not `CFSuite__Display_Category__c`).

## Solution

1. Run `sf sobject describe` on each object in a real org to get exact field API names
2. Update `_SOBJECT` and `_FIELDS` constants in all four migrator modules
3. Clarify with user what "Community Request" maps to — may need to rename/replace that migrator entirely
4. Update pipeline.py display names if object names change
5. Update tests to match new API names
