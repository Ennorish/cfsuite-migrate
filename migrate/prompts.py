"""Interactive prompt functions for org selection and object selection."""
import sys

import questionary
from rich.console import Console

import migrate.auth as auth
from migrate.models import OrgInfo, ProductionOrgError

console = Console()

# The four CFSuite objects in required insertion (dependency) order
MIGRATION_OBJECTS = [
    "Entitlement",
    "CFSuite Request Flow",
    "CFSuite Community Request",
    "CFSuite Preferred Comms Config",
]


def select_source_org(orgs: list[OrgInfo]) -> OrgInfo:
    """Prompt user to select source org. Exits if no orgs found."""
    if not orgs:
        console.print("[yellow]No SF CLI authenticated orgs found.[/yellow]")
        console.print("Add an org with: [bold]sf org login web[/bold]")
        sys.exit(0)
    choices = [org.alias for org in orgs]
    selected_alias = questionary.select(
        "Select SOURCE org (migrate FROM):", choices=choices
    ).ask()
    return next(org for org in orgs if org.alias == selected_alias)


def select_target_org(orgs: list[OrgInfo], source_alias: str) -> OrgInfo:
    """Prompt user to select target org, excluding source. Blocks production orgs."""
    candidates = [org for org in orgs if org.alias != source_alias]
    if not candidates:
        console.print("[yellow]No other authenticated orgs available as target.[/yellow]")
        console.print("Add a sandbox/scratch org with: [bold]sf org login web[/bold]")
        sys.exit(0)
    choices = [org.alias for org in candidates]
    selected_alias = questionary.select(
        "Select TARGET org (migrate TO):", choices=choices
    ).ask()
    selected = next(org for org in candidates if org.alias == selected_alias)
    try:
        auth.assert_not_production(selected)
    except ProductionOrgError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    return selected


def select_objects(available: list[str] | None = None) -> list[str]:
    """Prompt user to select which objects to migrate. Returns in dependency order."""
    if available is None:
        available = MIGRATION_OBJECTS
    ALL_LABEL = "All objects"
    choices = [ALL_LABEL] + list(available)
    selected = questionary.checkbox(
        "Select objects to migrate:", choices=choices
    ).ask()
    if ALL_LABEL in selected or not selected:
        return list(available)
    # Return in canonical dependency order
    return [obj for obj in available if obj in selected]
