---
phase: 01-foundation
plan: "01"
subsystem: auth
tags: [python, uv, pytest, pytest-subprocess, sf-cli, subprocess, salesforce]

# Dependency graph
requires: []
provides:
  - "uv project scaffold with pyproject.toml (typer, simple-salesforce, questionary, rich)"
  - "migrate/models.py: OrgInfo, Credentials dataclasses, ProductionOrgError, SFCLINotFoundError"
  - "migrate/auth.py: list_orgs(), get_credentials(), assert_not_production()"
  - "tests/test_auth.py: 7 unit tests covering all auth behaviors"
affects:
  - "01-02 (interactive CLI needs list_orgs and get_credentials)"
  - "all Phase 2 plans (migration depends on authenticated org connections)"

# Tech tracking
tech-stack:
  added: [uv, typer, simple-salesforce, questionary, rich, pytest, pytest-subprocess, ruff]
  patterns:
    - "subprocess.run with capture_output=True for SF CLI invocation"
    - "pytest-subprocess FakeProcess fixture for SF CLI mocking"
    - "Dataclass models for structured CLI output (OrgInfo, Credentials)"

key-files:
  created:
    - pyproject.toml
    - .python-version
    - migrate/__init__.py
    - migrate/models.py
    - migrate/auth.py
    - tests/__init__.py
    - tests/test_auth.py
    - uv.lock
  modified: []

key-decisions:
  - "Used callback lambda in pytest-subprocess to raise FileNotFoundError — FakeProcess.raise_exception() not available in v1.5.3"
  - "uv manages Python 3.11 runtime via .python-version — ensures consistent interpreter across team"

patterns-established:
  - "TDD RED-GREEN: write failing tests before implementation, commit RED state, then implement to GREEN"
  - "SF CLI subprocess calls always use check=False and inspect returncode manually"
  - "Production guard is a pure function on OrgInfo.is_sandbox — no subprocess call needed"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: 18min
completed: 2026-03-12
---

# Phase 1 Plan 01: Foundation Summary

**uv project scaffold with SF CLI auth layer — list_orgs, get_credentials, and production guard fully tested via pytest-subprocess mocks**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-12T03:46:15Z
- **Completed:** 2026-03-12T04:04:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Scaffolded Python 3.11 project with uv — pyproject.toml declares all runtime and dev deps
- Built `migrate/models.py` with OrgInfo and Credentials dataclasses and two custom exceptions
- Built `migrate/auth.py` integrating SF CLI via subprocess — list_orgs, get_credentials, assert_not_production
- 7 unit tests covering all specified behaviors, all passing, ruff reports no lint errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold project with uv and pyproject.toml** - `7c50571` (chore)
2. **Task 2 RED: Add failing tests for auth module** - `5d24269` (test)
3. **Task 2 GREEN: Implement auth module** - `1dedb93` (feat)

_Note: TDD task has two commits — RED test commit then GREEN implementation commit_

## Files Created/Modified

- `pyproject.toml` - Project config with all runtime deps and dev deps, ruff settings
- `.python-version` - Pins Python 3.11 for uv
- `uv.lock` - Locked dependency graph
- `migrate/__init__.py` - Package marker (empty)
- `migrate/models.py` - OrgInfo, Credentials dataclasses; ProductionOrgError, SFCLINotFoundError
- `migrate/auth.py` - list_orgs(), get_credentials(), assert_not_production() via SF CLI subprocess
- `tests/__init__.py` - Package marker (empty)
- `tests/test_auth.py` - 7 unit tests using pytest-subprocess FakeProcess fixture

## Decisions Made

- Used callback lambda (`def _raise_file_not_found(process): raise FileNotFoundError(...)`) instead of `FakeProcess.raise_exception()` which does not exist in pytest-subprocess 1.5.3. Functionally equivalent.
- uv automatically downloaded CPython 3.11.15 when building the venv per `.python-version` — the project consistently runs under 3.11 even though the system Python is 3.14.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pytest-subprocess callback API for FileNotFoundError test**
- **Found during:** Task 2 (TDD GREEN phase, test run)
- **Issue:** Plan's test template used `callback=FakeProcess.raise_exception(FileNotFoundError)` — this method does not exist in pytest-subprocess 1.5.3
- **Fix:** Replaced with a local lambda function passed as callback that raises FileNotFoundError directly
- **Files modified:** `tests/test_auth.py`
- **Verification:** `test_list_orgs_sf_cli_not_found` now passes (7/7 green)
- **Committed in:** `1dedb93` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan's template API call)
**Impact on plan:** Single-line test fix. No scope change, all 7 behaviors fully covered.

## Issues Encountered

- `uv` was not installed on the system — installed via Homebrew before scaffolding. No impact on deliverables.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Auth foundation complete — Plan 02 (interactive CLI) can call `list_orgs()` and `get_credentials()` directly
- `migrate/auth.py` raises typed exceptions (SFCLINotFoundError, ProductionOrgError, ValueError) that the CLI layer can catch and surface as user-friendly messages
- Phase 2 migration plans can rely on `Credentials.access_token` and `Credentials.instance_url` for simple-salesforce connections

---
*Phase: 01-foundation*
*Completed: 2026-03-12*

## Self-Check: PASSED

All files present: pyproject.toml, .python-version, migrate/__init__.py, migrate/models.py, migrate/auth.py, tests/__init__.py, tests/test_auth.py, 01-01-SUMMARY.md
All commits verified: 7c50571, 5d24269, 1dedb93
