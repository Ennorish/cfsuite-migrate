# Deferred Items

## Out-of-scope discoveries during 03-01 execution

### test_auth.py failures due to uncommitted auth.py changes

**Found during:** Task 2 (full test suite run)
**Issue:** migrate/auth.py has uncommitted changes that add `_get_alias_map()` which calls `sf alias list --json`. The test_auth.py fixtures only register `sf org list --json`, causing ProcessNotRegisteredError for the new subprocess call.
**Impact:** 7 tests in tests/test_auth.py fail when running the full suite.
**Root cause:** Pre-existing uncommitted modification to auth.py (shown in git diff at start of session) — not caused by 03-01 changes.
**Resolution needed:** Update test_auth.py fixtures to also register `sf alias list --json`, or commit/discard the auth.py changes if they are not intended for this phase.
