"""Unit tests for migrate/objects/community_request.py — all SF calls mocked."""
from unittest.mock import MagicMock, patch

from migrate.objects import community_request


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

SOURCE_RT_MAP = {"ProcessType": "012src1", "QuestionType": "012src2"}
TARGET_RT_MAP = {"ProcessType": "012tgt1", "QuestionType": "012tgt2"}

SOURCE_RECORDS = [
    {
        "Name": "Flow A",
        "RecordTypeId": "012src1",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": "src-rf-001",
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": "desc",
        "CFSuite__Order__c": 1,
        "CFSuite__Question_Text__c": None,
        "CFSuite__Response_Value__c": None,
    },
    {
        "Name": "Flow B",
        "RecordTypeId": "012src1",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": "src-rf-001",
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": "desc2",
        "CFSuite__Order__c": 2,
        "CFSuite__Question_Text__c": None,
        "CFSuite__Response_Value__c": None,
    },
    {
        "Name": "Flow C",
        "RecordTypeId": "012src2",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": None,
        "CFSuite__Active__c": False,
        "CFSuite__Description__c": None,
        "CFSuite__Order__c": 3,
        "CFSuite__Question_Text__c": "Q?",
        "CFSuite__Response_Value__c": None,
    },
]


# ---------------------------------------------------------------------------
# Test 1: Normal migration with RecordType remap and skip
# ---------------------------------------------------------------------------


