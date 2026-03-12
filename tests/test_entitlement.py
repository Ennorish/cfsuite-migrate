"""Tests for the entitlement object migrator."""
from unittest.mock import MagicMock, patch

import pytest

from migrate.objects.entitlement import migrate_entitlements


@pytest.fixture()
def source_client():
    return MagicMock()


@pytest.fixture()
def target_client():
    return MagicMock()


class TestMigrateEntitlements:
    def test_normal_migration_skips_existing(self, source_client, target_client):
        """3 source records, 1 already in target -> extracts 3, skips 1, inserts 2."""
        source_records = [
            {"Name": "Ent-A", "AccountId": "001A", "StartDate": "2024-01-01", "EndDate": None, "Status": "Active", "Type": "Type1"},
            {"Name": "Ent-B", "AccountId": "001B", "StartDate": "2024-02-01", "EndDate": None, "Status": "Active", "Type": "Type1"},
            {"Name": "Ent-C", "AccountId": "001C", "StartDate": "2024-03-01", "EndDate": None, "Status": "Active", "Type": "Type2"},
        ]

        with (
            patch("migrate.objects.entitlement.etl.extract_records", return_value=source_records) as mock_extract,
            patch("migrate.objects.entitlement.etl.find_existing_keys", return_value={"Ent-A"}) as mock_find,
            patch("migrate.objects.entitlement.sf_api.insert_records", return_value=[{"id": "003X"}, {"id": "003Y"}]) as mock_insert,
        ):
            result = migrate_entitlements(source_client, target_client)

        mock_extract.assert_called_once_with(
            source_client,
            "Entitlement",
            ["Name", "AccountId", "StartDate", "EndDate", "Status", "Type"],
        )
        mock_find.assert_called_once_with(
            target_client, "Entitlement", "Name", ["Ent-A", "Ent-B", "Ent-C"]
        )
        inserted_records = mock_insert.call_args[0][2]
        assert len(inserted_records) == 2
        inserted_names = {r["Name"] for r in inserted_records}
        assert inserted_names == {"Ent-B", "Ent-C"}

        assert result == {"extracted": 3, "skipped": 1, "inserted": 2}

    def test_all_skipped_no_insert_call(self, source_client, target_client):
        """All source records already exist in target -> no insert call, inserted=0."""
        source_records = [
            {"Name": "Ent-A", "AccountId": "001A", "StartDate": "2024-01-01", "EndDate": None, "Status": "Active", "Type": "Type1"},
            {"Name": "Ent-B", "AccountId": "001B", "StartDate": "2024-02-01", "EndDate": None, "Status": "Active", "Type": "Type1"},
        ]

        with (
            patch("migrate.objects.entitlement.etl.extract_records", return_value=source_records),
            patch("migrate.objects.entitlement.etl.find_existing_keys", return_value={"Ent-A", "Ent-B"}),
            patch("migrate.objects.entitlement.sf_api.insert_records") as mock_insert,
        ):
            result = migrate_entitlements(source_client, target_client)

        mock_insert.assert_not_called()
        assert result == {"extracted": 2, "skipped": 2, "inserted": 0}

    def test_empty_source_returns_zeros(self, source_client, target_client):
        """No records in source -> returns extracted=0, skipped=0, inserted=0."""
        with (
            patch("migrate.objects.entitlement.etl.extract_records", return_value=[]),
            patch("migrate.objects.entitlement.etl.find_existing_keys") as mock_find,
            patch("migrate.objects.entitlement.sf_api.insert_records") as mock_insert,
        ):
            result = migrate_entitlements(source_client, target_client)

        mock_find.assert_not_called()
        mock_insert.assert_not_called()
        assert result == {"extracted": 0, "skipped": 0, "inserted": 0}
