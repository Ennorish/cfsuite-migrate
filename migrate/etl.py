"""ETL helpers: extract, duplicate-skip, RecordType remap, two-pass insert."""
from simple_salesforce import Salesforce

from migrate import sf_api


def extract_records(client: Salesforce, sobject_api_name: str, fields: list[str]) -> list[dict]:
    """Query all records of sobject_api_name returning only the requested fields."""
    soql = f"SELECT {','.join(fields)} FROM {sobject_api_name}"
    return sf_api.query_all(client, soql)


def find_existing_keys(
    client: Salesforce,
    sobject_api_name: str,
    key_field: str,
    key_values: list[str],
) -> set[str]:
    """Return the subset of key_values that already exist in the target org.

    Used to skip records that are already present so inserts stay idempotent.
    Returns an empty set when key_values is empty (avoids malformed SOQL).
    """
    if not key_values:
        return set()
    quoted = ", ".join(f"'{v}'" for v in key_values)
    soql = f"SELECT {key_field} FROM {sobject_api_name} WHERE {key_field} IN ({quoted})"
    records = sf_api.query_all(client, soql)
    return {r[key_field] for r in records}


def remap_record_types(
    records: list[dict],
    source_rt_map: dict[str, str],
    target_rt_map: dict[str, str],
    rt_field: str = "RecordTypeId",
) -> None:
    """Replace source RecordTypeId values with target RecordTypeId values in place.

    Looks up the DeveloperName from source_rt_map (reverse lookup), then finds
    the corresponding target Id from target_rt_map.

    Raises ValueError if a source RecordTypeId maps to a DeveloperName that is
    absent from target_rt_map.
    """
    # Build reverse map: source Id -> DeveloperName
    reverse_source = {v: k for k, v in source_rt_map.items()}

    for record in records:
        source_id = record[rt_field]
        dev_name = reverse_source[source_id]
        if dev_name not in target_rt_map:
            raise ValueError(
                f"RecordType DeveloperName '{dev_name}' not found in target org. "
                "Ensure the RecordType exists in the target before migrating."
            )
        record[rt_field] = target_rt_map[dev_name]


def two_pass_insert(
    client: Salesforce,
    sobject: str,
    records: list[dict],
    self_ref_field: str,
    name_field: str,
) -> None:
    """Insert self-referential records in two passes to resolve parent links.

    Pass 1: Insert all records with self_ref_field set to None.
            Build a name -> new_id mapping from the insert results.
    Pass 2: For records that originally had a non-null self_ref_field, call
            a single-record update on the newly-inserted child to set the
            self_ref_field to the new parent ID (resolved by name_field value
            of the original parent record).
    """
    # Preserve original self-ref values before nulling them out
    original_parents: list[str | None] = [r.get(self_ref_field) for r in records]
    original_names: list[str] = [r[name_field] for r in records]

    # Pass 1: copy records with self_ref_field nulled
    pass1_records = [{**r, self_ref_field: None} for r in records]
    results = sf_api.insert_records(client, sobject, pass1_records)

    # Build name -> new_id map from insert results
    name_to_new_id: dict[str, str] = {
        original_names[i]: results[i]["id"] for i in range(len(results))
    }

    # Pass 2: update children that had a non-null original parent reference
    sobject_obj = getattr(client, sobject)
    for i, original_parent_name in enumerate(original_parents):
        if original_parent_name is not None:
            new_child_id = results[i]["id"]
            new_parent_id = name_to_new_id[original_parent_name]
            sobject_obj.update(new_child_id, {self_ref_field: new_parent_id})
