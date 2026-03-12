# Feature Research

**Domain:** Salesforce org-to-org configuration data migration CLI tool
**Researched:** 2026-03-12
**Confidence:** HIGH (core features derived from project requirements + MEDIUM for ecosystem landscape from WebSearch/official sources)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Org selection from authenticated orgs | Users work with `sf org` daily — they expect to pick from a named list, not paste usernames | LOW | Query `sf org list --json`, present as numbered menu |
| Production org guard | Every Salesforce migration tool blocks prod-as-target. Missing this is a safety dealbreaker | LOW | Check `IsSandbox` or org type via `sf org display --json`; hard-abort if prod |
| Self-referential lookup resolution | Request Flow and Community Request both have self-refs; a tool that can't handle this is useless for the domain | HIGH | Two-pass insert: insert null for self-ref first pass, update with resolved IDs second pass |
| Cross-object relationship preservation | Request Flow → Community Request lookup must resolve correctly; records arriving with broken lookups are worse than no records | HIGH | Build ID-mapping registry: source ID → target ID per object, resolve before inserting dependents |
| Record Type ID mapping by DeveloperName | IDs differ between every Salesforce org. Using source IDs directly breaks record types silently | MEDIUM | Query `RecordType` by `DeveloperName` in target org at migration start; build lookup table |
| Insert-only (skip existing records) | Users re-run migrations; overwriting customized target data would break trust immediately | MEDIUM | Query target for existing records by external key before inserting; skip matches |
| Post-migration record count validation | "Did it work?" is the first question after every run. A tool with no answer is not trustworthy | LOW | Count source vs target per object; report mismatches clearly |
| Object-level selection (individual or all) | Users won't always want to migrate all 4 objects; order matters (Entitlements first) | LOW | Interactive checkbox prompt or `--objects` flag |
| Clear error output with actionable messages | API failures, missing fields, and auth errors must surface as readable messages, not raw stack traces | MEDIUM | Catch API errors, translate to human messages, log full detail to file |
| Ordered migration (respects dependencies) | Entitlements before Request Flows; Request Flows before Community Requests. Wrong order = broken lookups | LOW | Hard-coded dependency order in execution plan |

### Differentiators (Competitive Advantage)

Features that set the product apart within the CFSuite migration context.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| CFSuite-specific relationship graph | Generic tools require config; this tool knows the exact 4-object model and handles it correctly by default | MEDIUM | Embed the object dependency graph (Entitlement → RequestFlow → CommunityRequest → PreferredComms) as code, not config |
| Dry-run / preview mode | Shows what would be migrated without touching the target — lets users verify before committing | MEDIUM | Query source counts and show dependency chain; flag any resolution issues without inserting |
| Relationship integrity check (post-migration) | Count validation is table stakes; verifying that lookup fields actually point to valid target records is the next level | MEDIUM | After insert, spot-check lookup fields on a sample or all records using SOQL; report broken references |
| Migration run summary report | Timestamped log of what was migrated, skipped, and failed — essential for team handoffs | LOW | Write structured JSON or plain-text report to `.migration_logs/` after each run |
| Re-runnable / idempotent behavior | Running twice produces same result as running once — safe for partial failures and re-runs after fixes | MEDIUM | Depends on skip-existing logic; requires stable external key strategy |
| Named org aliases in prompts | Show org aliases (e.g. "AdelaideDemo") not raw usernames — matches how the team thinks about their orgs | LOW | Use `alias` field from `sf org list` output |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in this context.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Upsert / update existing records | "Why not keep target data in sync with source?" | Overwrites target customizations silently. Teams often have environment-specific tweaks. Source of truth ambiguity destroys trust | Insert-only with clear skip logging; explicit "force update" flag if ever needed in v2 |
| Rollback / undo | "What if something goes wrong?" | Salesforce has no native transaction rollback across bulk inserts. A fake rollback that deletes inserted records is dangerous (might delete records the user already linked to other data). False safety promise is worse than no promise | Pre-migration snapshot guidance (Data Loader export to CSV); document manual rollback steps in README |
| Production org as target | "I need to push to prod directly" | Safety constraint exists for a reason; accidental prod writes cause real incidents | Require sandbox/scratch target; document manual prod-push workflow separately if truly needed |
| GUI / web interface | "Easier for non-technical users" | The team is technical; a GUI adds enormous build scope with no value for this audience | CLI with clear prompts and color-coded output is sufficient |
| Generic "any Salesforce object" migration | "Could we make it work for other objects?" | Generalizing the relationship graph makes the tool exponentially more complex to maintain and test. The CFSuite model is the value | Hard-code the 4 CFSuite objects; document how to extend if needed in a future milestone |
| Automatic retry loops on API failure | "Just retry until it works" | Masks underlying data problems. A record failing to insert has a reason — hiding it leads to partial migrations that look successful | Fail fast per record, log the failure with full context, let the user decide to re-run after fixing root cause |
| Storing credentials / token caching | "Faster without re-auth" | Security risk. Team uses `sf org` which already manages auth tokens safely | Rely entirely on `sf org` auth state; never read or store access tokens in the tool |

