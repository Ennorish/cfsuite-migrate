"""Tests for the FastAPI web UI routes."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from migrate.models import OrgInfo, SFCLINotFoundError
from migrate.web import app

client = TestClient(app)

# -- Test data --
sandbox1 = OrgInfo(alias="dev", username="dev@example.com", is_sandbox=True)
sandbox2 = OrgInfo(alias="uat", username="uat@example.com", is_sandbox=True)
prod_org = OrgInfo(alias="prod", username="prod@example.com", is_sandbox=False)


# -- Index --

def test_index_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# -- GET /api/orgs --

def test_get_orgs_returns_org_list():
    with patch("migrate.web.list_orgs", return_value=[sandbox1, sandbox2]):
        resp = client.get("/api/orgs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["alias"] == "dev"
    assert data[0]["username"] == "dev@example.com"
    assert data[0]["is_sandbox"] is True
    assert "alias" in data[0]
    assert "username" in data[0]
    assert "is_sandbox" in data[0]


def test_get_orgs_sf_cli_not_found():
    with patch("migrate.web.list_orgs", side_effect=SFCLINotFoundError("sf CLI not found")):
        resp = client.get("/api/orgs")
    assert resp.status_code == 500
    assert "error" in resp.json()


# -- GET /api/objects --

def test_get_objects_returns_list():
    resp = client.get("/api/objects")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 4
    for item in data:
        assert isinstance(item, str)


# -- POST /api/migrate validation --

def test_migrate_missing_params():
    resp = client.post("/api/migrate", json={})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_migrate_same_source_target():
    resp = client.post("/api/migrate", json={
        "source": "dev",
        "target": "dev",
        "objects": ["Entitlement"],
    })
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_migrate_blocks_production_target():
    with patch("migrate.web.list_orgs", return_value=[sandbox1, prod_org]):
        resp = client.post("/api/migrate", json={
            "source": "dev",
            "target": "prod",
            "objects": ["Entitlement"],
        })
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
    assert "production" in body["error"].lower()


def test_migrate_target_not_found():
    with patch("migrate.web.list_orgs", return_value=[sandbox1]):
        resp = client.post("/api/migrate", json={
            "source": "dev",
            "target": "nonexistent",
            "objects": ["Entitlement"],
        })
    assert resp.status_code == 400
    assert "error" in resp.json()


# -- POST /api/migrate success (SSE stream) --

def test_migrate_success_streams_sse():
    mock_results = [{"object": "Entitlement", "extracted": 5, "skipped": 1, "inserted": 4}]

    with (
        patch("migrate.web.list_orgs", return_value=[sandbox1, sandbox2]),
        patch("migrate.web.get_credentials", return_value=MagicMock()),
        patch("migrate.web.build_client", return_value=MagicMock()),
        patch("migrate.web.run_migration", return_value=mock_results),
    ):
        resp = client.post("/api/migrate", json={
            "source": "dev",
            "target": "uat",
            "objects": ["Entitlement"],
        })

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    # Parse SSE data lines
    events = []
    for line in resp.text.splitlines():
        if line.startswith("data:"):
            json_str = line[5:].strip()
            if json_str:
                events.append(json.loads(json_str))

    # Must have at least one event
    assert len(events) >= 1

    # Last event must be the complete event
    final = events[-1]
    assert final.get("event") == "complete"
    assert final.get("status") == "success"
    assert len(final["results"]) == 1
    assert final["results"][0]["inserted"] == 4
    assert final["results"][0]["extracted"] == 5
    assert final["results"][0]["skipped"] == 1


# -- serve CLI command --

def test_serve_command_calls_web_serve():
    from typer.testing import CliRunner
    from migrate.main import app as cli_app

    runner = CliRunner()
    with patch("migrate.web.serve") as mock_serve:
        result = runner.invoke(cli_app, ["serve", "--port", "9999"])
    mock_serve.assert_called_once_with(port=9999)
