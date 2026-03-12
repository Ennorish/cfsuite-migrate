---
phase: 02-core-etl
plan: "01"
subsystem: api
tags: [salesforce, simple-salesforce, etl, record-types, bulk-api, two-pass-insert]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Credentials dataclass (access_token, instance_url) from migrate/models.py
provides:
  - migrate/sf_api.py — Salesforce API wrapper: build_client, query_all, insert_records, get_record_type_map
  - migrate/etl.py — ETL helpers: extract_records, find_existing_keys, remap_record_types, two_pass_insert
affects: [02-core-etl plans 02-04, any object migrator]

# Tech tracking
tech-stack:
  added: [simple-salesforce (already in deps — used directly for first time)]
  patterns:
    - "Wrap simple-salesforce client construction behind build_client to isolate credential coupling"
    - "query_all always strips 'attributes' key — callers receive clean dicts"
    - "getattr(client.bulk, sobject) for dynamic SObject bulk access"
    - "Two-pass insert: null self-ref on pass 1, single-record update on pass 2 for simplicity"
    - "find_existing_keys short-circuits on empty list to avoid malformed IN () SOQL"

key-files:
  created:
    - migrate/sf_api.py
    - migrate/etl.py
    - tests/test_sf_api.py
    - tests/test_etl.py
  modified: []

key-decisions:
  - "Use getattr(client.bulk, sobject) for dynamic bulk SObject access rather than string interpolation on a URL"
  - "two_pass_insert uses single-record update (not a second bulk call) for pass 2 — children are a small subset"
  - "remap_record_types mutates records in place and returns None — matches the common ETL mutation pattern"
  - "find_existing_keys returns empty set on empty key_values — avoids emitting invalid SOQL with empty IN clause"

patterns-established:
  - "TDD RED-GREEN: failing import error confirms module absent, then implement to pass"
  - "Mock at module boundary: patch('migrate.etl.sf_api') intercepts all sf_api calls from etl"

requirements-completed: [DATA-08, DATA-09]

# Metrics
duration: 20min
completed: 2026-03-12
---

# Phase 2 Plan 01: Core ETL Engine Summary

**Salesforce API wrapper (simple-salesforce) + ETL primitives (RecordType remap, duplicate-skip, two-pass self-referential insert) shared by all four CFSuite object migrators**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-12T03:50:00Z
- **Completed:** 2026-03-12T04:10:19Z
- **Tasks:** 2 (4 commits: 2 RED + 2 GREEN)
- **Files modified:** 4

## Accomplishments

- `migrate/sf_api.py` wraps simple-salesforce: build_client from Credentials, query_all stripping attributes, bulk insert, RecordType map by DeveloperName
- `migrate/etl.py` provides shared ETL primitives: SOQL extraction, duplicate-skip key detection, RecordType ID remapping across orgs, two-pass self-referential insert
- 23 new tests (10 sf_api + 13 etl) all passing; full suite now 36 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: sf_api failing tests** - `c4468d4` (test)
2. **Task 1 GREEN: sf_api implementation** - `1794ad5` (feat)
3. **Task 2 RED: etl failing tests** - `0d7df60` (test)
4. **Task 2 GREEN: etl implementation** - `dd4aa90` (feat)

**Plan metadata:** _(final docs commit — see below)_

_Note: TDD tasks have two commits each (test RED then feat GREEN)_

## Files Created/Modified

- `migrate/sf_api.py` — Salesforce API wrapper; build_client, query_all, insert_records, get_record_type_map
- `migrate/etl.py` — ETL helpers; extract_records, find_existing_keys, remap_record_types, two_pass_insert
- `tests/test_sf_api.py` — 10 unit tests, all Salesforce calls mocked
- `tests/test_etl.py` — 13 unit tests, all sf_api calls mocked

## Decisions Made

- `getattr(client.bulk, sobject)` for dynamic bulk SObject access — avoids URL string construction, matches simple-salesforce's attribute-access design
- `two_pass_insert` uses single-record `client.{sobject}.update()` for pass 2 rather than a second bulk call, since only parent-having children need updating and the set is small
- `remap_record_types` mutates in place and returns None — consistent with ETL pipeline mutation pattern; callers need not collect a return value
- `find_existing_keys` short-circuits on empty `key_values` — avoids emitting `WHERE field IN ()` which is invalid SOQL

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock `__getattr__` assignment in test_insert_records_delegates_to_bulk**
- **Found during:** Task 1 (sf_api GREEN phase, first test run)
- **Issue:** Test set `client.bulk.__getattr__ = MagicMock(...)` which raises `AttributeError: Attempting to set unsupported magic method '__getattr__'` in Python's mock library
- **Fix:** Changed to `client.bulk.Account = fake_bulk_obj` — sets the named attribute directly on the MagicMock, which `getattr(client.bulk, 'Account')` then returns
- **Files modified:** tests/test_sf_api.py
- **Verification:** Test passed after fix; all 10 sf_api tests green
- **Committed in:** 1794ad5 (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Removed unused `call` import in test_etl.py flagged by ruff**
- **Found during:** Task 2 ruff check
- **Issue:** `from unittest.mock import MagicMock, patch, call` — `call` was imported but never used
- **Fix:** Removed `call` from import line
- **Files modified:** tests/test_etl.py
- **Verification:** `uv run ruff check migrate/ tests/` reports "All checks passed!"
- **Committed in:** dd4aa90 (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes required for correctness and lint compliance. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four ETL primitives available for Plans 02-02 through 02-05 (object migrators)
- Self-referential field names on CFSuite Request Flow and Community Request should be verified via `sf sobject describe` before implementing those migrators (existing blocker in STATE.md)

---
*Phase: 02-core-etl*
*Completed: 2026-03-12*

## Self-Check: PASSED

- migrate/sf_api.py: FOUND
- migrate/etl.py: FOUND
- tests/test_sf_api.py: FOUND
- tests/test_etl.py: FOUND
- Commits c4468d4, 1794ad5, 0d7df60, dd4aa90: ALL FOUND
