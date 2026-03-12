"""Migrator for CFSuite__Data_Settings__c (Community Request) records."""
from simple_salesforce import Salesforce

from migrate import etl, sf_api

SOBJECT = "CFSuite__Data_Settings__c"
FIELDS = [
    "Name",
    "RecordTypeId",
    "CFSuite__Parent_Question__c",
    "CFSuite__Request_Flow__c",
    "CFSuite__Active__c",
    "CFSuite__Description__c",
    "CFSuite__Order__c",
    "CFSuite__Question_Text__c",
    "CFSuite__Response_Value__c",
]
SELF_REF_FIELD = "CFSuite__Parent_Question__c"
CROSS_REF_FIELD = "CFSuite__Request_Flow__c"


def migrate_community_requests(
    source_client: Salesforce, target_client: Salesforce
) -> dict:
    """Migrate CFSuite__Data_Settings__c records from source to target org.

    Steps:
    1. Extract all records from source.
    2. Remap RecordTypeIds by DeveloperName.
    3. Resolve cross-object CFSuite__Request_Flow__c lookup by Name matching.
    4. Skip records already present in target (matched by Name).
    5. Insert remaining records via two-pass insert to resolve Parent_Question__c.

    Returns a dict with keys: extracted, skipped, inserted.
    """
    records = etl.extract_records(source_client, SOBJECT, FIELDS)
    if not records:
        return {"extracted": 0, "skipped": 0, "inserted": 0}

    extracted_count = len(records)

    # Step 2: Remap RecordTypes
    source_rt_map = sf_api.get_record_type_map(source_client, SOBJECT)
    target_rt_map = sf_api.get_record_type_map(target_client, SOBJECT)
    etl.remap_record_types(records, source_rt_map, target_rt_map)

    # Step 3: Resolve cross-object Request Flow lookup
    _resolve_request_flow_lookup(records, source_client, target_client)

    # Step 4: Skip existing
    names = [r["Name"] for r in records]
    existing = etl.find_existing_keys(target_client, SOBJECT, "Name", names)
    to_insert = [r for r in records if r["Name"] not in existing]
    skipped_count = len(records) - len(to_insert)

    if not to_insert:
        return {"extracted": extracted_count, "skipped": skipped_count, "inserted": 0}

    # Step 5: Two-pass insert to resolve Parent_Question__c
    etl.two_pass_insert(target_client, SOBJECT, to_insert, SELF_REF_FIELD, "Name")

    return {
        "extracted": extracted_count,
        "skipped": skipped_count,
        "inserted": len(to_insert),
    }


def _resolve_request_flow_lookup(
    records: list[dict],
    source_client: Salesforce,
    target_client: Salesforce,
) -> None:
    """Resolve CFSuite__Request_Flow__c from source Id to target Id via Name matching.

    For each record with a non-null CROSS_REF_FIELD:
    - Query source to get Request Flow Names for those Ids.
    - Query target to get all Request Flow Name -> Id mappings.
    - Replace source Id with target Id (or None if not found in target).

    Mutates records in place.
    """
    # Collect unique source RF Ids (ignore None)
    source_rf_ids = {
        r[CROSS_REF_FIELD]
        for r in records
        if r.get(CROSS_REF_FIELD) is not None
    }

    if not source_rf_ids:
        return

    # Query source for Names of those Ids
    ids_in = ", ".join(f"'{i}'" for i in source_rf_ids)
    source_rf_records = sf_api.query_all(
        source_client,
        f"SELECT Id, Name FROM CFSuite__Request_Flow__c WHERE Id IN ({ids_in})",
    )
    source_id_to_name: dict[str, str] = {r["Id"]: r["Name"] for r in source_rf_records}

    # Query target for all RF Name -> Id
    target_rf_records = sf_api.query_all(
        target_client,
        "SELECT Id, Name FROM CFSuite__Request_Flow__c",
    )
    target_name_to_id: dict[str, str] = {r["Name"]: r["Id"] for r in target_rf_records}

    # Replace source Id with target Id (graceful degradation on miss)
    for record in records:
        src_id = record.get(CROSS_REF_FIELD)
        if src_id is None:
            continue
        name = source_id_to_name.get(src_id)
        record[CROSS_REF_FIELD] = target_name_to_id.get(name) if name else None
