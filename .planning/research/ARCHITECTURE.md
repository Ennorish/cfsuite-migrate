# Architecture Research

**Domain:** Python CLI — Salesforce org-to-org data migration (insert-only, managed package config objects)
**Researched:** 2026-03-12
**Confidence:** HIGH (patterns are well-established; self-referential two-pass approach verified across multiple sources)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                              │
│   migrate.py  ──  argparse commands: run, validate, dry-run          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
               ┌───────────────┼────────────────┐
               ▼               ▼                ▼
┌──────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│   Auth Layer     │  │  Config/Schema  │  │   Orchestrator          │
│                  │  │  Layer          │  │                         │
│ sf org display   │  │ object_order.py │  │ Reads phase plan,       │
│ → access token   │  │ field_map.py    │  │ drives Extract →        │
│ + instance URL   │  │ record_type.py  │  │ Transform → Load        │
│ (source + dest)  │  │                 │  │ per object              │
└──────────┬───────┘  └────────┬────────┘  └──────────┬──────────────┘
           │                   │                      │
           └───────────────────┼──────────────────────┘
                               │
          ┌────────────────────┼────────────────────────┐
          ▼                    ▼                        ▼
┌──────────────────┐  ┌─────────────────────┐  ┌───────────────────┐
│   Extractor      │  │    Transformer       │  │    Loader         │
│                  │  │                      │  │                   │
│ SOQL query       │  │ Strip source IDs     │  │ Bulk API 2.0      │
│ source org       │  │ Map RecordType IDs   │  │ insert batches    │
│ → raw records    │  │ Resolve ext refs     │  │ Collect new IDs   │
│   (List[dict])   │  │ Build insert payload │  │ Log errors        │
└──────────────────┘  └─────────────────────┘  └───────────────────┘
                               │
               ┌───────────────┼────────────────┐
               ▼               ▼                ▼
┌──────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│  ID Map Store    │  │  Phase State    │  │   Validator             │
│  (in-memory +   │  │  (JSON on disk) │  │                         │
│   JSON file)     │  │  resume-safe    │  │ Post-load SOQL counts   │
│                  │  │                 │  │ spot-check spot values  │
│ source_id →      │  │ which objects   │  │ referential integrity   │
│ dest_id per obj  │  │ are complete    │  │ checks                  │
└──────────────────┘  └─────────────────┘  └─────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CLI Entry Point | Parse commands, coordinate components, surface errors | `argparse` with `run`, `validate`, `dry-run` subcommands |
| Auth Layer | Retrieve access token + instance URL for source and dest via SF CLI | `subprocess` → `sf org display --json`, parse JSON |
| Config / Schema Layer | Object load order, field exclusions, RecordType name-to-ID map, relationship definitions | Plain Python dicts / dataclasses, loaded once at startup |
| Orchestrator | Drive the per-object migration loop; decide phase order | Function that iterates the dependency-sorted object list |
| Extractor | Query source org via SOQL, page through all records | `simple-salesforce` `sf.query_all()` or Bulk API query |
| Transformer | Strip Salesforce-internal fields, remap RecordType IDs, resolve lookup references | Pure functions; returns list of insert-ready dicts |
| Loader | Bulk-insert records into dest org, capture result IDs | `simple-salesforce` Bulk 2.0 or REST `insert` |
| ID Map Store | Map every source record ID to its new dest record ID | In-memory dict, flushed to JSON after each object load |
| Phase State | Track which objects have been migrated; enables resume | JSON file written after each object completes |
| Validator | Post-migration count comparison and referential checks | SOQL `COUNT()` queries against dest org |

## Recommended Project Structure

```
migrate/
├── migrate.py              # CLI entry point — argparse, wires components
├── auth.py                 # SF CLI subprocess call → credentials dataclass
├── config.py               # Object order, field exclusions, relationship maps
├── extractor.py            # SOQL extraction from source org
├── transformer.py          # Data cleaning, RecordType remapping, lookup resolution
├── loader.py               # Bulk API insert, result collection
├── id_map.py               # Source-to-dest ID tracking (in-memory + JSON persistence)
├── validator.py            # Post-migration count and spot-check queries
├── state.py                # Phase state (what's done, what's pending)
├── models.py               # Dataclasses: Credentials, ObjectConfig, MigrationResult
└── utils.py                # Logging, error formatting, retry helpers
data/
├── id_map.json             # Written during migration — source→dest ID mapping
└── state.json              # Written during migration — phase completion tracking
```

