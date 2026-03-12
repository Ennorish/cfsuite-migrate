---
phase: 02-core-etl
plan: "03"
subsystem: object-migrators
tags: [salesforce, etl, community-request, preferred-comms, self-referential, cross-object-lookup, record-types]

# Dependency graph
requires:
  - phase: 02-core-etl
    plan: "01"
    provides: etl.two_pass_insert, etl.remap_record_types, etl.find_existing_keys, sf_api.query_all, sf_api.insert_records, sf_api.get_record_type_map
provides:
  - migrate/objects/community_request.py — migrate_community_requests function
  - migrate/objects/preferred_comms.py — migrate_preferred_comms function
affects: [02-core-etl plan 02-04 (CLI wiring)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-object lookup resolved by source Id -> Name -> target Id; None fallback on miss"
    - "migrate/objects/ package for all object-specific migrators"
    - "Two-pass insert delegated entirely to etl.two_pass_insert (not re-implemented per migrator)"

key-files:
  created:
    - migrate/objects/__init__.py
    - migrate/objects/community_request.py
    - migrate/objects/preferred_comms.py
    - tests/test_community_request.py
    - tests/test_preferred_comms.py
    - .planning/phases/02-core-etl/deferred-items.md
  modified: []

key-decisions:
  - "Cross-object Request Flow lookup uses source Id -> Name -> target Id two-query approach — mirrors how Name-based matching works for all other cross-org references"
  - "None fallback (not error) when target RF missing — allows partial migrations without blocking the whole run"
  - "migrate/objects/ package created to house all object migrators as a clean namespace"

requirements-completed: [DATA-04, DATA-05, DATA-06, DATA-07]

# Metrics
duration: 3min
completed: 2026-03-12
---

# Phase 2 Plan 03: Community Request + Preferred Comms Migrators Summary

**Community Request migrator (CFSuite__Data_Settings__c) with RecordType remap, two-pass self-ref insert for Parent_Question__c, and cross-object Request Flow lookup by Name; Preferred Comms Config migrator (CFSuite__Preferred_Comms_Config__c) with RecordType remap and straightforward bulk insert**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-12T04:13:25Z
- **Completed:** 2026-03-12T04:16:25Z
- **Tasks:** 2 (4 commits: 2 RED + 2 GREEN)
- **Files modified:** 5 created

## Accomplishments

- `migrate/objects/community_request.py` migrates CFSuite__Data_Settings__c: RecordType remap, cross-object Request Flow lookup (source Id -> Name -> target Id, None on miss), skip existing by Name, two-pass insert for Parent_Question__c
- `migrate/objects/preferred_comms.py` migrates CFSuite__Preferred_Comms_Config__c: RecordType remap, skip existing by Name, bulk insert
- 8 new tests (5 community request + 3 preferred comms) all passing; full non-deferred suite at 47 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: community_request failing tests** - `74267e0` (test)
2. **Task 1 GREEN: community_request implementation** - `86e9590` (feat)
3. **Task 2 RED: preferred_comms failing tests** - `8549957` (test)
4. **Task 2 GREEN: preferred_comms implementation** - `b1605c1` (feat)

_Note: TDD tasks have two commits each (test RED then feat GREEN)_

## Files Created/Modified

- `migrate/objects/__init__.py` — package init for object migrators
- `migrate/objects/community_request.py` — migrate_community_requests; RecordType remap, cross-object RF lookup, skip existing, two-pass insert
- `migrate/objects/preferred_comms.py` — migrate_preferred_comms; RecordType remap, skip existing, bulk insert
- `tests/test_community_request.py` — 5 tests: remap+skip, self-ref two-pass, cross-obj lookup hit/miss, empty source
- `tests/test_preferred_comms.py` — 3 tests: remap+insert, skip existing, empty source

## Decisions Made

- Cross-object Request Flow lookup uses a two-query approach (source Ids -> Names, then target Names -> Ids) to resolve across orgs by Name rather than Id
- None fallback when target RF not found — graceful degradation prevents a missing lookup from blocking the entire migration run
- migrate/objects/ package created to provide a clean namespace for all object-specific migrators

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `pytest` import in test_community_request.py flagged by ruff**
- **Found during:** Task 1 ruff check after GREEN
- **Issue:** `import pytest` was included but no `pytest.raises` or fixtures were used in the test file
- **Fix:** Removed the unused import
- **Files modified:** tests/test_community_request.py
- **Commit:** 86e9590 (Task 1 GREEN commit)

### Out-of-scope items (logged in deferred-items.md)

- `test_request_flow.py` has a pre-existing RED test failure and ruff F401 from plan 02-02 (migrate/objects/request_flow.py was never implemented). Logged to deferred-items.md; not in scope for this plan.

## Issues Encountered

- Pre-existing test failure in tests/test_request_flow.py (plan 02-02 incomplete): `test_self_referential_resolution` fails because the module was never implemented. Logged as deferred item.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Community Request and Preferred Comms migrators ready for CLI wiring in plan 02-04
- Plan 02-02 (request_flow migrator) implementation is still outstanding — see deferred-items.md

---
*Phase: 02-core-etl*
*Completed: 2026-03-12*

## Self-Check: PASSED

- migrate/objects/__init__.py: FOUND
- migrate/objects/community_request.py: FOUND
- migrate/objects/preferred_comms.py: FOUND
- tests/test_community_request.py: FOUND
- tests/test_preferred_comms.py: FOUND
- Commits 74267e0, 86e9590, 8549957, b1605c1: ALL FOUND
