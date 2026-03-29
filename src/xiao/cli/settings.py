"""Device settings — fan speed, DND, volume, water level."""

from __future__ import annotations

import typer
from rich import print as rprint

app = typer.Typer(no_args_is_help=True)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


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
