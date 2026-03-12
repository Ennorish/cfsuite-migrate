"""Pipeline orchestrator: runs object migrators in dependency order."""
import migrate.objects.community_request
import migrate.objects.entitlement
import migrate.objects.preferred_comms
import migrate.objects.request_flow

# Dependency-ordered list of (display_name, migrator_function) pairs.
# Order must be: Entitlement -> Request Flow -> Community Request -> Preferred Comms
OBJECT_MIGRATORS = [
    ("Entitlement", migrate.objects.entitlement.migrate_entitlements),
    ("CFSuite Request Flow", migrate.objects.request_flow.migrate_request_flows),
    ("CFSuite Community Request", migrate.objects.community_request.migrate_community_requests),
    ("CFSuite Preferred Comms Config", migrate.objects.preferred_comms.migrate_preferred_comms),
]


def run_migration(source_client, target_client, objects: list[str]) -> list[dict]:
    """Run migrators for the selected objects in dependency order.

    Args:
        source_client: Authenticated Salesforce client for source org.
        target_client: Authenticated Salesforce client for target org.
        objects: List of display names of objects to migrate (e.g. ["Entitlement"]).
                 Order of this list does not affect execution order — migrators
                 always run in the dependency order defined by OBJECT_MIGRATORS.

    Returns:
        List of result dicts: [{"object": name, "extracted": N, "skipped": N, "inserted": N}, ...]
        Only includes results for objects that were selected.
    """
    results = []
    for name, migrator_fn in OBJECT_MIGRATORS:
        if name not in objects:
            continue
        result = migrator_fn(source_client, target_client)
        results.append({"object": name, **result})
    return results
