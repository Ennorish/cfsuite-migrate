import json
import subprocess

from migrate.models import Credentials, OrgInfo, ProductionOrgError, SFCLINotFoundError


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
    all_orgs = data.get("result", {}).get("nonScratchOrgs", []) + data.get(
        "result", {}
    ).get("scratchOrgs", [])
    return [
        OrgInfo(
            alias=org.get("alias", org["username"]),
            username=org["username"],
            is_sandbox=org.get("isSandbox", False),
        )
        for org in all_orgs
    ]


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
