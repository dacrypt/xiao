"""Cleaning commands."""

from __future__ import annotations

import json

import typer
from rich import print as rprint
from rich.console import Console

from xiao.core.config import get_rooms, resolve_room
from xiao.core.exit_codes import EXIT_GENERIC, EXIT_VACUUM_UNRESPONSIVE
from xiao.core.room_cleaning import WaitingForWaterError, extract_code, normalize_zone, start_room_clean

app = typer.Typer(no_args_is_help=False)
err_console = Console(stderr=True)

FAN_LEVELS = ("silent", "standard", "medium", "turbo")
WATER_LEVELS = ("low", "medium", "high")


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


def _fail(msg: str, result=None) -> None:
    err_console.print(f"[red]✗ {msg}[/red]")
    if result is not None:
        err_console.print(json.dumps(result, indent=2, default=str), markup=False, highlight=False)
    raise typer.Exit(EXIT_GENERIC)


def parse_zone(raw: str) -> list[int]:
    """Parse ``"x1,y1,x2,y2"`` (millimetres) into four ints, or raise ValueError."""
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Zone must have 4 comma-separated coords x1,y1,x2,y2 (got {raw!r})")
    try:
        coords = [int(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"Zone coords must be integers in mm (got {raw!r})") from e
    return normalize_zone(coords)


@app.callback(invoke_without_command=True)
def clean(
    ctx: typer.Context,
    room: list[str] = typer.Option(None, "--room", "-r", help="Room ID or alias (repeatable)"),
    zone: list[str] = typer.Option(None, "--zone", "-z", help="Zone coords in mm: x1,y1,x2,y2 (repeatable)"),
    spot: bool = typer.Option(False, "--spot", "-s", help="Spot cleaning (local miIO mode only)"),
    repeat: int = typer.Option(1, "--repeat", min=1, help="Number of cleaning passes"),
    speed: str | None = typer.Option(None, "--speed", "--fan", help="Fan speed: silent, standard, medium, turbo"),
    water: str | None = typer.Option(None, "--water", "-w", help="Water level: low, medium, high"),
):
    """Start cleaning. Use flags for room/zone/spot modes; no flags = full house."""
    if ctx.invoked_subcommand is not None:
        return

    # ── Validate everything before touching the vacuum ──
    modes = [name for name, on in (("--room", bool(room)), ("--zone", bool(zone)), ("--spot", spot)) if on]
    if len(modes) > 1:
        _fail(f"Choose only one of {', '.join(modes)}.")
    if speed and speed.lower() not in FAN_LEVELS:
        _fail(f"Unknown speed {speed!r}. Use: {', '.join(FAN_LEVELS)}")
    if water and water.lower() not in WATER_LEVELS:
        _fail(f"Unknown water level {water!r}. Use: {', '.join(WATER_LEVELS)}")

    zones: list[list[int]] = []
    for z in zone or []:
        try:
            zones.append(parse_zone(z))
        except ValueError as e:
            _fail(str(e))

    room_ids: list[int] = []
    room_names: list[str] = []
    if room:
        aliases = get_rooms()
        for r in room:
            try:
                rid = resolve_room(r)
            except ValueError as e:
                _fail(str(e))
            room_ids.append(rid)
            room_names.append(aliases.get(str(rid), str(rid)))

    vac = _vacuum()

    # Fan / water are best-effort: some MIoT fields are only writable off-dock,
    # so a rejection is reported but does not abort the clean.
    if speed:
        code = extract_code(vac.set_fan_speed(speed.lower()))
        if code == 0:
            rprint(f"[cyan]Fan speed set to {speed.lower()}.[/cyan]")
        else:
            err_console.print(f"[yellow]Fan speed change rejected (code {code}); continuing.[/yellow]")
    if water:
        try:
            code = extract_code(vac.set_water_level(water.lower()))
            if code == 0:
                rprint(f"[cyan]Water level set to {water.lower()}.[/cyan]")
            else:
                err_console.print(f"[yellow]Water level change rejected (code {code}); continuing.[/yellow]")
        except (ValueError, AttributeError) as e:
            err_console.print(f"[yellow]Water level: {e}[/yellow]")

    if spot:
        try:
            result = vac.spot_clean()
        except NotImplementedError as e:
            _fail(str(e))
        if extract_code(result) != 0:
            _fail("Spot clean rejected by the vacuum.", result)
        rprint("[green]Spot cleaning started.[/green]")
    elif room_ids:
        try:
            clean_result = start_room_clean(
                vac,
                room_ids,
                repeat=repeat,
                fan=speed.lower() if speed else None,
                water=water.lower() if water else None,
            )
        except WaitingForWaterError as e:
            _fail(str(e))
        if not clean_result["accepted"]:
            _fail(f"Room clean rejected by the vacuum (code {clean_result['code']}).", clean_result["result"])
        rprint(f"[green]Cleaning rooms: {', '.join(room_names)} (x{repeat}).[/green]")
        if repeat > 1 and clean_result["transport"] == "miot":
            err_console.print(
                "[yellow]Note: the X20+ room action has no repeat input; one pass was requested.[/yellow]"
            )
        if clean_result["warning"]:
            err_console.print(f"[yellow]{clean_result['warning']}[/yellow]")
        if clean_result["verified_started"] is False:
            raise typer.Exit(EXIT_VACUUM_UNRESPONSIVE)
    elif zones:
        try:
            result = vac.clean_zone(zones, repeat=repeat) if repeat > 1 else vac.clean_zone(zones)
        except RuntimeError as e:
            _fail(str(e))
        if extract_code(result) != 0:
            _fail("Zone clean rejected by the vacuum.", result)
        rprint(f"[green]Zone cleaning started: {zones}[/green]")
    else:
        result = vac.start()
        if extract_code(result) != 0:
            _fail("Full clean rejected by the vacuum.", result)
        rprint("[green]Full house cleaning started.[/green]")