---

## Feature Dependencies

```
[Org Authentication via sf CLI]
    └──required by──> [Org Selection Prompt]
                          └──required by──> [Production Org Guard]
                          └──required by──> [Source/Target Queries]

[Source/Target Queries]
    └──required by──> [Record Type ID Mapping]
    └──required by──> [Insert-Only Skip Logic]
    └──required by──> [Object Selection]

[Record Type ID Mapping]
    └──required by──> [Any Insert Operation]

[Object Selection + Ordered Migration]
    └──required by──> [Cross-Object Relationship Preservation]
                          └──required by──> [Self-Referential Lookup Resolution]

[Self-Referential Lookup Resolution]
    └──required by──> [Relationship Integrity Check (post-migration)]

[Any Insert Operation]
    └──required by──> [Post-Migration Record Count Validation]
    └──required by──> [Migration Run Summary Report]

[Insert-Only Skip Logic] ──enables──> [Re-runnable / Idempotent Behavior]

[Dry-Run Mode] ──conflicts with──> [Any actual insert]; must be a separate execution path
```

### Dependency Notes

- **Record Type ID Mapping required before any insert:** Without this, all inserts either fail or silently assign wrong record types. Must be resolved at startup.
- **Ordered migration required before relationship preservation:** Entitlements must exist in target before Request Flow inserts reference them by name. Request Flows must exist before Community Request inserts resolve their lookup.
- **Self-referential resolution requires two-pass insert:** First pass inserts records with self-ref fields set to null. Second pass updates those fields using the ID map built during first pass. Cannot skip either pass.
- **Insert-only skip logic enables idempotency:** Without checking for existing records, re-running creates duplicates and breaks the relationship graph.
- **Dry-run conflicts with actual inserts:** These must be mutually exclusive execution paths (a `--dry-run` flag that completely bypasses all write operations).

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what the team needs to use this tool reliably.

- [ ] Org selection from `sf org list` (source + target) — users cannot use the tool without this
- [ ] Production org guard — non-negotiable safety requirement
- [ ] Record Type ID mapping by DeveloperName — every insert depends on this being correct
- [ ] Object selection (individual or all) with hard-coded dependency order — users need control
- [ ] Ordered migration execution (Entitlements → Request Flows → Community Requests → Preferred Comms) — wrong order breaks foreign keys
- [ ] Cross-object relationship preservation via ID-mapping registry — core value of the tool
- [ ] Self-referential lookup resolution (two-pass insert for Request Flow and Community Request) — without this, hierarchies arrive broken
- [ ] Insert-only with skip logic — prevents overwriting target customizations on re-runs
- [ ] Post-migration record count validation — minimum "did it work" signal
- [ ] Clear error output with actionable messages — migration failures must be debuggable

### Add After Validation (v1.x)

Features to add once core migration is confirmed working.

- [ ] Dry-run / preview mode — add when team wants to review before running; depends on core queries working reliably
- [ ] Relationship integrity check (spot-check lookups post-migration) — add when count validation alone proves insufficient
- [ ] Migration run summary report written to file — add when team is running migrations frequently and needs audit trail
- [ ] Named org aliases in prompts — polish item; add when basic prompts are validated

### Future Consideration (v2+)

Features to defer until v1 is proven in real migrations.

