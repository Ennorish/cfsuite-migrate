"""Request Flow object migrator with RecordType remap and two-pass self-referential insert."""
from simple_salesforce import Salesforce

import migrate.etl as etl
import migrate.sf_api as sf_api

_SOBJECT = "CFSuite__Request_Flow__c"
# Include Id so we can build a source_id -> name map for self-ref resolution.
# Id is stripped before insert (Salesforce rejects it as a non-writable field).
_FIELDS = [
    "Id",
    "Name",
    "RecordTypeId",
    "CFSuite__Display_Category__c",
    "CFSuite__Category_Journey__c",
    "CFSuite__Active__c",
    "CFSuite__Description__c",
    "CFSuite__Order__c",
    "CFSuite__Entitlement_Name__c",
]
_SELF_REF_FIELDS = ["CFSuite__Display_Category__c", "CFSuite__Category_Journey__c"]


def migrate_request_flows(source_client: Salesforce, target_client: Salesforce) -> dict:
    """Extract CFSuite__Request_Flow__c records from source and insert into target.

    Steps:
    1. Extract records (including Id) from source.
    2. Build source_id -> name map for self-ref resolution.
    3. Remap RecordTypeId from source to target by DeveloperName.
    4. Skip records already in target by Name.
    5. Two-pass insert to resolve both self-referential fields:
       Pass 1 — insert all records with self-ref fields nulled (and Id stripped).
       Pass 2 — for each record that had non-null self-ref values, update with
                the resolved target IDs (source_id -> name -> new_target_id).

    Returns:
        dict with keys: extracted (int), skipped (int), inserted (int)
    """
    records = etl.extract_records(source_client, _SOBJECT, _FIELDS)

    if not records:
        return {"extracted": 0, "skipped": 0, "inserted": 0}

    # Build source_id -> name map before any mutation
    source_id_to_name: dict[str, str] = {
        r["Id"]: r["Name"] for r in records if r.get("Id")
    }

    source_rt_map = sf_api.get_record_type_map(source_client, _SOBJECT)
    target_rt_map = sf_api.get_record_type_map(target_client, _SOBJECT)
    etl.remap_record_types(records, source_rt_map, target_rt_map)

    existing = etl.find_existing_keys(
        target_client, _SOBJECT, "Name", [r["Name"] for r in records]
    )
    to_insert = [r for r in records if r["Name"] not in existing]

    if not to_insert:
        return {
            "extracted": len(records),
            "skipped": len(existing),
            "inserted": 0,
        }

    # Save original self-ref values (source IDs) before nulling
    original_refs: list[dict] = [
        {f: r.get(f) for f in _SELF_REF_FIELDS} for r in to_insert
    ]
    original_names: list[str] = [r["Name"] for r in to_insert]

    # Pass 1: insert with Id stripped and all self-ref fields nulled out
    pass1_records = [
        {k: v for k, v in r.items() if k != "Id" and k not in _SELF_REF_FIELDS}
        | {f: None for f in _SELF_REF_FIELDS}
        for r in to_insert
    ]
    results = sf_api.insert_records(target_client, _SOBJECT, pass1_records)

    # Build name -> new_target_id map from insert results
    name_to_new_id: dict[str, str] = {
        original_names[i]: results[i]["id"] for i in range(len(results))
    }

    # Pass 2: update records that had non-null self-ref values
    sobject_obj = getattr(target_client, _SOBJECT)
    for i, orig in enumerate(original_refs):
        updates: dict[str, str] = {}
        for field in _SELF_REF_FIELDS:
            source_id = orig[field]
            if source_id is not None:
                # Resolve: source_id -> source record name -> new target id
                parent_name = source_id_to_name.get(source_id)
                if parent_name is not None and parent_name in name_to_new_id:
                    updates[field] = name_to_new_id[parent_name]
        if updates:
            new_child_id = results[i]["id"]
            sobject_obj.update(new_child_id, updates)

    return {
        "extracted": len(records),
        "skipped": len(existing),
        "inserted": len(to_insert),
    }
