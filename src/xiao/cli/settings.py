"""Device settings, fan speed, DND, volume, water level, and vacuum-extend toggles."""

from __future__ import annotations

import typer
from rich import print as rprint

app = typer.Typer(no_args_is_help=True)


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
            getattr(vac, setter_name)(enabled)
            rprint(f"[green]{label} set to {'On' if enabled else 'Off'}.[/green]")
        except (AttributeError, ValueError) as e:
            rprint(f"[red]{e}[/red]")
        return

    try:
        data = getattr(vac, getter_name)()
        state = "On" if data.get("enabled") else "Off"
        raw = data.get("raw")
        raw_suffix = f" (raw: {raw})" if raw is not None else ""
        rprint(f"[cyan]{label}:[/cyan] {state}{raw_suffix}")
    except (AttributeError, Exception) as e:
        rprint(f"[yellow]{label} not available: {e}[/yellow]")


@app.command()
def speed(
    preset: str | None = typer.Argument(None, help="Fan speed: silent, standard, medium, turbo"),
):
    """Get or set fan speed."""
    vac = _vacuum()
    if preset:
        try:
            vac.set_fan_speed(preset)
            rprint(f"[green]Fan speed set to {preset}.[/green]")
        except ValueError as e:
            rprint(f"[red]{e}[/red]")
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
    vac = _vacuum()
    if toggle:
        enabled = toggle.lower() in ("on", "true", "1", "yes")
        vac.set_dnd(enabled, start, end)
        state = "enabled" if enabled else "disabled"
        rprint(f"[green]DND {state}.[/green]")
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
    vac = _vacuum()
    if level is not None:
        vac.set_volume(level)
        rprint(f"[green]Volume set to {level}.[/green]")
    else:
        current = vac.volume()
        rprint(f"[cyan]Current volume:[/cyan] {current}")


@app.command()
def water(
    level: str | None = typer.Argument(None, help="Water level: low, medium, high"),
):
    """Get or set mop water level."""
    vac = _vacuum()
    if level:
        try:
            vac.set_water_level(level)
            rprint(f"[green]Water level set to {level}.[/green]")
        except (ValueError, AttributeError) as e:
            rprint(f"[red]{e}[/red]")
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
