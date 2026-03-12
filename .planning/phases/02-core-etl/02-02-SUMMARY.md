---
phase: 02-core-etl
plan: "02"
subsystem: object-migrators
tags: [entitlement, request-flow, two-pass-insert, record-type-remap, tdd]
dependency_graph:
  requires: [02-01]
  provides: [migrate_entitlements, migrate_request_flows]
  affects: [migrate/objects/]
tech_stack:
  added: []
  patterns:
    - two-pass insert for self-referential records (source_id->name->new_target_id)
    - source Id included in FIELDS then stripped before insert for self-ref resolution
    - insert-only with Name-based duplicate skip
key_files:
  created:
    - migrate/objects/__init__.py
    - migrate/objects/entitlement.py
    - migrate/objects/request_flow.py
    - tests/test_entitlement.py
    - tests/test_request_flow.py
  modified: []
decisions:
  - Include Id in request_flow FIELDS to build source_id->name map for self-ref resolution; Id stripped before insert
  - Custom two-pass flow (not etl.two_pass_insert) for request_flow — two self-ref fields require a single pass-1 insert then per-field pass-2 updates
  - Entitlements carry AccountId as-is — both orgs share Account names in CFSuite sandbox setup
metrics:
  duration_seconds: 203
  completed_date: "2026-03-12"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 02 Plan 02: Entitlement and Request Flow Migrators Summary

**One-liner:** Entitlement migrator (Name-dedup, no RecordType) and Request Flow migrator (RecordType remap + two-pass insert resolving Display_Category__c and Category_Journey__c self-refs via source_id->name->new_id map).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Entitlement migrator | 28b6bf4 | migrate/objects/__init__.py, migrate/objects/entitlement.py, tests/test_entitlement.py |
| 2 | Request Flow migrator with two-pass self-ref insert | 152fb4d | migrate/objects/request_flow.py, tests/test_request_flow.py |

TDD RED commits: 3e60aea (entitlement), 3b29ddb (request_flow)

## Decisions Made

**1. Include Id in request_flow FIELDS for self-ref resolution**
- Source self-ref fields hold source record IDs, not names
- Build `source_id -> name` map from extracted records before mutation
- Strip Id before pass-1 insert (Salesforce rejects write of non-writable Id field)
- Alternative (extra query for Id->Name) would add a Salesforce API call; including Id in the existing query is cheaper

**2. Custom two-pass flow instead of etl.two_pass_insert**
- `etl.two_pass_insert` handles one self-ref field at a time
- Request Flow has two self-ref fields (Display_Category__c, Category_Journey__c)
- Custom flow: single pass-1 insert with both fields nulled, then per-field pass-2 updates collected into one `.update()` call per record
- Produces one update call per record that has any non-null self-ref (not two calls per record)

**3. Entitlements carry AccountId as-is**
- CFSuite managed package: both orgs share same Account names in sandbox setup
- No AccountId remap needed; if this assumption breaks, Phase 3 validation will catch it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added Id to FIELDS and built source_id->name map**
- **Found during:** Task 2 (GREEN phase, test failure)
- **Issue:** Test expects pass-2 to resolve `"old-display-cat-id"` -> `"new-display-001"` but plan's custom flow didn't specify how source IDs in self-ref fields map to names. The plan's `etl.two_pass_insert` uses name_field directly which assumes self-ref holds names — Salesforce lookup fields hold IDs.
- **Fix:** Added `Id` to `_FIELDS`, built `source_id_to_name` map before mutation, updated test to include `Id` in source records
- **Files modified:** migrate/objects/request_flow.py, tests/test_request_flow.py

**2. [Rule 1 - Bug] Removed unused `_INSERT_FIELDS` variable**
- **Found during:** Task 2 implementation (IDE diagnostic)
- **Fix:** Removed dead variable; Id stripping handled inline in pass1_records comprehension

**3. [Rule 1 - Bug] Removed unused `call` import in test file**
- **Found during:** Task 2 ruff check
- **Fix:** Removed `call` from `unittest.mock` imports

## Verification

All 51 tests pass:
```
51 passed in 0.13s
```
Ruff clean: `All checks passed!`

## Self-Check: PASSED
