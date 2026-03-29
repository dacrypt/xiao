"""Device info and history commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from xiao.ui.formatters import render_device_info, render_history

app = typer.Typer(no_args_is_help=True)


def _vacuum():
    from xiao.cli.app import _vacuum as _get_vacuum

    return _get_vacuum()


@app.command()
def info():
    """Show device information."""
    vac = _vacuum()
    data = vac.device_info()
    render_device_info(data)


@app.command()
def history(
    full: bool = typer.Option(False, "--full", "-f", help="Show detailed history with all available data"),
):
    """Show cleaning history summary."""
    vac = _vacuum()
    data = vac.clean_history()

    if full:
        # Add last clean details
        try:
            last = vac.last_clean()
            if last:
                data.update({f"last_{k}" if not k.startswith("last_") else k: v for k, v in last.items()})
        except Exception:
            pass
        # Add consumable info
        try:
            cons = vac.consumable_status()
            for key in ("main_brush_remaining", "side_brush_remaining", "filter_remaining"):
                if key in cons:
                    data[key] = cons[key]
        except Exception:
            pass

    render_history(data)


@app.command("log")
def last_log():
    """Show last cleaning details."""
    vac = _vacuum()
    data = vac.last_clean()
    if data:
        render_history(data)
    else:
        rprint("[yellow]No cleaning log available.[/yellow]")
