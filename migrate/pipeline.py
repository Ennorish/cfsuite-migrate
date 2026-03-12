"""Pipeline orchestrator: runs object migrators in dependency order."""
import migrate.objects.community_request
import migrate.objects.entitlement
import migrate.objects.preferred_comms
import migrate.objects.request_flow

# Dependency-ordered list of (display_name, sobject_api_name, migrator_function) tuples.
# Order must be: Entitlement -> Request Flow -> Community Request -> Preferred Comms
OBJECT_MIGRATORS = [
    ("Entitlement", "Entitlement", migrate.objects.entitlement.migrate_entitlements),
    ("CFSuite Request Flow", "cfsuite1__CFSuite_Request_Flow__c", migrate.objects.request_flow.migrate_request_flows),
    ("CFSuite Community Request", "cfsuite1__Data_Settings__c", migrate.objects.community_request.migrate_community_requests),
    ("CFSuite Preferred Comms Config", "cfsuite1__CFSuite_Preferred_Comms_Config__c", migrate.objects.preferred_comms.migrate_preferred_comms),
]


def get_available_objects(client) -> list[str]:
    """Return display names of objects that exist in the given org."""
    described = client.describe()
    org_sobjects = {s["name"] for s in described["sobjects"]}
    return [name for name, api_name, _ in OBJECT_MIGRATORS if api_name in org_sobjects]


def run_migration(
    source_client,
    target_client,
    objects: list[str],
    on_progress=None,
) -> list[dict]:
    """Run migrators for the selected objects in dependency order.

    Args:
        source_client: Authenticated Salesforce client for source org.
        target_client: Authenticated Salesforce client for target org.
        objects: List of display names of objects to migrate (e.g. ["Entitlement"]).
                 Order of this list does not affect execution order — migrators
                 always run in the dependency order defined by OBJECT_MIGRATORS.
        on_progress: Optional callback called with (name, event, data) where event
                     is "start" (before migrator runs, data={}) or "done" (after
                     migrator completes, data=result dict with "object" key).

    Returns:
        List of result dicts: [{"object": name, "extracted": N, "skipped": N, "inserted": N}, ...]
        Only includes results for objects that were selected.
    """
    results = []
    for name, _api_name, migrator_fn in OBJECT_MIGRATORS:
        if name not in objects:
            continue
        if on_progress is not None:
            on_progress(name, "start", {})
        try:
            result = migrator_fn(source_client, target_client)
            row = {"object": name, **result}
        except Exception as e:
            row = {"object": name, "extracted": 0, "skipped": 0, "inserted": 0, "error": str(e)}
        if on_progress is not None:
            on_progress(name, "done", row)
        results.append(row)
    return results


def validate_results(results: list[dict]) -> list[dict]:
    """Annotate migration results with a match boolean.

    Args:
        results: List of result dicts with "extracted", "skipped", "inserted" keys.

    Returns:
        New list of dicts — each original result plus a "match" key (bool).
        match is True when extracted == skipped + inserted.
    """
    return [
        {**r, "match": r["extracted"] == r["skipped"] + r["inserted"]}
        for r in results
    ]
