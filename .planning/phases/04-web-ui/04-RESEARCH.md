# Phase 4: Web UI - Research

**Researched:** 2026-03-12
**Domain:** FastAPI local web server, vanilla JS single-page wizard, httpx testing
**Confidence:** HIGH

## Summary

Phase 4 is substantially pre-built. `migrate/web.py` contains a complete FastAPI application
with three API routes (`/api/orgs`, `/api/objects`, `/api/migrate`) and a `serve()` launcher
that opens a browser tab via `threading.Timer`. `migrate/static/index.html` contains the full
single-page wizard: searchable org picklists with sandbox/production badges, object checkboxes,
review panel, production-target warning, and per-object result display. The Typer `serve`
command is already wired in `migrate/main.py`. FastAPI 0.135.1 and uvicorn 0.41.0 are already
installed in the project venv.

The two gaps that remain: (1) no tests exist for `web.py` — the `TestClient` pattern requires
`httpx` as a dev dependency (not currently in `pyproject.toml`, though it was just installed
manually), and (2) the `on_progress` callback added in Phase 3 is not plumbed through
`do_migrate()` in `web.py` — the endpoint calls `run_migration` without a callback, so there
is no live output wired to the browser (the current results display is a post-completion
response, which is acceptable for Phase 4's success criteria).

**Primary recommendation:** Wire `httpx` into `pyproject.toml` dev dependencies, write
`tests/test_web.py` using `fastapi.testclient.TestClient` with mocked `auth` and `pipeline`
calls, and verify the `serve` command end-to-end with a Typer `CliRunner` smoke test.

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.1 | HTTP routing, request/response handling | Already in pyproject.toml; async-capable, Pydantic-native |
| uvicorn | 0.41.0 | ASGI server (runs FastAPI) | Standard uvicorn pairing; already in pyproject.toml |
| starlette | (fastapi dep) | TestClient, StaticFiles, HTMLResponse | Ships with FastAPI; no separate install |

### Dev/Test
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | Required by `fastapi.testclient.TestClient` | All web route tests |

### Already Present (no new installs needed beyond httpx)
- `typer` — `serve` command already wired
- `webbrowser` / `threading` — stdlib; browser-open already implemented in `serve()`
- `migrate.auth`, `migrate.pipeline`, `migrate.sf_api` — already imported by `web.py`

**Installation (only missing dev dep):**
```bash
uv add --dev httpx
```

Then add to `pyproject.toml` dev group:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-subprocess>=1.5",
    "ruff>=0.15.5",
    "httpx>=0.28",
]
```

## Architecture Patterns

### Existing File Layout (already in place)
```
migrate/
├── web.py              # FastAPI app + serve() launcher — EXISTS, complete
├── static/
│   └── index.html      # Single-page wizard — EXISTS, complete
└── main.py             # Typer serve command — EXISTS, wired
tests/
└── test_web.py         # MISSING — Wave 0 gap
```

### Pattern 1: FastAPI TestClient with Mocked Dependencies
**What:** Override auth/pipeline functions using `unittest.mock.patch` so tests never
invoke `sf` CLI or real Salesforce connections.
**When to use:** All API route tests.
**Example:**
```python
# Source: FastAPI docs — https://fastapi.tiangolo.com/tutorial/testing/
from unittest.mock import patch
from fastapi.testclient import TestClient
from migrate.web import app

client = TestClient(app)

def test_get_orgs_returns_list():
    fake_orgs = [OrgInfo(alias="dev", username="dev@example.com", is_sandbox=True)]
    with patch("migrate.web.list_orgs", return_value=fake_orgs):
        resp = client.get("/api/orgs")
    assert resp.status_code == 200
    assert resp.json()[0]["alias"] == "dev"