### Structure Rationale

- **Flat module layout:** Only ~300 total records across 4 objects. A flat structure is appropriate; sub-packages would be over-engineering.
- **auth.py separate from config.py:** Auth is runtime (credentials, tokens); config is design-time (object order, field maps). Keeping them separate makes dry-run and testing easier — config can be loaded without real org access.
- **id_map.json and state.json on disk:** Allows a failed mid-run migration to be resumed without re-inserting already-loaded objects.
- **transformer.py as pure functions:** No I/O, no side effects. Easy to unit-test and audit before running against the dest org.

## Architectural Patterns

### Pattern 1: Two-Pass Insert for Self-Referential Lookups

**What:** For objects with self-referential lookup fields (e.g., `Category_Journey__c`, `Parent_Question__c`), insert all records first with those fields set to `None`, then issue a second update pass that sets the parent lookup using the ID map.

**When to use:** Any object where a record can be both a parent and a child — i.e., the lookup field points to another record on the same object. Mandatory for CFSuite Request Flow and Community Request.

**Trade-offs:** Requires two API round-trips per self-referential object. Records briefly exist without parent links, which is acceptable for insert-only migration where no users see the dest org mid-flight.

**Example:**

```python
# Pass 1: insert all records, self-ref fields nulled out
SELF_REF_FIELDS = {
    "CFSuite_Request_Flow__c": ["Category_Journey__c", "Display_Category__c"],
    "Community_Request__c": ["Parent_Question__c"],
}

def strip_self_refs(records, object_name):
    fields = SELF_REF_FIELDS.get(object_name, [])
    return [{k: (None if k in fields else v) for k, v in r.items()} for r in records]

# Pass 2: update self-ref fields using the ID map
def build_self_ref_updates(source_records, object_name, id_map):
    fields = SELF_REF_FIELDS.get(object_name, [])
    updates = []
    for rec in source_records:
        update = {"Id": id_map[rec["Id"]]}
        for field in fields:
            if rec.get(field) and rec[field] in id_map:
                update[field] = id_map[rec[field]]
        if len(update) > 1:
            updates.append(update)
    return updates
```

### Pattern 2: RecordType DeveloperName Remapping

**What:** At startup, query both source and dest orgs for `RecordType` records filtered by `SObjectType`. Build a `DeveloperName → Id` map per org. In the transformer, replace source `RecordTypeId` with the dest ID that has the same `DeveloperName`.

**When to use:** Always — Record Type IDs are org-specific. This project uses a managed package so `DeveloperName` is identical across orgs.

**Trade-offs:** Requires two extra SOQL queries at startup. Very low cost, completely eliminates the most common migration failure mode.

**Example:**

```python
def build_record_type_map(sf_source, sf_dest, sobject_type):
    """Returns: {source_rt_id: dest_rt_id}"""
    soql = f"SELECT Id, DeveloperName FROM RecordType WHERE SObjectType = '{sobject_type}'"
    src = {r["DeveloperName"]: r["Id"] for r in sf_source.query_all(soql)["records"]}
    dst = {r["DeveloperName"]: r["Id"] for r in sf_dest.query_all(soql)["records"]}
    return {src[dn]: dst[dn] for dn in src if dn in dst}
```

### Pattern 3: External Reference Resolution via Entitlement Name

**What:** CFSuite Request Flow references Entitlements by `Name` (not by ID). In the transformer, look up the Entitlement's dest org ID using its Name, which is stable across orgs.

**When to use:** Any cross-object reference where the linking key is a business identifier (Name, DeveloperName, ExternalId) rather than a Salesforce record ID.

**Trade-offs:** Requires querying dest org Entitlements before loading Request Flow. If a Name doesn't match, fail loudly rather than inserting a null lookup.

## Data Flow

### Full Migration Run

