---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 02-core-etl-02-01-PLAN.md
last_updated: "2026-03-12T04:10:19Z"
last_activity: 2026-03-12 — Completed 02-01 core ETL engine (sf_api + etl modules)
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Reliably migrate CFSuite configuration objects between orgs with all record relationships intact
**Current focus:** Phase 2 — Core ETL

## Current Position

Phase: 2 of 3 (Core ETL)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-03-12 — Completed 02-01 core ETL engine (sf_api + etl modules)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P01 | 18 | 2 tasks | 8 files |
| Phase 01-foundation P02 | 2 | 2 tasks | 3 files |
| Phase 02-core-etl P01 | 20 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Insert-only (no upsert/delete): Avoids overwriting target customizations
- SF CLI for auth: Team already has orgs authenticated, no credential management needed
- Map Record Types by DeveloperName: IDs differ per org but names are consistent in managed package
- Migrate Entitlements first: Request Flows reference Entitlements by name, need them present in target
- [Phase 01-foundation]: Used pytest-subprocess callback lambda for FileNotFoundError test — FakeProcess.raise_exception() does not exist in v1.5.3
- [Phase 01-foundation]: uv manages Python 3.11 runtime via .python-version — consistent interpreter across team despite system Python 3.14
- [Phase 01-foundation]: Import migrate.auth as module (not from-import) so mock patches intercept calls at runtime
- [Phase 01-foundation]: select_target_org exits with code 1 on ProductionOrgError — distinguishes user error from clean no-orgs exit
- [Phase 02-core-etl]: getattr(client.bulk, sobject) for dynamic bulk SObject access — matches simple-salesforce attribute-access design
- [Phase 02-core-etl]: two_pass_insert uses single-record update for pass 2 (not a second bulk call) — children are a small subset
- [Phase 02-core-etl]: remap_record_types mutates records in place, returns None — consistent ETL mutation pattern
- [Phase 02-core-etl]: find_existing_keys short-circuits on empty key_values — avoids invalid SOQL with empty IN clause

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: Self-referential field names on CFSuite Request Flow (Category_Journey__c, Display_Category__c) and Community Request (Parent_Question__c) should be verified via `sf sobject describe` before Phase 2 implementation
- Phase 2: Trigger bypass mechanism for SupportContractTriggerHandler needs to be spec'd against actual dest org trigger code before any production-adjacent migration run

## Session Continuity

Last session: 2026-03-12T04:10:19Z
Stopped at: Completed 02-core-etl-02-01-PLAN.md
Resume file: None
