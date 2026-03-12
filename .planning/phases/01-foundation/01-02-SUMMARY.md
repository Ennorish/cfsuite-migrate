---
phase: 01-foundation
plan: "02"
subsystem: cli
tags: [python, typer, questionary, rich, pytest, tdd, sf-cli]

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: "migrate/auth.py: list_orgs(), assert_not_production(); migrate/models.py: OrgInfo, ProductionOrgError, SFCLINotFoundError"
provides:
  - "migrate/prompts.py: select_source_org(), select_target_org(), select_objects() — interactive questionary prompts"
  - "migrate/main.py: Typer app entry point wiring auth + prompts into runnable `cfsuite-migrate migrate` command"
  - "tests/test_prompts.py: 6 unit tests covering all prompt behaviors"
affects:
  - "Phase 2 migration plans (will call main.py command; source/target org credentials flow from this CLI)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED-GREEN: 6 failing tests committed before any prompts.py implementation"
    - "Import module reference (import migrate.auth as auth) rather than from-import, so unittest.mock.patch on migrate.auth.assert_not_production intercepts calls correctly"
    - "Questionary prompts return .ask() result — mock by patching questionary.select/checkbox to return a MagicMock with .ask() set"

key-files:
  created:
    - migrate/prompts.py
    - migrate/main.py
    - tests/test_prompts.py
  modified: []

key-decisions:
  - "Import migrate.auth as module (not from-import) so mock patches on migrate.auth.assert_not_production intercept calls at runtime"
  - "select_target_org exits with code 1 (not 0) on ProductionOrgError — distinguishes user error from clean no-orgs exit"

patterns-established:
  - "Module-level import for mockable dependencies: use 'import migrate.auth as auth' when tests need to patch that module's functions"
  - "Typer CLI no_args_is_help=True: running bare command shows help instead of failing silently"

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 1 Plan 02: Interactive CLI Summary

**Typer CLI entry point with questionary org/object selection prompts — no-orgs guidance, production org guard, and dependency-ordered object selection — wiring Plan 01's auth layer into a fully interactive `cfsuite-migrate migrate` command**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-12T03:51:00Z
- **Completed:** 2026-03-12T03:52:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Built `migrate/prompts.py` with three prompt functions: `select_source_org`, `select_target_org`, `select_objects`
- Built `migrate/main.py` as the Typer CLI entry point with `--source`/`--target` flag shortcuts and full production guard
- 6 unit tests covering all six specified behaviors, all passing; ruff reports no lint errors
- Full test suite (13 tests: 7 auth + 6 prompts) all green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests for prompts module** - `4b8122b` (test)
2. **Task 1 GREEN: Implement prompts module** - `900993d` (feat)
3. **Task 2: Wire Typer CLI entry point in main.py** - `38423b5` (feat)
4. **Lint fix: Remove unused imports** - `3683734` (fix)

_Note: TDD task has two commits — RED test commit then GREEN implementation commit_

## Files Created/Modified

- `migrate/prompts.py` - select_source_org, select_target_org, select_objects with questionary prompts
- `migrate/main.py` - Typer app, migrate command, --source/-s and --target/-t flags, production guard
- `tests/test_prompts.py` - 6 unit tests using unittest.mock.patch for questionary and migrate.auth

## Decisions Made

- Used `import migrate.auth as auth` (module reference) in prompts.py rather than `from migrate.auth import assert_not_production`. This ensures `unittest.mock.patch("migrate.auth.assert_not_production")` correctly intercepts the call at runtime — from-imports bind the name locally and bypass patches.
- `select_target_org` exits with code 1 on `ProductionOrgError`, not 0 — distinguishes error exits from the clean "no orgs" exit path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused imports flagged by ruff**
- **Found during:** Final verification (ruff check)
- **Issue:** Plan template included `get_credentials` import in main.py (not used in Phase 1) and tests imported `sys` (not used in test bodies)
- **Fix:** Removed `get_credentials` from main.py imports; removed `sys` from test_prompts.py imports
- **Files modified:** `migrate/main.py`, `tests/test_prompts.py`
- **Verification:** `uv run ruff check migrate/ tests/` reports "All checks passed!"
- **Committed in:** `3683734` (fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — unused imports from plan template)
**Impact on plan:** Single-line removals each. No scope change, all 6 behaviors fully covered.

## Issues Encountered

None — the import patching pattern worked correctly on first implementation attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 foundation complete — both auth layer (Plan 01) and interactive CLI (Plan 02) are implemented and tested
- Phase 2 can rely on `select_source_org` / `select_target_org` returning typed `OrgInfo` objects ready for `get_credentials(alias)` calls
- The `migrate` command accepts `--source`/`--target` flag shortcuts useful for scripted Phase 2 integration testing

---
*Phase: 01-foundation*
*Completed: 2026-03-12*
