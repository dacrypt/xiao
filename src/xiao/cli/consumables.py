"""Consumable status and reset commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from xiao.ui.formatters import render_consumables

app = typer.Typer(no_args_is_help=False)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.callback(invoke_without_command=True)
def consumables(ctx: typer.Context):
    """Show consumable status."""
    if ctx.invoked_subcommand is not None:
        return
    vac = _vacuum()
    data = vac.consumable_status()
    if data:
        render_consumables(data)
    else:
        rprint("[yellow]No consumable data available.[/yellow]")


@app.command()
def reset(
    component: str = typer.Argument(help="Consumable to reset: main_brush, side_brush, filter, sensor"),
):
    """Reset a consumable counter."""
    vac = _vacuum()
    try:
        vac.consumable_reset(component)
        rprint(f"[green]{component} counter reset.[/green]")
    except ValueError as e:
        rprint(f"[red]{e}[/red]")
