"""Tests for the request_flow object migrator."""
from unittest.mock import MagicMock, call, patch

import pytest

from migrate.objects.request_flow import migrate_request_flows


@pytest.fixture()
def source_client():
    return MagicMock()


@pytest.fixture()
def target_client():
    return MagicMock()


class TestMigrateRequestFlows:
    def test_normal_migration_with_recordtype_remap(self, source_client, target_client):
        """Source records with RecordTypeId are remapped to target RecordTypeId."""
        source_records = [
            {
                "Name": "Flow-A",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": None,
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "Desc A",
                "CFSuite__Order__c": 1,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
            {
                "Name": "Flow-B",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": None,
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "Desc B",
                "CFSuite__Order__c": 2,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
        ]

        # After remap, RecordTypeId should be "tgt-rt-001"
        def fake_remap(records, source_rt_map, target_rt_map, rt_field="RecordTypeId"):
            for r in records:
                r["RecordTypeId"] = "tgt-rt-001"

        with (
            patch("migrate.objects.request_flow.etl.extract_records", return_value=source_records),
            patch("migrate.objects.request_flow.sf_api.get_record_type_map", side_effect=[
                {"DisplayCategory": "src-rt-001"},
                {"DisplayCategory": "tgt-rt-001"},
            ]),
            patch("migrate.objects.request_flow.etl.remap_record_types", side_effect=fake_remap) as mock_remap,
            patch("migrate.objects.request_flow.etl.find_existing_keys", return_value=set()),
            patch("migrate.objects.request_flow.sf_api.insert_records", return_value=[
                {"id": "new-id-001"},
                {"id": "new-id-002"},
            ]) as mock_insert,
        ):
            result = migrate_request_flows(source_client, target_client)

        mock_remap.assert_called_once()
        inserted = mock_insert.call_args[0][2]
        assert all(r["RecordTypeId"] == "tgt-rt-001" for r in inserted)
        assert result == {"extracted": 2, "skipped": 0, "inserted": 2}

    def test_self_referential_resolution(self, source_client, target_client):
        """Category Journey referencing Display Category is resolved in pass-2."""
        # Display Category record (no self-refs)
        # Category Journey record referencing Display Category via CFSuite__Display_Category__c
        source_records = [
            {
                "Name": "Display Cat",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": None,
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "",
                "CFSuite__Order__c": 1,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
            {
                "Name": "Cat Journey",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": "old-display-cat-id",
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "",
                "CFSuite__Order__c": 2,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
        ]
        # insert_records returns new IDs for inserted records
        insert_results = [{"id": "new-display-001"}, {"id": "new-journey-001"}]
        # target_client.CFSuite__Request_Flow__c.update will be called for Cat Journey

        with (
            patch("migrate.objects.request_flow.etl.extract_records", return_value=source_records),
            patch("migrate.objects.request_flow.sf_api.get_record_type_map", side_effect=[
                {"DisplayCategory": "src-rt-001"},
                {"DisplayCategory": "tgt-rt-001"},
            ]),
            patch("migrate.objects.request_flow.etl.remap_record_types"),
            patch("migrate.objects.request_flow.etl.find_existing_keys", return_value=set()),
            patch("migrate.objects.request_flow.sf_api.insert_records", return_value=insert_results) as mock_insert,
        ):
            result = migrate_request_flows(source_client, target_client)

        # Pass 1: records inserted with self-ref fields set to None
        inserted_records = mock_insert.call_args[0][2]
        assert inserted_records[0]["CFSuite__Display_Category__c"] is None
        assert inserted_records[1]["CFSuite__Display_Category__c"] is None

        # Pass 2: target_client.CFSuite__Request_Flow__c.update called for Cat Journey
        sobject_obj = getattr(target_client, "CFSuite__Request_Flow__c")
        # The Cat Journey's CFSuite__Display_Category__c should be updated to new-display-001
        sobject_obj.update.assert_called_once_with(
            "new-journey-001",
            {"CFSuite__Display_Category__c": "new-display-001"},
        )

        assert result == {"extracted": 2, "skipped": 0, "inserted": 2}

    def test_skip_existing_records(self, source_client, target_client):
        """Records whose Name already exists in target are excluded before insert."""
        source_records = [
            {
                "Name": "Flow-Existing",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": None,
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "",
                "CFSuite__Order__c": 1,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
            {
                "Name": "Flow-New",
                "RecordTypeId": "src-rt-001",
                "CFSuite__Display_Category__c": None,
                "CFSuite__Category_Journey__c": None,
                "CFSuite__Active__c": True,
                "CFSuite__Description__c": "",
                "CFSuite__Order__c": 2,
                "CFSuite__Entitlement_Name__c": "Ent-A",
            },
        ]

        with (
            patch("migrate.objects.request_flow.etl.extract_records", return_value=source_records),
            patch("migrate.objects.request_flow.sf_api.get_record_type_map", side_effect=[
                {"DisplayCategory": "src-rt-001"},
                {"DisplayCategory": "tgt-rt-001"},
            ]),
            patch("migrate.objects.request_flow.etl.remap_record_types"),
            patch("migrate.objects.request_flow.etl.find_existing_keys", return_value={"Flow-Existing"}),
            patch("migrate.objects.request_flow.sf_api.insert_records", return_value=[{"id": "new-id-001"}]) as mock_insert,
        ):
            result = migrate_request_flows(source_client, target_client)

        inserted = mock_insert.call_args[0][2]
        assert len(inserted) == 1
        assert inserted[0]["Name"] == "Flow-New"
        assert result == {"extracted": 2, "skipped": 1, "inserted": 1}

    def test_empty_source_returns_zeros(self, source_client, target_client):
        """No records in source -> returns all zeros, no insert calls."""
        with (
            patch("migrate.objects.request_flow.etl.extract_records", return_value=[]),
            patch("migrate.objects.request_flow.sf_api.get_record_type_map") as mock_rt,
            patch("migrate.objects.request_flow.sf_api.insert_records") as mock_insert,
        ):
            result = migrate_request_flows(source_client, target_client)

        mock_rt.assert_not_called()
        mock_insert.assert_not_called()
        assert result == {"extracted": 0, "skipped": 0, "inserted": 0}
