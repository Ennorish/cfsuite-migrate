"""Typer CLI entry point for cfsuite-migrate."""
import typer
from rich.console import Console

from migrate.auth import assert_not_production, list_orgs
from migrate.models import ProductionOrgError, SFCLINotFoundError
from migrate.prompts import select_objects, select_source_org, select_target_org

app = typer.Typer(
    name="cfsuite-migrate",
    help="Migrate CFSuite configuration objects between Salesforce orgs.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def migrate(
    source: str = typer.Option(None, "--source", "-s", help="Source org alias (skips prompt)"),
    target: str = typer.Option(None, "--target", "-t", help="Target org alias (skips prompt)"),
) -> None:
    """Migrate CFSuite config objects from source org to target org."""
    try:
        orgs = list_orgs()
    except SFCLINotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Source org selection
    if source:
        source_org = next((o for o in orgs if o.alias == source), None)
        if not source_org:
            console.print(
                f"[red]Error:[/red] Org '{source}' not found. "
                "Run 'sf org list' to see authenticated orgs."
            )
            raise typer.Exit(1)
    else:
        source_org = select_source_org(orgs)

    # Target org selection (with production guard)
    if target:
        target_org = next((o for o in orgs if o.alias == target), None)
        if not target_org:
            console.print(f"[red]Error:[/red] Org '{target}' not found.")
            raise typer.Exit(1)
        try:
            assert_not_production(target_org)
        except ProductionOrgError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    else:
        target_org = select_target_org(orgs, source_alias=source_org.alias)

    # Object selection
    objects_to_migrate = select_objects()

    console.print(f"\n[green]Source:[/green] {source_org.alias} ({source_org.username})")
    console.print(f"[green]Target:[/green] {target_org.alias} ({target_org.username})")
    console.print(f"[green]Objects:[/green] {', '.join(objects_to_migrate)}")
    console.print("\n[yellow]Migration pipeline not yet implemented (Phase 2).[/yellow]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