def test_normal_migration_remap_and_skip():
    """3 source records, 1 already in target -> 2 inserted with target RecordTypeId."""
    source_client = MagicMock()
    target_client = MagicMock()

    with (
        patch("migrate.objects.community_request.etl") as mock_etl,
        patch("migrate.objects.community_request.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [r.copy() for r in SOURCE_RECORDS]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]
        # etl.remap_record_types mutates in place, returns None
        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        # Cross-object lookup: RF ids in source records
        mock_sf_api.query_all.side_effect = [
            # source RF query (get Names for src-rf-001 id)
            [{"Id": "src-rf-001", "Name": "RF Alpha"}],
            # target RF query (all RFs in target)
            [{"Id": "tgt-rf-001", "Name": "RF Alpha"}],
        ]

        # "Flow A" already exists in target -> skip
        mock_etl.find_existing_keys.return_value = {"Flow A"}

        mock_etl.two_pass_insert.return_value = None
        mock_sf_api.insert_records.return_value = []

        result = community_request.migrate_community_requests(source_client, target_client)

        assert result["extracted"] == 3
        assert result["skipped"] == 1
        assert result["inserted"] == 2


# ---------------------------------------------------------------------------
# Test 2: Self-referential resolution via two-pass insert
# ---------------------------------------------------------------------------


def test_self_referential_resolution():
    """Question record's Parent_Question__c points to Process -> two-pass resolves it."""
    source_client = MagicMock()
    target_client = MagicMock()

    process_rec = {
        "Name": "Process 1",
        "RecordTypeId": "012src1",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": None,
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": None,
        "CFSuite__Order__c": 1,
        "CFSuite__Question_Text__c": None,
        "CFSuite__Response_Value__c": None,
    }
    question_rec = {
        "Name": "Question 1",
        "RecordTypeId": "012src2",
        "CFSuite__Parent_Question__c": "Process 1",
        "CFSuite__Request_Flow__c": None,
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": None,
        "CFSuite__Order__c": 1,
        "CFSuite__Question_Text__c": "Q?",
        "CFSuite__Response_Value__c": None,
    }

    with (
        patch("migrate.objects.community_request.etl") as mock_etl,
        patch("migrate.objects.community_request.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [process_rec.copy(), question_rec.copy()]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]

        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        # No cross-object RF lookups needed (all None)
        mock_sf_api.query_all.return_value = []

        mock_etl.find_existing_keys.return_value = set()

        # Capture what was passed to two_pass_insert
        captured_records = []
        def fake_two_pass(client, sobject, records, self_ref_field, name_field):
            captured_records.extend(records)
        mock_etl.two_pass_insert.side_effect = fake_two_pass

        result = community_request.migrate_community_requests(source_client, target_client)

        # two_pass_insert should have been called
        mock_etl.two_pass_insert.assert_called_once()
        call_args = mock_etl.two_pass_insert.call_args
        assert call_args[0][3] == community_request.SELF_REF_FIELD
        assert call_args[0][4] == "Name"
        assert result["inserted"] == 2


# ---------------------------------------------------------------------------
# Test 3: Cross-object lookup resolves RF by Name
# ---------------------------------------------------------------------------


def test_cross_object_lookup_resolves_by_name():
    """Source record has CFSuite__Request_Flow__c = 'src-rf-001' -> resolved to target Id."""
    source_client = MagicMock()
    target_client = MagicMock()

    record = {
        "Name": "CR 1",
        "RecordTypeId": "012src1",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": "src-rf-001",
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": None,
        "CFSuite__Order__c": 1,
        "CFSuite__Question_Text__c": None,
        "CFSuite__Response_Value__c": None,
    }

    with (
        patch("migrate.objects.community_request.etl") as mock_etl,
        patch("migrate.objects.community_request.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [record.copy()]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]

        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        mock_sf_api.query_all.side_effect = [
            [{"Id": "src-rf-001", "Name": "RF Alpha"}],
            [{"Id": "tgt-rf-999", "Name": "RF Alpha"}],
        ]

        mock_etl.find_existing_keys.return_value = set()

        captured_records = []
        def fake_two_pass(client, sobject, records, self_ref_field, name_field):
            captured_records.extend(records)
        mock_etl.two_pass_insert.side_effect = fake_two_pass

        community_request.migrate_community_requests(source_client, target_client)

        # The inserted record should have target RF Id
        assert len(captured_records) == 1
        assert captured_records[0]["CFSuite__Request_Flow__c"] == "tgt-rf-999"


# ---------------------------------------------------------------------------
# Test 4: Cross-object lookup miss -> field set to None
# ---------------------------------------------------------------------------


def test_cross_object_lookup_miss_sets_none():
    """Source record references RF not in target -> field set to None, no error."""
    source_client = MagicMock()
    target_client = MagicMock()

    record = {
        "Name": "CR Missing",
        "RecordTypeId": "012src1",
        "CFSuite__Parent_Question__c": None,
        "CFSuite__Request_Flow__c": "src-rf-unknown",
        "CFSuite__Active__c": True,
        "CFSuite__Description__c": None,
        "CFSuite__Order__c": 1,
        "CFSuite__Question_Text__c": None,
        "CFSuite__Response_Value__c": None,
    }

    with (
        patch("migrate.objects.community_request.etl") as mock_etl,
        patch("migrate.objects.community_request.sf_api") as mock_sf_api,
    ):
        mock_etl.extract_records.return_value = [record.copy()]
        mock_sf_api.get_record_type_map.side_effect = [SOURCE_RT_MAP, TARGET_RT_MAP]

        def do_remap(records, src_map, tgt_map, rt_field="RecordTypeId"):
            reverse = {v: k for k, v in src_map.items()}
            for r in records:
                r[rt_field] = tgt_map[reverse[r[rt_field]]]
        mock_etl.remap_record_types.side_effect = do_remap

        # Source RF query returns the unknown id's Name
        mock_sf_api.query_all.side_effect = [
            [{"Id": "src-rf-unknown", "Name": "RF Unknown"}],
            # Target has no RF with that name
            [],
        ]

        mock_etl.find_existing_keys.return_value = set()

        captured_records = []
        def fake_two_pass(client, sobject, records, self_ref_field, name_field):
            captured_records.extend(records)
        mock_etl.two_pass_insert.side_effect = fake_two_pass

        # Should not raise
        result = community_request.migrate_community_requests(source_client, target_client)

        assert result["inserted"] == 1
        assert captured_records[0]["CFSuite__Request_Flow__c"] is None


# ---------------------------------------------------------------------------
# Test 5: Empty source returns all zeros
# ---------------------------------------------------------------------------


def test_empty_source_returns_zeros():
    """migrate_community_requests returns all-zero counts when source is empty."""
    source_client = MagicMock()
    target_client = MagicMock()

    with (
        patch("migrate.objects.community_request.etl") as mock_etl,
        patch("migrate.objects.community_request.sf_api") as _mock_sf_api,
    ):
        mock_etl.extract_records.return_value = []

        result = community_request.migrate_community_requests(source_client, target_client)

        assert result == {"extracted": 0, "skipped": 0, "inserted": 0}
