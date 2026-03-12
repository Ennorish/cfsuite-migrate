# Pitfalls Research

**Domain:** Salesforce org-to-org data migration (insert-only, Python CLI, self-referential lookups, cross-object dependencies)
**Researched:** 2026-03-12
**Confidence:** HIGH — findings corroborated across official Salesforce docs, SFDMU documentation, and multiple community sources

---

## Critical Pitfalls

### Pitfall 1: Self-Referential Lookup Fields Cannot Be Populated During Initial Insert

**What goes wrong:**
A record with a self-referential lookup (e.g., a "Parent" field pointing to another record on the same object) cannot be inserted with that field pre-populated. The target ID for the parent doesn't exist yet because all records are being created fresh in the destination org. Attempting a single-pass insert that includes self-reference fields results in either relationship corruption or API errors.

**Why it happens:**
Developers treat the self-referential lookup the same as a cross-object lookup. Cross-object lookups are solved by inserting the parent object first, then the child. But self-referential lookups belong to the same object — parent and child records must be created in the same batch, which makes a single-pass impossible.

**How to avoid:**
Use a mandatory two-pass strategy for every self-referential object:
1. Pass 1 — Insert all records with the self-reference field set to `None`. Store the source-ID-to-new-ID mapping as they come back from the API.
2. Pass 2 — Update records where `source_parent_id` is not null: look up the new target ID from the mapping, then issue an update via the API.

Build this two-pass logic into the migration script from the start. Do not attempt to hack around it at the end.

**Warning signs:**
- Any object in the schema has a field whose type is Lookup and whose related object is itself.
- The word "Parent" appears in field names on the objects being migrated.
- Inserting records succeeds but parent lookups are all blank in the destination org.

**Phase to address:**
Schema analysis / pre-migration planning phase. The two-pass structure must be designed before any insert code is written, because it affects how the ID mapping dictionary is built and how rollback works.

---

### Pitfall 2: Record Type IDs Are Org-Specific and Will Break Every Insert

**What goes wrong:**
`RecordTypeId` is a 15- or 18-character Salesforce ID that is unique per org. The source org's `RecordTypeId` values are meaningless in the destination org. If migrated verbatim, every record either fails with a `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` error or silently assigns the wrong record type.

**Why it happens:**
Developers extract records including `RecordTypeId` and pass that column straight to the insert payload without substitution. The field looks like a valid ID, so no obvious error appears during development when the destination org happens to have the same ID (which never actually happens across real orgs).

**How to avoid:**
At the start of the migration script, query `RecordType` on both source and destination orgs and build a translation dictionary keyed on `DeveloperName` (not `Name`, which can be localized):

```python
source_rt = {rt['DeveloperName']: rt['Id'] for rt in sf_source.query_all(
    "SELECT Id, DeveloperName FROM RecordType WHERE SObjectType = 'ObjectName__c'"
)['records']}

dest_rt = {rt['DeveloperName']: rt['Id'] for rt in sf_dest.query_all(
    "SELECT Id, DeveloperName FROM RecordType WHERE SObjectType = 'ObjectName__c'"
)['records']}

rt_map = {source_rt[k]: dest_rt[k] for k in source_rt if k in dest_rt}
```

Apply this map to every record before insert. Fail loudly if a `DeveloperName` exists in the source but not the destination — that is a schema gap that must be resolved before migration.

**Warning signs:**
- Any object being migrated has multiple record types in the source org.
- Inserted records land in the destination with a default record type instead of the expected one.
- API returns `FIELD_INTEGRITY_EXCEPTION` on `RecordTypeId`.

**Phase to address:**
Schema validation phase, before any insert. The Record Type translation map should be built and validated as a pre-flight check that gates the migration from proceeding.

---

### Pitfall 3: Cross-Object Lookup Relationships Broken by Wrong Insert Order

**What goes wrong:**
When objects have dependencies on each other (Object A looks up to Object B, Object B looks up to Object C, Object C looks up to Object A), inserting in the wrong order produces records with null lookups or insert failures due to required relationship fields.

**Why it happens:**
The dependency graph is not drawn out before the migration sequence is planned. Developers insert objects in alphabetical order or "the order that felt natural," leaving child records inserted before their parents exist.

**How to avoid:**
Before writing any insert code, draw the full dependency graph for all 4 objects. Identify:
- Which objects have no inbound dependencies (insert these first).
- Which objects depend on objects already inserted (insert these next).
- Which circular dependencies exist (require the two-pass pattern from Pitfall 1 or a deliberate null-then-update approach for that specific field).