```
CLI: migrate run --source <alias> --dest <alias>
  │
  ├── Auth Layer
  │     sf org display --json (source) → Credentials(access_token, instance_url)
  │     sf org display --json (dest)   → Credentials(access_token, instance_url)
  │
  ├── Schema Setup
  │     Query RecordType IDs (source + dest) per object
  │     Query Entitlement Names → IDs in dest org
  │     Determine object load order (see below)
  │
  ├── For each object in load order:
  │     Extractor  → SOQL query source → raw List[dict]
  │     Transformer → strip/remap/resolve → insert-ready List[dict]
  │     Loader (Pass 1) → Bulk insert → dest IDs
  │     ID Map    → record source_id → dest_id for every record
  │     State     → mark object as "pass1_complete"
  │
  ├── For each self-referential object (Pass 2):
  │     Transformer → build update payloads using ID Map
  │     Loader (Pass 2) → Bulk update self-ref fields
  │     State     → mark object as "complete"
  │
  └── Validator
        COUNT() source vs dest per object
        Spot-check referential integrity on key lookups
        Output: PASS / FAIL with diff details
```

### Key Data Flows

1. **ID propagation:** Every record inserted produces a new dest ID. The ID Map accumulates these across all objects. Lookups in later objects (e.g., Community Request → Request Flow) are resolved from this map, not from re-querying the dest org.

2. **Object load order dependency:** Entitlement must be loaded before Request Flow (Request Flow references Entitlement by Name). Preferred Comms Config has no external dependencies. Community Request references Request Flow so it loads last among the four.

3. **Error isolation:** Bulk API 2.0 returns per-record success/failure. Failed records are logged with their source ID and error message. The run continues for the remaining records; partial success is acceptable for migration (review and re-run failed records manually).

### Object Load Order

