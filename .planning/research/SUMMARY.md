# Project Research Summary

**Project:** CFSuite Sandbox Data Migration Tool
**Domain:** Python CLI — Salesforce org-to-org configuration data migration
**Researched:** 2026-03-12
**Confidence:** HIGH

## Executive Summary

This project is a purpose-built Python CLI tool for migrating CFSuite managed package configuration data between Salesforce orgs (sandbox-to-sandbox). The 4-object migration scope — Entitlements, CFSuite Request Flow (~2,339 records), Community Request (~751 records), and Preferred Comms Config — has a specific dependency graph and two self-referential lookup structures that make generic migration tools like Salesforce CLI's `data tree` or SFDMU inadequate without significant manual configuration. The native SF CLI has a confirmed open issue with self-referential lookups. The recommended approach is a custom ETL tool that embeds the CFSuite object graph as code, not configuration, and delegates authentication entirely to the SF CLI.

The recommended stack is Python 3.11+ with Typer for CLI, simple-salesforce for Salesforce REST/Bulk API access, questionary for interactive prompts, and rich for terminal output. The architecture follows a clean ETL pattern: Auth Layer → Extractor → Transformer → Loader → Validator, with an ID Map store and Phase State file providing resume capability. The critical structural decision is the two-pass insert strategy for self-referential objects: pass 1 inserts all records with self-ref fields nulled, pass 2 bulk-updates those fields using the ID map built in pass 1. This pattern must be designed from the start, not bolted on.

The top risks are (1) self-referential lookup handling, which cannot be done in a single API pass and is actively broken in the native CLI, (2) Record Type ID org-specificity — source IDs must never reach the destination org payload, and (3) trigger and validation rule interference from `SupportContractTriggerHandler` which fires on migrated records. All three risks are well-understood and have proven mitigations that must be implemented in the core architecture, not as afterthoughts.

## Key Findings

### Recommended Stack

The stack is lean and well-matched to a ~3,300-record one-time migration CLI. Typer 0.24.x provides type-hint-driven argument parsing with auto-generated help text. simple-salesforce 1.12.9 covers SOQL extraction, Bulk API 2.0 inserts, and describe calls in a single library with active maintenance. questionary 2.1.1 provides the interactive org-selection and object-selection prompts without the maintenance risk of PyInquirer (abandonware since 2019). rich 14.x handles multi-object progress bars and structured output. uv replaces pip for dependency management and is the 2025 standard for new Python projects.

The Python standard library `graphlib.TopologicalSorter` is sufficient for dependency ordering — no external `toposort` package required. The ID map fits in memory at this record volume; no SQLite is needed. Bulk API 2.0 is preferred over REST single-record inserts even at this scale because it handles rate limits gracefully and returns per-record success/failure in its response.

**Core technologies:**
- Python 3.11+: runtime — oldest actively maintained version, better error messages
- Typer 0.24.x: CLI framework — type-hint-driven, eliminates boilerplate, auto-generates help
- simple-salesforce 1.12.9: Salesforce client — covers REST, Bulk API 2.0, and SOQL in one library
- questionary 2.1.1: interactive prompts — checkbox, dropdown, arrow-key navigation; backed by prompt_toolkit 3
- rich 14.x: terminal output — per-object progress bars essential for 2,300+ record migrations
- uv: dependency management — 10-100x faster than pip, pyproject.toml native

### Expected Features

The MVP requires all 10 table-stakes features. The most complex are self-referential lookup resolution (two-pass insert) and cross-object relationship preservation via ID-mapping registry — these are HIGH implementation complexity but non-negotiable for data integrity. Production org guard and insert-only skip logic are LOW complexity safety requirements. The differentiating features (dry-run preview, relationship integrity check, migration run report) are clean additions after the core migration is validated.

**Must have (table stakes):**
- Org selection from `sf org list` — users expect a named list, not raw username entry
- Production org guard — hard-coded safety block; missing this is a dealbreaker
- Record Type ID mapping by DeveloperName — every insert depends on this being resolved at startup
- Ordered migration (Entitlements → Request Flow → Community Request → Preferred Comms) — wrong order breaks foreign keys
- Cross-object relationship preservation via ID-mapping registry — core value of the tool
- Self-referential two-pass insert for Request Flow and Community Request — without this, hierarchies arrive broken
- Insert-only with skip-existing logic — prevents overwriting target customizations on re-runs
- Post-migration record count validation — minimum signal that migration succeeded
- Object-level selection (individual or all) — users won't always migrate all 4 objects
- Clear error output with actionable messages — migration failures must be debuggable

