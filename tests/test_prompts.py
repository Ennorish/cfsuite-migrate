"""Unit tests for migrate/prompts.py — org selection and object selection prompts."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from migrate.models import OrgInfo, ProductionOrgError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_sandbox_orgs():
    return [
        OrgInfo(alias="Dev1", username="dev1@example.com", is_sandbox=True),
        OrgInfo(alias="Dev2", username="dev2@example.com", is_sandbox=True),
    ]


@pytest.fixture
def prod_org():
    return OrgInfo(alias="Prod", username="prod@example.com", is_sandbox=False)


# ---------------------------------------------------------------------------
# select_source_org tests
# ---------------------------------------------------------------------------

class TestSelectSourceOrg:
    def test_returns_matching_orginfo_for_selected_alias(self, two_sandbox_orgs):
        """Mocked questionary.select returns 'Dev1' — function returns Dev1 OrgInfo."""
        mock_question = MagicMock()
        mock_question.ask.return_value = "Dev1"

        with patch("questionary.select", return_value=mock_question):
            from migrate.prompts import select_source_org
            result = select_source_org(two_sandbox_orgs)

        assert result.alias == "Dev1"
        assert result.username == "dev1@example.com"

    def test_no_orgs_prints_guidance_and_exits(self, capsys):
        """Empty org list prints 'sf org login web' and raises SystemExit(0)."""
        from migrate.prompts import select_source_org

        with pytest.raises(SystemExit) as exc_info:
            select_source_org([])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "sf org login web" in captured.out


# ---------------------------------------------------------------------------
# select_target_org tests
# ---------------------------------------------------------------------------

class TestSelectTargetOrg:
    def test_excludes_source_from_choices(self, two_sandbox_orgs):
        """Source org (Dev1) must not appear in questionary choices."""
        mock_question = MagicMock()
        mock_question.ask.return_value = "Dev2"
        captured_choices = {}

        def capture_select(prompt, choices):
            captured_choices["choices"] = choices
            return mock_question

        with patch("questionary.select", side_effect=capture_select), \
             patch("migrate.auth.assert_not_production"):
            from migrate.prompts import select_target_org
            result = select_target_org(two_sandbox_orgs, source_alias="Dev1")

        assert "Dev1" not in captured_choices["choices"]
        assert result.alias == "Dev2"

    def test_production_org_selected_prints_error_and_exits(self, two_sandbox_orgs, prod_org):
        """When assert_not_production raises ProductionOrgError, prints error and exits with code 1."""
        all_orgs = two_sandbox_orgs + [prod_org]
        mock_question = MagicMock()
        mock_question.ask.return_value = "Prod"

        with patch("questionary.select", return_value=mock_question), \
             patch("migrate.auth.assert_not_production", side_effect=ProductionOrgError("production org")):
            from migrate.prompts import select_target_org

            with pytest.raises(SystemExit) as exc_info:
                select_target_org(all_orgs, source_alias="Dev1")

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# select_objects tests
# ---------------------------------------------------------------------------

class TestSelectObjects:
    FOUR_OBJECTS = [
        "Entitlement",
        "CFSuite Request Flow",
        "CFSuite Community Request",
        "CFSuite Preferred Comms Config",
    ]

    def test_all_objects_returns_all_in_dependency_order(self):
        """User selects 'All objects' — returns all four in canonical order."""
        mock_question = MagicMock()
        mock_question.ask.return_value = ["All objects"]

        with patch("questionary.checkbox", return_value=mock_question):
            from migrate.prompts import select_objects
            result = select_objects(available=self.FOUR_OBJECTS)

        assert result == self.FOUR_OBJECTS

    def test_individual_selection_returns_items_in_dependency_order(self):
        """User selects 2 items out of order — returns them in canonical dependency order."""
        # User picks CFSuite Community Request and Entitlement (out of dependency order)
        mock_question = MagicMock()
        mock_question.ask.return_value = ["CFSuite Community Request", "Entitlement"]

        with patch("questionary.checkbox", return_value=mock_question):
            from migrate.prompts import select_objects
            result = select_objects(available=self.FOUR_OBJECTS)

        # Entitlement comes before CFSuite Community Request in canonical order
        assert result == ["Entitlement", "CFSuite Community Request"]
