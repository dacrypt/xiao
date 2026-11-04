"""Room management commands."""

from __future__ import annotations

import typer
from rich import print as rprint
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from xiao.core.config import get_rooms, is_configured, resolve_room, set_room_alias

app = typer.Typer(no_args_is_help=False)
console = Console()


def render_known_rooms(rooms: list[dict]) -> None:
    """Shared table for `xiao rooms` and `xiao map rooms`."""
    if not rooms:
        rprint(
            "[yellow]No rooms found.[/yellow] The vacuum exposes no room list and no schedule references "
            "rooms yet. Map the house with a full `xiao start`, then create a schedule in the Xiaomi Home app "
            'or add aliases with: xiao rooms alias <id> "Name"'
        )
        return

    table = Table(title="Rooms", border_style="cyan")
    table.add_column("ID", style="bold", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Source", style="dim")
    for room in rooms:
        table.add_row(str(room["id"]), escape(room["name"]), ", ".join(room["sources"]))
    console.print(table)

    unaliased = [r for r in rooms if "alias" not in r["sources"]]
    if unaliased:
        rprint(f'\n[yellow]Tip:[/yellow] {len(unaliased)} rooms without aliases. Use: xiao rooms alias <id> "Name"')


@app.callback(invoke_without_command=True)
def rooms(ctx: typer.Context):
    """List rooms known to the vacuum (room mapping + schedules) and your aliases."""
    if ctx.invoked_subcommand is not None:
        return

    from xiao.core.room_cleaning import known_rooms

    vac = None
    if is_configured():
        from xiao.cli.app import _vacuum

        vac = _vacuum()
    render_known_rooms(known_rooms(vac, get_rooms()))


@app.command()
def alias(
    room_id: int = typer.Argument(help="Room ID"),
    name: str = typer.Argument(help="Room name/alias"),
):
    """Set an alias for a room ID."""
    set_room_alias(room_id, name)
    rprint(f'[green]✓ Room {room_id} → "{name}"[/green]')


@app.command("rename")
def rename_room(
    room: str = typer.Argument(help="Room ID or current alias"),
    name: str = typer.Argument(help="New room name"),
):
    """Rename a room (accepts the numeric ID or its current alias)."""
    try:
        room_id = resolve_room(room)
    except ValueError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    set_room_alias(room_id, name)
    rprint(f'[green]✓ Room {room_id} renamed to "{name}"[/green]')
