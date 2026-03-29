"""Cleaning commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from xiao.core.config import get_rooms, resolve_room

app = typer.Typer(no_args_is_help=False)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.callback(invoke_without_command=True)
def clean(
    ctx: typer.Context,
    room: list[str] = typer.Option(None, "--room", "-r", help="Room ID or name (repeatable)"),
    zone: str | None = typer.Option(None, "--zone", "-z", help="Zone coords: x1,y1,x2,y2"),
    spot: bool = typer.Option(False, "--spot", "-s", help="Spot cleaning"),
    repeat: int = typer.Option(1, "--repeat", help="Number of cleaning passes"),
    speed: str | None = typer.Option(None, "--speed", "--fan", help="Fan speed: silent, standard, medium, turbo"),
    water: str | None = typer.Option(None, "--water", "-w", help="Water level: low, medium, high"),
):
    """Start cleaning. Use flags for room/zone/spot modes."""
    if ctx.invoked_subcommand is not None:
        return

    vac = _vacuum()

    # Set fan speed if requested
    if speed:
        vac.set_fan_speed(speed)
        rprint(f"[cyan]Fan speed set to {speed}.[/cyan]")

    # Set water level if requested
    if water:
        try:
            vac.set_water_level(water)
            rprint(f"[cyan]Water level set to {water}.[/cyan]")
        except (ValueError, AttributeError) as e:
            rprint(f"[yellow]Water level: {e}[/yellow]")

    if spot:
        vac.spot_clean()
        rprint("[green]Spot cleaning started.[/green]")
    elif room:
        # Resolve room names/IDs
        room_ids = []
        room_names = []
        aliases = get_rooms()
        for r in room:
            try:
                rid = resolve_room(r)
                room_ids.append(rid)
                alias = aliases.get(str(rid), str(rid))
                room_names.append(alias)
            except ValueError as e:
                rprint(f"[red]{e}[/red]")
                raise typer.Exit(1) from e

        # Try MIoT room sweep first, fall back to cloud RPC
        try:
            vac.clean_rooms_miot(room_ids)
        except (AttributeError, Exception):
            vac.clean_rooms(room_ids, repeat=repeat)
        rprint(f"[green]Cleaning rooms: {', '.join(room_names)} (x{repeat}).[/green]")
    elif zone:
        coords = [int(c) for c in zone.split(",")]
        if len(coords) != 4:
            rprint("[red]Zone must have 4 coords: x1,y1,x2,y2[/red]")
            raise typer.Exit(1)
        vac.clean_zone([coords])
        rprint(f"[green]Zone cleaning started: {coords}[/green]")
    else:
        vac.start()
        rprint("[green]Full house cleaning started.[/green]")