- [ ] Support for additional CFSuite objects — defer until the 4 core objects are stable
- [ ] Parallelized batch inserts for large volumes — current volumes (~2,300 Request Flows) don't require this; revisit at 10x scale
- [ ] Force-update mode (upsert existing records) — explicit opt-in to override insert-only; defer until a real use case emerges

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Org selection from sf org list | HIGH | LOW | P1 |
| Production org guard | HIGH | LOW | P1 |
| Record Type ID mapping | HIGH | MEDIUM | P1 |
| Ordered migration execution | HIGH | LOW | P1 |
| Cross-object relationship preservation | HIGH | HIGH | P1 |
| Self-referential two-pass insert | HIGH | HIGH | P1 |
| Insert-only skip logic | HIGH | MEDIUM | P1 |
| Post-migration record count validation | HIGH | LOW | P1 |
| Clear error output | MEDIUM | MEDIUM | P1 |
| Dry-run preview mode | MEDIUM | MEDIUM | P2 |
| Relationship integrity check | MEDIUM | MEDIUM | P2 |
| Migration run summary report | MEDIUM | LOW | P2 |
| Named org aliases in prompts | LOW | LOW | P2 |
| Parallelized batch inserts | LOW | HIGH | P3 |
| Force-update mode | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

The relevant comparison is against tools the team might otherwise use for this migration.

| Feature | Salesforce CLI (data tree) | SFDMU | CFSuite Tool (this project) |
|---------|--------------------------|-------|----------------------------|
| Self-referential lookup handling | Broken — known open issue (#248) | Supported (Account.ParentId style) | Custom two-pass insert for CFSuite model |
| Record type ID mapping | Manual pre-processing required | Supported via external ID config | Automatic by DeveloperName at startup |
| Insert-only (skip existing) | Not native | Supported via upsert with external IDs | Native — core design principle |
| CFSuite 4-object dependency order | Manual — user must know order | Manual — user must configure export.json | Automatic — hard-coded in tool |
| SF CLI auth integration | Native | Native (sf plugin) | Native — delegates entirely to sf org |
| Production org guard | Not present | Not present by default | Hard-coded safety block |
| Python / no Node dependency | No | No (Node.js required) | Yes — team preference, no extra runtime |
| Post-migration validation | None built-in | Partial (error logs) | Record counts + relationship integrity check |

**Key insight:** SFDMU is the most capable generic tool but requires Node.js, a configuration file per migration, and manual knowledge of the CFSuite object graph. The native CLI tree import is actively broken for self-referential objects. This tool's value is that it knows the CFSuite model by design and runs in Python with no extra runtime dependencies.

---

## Sources

- [SFDMU GitHub — forcedotcom/SFDX-Data-Move-Utility](https://github.com/forcedotcom/SFDX-Data-Move-Utility) — key features including self-referential handling (MEDIUM confidence — GitHub README)
- [Salesforce CLI self-referencing lookup issue #248](https://github.com/forcedotcom/cli/issues/248) — confirmed native CLI cannot handle self-referential migrations (HIGH confidence — official Salesforce GitHub issue)
- [End Point Dev — Salesforce data migration promoting from sandbox to production](https://www.endpointdev.com/blog/2021/11/salesforce-data-migration/) — pattern for dependency-aware insert ordering (MEDIUM confidence)
- [Salesforce Data Migration Best Practices — softwebsolutions](https://www.softwebsolutions.com/resources/salesforce-data-migration-best-practices/) — external ID strategy, record type mapping practices (MEDIUM confidence)
- [Salesforce Org-to-Org Migration Guide — dataimporter.io 2025](https://www.dataimporter.io/blog/how-to-migrate-data-from-one-salesforce-org-to-another) — general org-to-org patterns (MEDIUM confidence)
- [Configuration data migration in Salesforce — Aneesh Bhat, Medium](https://medium.com/swlh/configuration-data-migration-in-salesforce-ce3e2041bc25) — configuration vs transactional migration distinction (MEDIUM confidence)
- [Metazoa — Migrate Related Sets of Data Between Salesforce Orgs](https://www.metazoa.com/snapshot-best-practices-dataset-migration/) — relationship key preservation patterns (MEDIUM confidence)

---

*Feature research for: Salesforce CFSuite configuration data migration CLI tool*
*Researched: 2026-03-12*
