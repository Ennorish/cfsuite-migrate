"""Unit tests for migrate/etl.py — all Salesforce calls mocked."""
from unittest.mock import MagicMock, patch

import pytest

from migrate import etl


# ---------------------------------------------------------------------------
# extract_records
# ---------------------------------------------------------------------------


def test_extract_records_builds_correct_soql():
    """extract_records must build SELECT <fields> FROM <sobject> and call query_all."""
    client = MagicMock()
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.query_all.return_value = []
        etl.extract_records(client, "Account", ["Id", "Name", "Type"])
        mock_sf_api.query_all.assert_called_once_with(
            client, "SELECT Id,Name,Type FROM Account"
        )


def test_extract_records_returns_query_all_result():
    """extract_records returns whatever query_all returns."""
    client = MagicMock()
    expected = [{"Id": "001", "Name": "Acme"}]
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.query_all.return_value = expected
        result = etl.extract_records(client, "Account", ["Id", "Name"])
        assert result == expected


# ---------------------------------------------------------------------------
# find_existing_keys
# ---------------------------------------------------------------------------


def test_find_existing_keys_returns_set_of_values():
    """find_existing_keys returns a set of key field values found in target."""
    client = MagicMock()
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.query_all.return_value = [
            {"Name": "Alpha"},
            {"Name": "Beta"},
        ]
        result = etl.find_existing_keys(client, "Account", "Name", ["Alpha", "Beta", "Gamma"])
        assert result == {"Alpha", "Beta"}


def test_find_existing_keys_empty_key_values():
    """find_existing_keys returns empty set when key_values is empty."""
    client = MagicMock()
    with patch("migrate.etl.sf_api") as mock_sf_api:
        result = etl.find_existing_keys(client, "Account", "Name", [])
        mock_sf_api.query_all.assert_not_called()
        assert result == set()


def test_find_existing_keys_soql_contains_in_clause():
    """find_existing_keys queries the target org using an IN clause."""
    client = MagicMock()
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.query_all.return_value = []
        etl.find_existing_keys(client, "Contact", "Email", ["a@b.com", "c@d.com"])
        call_soql = mock_sf_api.query_all.call_args[0][1]
        assert "Contact" in call_soql
        assert "Email" in call_soql
        assert "IN" in call_soql


# ---------------------------------------------------------------------------
# remap_record_types
# ---------------------------------------------------------------------------


def test_remap_record_types_swaps_ids_correctly():
    """remap_record_types replaces source IDs with target IDs via DeveloperName."""
    source_rt_map = {"Standard": "012SRC1", "Custom": "012SRC2"}
    target_rt_map = {"Standard": "012TGT1", "Custom": "012TGT2"}
    records = [
        {"Id": "001", "RecordTypeId": "012SRC1"},
        {"Id": "002", "RecordTypeId": "012SRC2"},
    ]
    etl.remap_record_types(records, source_rt_map, target_rt_map)
    assert records[0]["RecordTypeId"] == "012TGT1"
    assert records[1]["RecordTypeId"] == "012TGT2"


def test_remap_record_types_raises_on_missing_developer_name():
    """remap_record_types raises ValueError when source DeveloperName absent from target."""
    source_rt_map = {"Standard": "012SRC1", "LegacyType": "012SRC3"}
    target_rt_map = {"Standard": "012TGT1"}  # LegacyType missing
    records = [{"RecordTypeId": "012SRC3"}]
    with pytest.raises(ValueError, match="LegacyType"):
        etl.remap_record_types(records, source_rt_map, target_rt_map)


def test_remap_record_types_custom_rt_field():
    """remap_record_types uses the rt_field parameter when provided."""
    source_rt_map = {"TypeA": "SRCA"}
    target_rt_map = {"TypeA": "TGTA"}
    records = [{"MyRTField": "SRCA"}]
    etl.remap_record_types(records, source_rt_map, target_rt_map, rt_field="MyRTField")
    assert records[0]["MyRTField"] == "TGTA"


def test_remap_record_types_mutates_in_place():
    """remap_record_types mutates the records list in place (returns None)."""
    source_rt_map = {"Standard": "SRC1"}
    target_rt_map = {"Standard": "TGT1"}
    records = [{"RecordTypeId": "SRC1"}]
    result = etl.remap_record_types(records, source_rt_map, target_rt_map)
    assert result is None


# ---------------------------------------------------------------------------
# two_pass_insert
# ---------------------------------------------------------------------------


def test_two_pass_insert_pass1_nulls_self_ref_field():
    """two_pass_insert pass 1 inserts records with self_ref_field set to None."""
    client = MagicMock()
    records = [
        {"Name": "Root", "Parent__c": None},
        {"Name": "Child", "Parent__c": "Root"},
    ]
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.insert_records.return_value = [
            {"id": "new001", "success": True},
            {"id": "new002", "success": True},
        ]
        etl.two_pass_insert(client, "Account", records, "Parent__c", "Name")
        inserted = mock_sf_api.insert_records.call_args[0][2]
        for rec in inserted:
            assert rec["Parent__c"] is None


def test_two_pass_insert_pass2_sets_parent_id():
    """two_pass_insert pass 2 updates children's self_ref_field to the new parent ID."""
    client = MagicMock()
    records = [
        {"Name": "Root", "Parent__c": None},
        {"Name": "Child", "Parent__c": "Root"},
    ]
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.insert_records.return_value = [
            {"id": "new001", "success": True},
            {"id": "new002", "success": True},
        ]
        etl.two_pass_insert(client, "Account", records, "Parent__c", "Name")
        # Pass 2: update new002 (Child) to point parent to new001 (Root)
        account_obj = getattr(client, "Account")
        account_obj.update.assert_called_once_with("new002", {"Parent__c": "new001"})


def test_two_pass_insert_no_children_skips_pass2():
    """two_pass_insert does not call update when no records have a non-null self_ref_field."""
    client = MagicMock()
    records = [
        {"Name": "Root1", "Parent__c": None},
        {"Name": "Root2", "Parent__c": None},
    ]
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.insert_records.return_value = [
            {"id": "new001", "success": True},
            {"id": "new002", "success": True},
        ]
        etl.two_pass_insert(client, "Account", records, "Parent__c", "Name")
        account_obj = getattr(client, "Account")
        account_obj.update.assert_not_called()


def test_two_pass_insert_does_not_mutate_original_records():
    """two_pass_insert does not alter the caller's records list."""
    client = MagicMock()
    records = [
        {"Name": "Root", "Parent__c": None},
        {"Name": "Child", "Parent__c": "Root"},
    ]
    originals = [r.copy() for r in records]
    with patch("migrate.etl.sf_api") as mock_sf_api:
        mock_sf_api.insert_records.return_value = [
            {"id": "n1", "success": True},
            {"id": "n2", "success": True},
        ]
        etl.two_pass_insert(client, "Account", records, "Parent__c", "Name")
    assert records == originals
