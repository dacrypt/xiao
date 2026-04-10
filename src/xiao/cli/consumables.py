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
    """Show consumable status (main brush, side brush, filter, mop)."""
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
    component: str = typer.Argument(
        help="Consumable to reset: main_brush, side_brush, filter, mop, or 'all'"
    ),
):
    """Reset a consumable counter after replacing the physical part."""
    vac = _vacuum()
    if component == "all":
        results = vac.consumable_reset_all()
        for name, result in results.items():
            if result.get("ok"):
                rprint(f"  [green]✓ {name} reset[/green]")
            else:
                err = result.get("error") or f"code {result.get('code')}"
                rprint(f"  [red]✗ {name}: {err}[/red]")
        rprint("[green]All consumables reset.[/green]")
    else:
        try:
            vac.consumable_reset(component)
            rprint(f"[green]✓ {component} counter reset.[/green]")
        except ValueError as e:
            rprint(f"[red]{e}[/red]")
