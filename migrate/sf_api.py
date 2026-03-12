"""Salesforce API wrapper used by all ETL pipelines."""
from simple_salesforce import Salesforce

from migrate.models import Credentials


def build_client(creds: Credentials) -> Salesforce:
    """Construct a simple-salesforce client from a Credentials object."""
    return Salesforce(
        session_id=creds.access_token,
        instance_url=creds.instance_url,
    )


def query_all(client: Salesforce, soql: str) -> list[dict]:
    """Execute a SOQL query and return records with the 'attributes' key stripped."""
    response = client.query_all(soql)
    records = []
    for record in response["records"]:
        clean = {k: v for k, v in record.items() if k != "attributes"}
        records.append(clean)
    return records


def insert_records(client: Salesforce, sobject: str, records: list[dict]) -> list[dict]:
    """Insert records into the given SObject using REST API; returns list of result dicts.

    Automatically strips 'Id' from records since it's never valid on create.
    """
    sobject_obj = getattr(client, sobject)
    results = []
    for record in records:
        payload = {k: v for k, v in record.items() if k != "Id"}
        result = sobject_obj.create(payload)
        results.append(result)
    return results


# Lookup targets that can't be transferred between orgs
_NON_TRANSFERABLE_REFS = {"User", "Group"}


def get_shared_createable_fields(
    source_client: Salesforce,
    target_client: Salesforce,
    sobject: str,
    include_id: bool = False,
) -> list[str]:
    """Return createable fields shared between source and target, excluding non-transferable lookups.

    Always includes Name (even if auto-number / non-createable) for dedup/matching.
    Always includes Id when include_id=True.
    Strips fields that reference User/Group (OwnerId, etc.) since those IDs
    don't transfer across orgs. RecordTypeId is kept (handled by remap logic).

    Non-createable fields (Id, auto-number Name) must be stripped before insert.
    """
    source_desc = getattr(source_client, sobject).describe()
    target_desc = getattr(target_client, sobject).describe()

    target_createable = {f["name"] for f in target_desc["fields"] if f["createable"]}

    fields = []
    if include_id:
        fields.append("Id")

    name_included = False
    for f in source_desc["fields"]:
        # Always include Name for dedup/matching even if not createable
        if f["name"] == "Name":
            fields.append("Name")
            name_included = True
            continue
        if not f["createable"] or f["name"] not in target_createable:
            continue
        # Skip non-transferable lookups (User, Group) but keep RecordTypeId
        if f["type"] == "reference" and f["name"] != "RecordTypeId":
            refs = set(f.get("referenceTo", []))
            if refs and refs <= _NON_TRANSFERABLE_REFS:
                continue
        fields.append(f["name"])

    if not name_included:
        fields.append("Name")
    return fields


def get_non_createable_fields(client: Salesforce, sobject: str) -> set[str]:
    """Return set of field names that are NOT createable (must be stripped before insert)."""
    desc = getattr(client, sobject).describe()
    return {f["name"] for f in desc["fields"] if not f["createable"]}


def get_record_type_map(client: Salesforce, sobject: str) -> dict[str, str]:
    """Return a mapping of DeveloperName -> Id for all RecordTypes on sobject."""
    soql = f"SELECT Id, DeveloperName FROM RecordType WHERE SobjectType = '{sobject}'"
    results = query_all(client, soql)
    return {r["DeveloperName"]: r["Id"] for r in results}
