# CFSuite Migration Tool

Migrate CFSuite configuration data between Salesforce orgs via a browser-based wizard or CLI.

Built for Ennovative's CFSuite managed package (`cfsuite1__`) — handles RecordType remapping, self-referential lookups, cross-object references, and dynamic field discovery automatically.

## What it migrates

| Object | API Name | Notes |
|--------|----------|-------|
| Entitlement | `Entitlement` | Auto-creates a shared Account in target org from source org name |
| CFSuite Request Flow | `cfsuite1__CFSuite_Request_Flow__c` | Two-pass insert resolves self-referential lookups (`Display_Category__c`, `Category_Journey__c`) |
| CFSuite Community Request | `cfsuite1__Data_Settings__c` | Resolves cross-object `CFSuite_Request_Flow__c` lookup by Name + self-referential `Parent_Question__c` |
| CFSuite Preferred Comms Config | `cfsuite1__CFSuite_Preferred_Comms_Config__c` | Remaps RecordTypes by DeveloperName |

### How it works

1. **Dynamic field discovery** — queries both source and target org metadata to find all createable fields shared between them. No hardcoded field lists — if a field exists in both orgs and is writable, it gets migrated.

2. **Dependency-ordered migration** — objects are always migrated in the correct order: Entitlement → Request Flow → Community Request → Preferred Comms. This ensures cross-object lookups can be resolved.

3. **RecordType remapping** — source RecordType IDs are translated to target IDs by matching on `DeveloperName`. Both orgs must have the same RecordTypes deployed.

4. **Self-referential resolution** — records that reference other records of the same type (e.g. parent/child Request Flows) are inserted in two passes: first with the self-ref field nulled, then updated with the new target IDs.

5. **Cross-object resolution** — Community Requests reference Request Flows. The tool resolves these by Name matching: source RF ID → source RF Name → target RF ID.

6. **Smart field filtering** — automatically excludes:
   - Fields that don't exist in the target org (e.g. custom fields only in source)
   - Non-transferable lookups (`OwnerId`, `Unit_Manager__c` — reference User/Group)
   - Read-only system fields (`Status` on Entitlement, auto-number `Name`)

## Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **Salesforce CLI** (`sf`) — [Install guide](https://developer.salesforce.com/tools/salesforcecli)
- **CFSuite managed package** (`cfsuite1__`) installed in both source and target orgs

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/ennorish/cfsuite-migrate.git
cd cfsuite-migrate

# 2. Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 3. Install
pip install -e .

# 4. Launch the web UI
cfsuite-migrate serve
```

The browser opens automatically at `http://localhost:8765`.

## Authenticate Salesforce orgs

If you already have orgs authenticated with the Salesforce CLI, skip this step — the tool picks them up automatically.

```bash
# Log in to each org (opens browser for OAuth)
sf org login web --alias my_source_org
sf org login web --alias my_target_org

# Verify they show up
sf org list
```

## Usage

### Web UI (recommended)

```bash
cfsuite-migrate serve
```

The wizard has 3 steps:

1. **Select orgs** — pick source (left) and target (right) from dropdown lists. The username is shown below each selection for confirmation. Production orgs are blocked as targets.

2. **Select objects** — check which objects to migrate. Objects are listed in dependency order.

3. **Review & run** — confirms your selections, then click "Run Migration". Progress streams live — each object shows a spinner while running and a green checkmark (or red error) when done.

### CLI

```bash
# Interactive mode (prompts for org and object selection)
cfsuite-migrate migrate

# Non-interactive (specify orgs directly)
cfsuite-migrate migrate --source my_source_org --target my_target_org
```

### Custom port

```bash
cfsuite-migrate serve --port 9000
```

## Safety guardrails

- **Production guard** — the tool rejects any production org as a migration target. Only sandbox and scratch orgs are allowed. Detection is based on instance URL patterns (`--` for sandboxes, `.scratch.` for scratch orgs).

- **Idempotent** — records already in the target (matched by Name) are skipped. You can safely run the migration multiple times.

- **No destructive operations** — the tool only creates records, never updates or deletes existing ones (except for the two-pass self-ref update on newly-inserted records).

- **No secrets stored** — authentication is handled entirely by the Salesforce CLI. The tool reads session tokens at runtime and never persists them.

## API usage

The tool uses the Salesforce REST API (one API call per record insert). For reference:

| Records | Approx. API calls | Time |
|---------|-------------------|------|
| 50 | ~50-60 | ~30s |
| 500 | ~500-600 | ~5min |
| 1000 | ~1000-1200 | ~10min |

Salesforce sandboxes typically allow 100,000+ API calls per 24 hours, so this is well within limits for typical CFSuite configurations.

## Project structure

```
migrate/
  auth.py          # SF CLI org listing, credential retrieval, production guard
  etl.py           # Extract, dedup, RecordType remap, two-pass insert helpers
  sf_api.py        # Salesforce API wrapper (query, insert, field discovery)
  pipeline.py      # Migration orchestrator (dependency ordering, progress callbacks)
  web.py           # FastAPI web server + SSE streaming
  main.py          # Typer CLI entry point
  models.py        # Data classes (Credentials, OrgInfo, errors)
  prompts.py       # Interactive CLI prompts (questionary)
  static/
    index.html     # Single-page web UI wizard
  objects/
    entitlement.py         # Entitlement migrator
    request_flow.py        # Request Flow migrator (two-pass self-ref)
    community_request.py   # Community Request migrator (cross-ref + self-ref)
    preferred_comms.py     # Preferred Comms migrator
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `sf CLI not found` | Salesforce CLI not installed or not on PATH | Install from [developer.salesforce.com](https://developer.salesforce.com/tools/salesforcecli) |
| `Could not retrieve credentials` | Org not authenticated or session expired | Run `sf org login web --alias <org>` |
| `RecordType DeveloperName not found in target` | Target org is missing a RecordType that exists in source | Deploy the missing RecordType metadata to the target org |
| `REQUIRED_FIELD_MISSING` | Target org has a required field not populated in source | Check the field in question — it may need a default value in the target org |
| `INVALID_FIELD` | Field exists in source but not target | Should not happen with dynamic field discovery — check package versions match |
| Migration appears stuck | Large record set being inserted one at a time | Normal — check server logs (`/tmp/migrate-web.log`) for progress |
| `Target is a production org` | Production guard triggered | Use a sandbox or scratch org as target |
