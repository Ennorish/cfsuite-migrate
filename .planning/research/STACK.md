# Stack Research

**Domain:** Python CLI tool for Salesforce data migration between orgs
**Researched:** 2026-03-12
**Confidence:** HIGH (core choices) / MEDIUM (supporting libraries)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.11 | Runtime | 3.11+ gives better error messages and performance. 3.9 is simple-salesforce's minimum, but 3.11 is the oldest actively maintained version as of 2026. Pin to 3.11+ to avoid CI surprises. |
| Typer | 0.24.x | CLI framework + argument parsing | Built on Click but uses Python type hints — eliminates boilerplate, auto-generates help text, and gives IDE autocompletion. Better DX than raw Click for a project this size. Click has 38.7% market share but Typer is the modern default for greenfield tools. |
| simple-salesforce | 1.12.9 | Salesforce REST API client | The standard Python library for Salesforce REST API. Supports SOQL queries, insert/update/delete, bulk operations, and describe calls. Actively maintained (Aug 2024 release). No credential storage — uses session tokens, compatible with SF CLI auth flow. |
| questionary | 2.1.1 | Interactive terminal prompts | Provides checkbox multi-select, dropdown lists, and confirmation prompts with arrow-key navigation. Backed by prompt_toolkit 3. Better UX than raw `input()` for org selection and object selection menus. |
| rich | 14.x | Terminal output formatting | Progress bars, tables, colored status messages. Critical for showing migration progress on 2,300+ record migrations without flooding stdout. Typer's built-in progressbar is sufficient for simple cases; rich.Progress gives per-object granularity. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| toposort | 1.10+ | Topological sort for object dependency resolution | Use for computing the correct insert order across objects. Request Flows self-reference across 3 record types; Community Requests self-reference across Process/Question/Response. Standard library `graphlib.TopologicalSorter` (Python 3.9+) is also viable — use stdlib to avoid a dependency. |
| pytest | 8.x | Test runner | Standard Python test framework. Use for unit tests on the dependency resolution logic, ID remapping, and org safety checks. These are the highest-risk correctness paths. |
| pytest-subprocess | 1.5.x | Mock SF CLI subprocess calls | Fakes `subprocess.Popen()` calls so tests don't need a real SF CLI or authenticated orgs. Essential for testing the `sf org list --json` parsing and auth detection without live orgs. |
| pydantic | 2.x | Data validation for config and record models | Optional but useful if you want to validate the structure of SF CLI JSON output or build typed record models. Only add if the untyped dict approach becomes unwieldy — the project may not need it. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Dependency and virtual environment management | 10-100x faster than pip. Creates `pyproject.toml`-based projects natively. `uv sync` replaces `pip install -r requirements.txt`. Strongly preferred for new Python projects in 2025+. Run `uv init` to scaffold. |
| ruff | Linting and formatting | Replaces flake8 + isort + black in a single Rust-based tool. Negligible runtime cost. Include in pre-commit. Configure in `pyproject.toml [tool.ruff]`. |
| pyproject.toml | Project metadata and dependency declaration | The 2025 standard. No `setup.py` or `requirements.txt`. All deps declared under `[project.dependencies]`. CLI entry point declared under `[project.scripts]`. |

## Installation

```bash
# Bootstrap with uv (install uv first: https://docs.astral.sh/uv/getting-started/installation/)
uv init cfsuite-migrate
cd cfsuite-migrate

# Core runtime dependencies
uv add typer simple-salesforce questionary rich

# Dev/test dependencies
uv add --dev pytest pytest-subprocess ruff

# Run the tool
uv run python -m cfsuite_migrate
```

