# Roadmap: CFSuite Sandbox Data Migration Tool

## Overview

Three phases deliver a working CLI migration tool. Phase 1 establishes the project scaffold, SF CLI integration, interactive org selection, and production org safety guard — everything needed to authenticate and select a migration target. Phase 2 builds the full ETL pipeline: extraction from source, RecordType ID mapping, dependency-ordered insertion, insert-only skip logic, and the two-pass strategy for self-referential objects. Phase 3 adds post-migration validation and progress output, completing the tool to a state the team can rely on in production workflows.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - CLI scaffold, SF CLI auth, interactive org selection, production org safety guard (completed 2026-03-12)
- [ ] **Phase 2: Core ETL** - Full migration pipeline from extraction through two-pass self-referential insert
- [ ] **Phase 3: Validation and Polish** - Post-migration count validation and real-time progress output

## Phase Details

### Phase 1: Foundation
**Goal**: Users can run the CLI, select source and target orgs from their SF CLI authenticated list, choose which objects to migrate, and be blocked from targeting a production org
**Depends on**: Nothing (first phase)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, AUTH-01, AUTH-02
**Success Criteria** (what must be TRUE):
  1. User runs the CLI and sees an interactive prompt listing their SF CLI authenticated orgs by name/alias for source selection
  2. User selects a target org and if it is a production org, the CLI exits with a clear error before any migration begins
  3. User can select individual objects to migrate or choose "all" from a menu
  4. User is shown the `sf org login web` command to add a new org when their desired org is not in the list
  5. All authentication uses SF CLI access tokens — no credentials are stored by the script
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffold (pyproject.toml, uv) and SF CLI auth layer (list_orgs, get_credentials, production guard)
- [ ] 01-02-PLAN.md — Interactive CLI prompts (org selection, object selection) wired to Typer entry point

### Phase 2: Core ETL
**Goal**: All four CFSuite objects migrate from source to target with record relationships intact, self-referential hierarchies preserved, and existing records in the target skipped
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, DATA-09
**Success Criteria** (what must be TRUE):
  1. Entitlements migrate before Request Flows, Request Flows before Community Requests, Community Requests before Preferred Comms Config — cross-object lookups resolve correctly
  2. Request Flow self-referential hierarchy (Display Category → Category Journey → Case Assignment) arrives intact in the target org
  3. Community Request parent-child hierarchy (Process → Question → Response) arrives intact in the target org with Parent_Question__c lookups correctly resolved
  4. Records already present in the target org are skipped — re-running the migration does not duplicate records
  5. Record Type IDs are mapped by DeveloperName — source IDs never reach the target org payload
**Plans**: TBD

### Phase 3: Validation and Polish
**Goal**: Users receive confirmation that migration succeeded with record counts and real-time progress during the migration run
**Depends on**: Phase 2
**Requirements**: CLI-05, VAL-01
**Success Criteria** (what must be TRUE):
  1. During migration, user sees live output showing which object is being processed and how many records have been inserted
  2. After migration completes, user sees a per-object record count comparison (source extracted vs target inserted + skipped) that confirms no records were silently lost
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete   | 2026-03-12 |
| 2. Core ETL | 0/TBD | Not started | - |
| 3. Validation and Polish | 0/TBD | Not started | - |
