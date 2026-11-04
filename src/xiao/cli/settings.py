"""Device settings, fan speed, DND, volume, water level, and vacuum-extend controls."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import typer
from rich import print as rprint
from rich.console import Console

from xiao.core.exit_codes import EXIT_GENERIC
from xiao.core.room_cleaning import extract_code

if TYPE_CHECKING:
    from collections.abc import Callable

app = typer.Typer(no_args_is_help=True)
err_console = Console(stderr=True)

FAN_LEVELS = ("silent", "standard", "medium", "turbo")
WATER_LEVELS = ("low", "medium", "high")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _fail(msg: str) -> None:
    err_console.print(f"[red]✗ {msg}[/red]")
    raise typer.Exit(EXIT_GENERIC)


def _apply(setter: Callable[[], Any], success: str) -> None:
    """Run a setter; exit non-zero if it raises or the vacuum rejects the write."""
    try:
        result = setter()
    except (AttributeError, ValueError, NotImplementedError) as e:
        _fail(str(e))
    code = extract_code(result)
    if code != 0:
        _fail(f"Setting rejected by the vacuum (code {code}).")
    rprint(f"[green]{success}[/green]")


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


def _parse_toggle(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"on", "true", "1", "yes", "enable", "enabled"}:
        return True
    if normalized in {"off", "false", "0", "no", "disable", "disabled"}:
        return False
    raise ValueError("Toggle must be on/off")


def _render_toggle_setting(label: str, getter_name: str, setter_name: str, toggle: str | None) -> None:
    vac = _vacuum()
    if toggle is not None:
        try:
            enabled = _parse_toggle(toggle)
        except ValueError as e:
            _fail(str(e))
        _apply(lambda: getattr(vac, setter_name)(enabled), f"{label} set to {'On' if enabled else 'Off'}.")
        return

    try:
        data = getattr(vac, getter_name)()
        state = "On" if data.get("enabled") else "Off"
        raw = data.get("raw")
        raw_suffix = f" (raw: {raw})" if raw is not None else ""
        rprint(f"[cyan]{label}:[/cyan] {state}{raw_suffix}")
    except (AttributeError, Exception) as e:
        rprint(f"[yellow]{label} not available: {e}[/yellow]")


def _render_minutes_setting(label: str, getter_name: str, setter_name: str, minutes: int | None) -> None:
    vac = _vacuum()
    if minutes is not None:
        _apply(lambda: getattr(vac, setter_name)(minutes), f"{label} set to {minutes} min.")
        return

    try:
        data = getattr(vac, getter_name)()
        current = data.get("minutes")
        raw = data.get("raw")
        if current is None:
            rprint(f"[yellow]{label} not available.[/yellow]")
            return
        raw_suffix = f" (raw: {raw})" if raw is not None else ""
        rprint(f"[cyan]{label}:[/cyan] {current} min{raw_suffix}")
    except (AttributeError, Exception) as e:
        rprint(f"[yellow]{label} not available: {e}[/yellow]")


def _render_mode_setting(label: str, getter_name: str, setter_name: str, mode: str | None) -> None:
    vac = _vacuum()
    if mode is not None:
        _apply(lambda: getattr(vac, setter_name)(mode), f"{label} set to {mode.title()}.")
        return

    try:
        data = getattr(vac, getter_name)()
        current = data.get("mode")
        raw = data.get("raw")
        if current is None:
            rprint(f"[yellow]{label} not available.[/yellow]")
            return
        raw_suffix = f" (raw: {raw})" if raw is not None else ""
        rprint(f"[cyan]{label}:[/cyan] {current.title()}{raw_suffix}")
    except (AttributeError, Exception) as e:
        rprint(f"[yellow]{label} not available: {e}[/yellow]")


@app.command()
def speed(
    preset: str | None = typer.Argument(None, help="Fan speed: silent, standard, medium, turbo"),
):
    """Get or set fan speed."""
    if preset and preset.lower() not in FAN_LEVELS:
        _fail(f"Unknown speed {preset!r}. Use: {', '.join(FAN_LEVELS)}")
    vac = _vacuum()
    if preset:
        _apply(lambda: vac.set_fan_speed(preset.lower()), f"Fan speed set to {preset.lower()}.")
    else:
        current = vac.fan_speed()
        rprint(f"[cyan]Current fan speed:[/cyan] {current}")


@app.command()
def dnd(
    toggle: str | None = typer.Argument(None, help="on/off"),
    start: str | None = typer.Option(None, "--start", help="Start time HH:MM"),
    end: str | None = typer.Option(None, "--end", help="End time HH:MM"),
):
    """Get or set Do Not Disturb mode."""
    if toggle:
        try:
            enabled = _parse_toggle(toggle)
        except ValueError as e:
            _fail(str(e))
        for label, value in (("--start", start), ("--end", end)):
            if value is not None and not _HHMM.match(value):
                _fail(f"{label} must be HH:MM (24h), got {value!r}")
    vac = _vacuum()
    if toggle:
        state = "enabled" if enabled else "disabled"
        _apply(lambda: vac.set_dnd(enabled, start, end), f"DND {state}.")
    else:
        status = vac.dnd_status()
        if status:
            for k, v in status.items():
                rprint(f"  [bold]{k}:[/bold] {v}")
        else:
            rprint("[yellow]DND status not available.[/yellow]")


@app.command()
def volume(
    level: int | None = typer.Argument(None, help="Volume level 0-100"),
):
    """Get or set voice volume."""
    if level is not None and not 0 <= level <= 100:
        _fail("Volume must be between 0 and 100.")
    vac = _vacuum()
    if level is not None:
        _apply(lambda: vac.set_volume(level), f"Volume set to {level}.")
    else:
        current = vac.volume()
        rprint(f"[cyan]Current volume:[/cyan] {current}")


@app.command()
def water(
    level: str | None = typer.Argument(None, help="Water level: low, medium, high"),
):
    """Get or set mop water level."""
    if level and level.lower() not in WATER_LEVELS:
        _fail(f"Unknown water level {level!r}. Use: {', '.join(WATER_LEVELS)}")
    vac = _vacuum()
    if level:
        _apply(lambda: vac.set_water_level(level.lower()), f"Water level set to {level.lower()}.")
    else:
        try:
            data = vac.water_level()
            wl = data.get("water_level", "Unknown")
            raw = data.get("water_level_raw", "")
            rprint(f"[cyan]Water level:[/cyan] {wl} (raw: {raw})")
            mm = data.get("mop_mode_raw")
            if mm is not None:
                rprint(f"[cyan]Mop mode raw:[/cyan] {mm}")
        except (AttributeError, Exception) as e:
            rprint(f"[yellow]Water level not available: {e}[/yellow]")


@app.command()
def resume_after_charge(
    toggle: str | None = typer.Argument(None, help="on/off"),
):
    """Get or set automatic resume after charging."""
    _render_toggle_setting("Resume after charge", "resume_after_charge", "set_resume_after_charge", toggle)


@app.command()
def carpet_boost(
    toggle: str | None = typer.Argument(None, help="on/off"),
):
    """Get or set carpet boost."""
    _render_toggle_setting("Carpet boost", "carpet_boost", "set_carpet_boost", toggle)


@app.command()
def child_lock(
    toggle: str | None = typer.Argument(None, help="on/off"),
):
    """Get or set child lock."""
    _render_toggle_setting("Child lock", "child_lock", "set_child_lock", toggle)


@app.command()
def smart_wash(
    toggle: str | None = typer.Argument(None, help="on/off"),
):
    """Get or set smart mop washing at the base station."""
    _render_toggle_setting("Smart wash", "smart_wash", "set_smart_wash", toggle)


@app.command()
def carpet_avoidance(
    mode: str | None = typer.Argument(None, help="Mode: avoid/auto"),
):
    """Get or set carpet avoidance mode."""
    _render_mode_setting("Carpet avoidance", "carpet_avoidance", "set_carpet_avoidance", mode)


@app.command()
def clean_rags_tip(
    minutes: int | None = typer.Argument(None, help="Reminder interval in minutes (0-120)"),
):
    """Get or set the clean-rags reminder interval."""
    _render_minutes_setting("Clean rags tip", "clean_rags_tip", "set_clean_rags_tip", minutes)