The team installs by cloning and running `uv sync`, which reads `pyproject.toml` and recreates the exact environment. No global pip installs required. Python version is pinned via `.python-version` file that `uv` manages.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer 0.24.x | Click 8.x | When you need advanced plugin systems or are adding to an existing Click app. Click is more battle-tested for complex multi-command CLIs. |
| Typer 0.24.x | argparse (stdlib) | When zero dependencies is a hard requirement. argparse requires significantly more boilerplate for the multi-option prompts this tool needs. |
| questionary | InquirerPy | When you need fuzzy-search filtering in prompts. InquirerPy has more customization but higher complexity. questionary covers this tool's needs with less overhead. |
| simple-salesforce | direct `requests` + Salesforce REST | When simple-salesforce's abstraction is a poor fit. For this project simple-salesforce covers everything: SOQL, insert, describe, and bulk. No reason to roll your own. |
| rich | tqdm | tqdm is fine for single progress bars. rich.Progress handles multiple simultaneous object-level bars (e.g., Request Flow: 1200/2300, Community Request: 400/750) which this migration will need. |
| uv | pip + venv | When the team can't install uv (restricted corporate environments). Fall back to `requirements.txt` + `python -m venv`. The runtime code is identical. |
| graphlib.TopologicalSorter (stdlib) | toposort PyPI package | stdlib is sufficient for this tool's DAG resolution. Use stdlib to keep dependencies minimal — only add `toposort` package if the stdlib API is awkward for the graph structure chosen. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyInquirer | Unmaintained since 2019, depends on deprecated `prompt_toolkit` 1.x, broken on Python 3.10+. Many tutorials reference it but it is abandonware. | questionary or InquirerPy |
| Beatbox / apex-tooling-salesforce | Old SOAP-based Python Salesforce clients, effectively unmaintained. REST API is the current standard. | simple-salesforce |
| `sfdx` CLI commands | The legacy `sfdx` CLI has been superseded by `sf` (Salesforce CLI v2). All commands have moved to `sf org`, `sf data`, etc. Using `sfdx` will break on orgs that only have the new CLI installed. | `sf` CLI with `--json` flag |
| Storing SF credentials in config files | Hard security constraint in PROJECT.md. Never cache access tokens or passwords. | Invoke `sf org list --json` at runtime to read already-authenticated orgs from SF CLI's own credential store. |
| SQLite or local DB for ID mapping | Adds a dependency and file management complexity. The ID remapping (source ID → target ID) can be held in memory as a dict for the record volumes in scope (~3,000 records total). | In-memory dict mapping |
| Bulk API 2.0 directly | Bulk API is warranted at >2,000 records per object. This migration has ~2,300 Request Flows (borderline) but the insert is a one-time operation, not repeated. simple-salesforce's standard `bulk` interface handles this cleanly without building raw HTTP batch jobs. | `sf.bulk.Object.insert()` via simple-salesforce's bulk interface if REST API limits are hit |

## Stack Patterns by Variant

**If record volumes exceed REST API single-call limits (200 records/call):**
- Use simple-salesforce's `bulk` interface: `sf.bulk.cfsuite1__CFSuite_Request_Flow__c.insert(records)`
- This wraps Bulk API 2.0 automatically, handles chunking and async polling
- The standard REST path via `sf.SObject.insert()` handles batches of 200; for 2,300 records you will hit this and should prefer bulk from the start

**If the team wants a one-command install without Python knowledge:**
- Package as a standalone binary using PyInstaller or `uv tool install`
- `uv tool install git+https://github.com/ennovative/cfsuite-migrate` installs a global CLI command
- This is out of scope for v1 but the pyproject.toml structure set up now supports it without refactoring

**If SF CLI is not installed on a machine:**
- Detect by running `sf --version` and catching `FileNotFoundError`
- Fail fast with a clear error message pointing to the SF CLI install page
- Do NOT attempt to handle authentication without SF CLI — that violates the auth constraint

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| typer 0.24.x | Python >=3.8, click >=8.0 | click is a transitive dependency; typer manages it. |
| simple-salesforce 1.12.9 | Python >=3.9 | Confirmed on PyPI. Works with Salesforce API v55.0+. |
| questionary 2.1.1 | Python >=3.9, prompt_toolkit >=3.0 | prompt_toolkit 3.x is required; do not pin prompt_toolkit manually to avoid conflicts with typer/rich. |
| rich 14.x | Python >=3.8 | No known conflicts with other stack members. |
| pytest-subprocess 1.5.x | pytest >=7.0 | Hooks on `subprocess.Popen`; compatible with how simple-salesforce uses requests (not subprocess). |

## Sources

- PyPI: https://pypi.org/project/typer/ — version 0.24.1 confirmed (released Feb 21, 2026)
- PyPI: https://pypi.org/project/simple-salesforce/ — version 1.12.9 confirmed (released Aug 23, 2024); docs at https://simple-salesforce.readthedocs.io/
- PyPI: https://pypi.org/project/questionary/ — version 2.1.1 confirmed (released Aug 28, 2025)
- Rich docs: https://rich.readthedocs.io/en/stable/progress.html — version 14.1.0 confirmed
- pytest-subprocess: https://pypi.org/project/pytest-subprocess/ — WebSearch confirmed, MEDIUM confidence on exact version
- uv recommendation: https://realpython.com/uv-vs-pip/ and https://blog.appsignal.com/2025/09/24/switching-from-pip-to-uv-in-python-a-comprehensive-guide.html — 2025 standard recommendation
- Salesforce Bulk API 2.0 threshold: https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/asynch_api_intro.htm — >2,000 records threshold confirmed HIGH confidence
- SF CLI JSON support: https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_dev_cli_json_support.htm — `--json` flag confirmed
- Topological sort for Salesforce: https://medium.com/@justusvandenberg/programmatically-determine-the-object-loading-order-for-salesforce-data-migrations-using-apex-1f65841531fb — MEDIUM confidence (Apex but pattern applies to Python)

---
*Stack research for: CFSuite Sandbox Data Migration Tool (Python CLI)*
*Researched: 2026-03-12*
