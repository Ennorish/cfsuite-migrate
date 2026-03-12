"""Tests for migrate.auth module covering SF CLI integration and production guard."""

import json
import pytest
from pytest_subprocess import FakeProcess

from migrate.auth import assert_not_production, get_credentials, list_orgs
from migrate.models import Credentials, OrgInfo, ProductionOrgError, SFCLINotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SF_ORG_LIST_EMPTY = json.dumps(
    {"status": 0, "result": {"nonScratchOrgs": [], "scratchOrgs": []}}
)

SF_ORG_LIST_TWO_ORGS = json.dumps(
    {
        "status": 0,
        "result": {
            "nonScratchOrgs": [
                {
                    "alias": "ProdOrg",
                    "username": "prod@example.com",
                    "connectedStatus": "Connected",
                    "isSandbox": False,
                    "isDefaultUsername": False,
                }
            ],
            "scratchOrgs": [
                {
                    "alias": "MyDev",
                    "username": "mydev@example.com",
                    "connectedStatus": "Connected",
                    "isSandbox": True,
                    "isDefaultUsername": False,
                }
            ],
        },
    }
)

SF_ORG_DISPLAY_VALID = json.dumps(
    {
        "status": 0,
        "result": {
            "accessToken": "abc123",
            "instanceUrl": "https://mydev.salesforce.com",
            "alias": "MyDev",
            "username": "mydev@example.com",
        },
    }
)


# ---------------------------------------------------------------------------
# list_orgs tests
# ---------------------------------------------------------------------------


def test_list_orgs_empty(fp: FakeProcess) -> None:
    """list_orgs() returns empty list when sf returns zero orgs."""
    fp.register(["sf", "org", "list", "--json"], stdout=SF_ORG_LIST_EMPTY)
    result = list_orgs()
    assert result == []


def test_list_orgs_two_orgs(fp: FakeProcess) -> None:
    """list_orgs() returns two OrgInfo objects with correct fields."""
    fp.register(["sf", "org", "list", "--json"], stdout=SF_ORG_LIST_TWO_ORGS)
    result = list_orgs()
    assert len(result) == 2

    # Find by alias
    by_alias = {org.alias: org for org in result}
    assert "MyDev" in by_alias
    assert "ProdOrg" in by_alias

    assert by_alias["MyDev"].username == "mydev@example.com"
    assert by_alias["MyDev"].is_sandbox is True

    assert by_alias["ProdOrg"].username == "prod@example.com"
    assert by_alias["ProdOrg"].is_sandbox is False


def test_list_orgs_sf_cli_not_found(fp: FakeProcess) -> None:
    """list_orgs() raises SFCLINotFoundError when sf CLI is not installed."""
    def _raise_file_not_found(process: object) -> None:
        raise FileNotFoundError("No such file or directory: 'sf'")

    fp.register(["sf", "org", "list", "--json"], callback=_raise_file_not_found)
    with pytest.raises(SFCLINotFoundError):
        list_orgs()


# ---------------------------------------------------------------------------
# get_credentials tests
# ---------------------------------------------------------------------------


def test_get_credentials_valid(fp: FakeProcess) -> None:
    """get_credentials() returns Credentials with correct fields for valid alias."""
    fp.register(
        ["sf", "org", "display", "--json", "--target-org", "MyDev"],
        stdout=SF_ORG_DISPLAY_VALID,
    )
    creds = get_credentials("MyDev")
    assert isinstance(creds, Credentials)
    assert creds.access_token == "abc123"
    assert creds.instance_url == "https://mydev.salesforce.com"


def test_get_credentials_bad_alias(fp: FakeProcess) -> None:
    """get_credentials() raises ValueError with alias name when sf returns exit code 1."""
    fp.register(
        ["sf", "org", "display", "--json", "--target-org", "BadAlias"],
        returncode=1,
        stdout="",
    )
    with pytest.raises(ValueError, match="BadAlias"):
        get_credentials("BadAlias")


# ---------------------------------------------------------------------------
# assert_not_production tests
# ---------------------------------------------------------------------------


def test_assert_not_production_sandbox() -> None:
    """assert_not_production() returns without raising for sandbox orgs."""
    org = OrgInfo(alias="MyDev", username="mydev@example.com", is_sandbox=True)
    # Should not raise
    assert_not_production(org)


def test_assert_not_production_production() -> None:
    """assert_not_production() raises ProductionOrgError for production orgs."""
    org = OrgInfo(alias="ProdOrg", username="prod@example.com", is_sandbox=False)
    with pytest.raises(ProductionOrgError, match="ProdOrg"):
        assert_not_production(org)
