---
phase: 03-validation-and-polish
plan: "01"
subsystem: cli
tags: [rich, progress, validation, pipeline, tdd]

# Dependency graph
requires:
  - phase: 02-core-etl
    provides: run_migration function and pipeline orchestrator
provides:
  - on_progress callback in run_migration for live per-object progress output
  - validate_results function that annotates results with match boolean
  - Rich Table summary after migration with OK/MISMATCH status per object
affects: [04-web-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [callback injection for observable pipeline steps, annotate-then-render validation pattern]

key-files:
  created:
    - tests/test_progress.py
  modified:
    - migrate/pipeline.py
    - migrate/main.py
    - tests/test_pipeline.py

key-decisions:
  - "on_progress callback uses (name, event, data) signature with 'start'/{} and 'done'/result events — composable and testable without side effects in pipeline.py"
  - "validate_results returns new list with match key added (not mutation) — keeps pipeline results immutable and test-friendly"
  - "Simple console.print for live output (not rich.progress.Progress) — readable in non-TTY environments and easier to test"
  - "Totals row via add_section() + add_row() instead of a separate footer — native Rich Table pattern"

patterns-established:
  - "Progress callback pattern: pass on_progress=None to pipeline, call before/after each step — zero overhead when not provided"
  - "Validate-then-render: compute derived fields (match) in a separate function, render in CLI — keeps logic out of display layer"

requirements-completed: [CLI-05, VAL-01]

# Metrics
duration: 25min
completed: 2026-03-12
---

# Phase 3 Plan 01: Validation and Progress Output Summary

**Real-time per-object migration progress via on_progress callback and a post-migration Rich Table with OK/MISMATCH validation status**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-12T04:30:00Z
- **Completed:** 2026-03-12T04:55:00Z
- **Tasks:** 2 completed
- **Files modified:** 4 (pipeline.py, main.py, test_pipeline.py, test_progress.py)

## Accomplishments

- Added optional `on_progress(name, event, data)` callback to `run_migration` with full backward compatibility (default None)
- Added `validate_results()` to pipeline that annotates results with `match = (extracted == skipped + inserted)`
- Replaced silent post-migration printout with a Rich Table showing all objects with extracted/skipped/inserted/status columns and a totals row
- CLI now prints "Migrating {name}..." before each object and counts after, giving users live feedback during potentially long runs
- 10 new tests covering callback invocation order, skip behavior, validation logic, and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Add progress callback to pipeline and test it** - `1b7d4e4` (feat, TDD)
2. **Task 2: Wire rich progress display and validation table into CLI** - `d002476` (feat)

## Files Created/Modified

- `migrate/pipeline.py` - Added `on_progress` parameter to `run_migration`, new `validate_results()` function
- `migrate/main.py` - Added `on_progress` callback, `validate_results` call, and Rich Table summary rendering
- `tests/test_pipeline.py` - Added `TestRunMigrationCallback` class with 5 new tests
- `tests/test_progress.py` - New file: 5 tests covering validate_results (all match, mismatch, empty)

## Decisions Made

- `on_progress` callback uses `(name, event, data)` with events `"start"` (data=`{}`) and `"done"` (data=result dict) — composable and testable without any side effects in pipeline.py
- `validate_results` returns a new list (not mutation) — keeps pipeline results immutable and separately testable
- Used `console.print` for live output rather than `rich.progress.Progress` — works cleanly in non-TTY environments (CI, pipes) and is straightforward to test
- Rich Table totals row added with `add_section()` for a native visual separator

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing test_auth.py failures (out of scope):** The uncommitted changes to `migrate/auth.py` (present before this plan ran) add a `_get_alias_map()` call that runs `sf alias list --json`. The existing test_auth.py fixtures only register `sf org list --json`, causing 7 test failures when running the full suite. This is not caused by 03-01 changes — our plan's tests (test_pipeline.py, test_progress.py) all pass. Logged to `deferred-items.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pipeline and CLI now provide live feedback and post-migration validation — ready for 04-web-ui to consume the same pipeline APIs
- `on_progress` callback and `validate_results` are clean interfaces usable from a web layer without modification
- Deferred: test_auth.py needs fixture updates to register `sf alias list --json` before the full suite can pass cleanly

---
*Phase: 03-validation-and-polish*
*Completed: 2026-03-12*

## Self-Check: PASSED

- migrate/pipeline.py: FOUND
- migrate/main.py: FOUND
- tests/test_pipeline.py: FOUND
- tests/test_progress.py: FOUND
- .planning/phases/03-validation-and-polish/03-01-SUMMARY.md: FOUND
- Commit 1b7d4e4 (Task 1): FOUND
- Commit d002476 (Task 2): FOUND