```

### Pattern 2: Patch at call site, not at definition site
**What:** Patch `migrate.web.list_orgs` (the name as imported in `web.py`), not
`migrate.auth.list_orgs`.
**When to use:** All patches in `test_web.py` — same pattern used in the existing test suite.

### Pattern 3: TestClient for `/` route returns HTML
**What:** The index route reads from a file on disk; tests should assert status 200
and content-type `text/html`.
**Example:**
```python
def test_index_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
```

### Pattern 4: do_migrate endpoint error paths
**What:** The `/api/migrate` endpoint has several guard clauses (missing params,
same source/target, SF CLI not found, production org target) — each should have
a test asserting `status_code` and `error` key in the JSON response.

### Anti-Patterns to Avoid
- **Calling `serve()` in tests:** `serve()` calls `uvicorn.run()` which blocks;
  use `TestClient(app)` directly — it exercises all routes without starting a real server.
- **Testing real SF CLI calls in test_web.py:** Every test must mock `list_orgs`,
  `get_credentials`, `build_client`, `run_migration` — exactly as the CLI tests mock auth.
- **Importing StaticFiles at test time without the static dir present:** `web.py` does NOT
  mount StaticFiles as middleware (it reads the file in the route handler), so this is not
  a risk — but confirm `migrate/static/index.html` exists before running tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP test client | Custom test server setup | `fastapi.testclient.TestClient` | In-process; no port binding needed |
| Browser auto-open | Manual subprocess | `webbrowser.open()` + `threading.Timer` (already in place) | Already implemented |
| CORS for localhost | Custom middleware | Not needed — same origin (127.0.0.1:port) for both server and browser | No cross-origin requests |
| Async test runner | pytest-asyncio | Not needed — TestClient wraps async handlers synchronously | Simpler, fewer deps |

**Key insight:** The web layer is a thin wrapper around already-tested pipeline functions.
Testing strategy is "mock the seams, test the HTTP layer's decisions" — not
re-testing pipeline logic.

## Common Pitfalls

### Pitfall 1: Patching the wrong module namespace
**What goes wrong:** `patch("migrate.auth.list_orgs")` doesn't affect `web.py` because
`web.py` already imported `list_orgs` into its own namespace at import time.
**Why it happens:** Python binds names at import; patch must target where the name is *used*.
**How to avoid:** Always patch `migrate.web.list_orgs`, `migrate.web.run_migration`, etc.
**Warning signs:** Mock is set but real subprocess calls still happen during test.

### Pitfall 2: `do_migrate` calls `list_orgs` twice
**What goes wrong:** The endpoint calls `list_orgs()` once to validate the production guard,
independently of the caller's org list. Tests must mock this call or it will hit the real CLI.
**How to avoid:** In tests for `/api/migrate`, always patch `migrate.web.list_orgs` as well as
`migrate.web.get_credentials`, `migrate.web.build_client`, `migrate.web.run_migration`.

### Pitfall 3: `run_migration` returns plain dicts, not Pydantic models
**What goes wrong:** The endpoint returns `{"status": "success", "results": results}` where
`results` is a list of plain dicts (`{"object":..., "extracted":..., ...}`). Pydantic
validation does not apply — no automatic coercion. If the pipeline ever returns unexpected
keys, they will pass through silently.
**How to avoid:** Tests should assert exact keys in result dicts, not just status code.

### Pitfall 4: `index.html` path depends on `__file__`
**What goes wrong:** `STATIC_DIR = Path(__file__).parent / "static"` — if tests move
`web.py` or run from an unexpected cwd, the path breaks.
**How to avoid:** The file already uses `Path(__file__).parent` which is absolute and cwd-
independent. No action needed, but note when troubleshooting 500 errors on index route.

### Pitfall 5: Missing `httpx` in `pyproject.toml`
**What goes wrong:** `fastapi.testclient.TestClient` raises `RuntimeError: httpx not found`
at import time (confirmed during research). `httpx` was installed manually but is not in
`pyproject.toml` dev group yet.
**How to avoid:** First task of Phase 4 must add `httpx>=0.28` to `[dependency-groups] dev`.

## Code Examples

Verified patterns from official sources and existing codebase:

### Route testing with mocked auth
```python
# Source: FastAPI testing docs + existing test pattern in tests/test_auth.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from migrate.models import OrgInfo
from migrate.web import app

client = TestClient(app)

def test_get_orgs_sf_cli_not_found():
    from migrate.models import SFCLINotFoundError
    with patch("migrate.web.list_orgs", side_effect=SFCLINotFoundError("sf not found")):
        resp = client.get("/api/orgs")
    assert resp.status_code == 500
    assert "error" in resp.json()
```

### Migrate endpoint — production org blocked
```python
def test_migrate_blocks_production_target():
    prod_org = OrgInfo(alias="prod-org", username="prod@example.com", is_sandbox=False)
    sandbox_org = OrgInfo(alias="dev", username="dev@example.com", is_sandbox=True)
    with patch("migrate.web.list_orgs", return_value=[sandbox_org, prod_org]):
        resp = client.post("/api/migrate", json={
            "source": "dev",
            "target": "prod-org",
            "objects": ["Entitlement"],
        })
    assert resp.status_code == 400
    assert "production" in resp.json()["error"].lower()
```

### Migrate endpoint — success path
```python
def test_migrate_success():
    sb1 = OrgInfo(alias="dev", username="dev@example.com", is_sandbox=True)
    sb2 = OrgInfo(alias="uat", username="uat@example.com", is_sandbox=True)
    fake_results = [{"object": "Entitlement", "extracted": 3, "skipped": 0, "inserted": 3}]
    with patch("migrate.web.list_orgs", return_value=[sb1, sb2]), \
         patch("migrate.web.get_credentials", return_value=MagicMock()), \
         patch("migrate.web.build_client", return_value=MagicMock()), \
         patch("migrate.web.run_migration", return_value=fake_results):
        resp = client.post("/api/migrate", json={
            "source": "dev", "target": "uat", "objects": ["Entitlement"]
        })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["results"][0]["inserted"] == 3
