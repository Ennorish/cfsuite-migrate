"""Entitlement object migrator."""
from simple_salesforce import Salesforce

import migrate.etl as etl
import migrate.sf_api as sf_api

_FIELDS = ["Name", "AccountId", "StartDate", "EndDate", "Status", "Type"]
_SOBJECT = "Entitlement"


def migrate_entitlements(source_client: Salesforce, target_client: Salesforce) -> dict:
    """Extract Entitlement records from source and insert into target, skipping existing.

    Skips records whose Name already exists in target (idempotent).
    AccountId is carried over as-is — both orgs share the same Account names in
    CFSuite sandbox setup.

    Returns:
        dict with keys: extracted (int), skipped (int), inserted (int)
    """
    records = etl.extract_records(source_client, _SOBJECT, _FIELDS)

    if not records:
        return {"extracted": 0, "skipped": 0, "inserted": 0}

    existing = etl.find_existing_keys(
        target_client, _SOBJECT, "Name", [r["Name"] for r in records]
    )
    to_insert = [r for r in records if r["Name"] not in existing]

    if to_insert:
        sf_api.insert_records(target_client, _SOBJECT, to_insert)

    return {
        "extracted": len(records),
        "skipped": len(existing),
        "inserted": len(to_insert),
    }