**Should have (differentiators):**
- Dry-run / preview mode — shows what would be migrated without touching target
- Relationship integrity check (post-migration spot-check on lookup fields) — goes beyond count validation
- Migration run summary report written to `.migration_logs/` — essential for team handoffs
- Named org aliases in prompts — matches how the team refers to their orgs

**Defer (v2+):**
- Support for additional CFSuite objects beyond the core 4
- Parallelized batch inserts — current volumes don't require this; revisit at 10x scale
- Force-update mode (opt-in upsert of existing records) — defer until a real use case emerges

### Architecture Approach

The architecture is a flat ETL pipeline with 10 modules and 2 runtime data files. Auth Layer retrieves credentials from SF CLI via subprocess; Extractor queries the source org via SOQL; Transformer strips internal fields, remaps Record Types, and resolves lookups using the ID Map; Loader bulk-inserts into the dest org and collects new IDs; Validator runs post-load SOQL counts and spot-checks. The ID Map is persisted to `id_map.json` after each batch so a crashed run can be resumed. Phase State is written to `state.json` after each object completes, enabling the Orchestrator to skip already-completed stages on re-run. Transformer functions are pure (no I/O, no side effects) making them fully unit-testable without org access.

**Major components:**
1. Auth Layer — `sf org display --json` via subprocess, returns Credentials dataclass (access_token, instance_url)
2. Config / Schema Layer — object load order, field exclusions, RecordType name-to-ID map, self-ref field definitions
3. Orchestrator — drives per-object ETL loop in dependency order, manages pass 1 / pass 2 sequencing
4. Extractor — SOQL queries via `simple-salesforce.query_all()`, returns `List[dict]`
5. Transformer — pure functions: strip source IDs, remap RecordTypes, resolve lookups, build insert payload
6. Loader — Bulk API 2.0 insert via `simple-salesforce bulk2`, captures dest IDs, logs per-record failures
7. ID Map Store — in-memory dict flushed to `id_map.json` after each batch; sole shared state between object runs
8. Phase State — `state.json` written after each stage completes; enables resume without re-inserting
9. Validator — post-load SOQL COUNT() comparisons and referential integrity spot-checks

### Critical Pitfalls

1. **Self-referential lookup fields cannot be populated in a single insert pass** — mandatory two-pass strategy: insert with self-ref fields null, build ID map, then bulk-update the self-ref fields. Must be designed into the architecture from the start. Affects Request Flow (Category_Journey__c, Display_Category__c) and Community Request (Parent_Question__c).

2. **Record Type IDs are org-specific and will silently break every insert** — at startup, query RecordType by DeveloperName on both orgs and build a translation map. Never pass a source RecordTypeId to the dest org. Fail loudly if a DeveloperName exists in source but not dest.

3. **Cross-object lookup broken by wrong insert order** — document the dependency graph and hard-code the insert order before writing any insert code. Entitlements must exist before Request Flow inserts; Request Flow must exist before Community Request inserts.

4. **Triggers and validation rules fire on migrated records** — SupportContractTriggerHandler will reject records mid-migration. Implement a migration bypass flag via Hierarchical Custom Setting before any insert testing. Test with triggers active first to understand what fires.

5. **No ID mapping persistence means no recovery path** — the ID map must be flushed to disk after every batch. Loss of the in-memory map makes Pass 2 (self-ref update) impossible and prevents re-run after failure. Design persistence as a core component, not an afterthought.

## Implications for Roadmap

Based on research, the architecture's build order directly dictates the phase structure. Each layer must be verifiable before the next is built. The component dependency graph from ARCHITECTURE.md resolves to 5 natural phases:

### Phase 1: Foundation — Auth, Config, and Project Scaffold

**Rationale:** Auth and Config have no dependencies and are required by every other component. Getting the project skeleton and SF CLI integration working first enables all subsequent phases to be tested against real orgs. uv and pyproject.toml scaffolding belongs here.

