"""Tests for validate_results in migrate/pipeline.py."""
from migrate.pipeline import validate_results


class TestValidateResultsAllMatch:
    """All results matching: every result has match=True."""

    def test_all_match(self):
        results = [
            {"object": "Entitlement", "extracted": 5, "skipped": 0, "inserted": 5},
            {"object": "CFSuite Request Flow", "extracted": 3, "skipped": 1, "inserted": 2},
        ]
        validated = validate_results(results)
        assert len(validated) == 2
        assert validated[0]["match"] is True
        assert validated[1]["match"] is True

    def test_all_match_preserves_original_fields(self):
        results = [
            {"object": "Entitlement", "extracted": 10, "skipped": 2, "inserted": 8},
        ]
        validated = validate_results(results)
        assert validated[0]["object"] == "Entitlement"
        assert validated[0]["extracted"] == 10
        assert validated[0]["skipped"] == 2
        assert validated[0]["inserted"] == 8


class TestValidateResultsMismatch:
    """One mismatch: extracted != skipped + inserted."""

    def test_mismatch_flagged(self):
        results = [
            {"object": "Entitlement", "extracted": 10, "skipped": 3, "inserted": 5},
        ]
        validated = validate_results(results)
        assert validated[0]["match"] is False

    def test_partial_mismatch_in_mixed_results(self):
        results = [
            {"object": "Entitlement", "extracted": 5, "skipped": 0, "inserted": 5},
            {"object": "CFSuite Request Flow", "extracted": 10, "skipped": 3, "inserted": 5},
        ]
        validated = validate_results(results)
        assert validated[0]["match"] is True
        assert validated[1]["match"] is False


class TestValidateResultsEmpty:
    """Empty results: returns empty list."""

    def test_empty_results(self):
        assert validate_results([]) == []
