"""Siri Shortcuts for the vacuum (works with Siri in any language)."""

from __future__ import annotations

import socket
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console

from xiao.core.exit_codes import EXIT_GENERIC

app = typer.Typer(no_args_is_help=True)
err_console = Console(stderr=True)


def _default_url(port: int) -> str:
    host = socket.gethostname().split(".")[0]
    return f"http://{host}.local:{port}"


def _pairs(values: list[str] | None, what: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values or []:
        key, sep, value = raw.partition("=")
        if not sep or not key.strip() or not value.strip():
            err_console.print(f"[red]✗ {what} must look like KEY=VALUE (got {raw!r})[/red]")
            raise typer.Exit(EXIT_GENERIC)
        result[key.strip()] = value.strip()
    return result


@app.command("export")
def export(
    out: Path = typer.Option(Path("xiao-shortcuts"), "--out", "-o", help="Folder for the .shortcut files"),
    url: str | None = typer.Option(
        None, help="How the iPhone reaches `xiao web` (default: http://<this-mac>.local:8120)"
    ),
    port: int = typer.Option(8120, help="Port of `xiao web`, used for the default --url"),
    lang: str = typer.Option("es", help="Shortcut names and Siri's answers: es | en"),
    name: list[str] = typer.Option(None, "--name", help='Rename a room shortcut: --name "7=Aspiradora a la cocina nueva"'),
    zone: list[str] = typer.Option(None, "--zone", help='Extra zone shortcut: --zone "comedor=x1,y1,x2,y2"'),
    sign: bool = typer.Option(True, "--sign/--no-sign", help="Sign with macOS `shortcuts sign` (needed to import)"),
):
    """Generate one Siri shortcut per room (plus house, dock, stop and status).

    Siri doesn't understand robot-vacuum commands in Spanish, but it runs any
    shortcut by name: «Oye Siri, aspiradora a la cocina». Each shortcut calls
    POST /api/voice on `xiao web` and Siri reads back the answer. `xiao web`
    must listen on the network (`--host 0.0.0.0`); the files embed its token.
    """
    from xiao.core.config import ensure_web_token, get_rooms
    from xiao.core.shortcuts import default_specs, write_shortcuts

    if lang not in ("es", "en"):
        err_console.print("[red]✗ --lang must be es or en[/red]")
        raise typer.Exit(EXIT_GENERIC)
    rooms = get_rooms()
    if not rooms:
        err_console.print('[red]✗ No room names yet. Run `xiao map rooms` and `xiao rooms alias <id> "<name>"`.[/red]')
        raise typer.Exit(EXIT_GENERIC)
    zones = _pairs(zone, "--zone")
    try:
        specs = default_specs(rooms, lang=lang, names=_pairs(name, "--name"), zones=zones)
        files = write_shortcuts(specs, out, url or _default_url(port), ensure_web_token(), sign=sign)
    except (ValueError, RuntimeError, OSError) as e:
        err_console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(EXIT_GENERIC) from e

    rprint(f"[green]✓ {len(files)} shortcuts in {out.resolve()}[/green] → {url or _default_url(port)}")
    for path in files:
        rprint(f"  • {path.stem}")
    rprint(
        "[dim]AirDrop them to the iPhone (or open them on this Mac to sync via iCloud) and tap "
        "«Agregar atajo». They contain the xiao web token: don't share them.[/dim]"
    )
