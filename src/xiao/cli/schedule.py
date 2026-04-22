"""Schedule management commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)
console = Console()


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.callback()
def schedule_root(ctx: typer.Context) -> None:
    """Show schedules by default when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        list_schedules(as_json=False)
        raise typer.Exit(0)


@app.command("list")
def list_schedules(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all cleaning schedules with room names."""
    vac = _vacuum()

    try:
        schedules = vac.schedules_parsed()
    except AttributeError:
        # Fallback for non-cloud vacuum
        timers = vac.timer_list()
        from xiao.ui.formatters import render_schedules

        render_schedules(timers)
        return

    if as_json:
        rprint(json.dumps(schedules, indent=2, ensure_ascii=False))
        return

    if not schedules:
        rprint("[yellow]No schedules found.[/yellow]")
        return

    table = Table(title="Cleaning Schedules", border_style="cyan")
    table.add_column("#", style="bold", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Time", style="bold cyan")
    table.add_column("Days")
    table.add_column("Mode")
    table.add_column("Fan")
    table.add_column("Water")
    table.add_column("Rooms")

    for s in schedules:
        if s.get("parse_error"):
            table.add_row("?", "?", s.get("raw", ""), "", "", "", "", "")
            continue

        status = "[green]●[/green]" if s["enabled"] else "[red]○[/red]"
        rooms = ", ".join(s["rooms_display"])

        table.add_row(
            str(s["id"]),
            status,
            s["time"],
            s["days_display"],
            s["mode"],
            s["fan"],
            s["water"],
            rooms,
        )

    console.print(table)


@app.command()
def add(
    cron: str = typer.Argument(help="Cron expression, e.g. '30 12 * * 1,3,5'"),
):
    """Add a cleaning schedule."""
    vac = _vacuum()
    vac.timer_add(cron)
    rprint(f"[green]Schedule added: {cron}[/green]")


@app.command()
def remove(
    timer_id: str = typer.Argument(help="Timer ID to remove"),
):
    """Remove a cleaning schedule."""
    vac = _vacuum()
    vac.timer_delete(timer_id)
    rprint(f"[green]Schedule {timer_id} removed.[/green]")
