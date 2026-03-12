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
    """Bulk-insert records into the given SObject; returns the list of result dicts."""
    bulk_obj = getattr(client.bulk, sobject)
    return bulk_obj.insert(records)


def get_record_type_map(client: Salesforce, sobject: str) -> dict[str, str]:
    """Return a mapping of DeveloperName -> Id for all RecordTypes on sobject."""
    soql = f"SELECT Id, DeveloperName FROM RecordType WHERE SobjectType = '{sobject}'"
    results = query_all(client, soql)
    return {r["DeveloperName"]: r["Id"] for r in results}
