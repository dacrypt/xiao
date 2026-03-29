"""Map and room management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from xiao.ui.formatters import render_rooms

app = typer.Typer(no_args_is_help=True)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.command()
def rooms():
    """List available rooms with their IDs."""
    vac = _vacuum()
    room_list = vac.rooms()
    render_rooms(room_list)


@app.command()
def show():
    """Show map information."""
    vac = _vacuum()
    room_list = vac.rooms()
    if room_list:
        rprint(f"[cyan]Map has {len(room_list)} rooms.[/cyan]")
        render_rooms(room_list)
    else:
        rprint("[yellow]No map data available. Run a full clean first to generate a map.[/yellow]")