With 4 objects and ~3,300 records, this graph is small enough to resolve manually. Document the resolved insert order as a numbered list that the script enforces.

**Warning signs:**
- An object's lookup field points to another object in the migration set.
- Inserts succeed but lookup fields are null in the destination.
- API returns `FIELD_CUSTOM_VALIDATION_EXCEPTION` triggered by a validation rule that requires a parent to be present.

**Phase to address:**
Schema analysis phase. The insert order must be locked before coding starts. Any phase where insert logic is written must reference the resolved order document, not re-derive it.

---

### Pitfall 4: Triggers and Validation Rules Fire on Migrated Records and Cause Failures

**What goes wrong:**
The destination org has active Apex triggers and validation rules designed for normal user-driven record creation. When migration inserts records programmatically — often in bulk, without the expected field states — triggers throw exceptions, validation rules reject records, and the migration fails partway through with a mix of inserted and non-inserted records.

In this project: `SupportContractTriggerHandler` enforces "one Active contract per project" and syncs convenience fields. This trigger will fire on every inserted `Support_Contract__c` record. If migrating multiple contracts per project (even if only one will be Active), the trigger may reject records that are valid in the final data state but invalid mid-migration.

**Why it happens:**
Developers test in a clean sandbox without full production trigger coverage. Or they assume the migration user bypasses automation — it does not, unless specifically coded.

**How to avoid:**
Two approaches — choose based on trigger complexity:

Option A (preferred for this project): Add a migration bypass flag using a Hierarchical Custom Setting. The migration script sets this flag for the migration user. Triggers and validation rules check `!$Permission.Data_Migration` or the custom setting before executing. This is reversible and auditable.

Option B (acceptable for one-time sandbox-to-sandbox): Temporarily deactivate triggers and validation rules before migration, then reactivate after. Requires org admin access. Document exactly what was deactivated and reactivate immediately after.

Never leave triggers deactivated. Create a pre-migration checklist and a post-migration checklist that are mirror images of each other.

**Warning signs:**
- Insert errors mention trigger class names (`SupportContractTriggerHandler`).
- Errors mention `FIELD_CUSTOM_VALIDATION_EXCEPTION` with validation rule messages.
- Records insert successfully in isolation but fail in bulk.

**Phase to address:**
Pre-migration preparation phase. The bypass mechanism must be in place and tested before any production migration run begins. Test in the destination sandbox with triggers active first to understand what fires.

---

### Pitfall 5: No ID Mapping Persistence — Losing the Source-to-Destination ID Map

