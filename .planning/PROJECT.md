# CFSuite Sandbox Data Migration Tool

## What This Is

A Python CLI tool that migrates CFSuite configuration data between Salesforce orgs. It guides users through selecting source/target orgs and which objects to migrate, then handles the data transfer while preserving all record relationships. Designed for use by the Ennovative team via GitHub.

## Core Value

Reliably migrate CFSuite configuration objects between orgs with all record relationships intact — so teams don't have to manually recreate complex request flow hierarchies in each sandbox.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Interactive CLI that prompts for source org, target org, and objects to migrate
- [ ] Authenticate via SF CLI (sf org) — users select from their authenticated orgs
- [ ] Block production orgs as migration targets (sandboxes/scratch orgs only)
- [ ] Migrate CFSuite Request Flow (`cfsuite1__CFSuite_Request_Flow__c`) — 3 record types (Case Assignment, Category Journey, Display Category), self-referential lookups (Category_Journey__c, Display_Category__c), Account lookup
- [ ] Migrate CFSuite Community Request (`cfsuite1__Data_Settings__c`) — 3 record types (Guided Request Process, Question, Response), self-referential Parent_Question__c lookup, lookup to Request Flow
- [ ] Migrate Entitlement (standard object) — linked to Account and SLA Process by name
- [ ] Migrate CFSuite Preferred Comms Config (`cfsuite1__CFSuite_Preferred_Comms_Config__c`) — 2 record types (Customer Notification, Emergency Notification)
- [ ] Preserve all record relationships across objects (Request Flow → Community Request, Request Flow self-references, Community Request self-references)
- [ ] Map Record Type IDs by DeveloperName (IDs differ between orgs, names are same since managed package)
- [ ] Insert-only migration — skip records that already exist, don't update or delete
- [ ] Post-migration validation — verify record counts and relationship integrity
- [ ] Allow user to select individual objects or "all" for migration
- [ ] Usable by team via GitHub clone + simple setup

### Out of Scope

- Production orgs as targets — safety constraint to prevent accidental data pushes to prod
- Full org migration — only the 4 specified CFSuite objects
- Upsert/update of existing records — insert-only to avoid overwriting customizations
- Rollback capability — out of scope for v1
- GUI/web interface — CLI is sufficient for the team

## Context

- These are CFSuite managed package objects used across Ennovative's council clients (Bayside, Melville, Surf Coast, etc.)
- Record volumes are manageable: ~2,300 Request Flows, ~750 Community Requests, ~200 Entitlements, ~22 Preferred Comms Configs
- Request Flow has complex self-referential structure: Display Category → Category Journey → Case Assignment chain
- Community Request (Data_Settings__c) has parent-child self-reference for guided request processes (Process → Question → Response hierarchy)
- Request Flow references Entitlements by name (`Entitlement_Process_Name__c` text field), not lookup — so Entitlements should be migrated first or names matched
- Record Type IDs differ between orgs but DeveloperName is consistent (managed package)
- Team already uses SF CLI with authenticated orgs

## Constraints

- **Tech stack**: Python — team preference
- **Auth**: SF CLI only — no storing credentials, leverage existing `sf org` auth
- **Safety**: Never allow production org as target
- **Distribution**: GitHub repo — team clones and runs locally
- **Data integrity**: All self-referential and cross-object lookups must resolve correctly in target

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Insert-only (no upsert/delete) | Avoids overwriting target customizations | — Pending |
| SF CLI for auth | Team already has orgs authenticated, no credential management needed | — Pending |
| Map Record Types by DeveloperName | IDs differ per org but names are consistent in managed package | — Pending |
| Migrate Entitlements first | Request Flows reference Entitlements by name, need them present in target | — Pending |

---
*Last updated: 2026-03-12 after initialization*
