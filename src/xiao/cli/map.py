"""Map and room management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from xiao.core.config import get_rooms

app = typer.Typer(no_args_is_help=True)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.command()
def rooms():
    """List room IDs known to the vacuum (run this before `xiao clean -r`)."""
    from xiao.cli.rooms import render_known_rooms
    from xiao.core.room_cleaning import known_rooms

    render_known_rooms(known_rooms(_vacuum(), get_rooms()))


@app.command()
def show():
    """Show what the cloud exposes about the map and its rooms."""
    from xiao.cli.rooms import render_known_rooms
    from xiao.core.room_cleaning import known_rooms

    vac = _vacuum()
    device_rooms = vac.rooms()
    if device_rooms:
        rprint(f"[cyan]Device room mapping: {len(device_rooms)} rooms.[/cyan]")
    else:
        rprint("[dim]The device exposes no room mapping via the cloud; using schedules and aliases.[/dim]")
    render_known_rooms(known_rooms(vac, get_rooms()))
