"""Migrator for cfsuite1__CFSuite_Preferred_Comms_Config__c records."""
from simple_salesforce import Salesforce

from migrate import etl, sf_api

SOBJECT = "cfsuite1__CFSuite_Preferred_Comms_Config__c"


def migrate_preferred_comms(
    source_client: Salesforce, target_client: Salesforce
) -> dict:
    """Migrate cfsuite1__CFSuite_Preferred_Comms_Config__c records from source to target org.

    Dynamically discovers createable fields shared between both orgs.

    Returns a dict with keys: extracted, skipped, inserted.
    """
    fields = sf_api.get_shared_createable_fields(source_client, target_client, SOBJECT)
    records = etl.extract_records(source_client, SOBJECT, fields)
    if not records:
        return {"extracted": 0, "skipped": 0, "inserted": 0}

    extracted_count = len(records)

    # Step 2: Remap RecordTypes
    source_rt_map = sf_api.get_record_type_map(source_client, SOBJECT)
    target_rt_map = sf_api.get_record_type_map(target_client, SOBJECT)
    etl.remap_record_types(records, source_rt_map, target_rt_map)

    # Step 3: Skip existing
    names = [r["Name"] for r in records]
    existing = etl.find_existing_keys(target_client, SOBJECT, "Name", names)
    to_insert = [r for r in records if r["Name"] not in existing]
    skipped_count = len(records) - len(to_insert)

    if not to_insert:
        return {"extracted": extracted_count, "skipped": skipped_count, "inserted": 0}

    # Step 4: Insert
    sf_api.insert_records(target_client, SOBJECT, to_insert)

    return {
        "extracted": extracted_count,
        "skipped": skipped_count,
        "inserted": len(to_insert),
    }
