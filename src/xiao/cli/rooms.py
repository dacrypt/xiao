"""Room management commands."""

from __future__ import annotations

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from xiao.core.config import get_rooms, set_room_alias

app = typer.Typer(no_args_is_help=False)
console = Console()


@app.callback(invoke_without_command=True)
def rooms(ctx: typer.Context):
    """List rooms with IDs and aliases."""
    if ctx.invoked_subcommand is not None:
        return

    room_aliases = get_rooms()

    # Known room IDs from schedules (discovered from device)
    known_ids = {1, 2, 3, 4, 6, 7, 8, 10, 12}
    # Merge with any aliases that might have other IDs
    for rid in room_aliases:
        known_ids.add(int(rid))

    table = Table(title="Rooms", border_style="cyan")
    table.add_column("ID", style="bold", justify="right")
    table.add_column("Alias", style="cyan")

    for rid in sorted(known_ids):
        alias = room_aliases.get(str(rid), "[dim]—[/dim]")
        table.add_row(str(rid), alias)

    console.print(table)

    unaliased = [rid for rid in sorted(known_ids) if str(rid) not in room_aliases]
    if unaliased:
        rprint(f'\n[yellow]Tip:[/yellow] {len(unaliased)} rooms without aliases. Use: xiao rooms alias <id> "Name"')


@app.command()
def alias(
    room_id: int = typer.Argument(help="Room ID"),
    name: str = typer.Argument(help="Room name/alias"),
):
    """Set an alias for a room ID."""
    set_room_alias(room_id, name)
    rprint(f'[green]✓ Room {room_id} → "{name}"[/green]')
