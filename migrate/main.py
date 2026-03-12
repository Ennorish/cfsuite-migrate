"""Typer CLI entry point for cfsuite-migrate."""
import typer
from rich.console import Console
from rich.table import Table

from migrate.auth import assert_not_production, get_credentials, list_orgs
from migrate.models import ProductionOrgError, SFCLINotFoundError
from migrate.pipeline import run_migration, validate_results
from migrate.prompts import select_objects, select_source_org, select_target_org
from migrate.sf_api import build_client

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

    try:
        # Build Salesforce clients
        source_creds = get_credentials(source_org.alias)
        target_creds = get_credentials(target_org.alias)
        source_client = build_client(source_creds)
        target_client = build_client(target_creds)

        # Run migration pipeline with live per-object progress
        console.print("\n[bold]Starting migration...[/bold]\n")

        def on_progress(name, event, data):
            if event == "start":
                console.print(f"  [cyan]Migrating {name}...[/cyan]")
            elif event == "done":
                console.print(
                    f"  [green]{name}:[/green] {data['extracted']} extracted, "
                    f"{data['skipped']} skipped, {data['inserted']} inserted"
                )

        results = run_migration(source_client, target_client, objects_to_migrate, on_progress=on_progress)

        # Display validation summary table
        console.print("\n[bold green]Migration complete![/bold green]\n")
        validated = validate_results(results)

        table = Table(title="Migration Summary")
        table.add_column("Object", style="bold")
        table.add_column("Extracted", justify="right")
        table.add_column("Skipped", justify="right")
        table.add_column("Inserted", justify="right")
        table.add_column("Status", justify="center")

        total_extracted = total_skipped = total_inserted = 0
        for r in validated:
            status = "[green]OK[/green]" if r["match"] else "[red]MISMATCH[/red]"
            table.add_row(
                r["object"],
                str(r["extracted"]),
                str(r["skipped"]),
                str(r["inserted"]),
                status,
            )
            total_extracted += r["extracted"]
            total_skipped += r["skipped"]
            total_inserted += r["inserted"]

        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{total_extracted}[/bold]",
            f"[bold]{total_skipped}[/bold]",
            f"[bold]{total_inserted}[/bold]",
            "",
        )

        console.print(table)
    except Exception as e:
        console.print(f"\n[red]Migration failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def serve(
    port: int = typer.Option(8765, "--port", "-p", help="Port for the web UI"),
) -> None:
    """Launch the web UI in your browser."""
    from migrate.web import serve as start_server

    console.print(f"[green]Starting web UI at http://localhost:{port}[/green]")
    start_server(port=port)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
