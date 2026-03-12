"""Entitlement object migrator."""
from simple_salesforce import Salesforce

import migrate.etl as etl
import migrate.sf_api as sf_api

# Status is a non-writable system field — excluded from insert.
_FIELDS = ["Name", "AccountId", "StartDate", "EndDate", "Type"]
_SOBJECT = "Entitlement"


def migrate_entitlements(source_client: Salesforce, target_client: Salesforce) -> dict:
    """Extract Entitlement records from source and insert into target, skipping existing.

    Skips records whose Name already exists in target (idempotent).
    AccountId is resolved by Account Name matching across orgs.

    Returns:
        dict with keys: extracted (int), skipped (int), inserted (int)
    """
    records = etl.extract_records(source_client, _SOBJECT, _FIELDS)

    if not records:
        return {"extracted": 0, "skipped": 0, "inserted": 0}

    # Resolve AccountId: source Account Id -> Account Name -> target Account Id
    _resolve_account_ids(records, source_client, target_client)

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


def _resolve_account_ids(
    records: list[dict],
    source_client: Salesforce,
    target_client: Salesforce,
) -> None:
    """Map all Entitlements to a single Account in target, created from source org name.

    Looks up the source org's Organization Name, finds or creates an Account with
    that name in the target, and sets all records' AccountId to it.
    """
    # Get source org name
    org_info = sf_api.query_all(source_client, "SELECT Name FROM Organization LIMIT 1")
    org_name = org_info[0]["Name"] if org_info else "CFSuite Migration Account"

    # Find or create the account in target
    existing = sf_api.query_all(
        target_client, f"SELECT Id FROM Account WHERE Name = '{org_name}' LIMIT 1"
    )
    if existing:
        account_id = existing[0]["Id"]
    else:
        result = target_client.Account.create({"Name": org_name})
        account_id = result["id"]

    # Set all records to this single account
    for record in records:
        record["AccountId"] = account_id
