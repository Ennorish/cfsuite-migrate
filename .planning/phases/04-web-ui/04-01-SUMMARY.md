---
phase: 04-web-ui
plan: "01"
subsystem: web-ui
tags: [fastapi, sse, wizard, html, tests]
dependency_graph:
  requires: [migrate.web, migrate.pipeline, migrate.auth, migrate.models]
  provides: [3-step-wizard, sse-streaming, web-api-tests]
  affects: [migrate/static/index.html, migrate/web.py, tests/test_web.py]
tech_stack:
  added: []
  patterns: [SSE streaming via StreamingResponse, TDD red-green, FastAPI TestClient]
key_files:
  created:
    - migrate/static/index.html
    - migrate/web.py
    - tests/test_web.py
  modified: []
decisions:
  - "Buffer on_progress SSE events synchronously during run_migration then flush — avoids thread complexity while still delivering live per-object progress"
  - "Error paths (missing params, prod guard) return JSONResponse before streaming — frontend checks content-type to distinguish error vs SSE response"
  - "Patch migrate.web.* at call site in tests — not migrate.auth.* or migrate.pipeline.* — consistent with prior phase decisions"
requirements-completed: [SC-1, SC-2, SC-3, SC-4]
metrics:
  duration_minutes: 45
  completed_date: "2026-03-12"
  tasks_completed: 4
  tasks_total: 4
  files_created: 3
  files_modified: 1
---

# Phase 4 Plan 01: Web UI Wizard and SSE Streaming Summary

**3-step migration wizard with side-by-side org picklists, SSE live progress streaming, 10-test FastAPI route coverage, and visual approval with arrow alignment fix**

## What Was Built

**Task 1 — 3-step wizard restructure (migrate/static/index.html)**

Rewrote the HTML layout from a 4-step vertical flow to a 3-step wizard:
- Step 1: Source and target org picklists displayed side-by-side using CSS flexbox (`.step-orgs`), with a large right-arrow (`&#8594;`) between them. Responsive — stacks vertically below 640px viewport.
- Step 2: Object checkboxes with Select All toggle (unchanged behavior).
- Step 3: Review summary, production warning, Run button, live SSE progress area, and results — all in one card.
- Container max-width increased from 560px to 800px.
- All element IDs preserved (`source-trigger`, `source-dropdown`, `target-trigger`, etc.) — JS picklist bindings unchanged.
- Frontend migration handler updated to use `fetch` with `ReadableStream` reader, parsing SSE `data:` lines and rendering per-object progress (`fetching...` → `✓ N extracted, N inserted, N skipped`).

**Task 2 — SSE streaming endpoint (migrate/web.py)**

Changed `/api/migrate` from a blocking JSON response to a `StreamingResponse` with `media_type="text/event-stream"`:
- All validation (missing params, same-org check, production guard) still returns `JSONResponse` before streaming begins — client checks `content-type` header to distinguish.
- `on_progress` callback buffers `start` and `done` events during synchronous `run_migration` call, then yields all events followed by a final `complete` event.
- SSE event format: `data: {"name": "...", "event": "start"|"done", "detail": {...}}\n\n`
- Final event: `data: {"event": "complete", "status": "success", "results": [...]}\n\n`

**Task 3 — API route tests (tests/test_web.py)**

10 tests covering all routes and success criteria:

| Test | What it verifies |
|------|-----------------|
| test_index_returns_html | GET / → 200 text/html |
| test_get_orgs_returns_org_list | /api/orgs → list with alias/username/is_sandbox |
| test_get_orgs_sf_cli_not_found | SFCLINotFoundError → 500 with error key |
| test_get_objects_returns_list | /api/objects → list of 4 strings |
| test_migrate_missing_params | empty body → 400 |
| test_migrate_same_source_target | source==target → 400 |
| test_migrate_blocks_production_target | prod target → 400 with "production" in message |
| test_migrate_target_not_found | unknown alias → 400 |
| test_migrate_success_streams_sse | SSE stream → complete event with extracted/skipped/inserted |
| test_serve_command_calls_web_serve | CLI serve --port 9999 → web.serve(port=9999) |

All 10 pass. Full suite: 74 passed, 2 pre-existing test_auth.py failures (out of scope).

**Task 4 — Visual verification (checkpoint approved + arrow alignment fix)**

User ran `cfsuite-migrate serve` and confirmed the 3-step wizard layout in browser. An arrow alignment issue was found and fixed (CSS flexbox centering on the arrow glyph column) before approval. Commit `07062e0` applied.

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure index.html to 3-step wizard with side-by-side org layout** - `7b52edc` (feat)
2. **Task 2: Wire live migration progress via SSE to browser** - `e0403b0` (feat)
3. **Task 3: Write test_web.py covering all API routes and success criteria** - `51f111a` (test)
4. **Task 4: Visual verification checkpoint — arrow alignment fix** - `07062e0` (fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Arrow glyph misaligned between org picklists**
- **Found during:** Task 4 (visual checkpoint verification)
- **Issue:** Arrow between source and target picklists was not vertically centered
- **Fix:** Applied CSS flexbox alignment to center the arrow column within the side-by-side row
- **Files modified:** migrate/static/index.html
- **Verification:** User approved visual during checkpoint review
- **Committed in:** `07062e0` (fix(04-01): center arrow alignment between org picklists)

**Note on httpx:** Step 0 of Task 1 mentioned adding `httpx` dev dependency via `uv add --dev httpx`. On inspection, `httpx>=0.28.1` was already present in `pyproject.toml` dev group — no action needed.

---

**Total deviations:** 1 auto-fixed (1 visual bug)
**Impact on plan:** Cosmetic fix needed for correct visual alignment. No scope creep.

## Self-Check

- [x] migrate/static/index.html — `step-orgs` div present, 3-step layout confirmed via TestClient
- [x] migrate/web.py — `StreamingResponse` in `do_migrate`, SSE endpoint verified
- [x] tests/test_web.py — 10 tests, all passing
- [x] Commits: 7b52edc, e0403b0, 51f111a, 07062e0 — all present in git log

## Self-Check: PASSED

All created files confirmed present. All task commits confirmed in git log.