**Delivers:** Working `migrate` CLI command that authenticates against source and dest orgs, lists authenticated orgs via `sf org list`, enforces production org guard, and loads the object dependency config.

**Addresses:** Org selection from sf org list, production org guard, object-level selection (flag/prompt).

**Avoids:** Authentication gaps mid-run (access token expiry), missing SF CLI detection (fail fast with clear error), credential storage anti-pattern.

### Phase 2: Extraction and Schema Validation

**Rationale:** Extractor depends only on Auth and can be validated against a real source org immediately. Record Type mapping and Entitlement name lookup must be solved before any insert code is written — they are pre-flight checks that gate all inserts.

**Delivers:** SOQL extraction from source org with record counts, Record Type translation map built and validated at startup, Entitlement name-to-ID map for dest org, dry-run-compatible output showing what would be migrated.

**Addresses:** Record Type ID mapping by DeveloperName, ordered migration dependency resolution, dry-run / preview mode (partial).

**Avoids:** Record Type ID org-specificity pitfall, schema gaps discovered mid-migration rather than pre-flight.

### Phase 3: Core ETL — Transformer, Loader, and ID Map

**Rationale:** Transformer is pure functions and can be built and fully unit-tested before any dest org writes. Loader and ID Map then wire together to execute the first complete migration pass. This is the highest-risk phase because it touches the dest org.

**Delivers:** Complete single-pass ETL for objects without self-referential fields (Entitlements, Preferred Comms Config). Bulk API 2.0 inserts with per-record failure logging. ID map persisted to `id_map.json`. Phase state persisted to `state.json`. Insert-only skip logic.

**Addresses:** Cross-object relationship preservation, insert-only with skip-existing logic, clear error output, post-migration record count validation.

**Avoids:** Single-record REST insert anti-pattern (use Bulk API 2.0 from the start), partial batch failure handling gap (check per-record success flags, not just HTTP 200), ID map not persisted (flush to disk after every batch).

### Phase 4: Self-Referential Two-Pass Insert

**Rationale:** This is the most complex and highest-correctness-risk component. It builds on the working ETL from Phase 3 and adds Pass 2 update logic for Request Flow and Community Request. Must be designed and tested carefully before the full 2,339 + 751 record migration runs.

**Delivers:** Two-pass insert for CFSuite Request Flow (Category_Journey__c, Display_Category__c) and Community Request (Parent_Question__c). Pass 2 bulk-updates self-ref fields using the persisted ID map. Phase state marks pass1_complete and complete separately per object.

**Addresses:** Self-referential two-pass insert requirement (the highest-criticality pitfall), relationship integrity between Request Flow and Community Request.

**Avoids:** Single-pass self-ref insert (permanently broken parent lookups), skipping ID map persistence between passes.

### Phase 5: Validation, Resume, and Polish

**Rationale:** Validator is independent of migration logic and queries only the dest org. Resume capability (checking state.json at startup) can be added around the working Orchestrator. Polish items (run report, named aliases) belong last.

**Delivers:** Post-migration SOQL COUNT() comparison per object. Referential integrity spot-checks on key lookup fields. Resume from last checkpoint on re-run. Migration run summary report written to `.migration_logs/`. Named org aliases in interactive prompts.

**Addresses:** Post-migration record count validation, relationship integrity check, re-runnable / idempotent behavior, migration run summary report, named org aliases.

**Avoids:** "Looks done but isn't" scenarios — ID map completeness check, trigger bypass removal verification, partial failure log validation.

### Phase Ordering Rationale

- Auth and Config have zero dependencies and are required by every downstream component — they must come first.
- Record Type mapping is a pre-flight check that gates all inserts; it belongs in Extraction before any Loader code is written.
- Transformer is pure functions — build and test it before writing any dest org insert code to reduce risk of discovering logic errors after records are already inserted.
- Two-pass logic for self-referential objects is the hardest correctness problem and should be isolated to its own phase rather than mixed into the initial ETL to reduce cognitive load and testing surface.
- Validator and resume capability add resilience around a working migration — they are not blockers for correctness and belong at the end.

### Research Flags

