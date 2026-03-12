import json
import subprocess

from migrate.models import Credentials, OrgInfo, ProductionOrgError, SFCLINotFoundError


def _is_sandbox_url(instance_url: str) -> bool:
    """Detect sandbox/scratch orgs by instance URL pattern."""
    url = (instance_url or "").lower()
    return ".sandbox." in url or ".scratch." in url or "--" in url


def _get_alias_map() -> dict[str, str]:
    """Return username -> alias mapping from sf alias registry."""
    result = subprocess.run(
        ["sf", "alias", "list", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    data = json.loads(result.stdout)
    return {entry["value"]: entry["alias"] for entry in data.get("result", [])}


def list_orgs() -> list[OrgInfo]:
    """Return all orgs authenticated with SF CLI."""
    try:
        result = subprocess.run(
            ["sf", "org", "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise SFCLINotFoundError(
            "sf CLI not found. Install from: https://developer.salesforce.com/tools/salesforcecli"
        )
    data = json.loads(result.stdout)
    alias_map = _get_alias_map()
    all_orgs = data.get("result", {}).get("nonScratchOrgs", []) + data.get(
        "result", {}
    ).get("scratchOrgs", [])
    seen = set()
    org_list = []
    for org in all_orgs:
        username = org["username"]
        alias = alias_map.get(username, org.get("alias", username))
        if alias in seen:
            continue
        seen.add(alias)
        org_list.append(
            OrgInfo(
                alias=alias,
                username=username,
                is_sandbox=_is_sandbox_url(org.get("instanceUrl", "")),
            )
        )
    return org_list


def get_credentials(alias: str) -> Credentials:
    """Extract access token and instance URL for a given org alias."""
    result = subprocess.run(
        ["sf", "org", "display", "--json", "--target-org", alias],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"Could not retrieve credentials for org '{alias}'. Is it authenticated?"
        )
    data = json.loads(result.stdout)
    r = data["result"]
    return Credentials(
        access_token=r["accessToken"],
        instance_url=r["instanceUrl"],
        alias=r.get("alias", alias),
        username=r["username"],
    )


def assert_not_production(org: OrgInfo) -> None:
    """Raise ProductionOrgError if org is a production org."""
    if not org.is_sandbox:
        raise ProductionOrgError(
            f"'{org.alias}' is a production org. Migration targets must be sandboxes or scratch orgs."
        )