```

### Typer serve command smoke test
```python
# Tests that `cfsuite-migrate serve` wires to web.serve() correctly
from typer.testing import CliRunner
from unittest.mock import patch
from migrate.main import app

runner = CliRunner()

def test_serve_command_calls_web_serve():
    with patch("migrate.web.serve") as mock_serve:
        result = runner.invoke(app, ["serve", "--port", "9999"])
    mock_serve.assert_called_once_with(port=9999)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Template engines (Jinja2) for server-side HTML | Single static HTML file served from disk | FastAPI era | Zero extra dependency; entire UI in one file |
| `pytest-httpserver` / `respx` for API testing | `fastapi.testclient.TestClient` | FastAPI 0.x | In-process; no port; synchronous API |
| `requests` in tests | `httpx` (required by TestClient) | Starlette dropped requests dep | Must install httpx for TestClient |

**Deprecated/outdated:**
- `requests` as test HTTP client: Starlette's TestClient now requires `httpx` — do not add
  `requests` as a dev dep for this purpose.

## Open Questions

1. **Live browser progress streaming**
   - What we know: The success criteria only require "results display per-object counts",
     which the current blocking `/api/migrate` response satisfies. No streaming is required.
   - What's unclear: Whether a future iteration will want SSE/WebSocket for live progress.
   - Recommendation: Accept the current synchronous POST pattern. Do not add SSE complexity.
     If desired later, the `on_progress` callback already exists in the pipeline.

2. **`on_progress` callback in the web endpoint**
   - What we know: `do_migrate()` calls `run_migration(source_client, target_client, objects)`
     without passing `on_progress`. This means no server-side console progress during web runs.
   - What's unclear: Whether the team wants server-side console logging during browser-triggered
     runs (would be cosmetic only — output goes to the terminal running uvicorn).
   - Recommendation: Out of scope for Phase 4 unless explicitly requested. The browser result
     display already satisfies all four success criteria.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | none (uses pyproject.toml defaults) |
| Quick run command | `uv run pytest tests/test_web.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

Phase 4 requirements are TBD (not yet formally assigned IDs). Mapping against the four
success criteria from the roadmap:

| Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-----------|----------|-----------|-------------------|-------------|
| SC-1: `serve` opens browser | `serve` command calls `web.serve()` | unit/smoke | `uv run pytest tests/test_web.py::test_serve_command_calls_web_serve -x` | Wave 0 |
| SC-2: Searchable org picklists with badges | `/api/orgs` returns `is_sandbox` field | unit | `uv run pytest tests/test_web.py::test_get_orgs_returns_org_list -x` | Wave 0 |
| SC-3: Production orgs blocked as target | `/api/migrate` returns 400 for prod target | unit | `uv run pytest tests/test_web.py::test_migrate_blocks_production_target -x` | Wave 0 |
| SC-4: Results show per-object counts | `/api/migrate` success response structure | unit | `uv run pytest tests/test_web.py::test_migrate_success_returns_counts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_web.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_web.py` — covers all four success criteria above
- [ ] `httpx>=0.28` added to `[dependency-groups] dev` in `pyproject.toml` — required for
  `fastapi.testclient.TestClient` import (confirmed missing via `uv run python` check)

## Sources

### Primary (HIGH confidence)
- Direct inspection of `migrate/web.py` — confirmed existing routes, guards, serve() impl
- Direct inspection of `migrate/static/index.html` — confirmed full UI already present
- Direct inspection of `migrate/main.py` — confirmed `serve` command already wired
- `uv run python -c "import fastapi; print(fastapi.__version__)"` — fastapi 0.135.1 installed
- `uv run python -c "import uvicorn; print(uvicorn.__version__)"` — uvicorn 0.41.0 installed
- Runtime error from `fastapi.testclient.TestClient` import — confirmed httpx missing from venv
- `uv add --dev httpx` dry-run — resolved to httpx 0.28.1 + httpcore 1.0.9

### Secondary (MEDIUM confidence)
- FastAPI testing docs pattern (TestClient + patch at call site) — consistent with existing
  project test patterns in `tests/test_auth.py`, `tests/test_pipeline.py`

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via `uv run python`, all deps already in venv
- Architecture: HIGH — web.py and index.html read directly; no inference required
- Pitfalls: HIGH — namespace patch pitfall confirmed by inspecting web.py imports;
  httpx gap confirmed by runtime error

**Research date:** 2026-03-12
**Valid until:** 2026-06-12 (FastAPI stable; low churn expected)