**What goes wrong:**
The migration script runs, creates new records in the destination org, and the new Salesforce IDs are returned by the API. These are the only link between source records and destination records. If the mapping is held only in memory and the script crashes, or the mapping file is not saved, there is no way to:
- Resolve relationships in subsequent passes (Pitfall 1's Pass 2 becomes impossible).
- Perform rollback (you cannot delete records you cannot identify).
- Re-run the migration for a subset of failed records.

**Why it happens:**
Developers write a single-run script assuming success. The mapping is built in a Python dict that lives only for the duration of the process. A network error or API timeout mid-migration leaves a partially populated destination org with no recovery path.

**How to avoid:**
Persist the ID mapping to disk immediately after each batch insert:

```python
import json, pathlib

mapping_file = pathlib.Path("migration_id_map.json")
if mapping_file.exists():
    id_map = json.loads(mapping_file.read_text())
else:
    id_map = {}

# After each batch insert:
for result, source_record in zip(insert_results, source_batch):
    if result['success']:
        id_map[source_record['Id']] = result['id']

mapping_file.write_text(json.dumps(id_map, indent=2))
```

Also checkpoint which source IDs have already been successfully inserted so re-runs skip already-processed records instead of creating duplicates.

**Warning signs:**
- The script has no file I/O for tracking state.
- Pass 2 (self-reference update) reads the mapping from the same dict built in Pass 1, with no persistence between them.
- No rollback log exists.

**Phase to address:**
Script architecture phase. The ID mapping persistence layer must be designed as a core component, not bolted on after the basic insert loop works.

---

### Pitfall 6: Partial Batch Failures Leave the Destination in an Inconsistent State

**What goes wrong:**
The Bulk API and REST API both allow partial success within a batch: some records insert successfully and others fail. If the script does not detect and handle partial failures, it will proceed to the next object's inserts with the assumption that all parents were created. Child record inserts then silently null out their lookup fields (because the parent was never created) or fail entirely.

With 3,300 records across 4 objects with dependencies, a 2% partial failure rate means ~66 records with broken relationships cascading through subsequent inserts.

**Why it happens:**
Developers check that the API call itself did not throw an exception and move on, without checking per-record `success` flags in the response.

**How to avoid:**
After every batch insert, inspect every record in the response:

```python
failures = [r for r in results if not r['success']]
if failures:
    # Log each failure with source record ID and error message
    for f in failures:
        logger.error(f"Insert failed: {f['errors']}")
    # Do NOT proceed — halt or skip the failed source IDs explicitly
    raise MigrationBatchError(f"{len(failures)} records failed in batch")
```

Design the script to be strict: halt on any failure in an upstream object. Allow continuation only if the failed records are isolated leaf-level records with no downstream dependents.

**Warning signs:**
- The insert response is checked only for HTTP status 200, not per-record `success`.
- Lookup fields in destination records are null when the source had values.
- Record counts in destination do not match source after migration.

**Phase to address:**
Script development phase. Error handling must be part of the initial design, not added after the happy path works.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-code Record Type IDs directly in script | Saves building a dynamic lookup | Breaks silently if org is refreshed or Record Types are renamed; fails on any second run against a different org | Never — the dynamic translation map takes 10 minutes and prevents all future failures |
| Single-pass insert for self-referential objects (leave field null forever) | Simpler script | Parent relationships permanently broken; data integrity failure | Never — the relationships exist for a reason |
| Skip ID mapping persistence (in-memory only) | Simpler script | No rollback, no re-run capability, no Pass 2 for self-references | Never for a migration that spans multiple objects |
| Disable all automation org-wide rather than per-user bypass | Faster to implement | Risks missing trigger behavior that must be re-tested; creates a window where live users operate without data guards | Only acceptable in a sandbox with zero concurrent users |
| Use REST API single-record inserts instead of batched inserts | Simpler error handling per record | API rate limits hit at ~3,300 calls; migration takes hours instead of minutes | Never — always batch, even at this small scale |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SF CLI auth via `sf org login` | Assuming the access token never expires during a long migration run | Access tokens expire in 2 hours by default. Use `sf org display --json` to extract the token right before the migration run, or use a connected app with JWT bearer flow for programmatic non-interactive auth |
| simple-salesforce bulk insert | Using `bulk_handler.insert()` and treating the return as a simple success/fail | The return is a list of per-record result dicts. Inspect `result['success']` and `result['errors']` on every element |
| simple-salesforce REST insert | Using `sf_dest.Object__c.create()` in a loop record-by-record | Use the Composite API or bulk insert. 3,300 individual REST calls will exhaust API limits and take ~30 minutes |
| Salesforce Bulk API 2.0 | Assuming async jobs complete immediately | Bulk jobs are asynchronous. The script must poll job status until `state == 'JobComplete'` before reading results |
| SF CLI org alias | Using org alias directly in simple-salesforce auth | simple-salesforce requires explicit credentials (instance URL + access token or username/password + security token). Extract from `sf org display --json --target-org <alias>` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-record REST API calls instead of batch | Migration takes hours; API daily limit consumed | Use Bulk API 2.0 or batched Composite API requests | At ~200+ records, single-record calls become impractical |
| Loading all 3,300 source records into memory before any insert | High memory usage on large orgs; script crashes for orgs with more records | Process in chunks of 200-500 records per batch | Not a problem at 3,300 records, but matters if this script is reused for a larger org |
| Re-querying the source org during Pass 2 updates instead of using the persisted map | Extra API calls; risk of source data changing between passes | Use the persisted ID map from Pass 1 entirely | Any time the source org is live during migration |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing SF credentials (username, password, security token) in the Python script file | Credentials committed to git; any org access compromised | Use environment variables or a `.env` file excluded from version control; load with `python-dotenv` |
| Using a System Administrator profile for the migration user without a post-migration audit | Admin access token can be reused for unintended operations if the script or token leaks | Use a dedicated integration user with only the permissions required for the migration objects |
| Not disabling or revoking the migration user's access after migration completes | Persistent attack surface | Document and execute a post-migration decommission step for the migration user/connected app |

---

## "Looks Done But Isn't" Checklist

- [ ] **Self-referential relationships:** All parent lookup fields are null after Pass 1 — verify Pass 2 has actually run and populated them, not just that Pass 2 code exists
- [ ] **Record Types:** Records in destination show the correct Record Type label, not just a default — query `RecordTypeId` and compare `DeveloperName` back to source
- [ ] **Cross-object lookups:** Count records in destination per object and compare to source; null lookups produce the correct count but wrong data
- [ ] **ID mapping completeness:** `len(id_map) == total_source_records` — if the mapping has fewer entries than source records, some inserts silently failed
- [ ] **Trigger bypass removed:** After migration, verify the bypass mechanism (custom setting or deactivated triggers) has been reversed and triggers are active again
- [ ] **Partial failures logged:** A zero-error run is suspicious — verify the failure log is actually being written and was checked, not just that no exception was raised

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Self-referential fields null after migration | MEDIUM | Re-run Pass 2 using the persisted ID map. If map was lost, re-query destination records against source by a unique business field (e.g., Name + CreatedDate range) to rebuild it |
| Wrong Record Types assigned | MEDIUM | Query destination records where `RecordTypeId` does not match expected; bulk-update `RecordTypeId` using the correct translation map |
| Partial failure mid-migration left broken cross-object links | HIGH | Identify which source IDs are missing from the destination (compare source query to ID map). Delete the orphaned dependent records if delete permission is available; re-run inserts for missing parents first, then re-insert orphaned children |
| Migration user token expired mid-run | LOW | Re-authenticate with SF CLI; update the token in the running environment; re-run script from the last checkpoint (requires persisted ID map and processed-ID set) |
| Triggers rejected records in bulk | MEDIUM | Enable the bypass mechanism; identify source IDs that failed (from the error log); re-run inserts for only those records |
| No ID map persisted, migration partially complete | HIGH | Cannot safely re-run without duplicating already-inserted records. Must either: (a) hard-delete all destination records for the migrated objects and restart, or (b) query both orgs by unique business fields to reconstruct the map manually |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Self-referential lookup two-pass requirement | Schema analysis + script architecture | Pass 2 executes and parent fields are populated; spot-check 10 records in destination |
| Record Type ID translation | Pre-flight validation (before first insert) | Script logs a RT translation map and halts if any source DeveloperName is absent from destination |
| Cross-object insert order | Schema analysis — dependency graph documented | Insert order is a named constant in the script, not inferred at runtime |
| Trigger and validation rule interference | Pre-migration preparation (bypass mechanism built and tested) | Run a 10-record test insert with bypass active; then run same 10 records with bypass inactive to confirm triggers were actually firing |
| ID mapping not persisted | Script architecture — checkpoint design | After a simulated crash (kill script mid-run), verify script resumes from checkpoint without duplicating records |
| Partial batch failure handling | Script development — error handling design | Inject a deliberate bad record into a test batch and confirm the script halts and logs the failure, rather than continuing |

---

## Sources

- [SFDMU: Can child records with a self-lookup field be inserted in a single job?](https://help.sfdmu.com/faq/sfdmu-data-insertion-and-limitations/can-child-records-with-a-self-lookup-field-be-inserted-in-a-single-job) — HIGH confidence, official tool documentation
- [Salesforce CLI Issue #248: Improve handling of self-referencing lookups](https://github.com/forcedotcom/cli/issues/248) — HIGH confidence, official Salesforce CLI GitHub
- [Set Salesforce Audit Field Values for Imported Records](https://help.salesforce.com/s/articleView?id=000385636&language=en_US&type=1) — HIGH confidence, official Salesforce Help
- [Bypassing Salesforce Data Validation for Import & Migration](https://nextian.com/salesforce/bypassing-salesforce-data-validation-in-rules-and-apex-triggers-for-data-import-migration/) — MEDIUM confidence, verified against community patterns
- [How I Solved This: Migrating Data While Keeping IDs Consistent](https://admin.salesforce.com/blog/2020/how-i-solved-this-migrating-data-while-keeping-ids-consistent) — HIGH confidence, official Salesforce Admins blog
- [Migrate Related Sets of Data Between Salesforce Orgs](https://www.metazoa.com/snapshot-best-practices-dataset-migration/) — MEDIUM confidence, commercial tool documentation
- [Salesforce Org-to-Org Data Migration Guidelines](https://medium.com/@Suraj_Pillai/salesforce-org-to-org-data-migration-guidelines-a98e4b68ac9c) — MEDIUM confidence, practitioner experience
- [Salesforce Bulk API 2.0 Limits and Allocations](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_bulkapi.htm) — HIGH confidence, official Salesforce developer documentation
- [simple-salesforce GitHub — bulk.py](https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/bulk.py) — HIGH confidence, library source

---
*Pitfalls research for: Salesforce org-to-org data migration, Python CLI, self-referential lookups, cross-object dependencies*
*Researched: 2026-03-12*
