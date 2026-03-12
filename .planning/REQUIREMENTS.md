# Requirements: CFSuite Sandbox Data Migration Tool

**Defined:** 2026-03-12
**Core Value:** Reliably migrate CFSuite configuration objects between orgs with all record relationships intact

## v1 Requirements

### CLI & User Experience

- [ ] **CLI-01**: User can select source org from SF CLI authenticated orgs via interactive prompt
- [ ] **CLI-02**: User can select target org from SF CLI authenticated orgs via interactive prompt
- [ ] **CLI-03**: User can add a new org by being shown the `sf org login web` command to run
- [ ] **CLI-04**: User can select individual objects to migrate or choose "all"
- [ ] **CLI-05**: User sees progress output during migration (object being processed, record counts)

### Authentication & Safety

- [ ] **AUTH-01**: Script authenticates to orgs using SF CLI access tokens (no credential storage)
- [ ] **AUTH-02**: Script blocks production orgs as migration targets (sandbox/scratch only)

### Data Migration

- [ ] **DATA-01**: Migrate Entitlement records with Account lookup resolution
- [ ] **DATA-02**: Migrate CFSuite Request Flow records with Record Type ID mapping
- [ ] **DATA-03**: Resolve Request Flow self-referential lookups (Category_Journey__c, Display_Category__c) via two-pass insert
- [ ] **DATA-04**: Migrate CFSuite Community Request (Data_Settings__c) with Record Type ID mapping
- [ ] **DATA-05**: Resolve Community Request self-referential lookup (Parent_Question__c) via two-pass insert
- [ ] **DATA-06**: Resolve Community Request → Request Flow cross-object lookup
- [ ] **DATA-07**: Migrate CFSuite Preferred Comms Config records with Record Type ID mapping
- [ ] **DATA-08**: Insert-only migration — skip records that already exist in target
- [ ] **DATA-09**: Enforce object insertion order: Entitlements → Request Flows → Community Requests → Preferred Comms

### Validation

- [ ] **VAL-01**: Post-migration record count comparison (source extracted vs target inserted + skipped)

## v2 Requirements

### Validation

- **VAL-02**: Relationship integrity verification (lookups resolve correctly in target)

### Resilience

- **RES-01**: Checkpoint/resume from failed migration point
- **RES-02**: Dry-run mode (preview what would be migrated without inserting)

### UX

- **UX-01**: Migration summary report saved to file

## Out of Scope

| Feature | Reason |
|---------|--------|
| Production org as target | Safety constraint — prevent accidental data pushes to prod |
| Upsert/update existing records | Avoids overwriting target customizations |
| Rollback capability | Complexity not justified for sandbox-to-sandbox use case |
| GUI/web interface | CLI sufficient for team |
| Full org migration | Only 4 specified CFSuite objects needed |
| Delete records in target | Insert-only to preserve target data |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | — | Pending |
| CLI-02 | — | Pending |
| CLI-03 | — | Pending |
| CLI-04 | — | Pending |
| CLI-05 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| DATA-01 | — | Pending |
| DATA-02 | — | Pending |
| DATA-03 | — | Pending |
| DATA-04 | — | Pending |
| DATA-05 | — | Pending |
| DATA-06 | — | Pending |
| DATA-07 | — | Pending |
| DATA-08 | — | Pending |
| DATA-09 | — | Pending |
| VAL-01 | — | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after initial definition*
