"""Unit tests for migrate/objects/preferred_comms.py — all SF calls mocked."""
from unittest.mock import MagicMock, patch

from migrate.objects import preferred_comms


# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

SOURCE_RT_MAP = {"Standard": "012src1", "Custom": "012src2"}
TARGET_RT_MAP = {"Standard": "012tgt1", "Custom": "012tgt2"}

SOURCE_RECORDS = [
    {
        "Name": "Comms Config A",
        "RecordTypeId": "012src1",
        "cfsuite1__Active__c": True,
        "cfsuite1__Description__c": "Email config",
        "cfsuite1__Events__c": "Case Created",
        "cfsuite1__Included_Categories__c": None,
        "cfsuite1__Excluded_Categories__c": None,
        "cfsuite1__Record_Type_Names__c": None,
        "cfsuite1__Status__c": "Active",
    },
    {
        "Name": "Comms Config B",
        "RecordTypeId": "012src2",
        "cfsuite1__Active__c": False,
        "cfsuite1__Description__c": None,
        "cfsuite1__Events__c": "Case Updated",
        "cfsuite1__Included_Categories__c": None,
        "cfsuite1__Excluded_Categories__c": None,
        "cfsuite1__Record_Type_Names__c": None,
        "cfsuite1__Status__c": None,
    },
]


# ---------------------------------------------------------------------------
# Test 1: Normal migration with RecordType remap
# ---------------------------------------------------------------------------


def test_normal_migration_remap_inserts_with_target_rt():
    """Records are inserted with target RecordTypeId after remap."""
    source_client = MagicMock()
    target_client = MagicMock()

    with (
        patch("migrate.objects.preferred_comms.etl") as mock_etl,
        patch("migrate.objects.preferred_comms.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [r.copy() for r in SOURCE_RECORDS]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]

        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        mock_etl.find_existing_keys.return_value = set()
        mock_sf_api.insert_records.return_value = [
            {"id": "new001", "success": True},
            {"id": "new002", "success": True},
        ]

        result = preferred_comms.migrate_preferred_comms(source_client, target_client)

        assert result["extracted"] == 2
        assert result["skipped"] == 0
        assert result["inserted"] == 2

        # Verify insert was called with target RT IDs
        call_args = mock_sf_api.insert_records.call_args
        inserted = call_args[0][2]
        assert inserted[0]["RecordTypeId"] == "012tgt1"
        assert inserted[1]["RecordTypeId"] == "012tgt2"


# ---------------------------------------------------------------------------
# Test 2: Skip existing records
# ---------------------------------------------------------------------------


def test_skip_existing_records():
    """Records whose Name already exists in target are excluded from insert."""
    source_client = MagicMock()
    target_client = MagicMock()

    with (
        patch("migrate.objects.preferred_comms.etl") as mock_etl,
        patch("migrate.objects.preferred_comms.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [r.copy() for r in SOURCE_RECORDS]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]

        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        # "Comms Config A" already in target
        mock_etl.find_existing_keys.return_value = {"Comms Config A"}
        mock_sf_api.insert_records.return_value = [{"id": "new002", "success": True}]

        result = preferred_comms.migrate_preferred_comms(source_client, target_client)

        assert result["extracted"] == 2
        assert result["skipped"] == 1
        assert result["inserted"] == 1

        # Only Config B should be inserted
        call_args = mock_sf_api.insert_records.call_args
        inserted = call_args[0][2]
        assert len(inserted) == 1
        assert inserted[0]["Name"] == "Comms Config B"


# ---------------------------------------------------------------------------
# Test 3: Empty source returns all zeros
# ---------------------------------------------------------------------------


def test_empty_source_returns_zeros():
    """migrate_preferred_comms returns all-zero counts when source is empty."""
    source_client = MagicMock()
    target_client = MagicMock()

    with (
        patch("migrate.objects.preferred_comms.etl") as mock_etl,
        patch("migrate.objects.preferred_comms.sf_api") as _mock_sf_api,
    ):
        mock_etl.extract_records.return_value = []

        result = preferred_comms.migrate_preferred_comms(source_client, target_client)

        assert result == {"extracted": 0, "skipped": 0, "inserted": 0}
        mock_etl.remap_record_types.assert_not_called()
