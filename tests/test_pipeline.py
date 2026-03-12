"""Tests for the pipeline orchestrator (migrate/pipeline.py)."""
from unittest.mock import MagicMock, patch

import pytest

from migrate.pipeline import run_migration


@pytest.fixture
def mock_clients():
    source = MagicMock(name="source_client")
    target = MagicMock(name="target_client")
    return source, target


class TestRunMigrationAllObjects:
    """All four objects selected: all migrators called in dependency order."""

    def test_all_objects_calls_all_migrators(self, mock_clients):
        source, target = mock_clients
        all_objects = [
            "Entitlement",
            "CFSuite Request Flow",
            "CFSuite Community Request",
            "CFSuite Preferred Comms Config",
        ]
        fake_results = [
            {"extracted": 5, "skipped": 0, "inserted": 5},
            {"extracted": 3, "skipped": 1, "inserted": 2},
            {"extracted": 7, "skipped": 2, "inserted": 5},
            {"extracted": 4, "skipped": 0, "inserted": 4},
        ]
        with (
            patch(
                "migrate.objects.entitlement.migrate_entitlements",
                return_value=fake_results[0],
            ) as mock_ent,
            patch(
                "migrate.objects.request_flow.migrate_request_flows",
                return_value=fake_results[1],
            ) as mock_rf,
            patch(
                "migrate.objects.community_request.migrate_community_requests",
                return_value=fake_results[2],
            ) as mock_cr,
            patch(
                "migrate.objects.preferred_comms.migrate_preferred_comms",
                return_value=fake_results[3],
            ) as mock_pc,
        ):
            results = run_migration(source, target, all_objects)

        mock_ent.assert_called_once_with(source, target)
        mock_rf.assert_called_once_with(source, target)
        mock_cr.assert_called_once_with(source, target)
        mock_pc.assert_called_once_with(source, target)

        assert len(results) == 4
        assert results[0] == {"object": "Entitlement", **fake_results[0]}
        assert results[1] == {"object": "CFSuite Request Flow", **fake_results[1]}
        assert results[2] == {"object": "CFSuite Community Request", **fake_results[2]}
        assert results[3] == {"object": "CFSuite Preferred Comms Config", **fake_results[3]}

    def test_all_objects_results_contain_correct_counts(self, mock_clients):
        source, target = mock_clients
        all_objects = [
            "Entitlement",
            "CFSuite Request Flow",
            "CFSuite Community Request",
            "CFSuite Preferred Comms Config",
        ]
        with (
            patch(
                "migrate.objects.entitlement.migrate_entitlements",
                return_value={"extracted": 10, "skipped": 2, "inserted": 8},
            ),
            patch(
                "migrate.objects.request_flow.migrate_request_flows",
                return_value={"extracted": 6, "skipped": 3, "inserted": 3},
            ),
            patch(
                "migrate.objects.community_request.migrate_community_requests",
                return_value={"extracted": 0, "skipped": 0, "inserted": 0},
            ),
            patch(
                "migrate.objects.preferred_comms.migrate_preferred_comms",
                return_value={"extracted": 2, "skipped": 2, "inserted": 0},
            ),
        ):
            results = run_migration(source, target, all_objects)

        assert results[0]["extracted"] == 10
        assert results[0]["inserted"] == 8
        assert results[2]["extracted"] == 0


class TestRunMigrationSubsetObjects:
    """Subset selected: only those migrators called, in dependency order."""

    def test_entitlement_and_preferred_comms_only(self, mock_clients):
        source, target = mock_clients
        selected = ["CFSuite Preferred Comms Config", "Entitlement"]  # reversed order in input
        with (
            patch(
                "migrate.objects.entitlement.migrate_entitlements",
                return_value={"extracted": 2, "skipped": 0, "inserted": 2},
            ) as mock_ent,
            patch(
                "migrate.objects.request_flow.migrate_request_flows",
            ) as mock_rf,
            patch(
                "migrate.objects.community_request.migrate_community_requests",
            ) as mock_cr,
            patch(
                "migrate.objects.preferred_comms.migrate_preferred_comms",
                return_value={"extracted": 3, "skipped": 1, "inserted": 2},
            ) as mock_pc,
        ):
            results = run_migration(source, target, selected)

        mock_ent.assert_called_once_with(source, target)
        mock_rf.assert_not_called()
        mock_cr.assert_not_called()
        mock_pc.assert_called_once_with(source, target)

        assert len(results) == 2
        # Entitlement should come first (dependency order), not input order
        assert results[0]["object"] == "Entitlement"
        assert results[1]["object"] == "CFSuite Preferred Comms Config"

    def test_only_community_request(self, mock_clients):
        source, target = mock_clients
        selected = ["CFSuite Community Request"]
        with (
            patch(
                "migrate.objects.entitlement.migrate_entitlements",
            ) as mock_ent,
            patch(
                "migrate.objects.request_flow.migrate_request_flows",
            ) as mock_rf,
            patch(
                "migrate.objects.community_request.migrate_community_requests",
                return_value={"extracted": 5, "skipped": 0, "inserted": 5},
            ) as mock_cr,
            patch(
                "migrate.objects.preferred_comms.migrate_preferred_comms",
            ) as mock_pc,
        ):
            results = run_migration(source, target, selected)

        mock_ent.assert_not_called()
        mock_rf.assert_not_called()
        mock_cr.assert_called_once_with(source, target)
        mock_pc.assert_not_called()

        assert len(results) == 1
        assert results[0]["object"] == "CFSuite Community Request"
        assert results[0]["inserted"] == 5


class TestRunMigrationEmptyList:
    """Empty object list: returns empty results, no migrators called."""

    def test_empty_objects_list(self, mock_clients):
        source, target = mock_clients
        with (
            patch(
                "migrate.objects.entitlement.migrate_entitlements",
            ) as mock_ent,
            patch(
                "migrate.objects.request_flow.migrate_request_flows",
            ) as mock_rf,
            patch(
                "migrate.objects.community_request.migrate_community_requests",
            ) as mock_cr,
            patch(
                "migrate.objects.preferred_comms.migrate_preferred_comms",
            ) as mock_pc,
        ):
            results = run_migration(source, target, [])

        mock_ent.assert_not_called()
        mock_rf.assert_not_called()
        mock_cr.assert_not_called()
        mock_pc.assert_not_called()

        assert results == []
