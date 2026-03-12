---
phase: 4
slug: web-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none (uses pyproject.toml defaults) |
| **Quick run command** | `uv run pytest tests/test_web.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_web.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | SC-1: serve opens browser | unit/smoke | `uv run pytest tests/test_web.py::test_serve_command -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | SC-2: searchable org picklists with badges | unit | `uv run pytest tests/test_web.py::test_get_orgs -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | SC-3: production orgs blocked | unit | `uv run pytest tests/test_web.py::test_migrate_blocks_production -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | SC-4: results per-object counts | unit | `uv run pytest tests/test_web.py::test_migrate_success -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `httpx>=0.28` added to `[dependency-groups] dev` in `pyproject.toml` — required for `fastapi.testclient.TestClient`
- [ ] `tests/test_web.py` — stubs covering all four success criteria

*httpx confirmed missing via runtime error during research.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser auto-opens on `serve` | SC-1 | `webbrowser.open()` requires a display | Run `cfsuite-migrate serve` locally, verify browser tab opens |
| Org dropdown searchability | SC-2 | Client-side JS filtering in index.html | Open wizard in browser, type in org dropdown, verify filter works |
| Color-coded sandbox/prod badges | SC-2 | Visual CSS assertion | Open wizard, verify sandbox=green, prod=red badges |
| Production target warning visible | SC-3 | Visual UI element | Select production org as target, verify warning displays |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
