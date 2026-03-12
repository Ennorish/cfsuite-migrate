"""Unit tests for migrate/sf_api.py — all Salesforce calls mocked."""
from unittest.mock import MagicMock, patch

import pytest

from migrate.models import Credentials
from migrate import sf_api


@pytest.fixture
def creds():
    return Credentials(
        access_token="TOKEN123",
        instance_url="https://example.salesforce.com",
        alias="source",
        username="user@example.com",
    )


# ---------------------------------------------------------------------------
# build_client
# ---------------------------------------------------------------------------


def test_build_client_uses_access_token_as_session_id(creds):
    """build_client must pass access_token as session_id to Salesforce()."""
    with patch("migrate.sf_api.Salesforce") as MockSF:
        sf_api.build_client(creds)
        MockSF.assert_called_once_with(
            session_id=creds.access_token,
            instance_url=creds.instance_url,
        )


def test_build_client_returns_salesforce_instance(creds):
    """build_client returns the Salesforce instance produced by the constructor."""
    with patch("migrate.sf_api.Salesforce") as MockSF:
        fake_client = MagicMock()
        MockSF.return_value = fake_client
        result = sf_api.build_client(creds)
        assert result is fake_client


# ---------------------------------------------------------------------------
# query_all
# ---------------------------------------------------------------------------


def test_query_all_strips_attributes_key():
    """query_all must remove the 'attributes' key from every record."""
    client = MagicMock()
    client.query_all.return_value = {
        "records": [
            {"attributes": {"type": "Account"}, "Id": "001", "Name": "Acme"},
            {"attributes": {"type": "Account"}, "Id": "002", "Name": "Beta"},
        ]
    }
    results = sf_api.query_all(client, "SELECT Id, Name FROM Account")
    assert results == [{"Id": "001", "Name": "Acme"}, {"Id": "002", "Name": "Beta"}]


def test_query_all_delegates_soql_to_client():
    """query_all forwards the SOQL string to client.query_all."""
    client = MagicMock()
    soql = "SELECT Id FROM Contact"
    client.query_all.return_value = {"records": []}
    sf_api.query_all(client, soql)
    client.query_all.assert_called_once_with(soql)


def test_query_all_empty_result():
    """query_all handles an empty records list."""
    client = MagicMock()
    client.query_all.return_value = {"records": []}
    assert sf_api.query_all(client, "SELECT Id FROM Foo") == []


# ---------------------------------------------------------------------------
# insert_records
# ---------------------------------------------------------------------------


def test_insert_records_delegates_to_bulk():
    """insert_records calls client.bulk.<sobject>.insert and returns results."""
    client = MagicMock()
    fake_bulk_obj = MagicMock()
    fake_bulk_obj.insert.return_value = [
        {"id": "0011", "success": True},
        {"id": "0012", "success": True},
    ]
    # Support getattr(client.bulk, sobject)
    client.bulk.__getattr__ = MagicMock(return_value=fake_bulk_obj)

    records = [{"Name": "A"}, {"Name": "B"}]
    results = sf_api.insert_records(client, "Account", records)

    fake_bulk_obj.insert.assert_called_once_with(records)
    assert results == [{"id": "0011", "success": True}, {"id": "0012", "success": True}]


def test_insert_records_returns_list_from_bulk():
    """insert_records returns whatever the bulk insert operation returns."""
    client = MagicMock()
    expected = [{"id": "abc", "success": True}]
    getattr(client.bulk, "Custom__c").insert.return_value = expected

    result = sf_api.insert_records(client, "Custom__c", [{"Field__c": "val"}])
    assert result == expected


# ---------------------------------------------------------------------------
# get_record_type_map
# ---------------------------------------------------------------------------


def test_get_record_type_map_returns_developer_name_to_id():
    """get_record_type_map returns {DeveloperName: Id} for the given SObject."""
    client = MagicMock()
    client.query_all.return_value = {
        "records": [
            {"attributes": {}, "Id": "012A", "DeveloperName": "Standard"},
            {"attributes": {}, "Id": "012B", "DeveloperName": "Custom"},
        ]
    }
    result = sf_api.get_record_type_map(client, "Case")
    assert result == {"Standard": "012A", "Custom": "012B"}


def test_get_record_type_map_queries_correct_sobject_type():
    """get_record_type_map queries RecordType filtered by the given SobjectType."""
    client = MagicMock()
    client.query_all.return_value = {"records": []}
    sf_api.get_record_type_map(client, "Entitlement")
    call_args = client.query_all.call_args[0][0]
    assert "SobjectType = 'Entitlement'" in call_args
    assert "RecordType" in call_args


def test_get_record_type_map_empty():
    """get_record_type_map returns empty dict when no RecordTypes exist."""
    client = MagicMock()
    client.query_all.return_value = {"records": []}
    result = sf_api.get_record_type_map(client, "NoRecordTypeObject")
    assert result == {}