```
1. Entitlement (196 records) — no internal dependencies
2. Preferred Comms Config (22 records) — no internal dependencies
3. CFSuite Request Flow (2339 records)
       Pass 1: insert all, self-ref fields null
       Pass 2: update Category_Journey__c, Display_Category__c
4. Community Request / Data Settings (751 records)
       Pass 1: insert all, Parent_Question__c null
       Pass 2: update Parent_Question__c
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| < 5000 records (this project) | REST API or Bulk API 2.0 with single job per object; no parallelism needed |
| 5k–100k records | Bulk API 2.0 with chunked CSV upload; adjust batch size to 5000 |
| 100k+ records | Parallel Bulk jobs per object where no cross-object deps; streaming extractor to avoid memory |

This project sits firmly in the < 5000 range. Bulk API 2.0 is still preferred over REST even at this scale because it handles rate limits gracefully and gives per-record error reporting in the response CSV.

### Scaling Priorities

1. **First bottleneck:** Bulk API governor limits — 10,000 API calls/day on dev orgs, 15,000 on production. With ~3300 total records this is not a concern.
2. **Second bottleneck:** Memory for ID Map — at this scale, an in-memory dict (~3300 entries) is negligible. For 100k+ records, stream and flush to SQLite.

## Anti-Patterns

### Anti-Pattern 1: Inserting Self-Referential Records Without a Two-Pass Strategy

**What people do:** Attempt to insert all records in one pass, hoping topological sort resolves parent-before-child ordering.

**Why it's wrong:** Self-referential hierarchies can be arbitrarily deep and can form cycles. Topological sort fails on cycles. Even on a DAG, sorting 2339 records into strict parent-before-child order is complex and fragile.

**Do this instead:** Insert all records with self-ref fields nulled, build the ID map, then run a single bulk update to set all parent lookups at once.

### Anti-Pattern 2: Hardcoding Salesforce Record IDs

**What people do:** Copy RecordTypeId, lookup field values, or related record IDs from source org into the insert payload without remapping.

**Why it's wrong:** All Salesforce IDs are org-specific 15/18-character strings. Hardcoded source IDs inserted into the dest org will silently create broken lookups or throw insert errors.

**Do this instead:** Never pass a source ID directly to the dest org. All IDs must go through either the ID Map (for migrated records) or a DeveloperName/Name lookup (for reference objects).

### Anti-Pattern 3: Using REST Single-Record Insert for Bulk Operations

**What people do:** Loop over records and call `sf.SObject.create(record)` one at a time.

**Why it's wrong:** 2339 records = 2339 API calls. At 5–10 calls/second, that is 4–8 minutes plus governor limit risk.

**Do this instead:** Use Bulk API 2.0 (`sf.bulk2.SObject.insert(data)`) which processes records in server-side batches and returns a results CSV with per-record success/failure.

### Anti-Pattern 4: No Resume Capability

**What people do:** Run the entire migration as a single transaction. If it fails halfway through, start from scratch.

**Why it's wrong:** With 4 objects and a two-pass strategy per self-referential object, there are 6 logical stages. A failure at stage 5 should not require re-inserting the first 3 objects' records.

**Do this instead:** Write `state.json` after each stage completes. At startup, check state and skip already-completed stages. Write the ID map to `id_map.json` incrementally.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Source Salesforce Org | `sf org display --json` via subprocess → `simple-salesforce` with access token | Requires source alias to be authenticated in SF CLI before running |
| Dest Salesforce Org | Same pattern as source | Requires dest alias authenticated separately |
| Salesforce Bulk API 2.0 | `simple-salesforce` `bulk2` namespace | Used for inserts; REST used for schema queries at startup |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Auth → Extractor/Loader | Passes `Credentials` dataclass (access_token, instance_url) | Neither Extractor nor Loader call SF CLI directly |
| Extractor → Transformer | Returns `List[dict]` (raw SOQL records including `attributes` key) | Transformer strips `attributes` key before building payload |
| Transformer → Loader | Returns `List[dict]` (clean insert payload, no source IDs, no `attributes`) | Loader does not inspect field contents — pure passthrough to Bulk API |
| Loader → ID Map | Loader returns `List[{source_id, dest_id}]` which Orchestrator writes to ID Map | ID Map is the only shared state between object migration runs |
| ID Map → Transformer (Pass 2) | ID Map is read during self-ref update payload construction | Transformer must not mutate the ID Map — read-only access |

## Build Order Implications for Roadmap

The dependency graph between components dictates this build order:

1. **Auth + models** — no dependencies; needed by everything
2. **Config** — no dependencies; defines the migration contract
3. **Extractor** — depends on Auth; can be validated against source org immediately
4. **Transformer** — depends on Config and ID Map interface; pure functions, fully testable without org access
5. **Loader + ID Map** — depends on Auth; can be tested with a small fixture set against dest org
6. **Orchestrator** — wires Extractor → Transformer → Loader in object-load-order sequence
7. **Self-ref two-pass logic** — builds on Orchestrator + ID Map; adds Pass 2 update stage for Request Flow and Community Request
8. **State / resume** — adds persistence around Orchestrator; can be added after basic flow works
9. **Validator** — independent of migration logic; queries dest org only; build last

This order minimizes integration risk: each layer can be verified before the next is built.

## Sources

- [Salesforce Bulk API 2.0 Documentation](https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/bulk_api_2_0.htm)
- [Relationship Fields in Bulk API CSV Headers](https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/datafiles_csv_rel_field_header_row.htm)
- [simple-salesforce GitHub](https://github.com/simple-salesforce/simple-salesforce) — Python Salesforce REST/Bulk client
- [Streamlining Salesforce Data Migration Using Python ETL — Salesforce Ben](https://www.salesforceben.com/streamlining-salesforce-data-migration-using-python-etl-within-google-colab/)
- [SFDMU Help Center — self-referential field handling](https://help.sfdmu.com/)
- [SF CLI: sf org display for access token extraction](https://gist.github.com/v-rudkov/8497a2ce74cea0493fb13a326b93056d)
- [Import Related Records with an External ID — Salesforce Help](https://help.salesforce.com/s/articleView?id=000383207&language=en_US&type=1)
- Self-referential two-pass pattern: confirmed by multiple Salesforce community sources and SFDMU documentation — self-reference must be done in a subsequent update rather than the original insert

---
*Architecture research for: Python CLI Salesforce org-to-org data migration (CFSuite managed package config objects)*
*Researched: 2026-03-12*