Phases with well-documented patterns (skip research-phase during planning):
- **Phase 1:** SF CLI auth via subprocess and uv scaffolding are standard, well-documented patterns. No additional research needed.
- **Phase 2:** SOQL extraction and Record Type mapping pattern is fully specified in STACK.md and ARCHITECTURE.md with code examples.
- **Phase 3:** Bulk API 2.0 via simple-salesforce is documented in official sources with confirmed patterns. ETL structure is standard.

Phases likely needing deeper research or pre-work during planning:
- **Phase 4:** The exact self-referential field names on CFSuite Request Flow (Category_Journey__c, Display_Category__c) and Community Request (Parent_Question__c) should be verified against the actual managed package schema before implementation. ARCHITECTURE.md lists them but they should be confirmed via `sf sobject describe` against a real org.
- **Phase 4:** Trigger bypass mechanism — the specific Hierarchical Custom Setting approach needs to be designed against the actual dest org's trigger code before the migration is run against any production-adjacent data. PITFALLS.md flags SupportContractTriggerHandler specifically.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core library choices confirmed on PyPI with version numbers. Typer 0.24.1 released Feb 2026, simple-salesforce 1.12.9 released Aug 2024, questionary 2.1.1 released Aug 2025, rich 14.x confirmed. uv recommendation from multiple 2025 sources. |
| Features | HIGH | Table-stakes features derived directly from project requirements. Differentiators validated against SFDMU comparison and competitor analysis. Anti-features have clear rationale tied to this project's insert-only constraint. |
| Architecture | HIGH | Two-pass self-referential pattern confirmed by SFDMU documentation and multiple community sources. ETL module structure is established Python CLI practice. Bulk API 2.0 threshold and behavior confirmed via official Salesforce docs. |
| Pitfalls | HIGH | Self-referential limitation confirmed by official Salesforce CLI GitHub issue #248. Record Type pitfall is universally documented in Salesforce migration literature. Trigger interference is project-specific (SupportContractTriggerHandler identified). |

**Overall confidence:** HIGH

### Gaps to Address

- **Self-referential field names on CFSuite objects:** Research assumes Category_Journey__c, Display_Category__c (Request Flow) and Parent_Question__c (Community Request) based on project context. These should be verified via `sf sobject describe cfsuite1__CFSuite_Request_Flow__c --json` against a real org before Phase 4 implementation.

- **Trigger bypass implementation detail:** The SupportContractTriggerHandler bypass mechanism (Hierarchical Custom Setting approach) needs to be spec'd against the actual trigger code in the dest org. The pattern is correct; the specific Custom Setting name and field to check are not yet determined.

- **Preferred Comms Config field mapping:** This object (22 records, no dependencies) is included in scope but its field structure was not analyzed in detail. Pre-flight field describe at migration startup will catch any schema gaps.

- **pytest-subprocess version:** STACK.md notes MEDIUM confidence on the exact version of pytest-subprocess. This is a dev dependency only and does not affect production behavior — confirm version at project scaffold time.

## Sources

### Primary (HIGH confidence)

- PyPI — typer 0.24.1 (Feb 2026), simple-salesforce 1.12.9 (Aug 2024), questionary 2.1.1 (Aug 2025), rich 14.1.0
- Salesforce CLI GitHub Issue #248 — confirmed native CLI cannot handle self-referential lookups
- SFDMU Help Center — self-referential field handling documentation
- Salesforce Bulk API 2.0 official docs — >2,000 records threshold, async polling behavior, per-record result CSV
- Salesforce Admins Blog — "How I Solved This: Migrating Data While Keeping IDs Consistent"
- simple-salesforce GitHub — bulk.py source confirms per-record result inspection pattern

### Secondary (MEDIUM confidence)

- End Point Dev — dependency-aware insert ordering pattern for Salesforce migration
- Metazoa Snapshot best practices — relationship key preservation patterns
- Salesforce Ben — Python ETL pattern for Salesforce data migration
- Topological sort for Salesforce (Medium/@justusvandenberg) — pattern confirmed, Apex but applicable to Python
- uv vs pip (Real Python, AppSignal 2025) — uv as 2025 standard recommendation

### Tertiary (LOW confidence)

- Soft Web Solutions — external ID strategy and record type mapping practices (MEDIUM community consensus)
- dataimporter.io 2025 guide — general org-to-org patterns

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*
