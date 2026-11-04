"""Main xiao CLI application."""

from __future__ import annotations

import json
import logging
import os
import sys

import typer
from rich import print as rprint
from rich.console import Console

from xiao.cli import clean, consumables, device, rooms, schedule, settings, setup
from xiao.cli import doctor as doctor_mod
from xiao.cli import map as map_cmd
from xiao.cli._cta import help_epilog, maybe_show_first_run_cta
from xiao.core.config import get_cloud_config, harden_permissions, save_cloud_session
from xiao.core.exit_codes import EXIT_GENERIC, EXIT_NOT_CONFIGURED, EXIT_TOKEN_EXPIRED
from xiao.core.room_cleaning import extract_code
from xiao.core.service import XiaoError, build_vacuum
from xiao.ui.formatters import render_full_status, render_report, render_status

console = Console()

app = typer.Typer(
    name="xiao",
    help="Control your Xiaomi/Roborock vacuum from the terminal.",
    epilog=help_epilog(),
    invoke_without_command=True,
    no_args_is_help=False,
)


def _print_version(value: bool) -> None:
    if value:
        from xiao import __version__

        sys.stdout.write(f"xiao {__version__}\n")
        raise typer.Exit(0)


@app.callback()
def _root_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_print_version,
        is_eager=True,
        help="Print the xiao version and exit.",
    ),
) -> None:
    """Run on every CLI invocation. Shows the first-run CTA; sets up
    debug logging when XIAO_DEBUG=1; when no subcommand is given, prints
    vacuum status if configured, or help otherwise."""
    if os.environ.get("XIAO_DEBUG") == "1":
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(levelname)s %(name)s] %(message)s",
        )

    harden_permissions()
    maybe_show_first_run_cta()

    if ctx.invoked_subcommand is None:
        from xiao.core.config import is_configured

        if is_configured():
            try:
                render_status(_vacuum().status())
            except Exception as e:
                rprint(f"[red]Failed to fetch status: {e}[/red]")
                raise typer.Exit(1) from e
            raise typer.Exit(0)
        rprint(ctx.get_help())
        raise typer.Exit(0)


app.add_typer(setup.app, name="setup", help="Setup and configure your vacuum.")
app.add_typer(clean.app, name="clean", help="Cleaning commands.")
app.add_typer(consumables.app, name="consumables", help="Consumable status and reset.")
app.add_typer(schedule.app, name="schedule", help="Manage cleaning schedules.")
app.add_typer(settings.app, name="settings", help="Device settings.")
app.add_typer(device.app, name="device", help="Device info and history.")
app.add_typer(map_cmd.app, name="map", help="Map and room management.")
app.add_typer(rooms.app, name="rooms", help="Room aliases and management.")
app.command("doctor")(doctor_mod.doctor)


@app.command("mcp")
def mcp_cmd() -> None:
    """Run an MCP server exposing vacuum control as structured tools.

    Requires the `mcp` extra: `pip install "xiao-cli[mcp]"`. Speaks
    MCP over stdio so hosts like Claude Desktop and Cursor can connect.
    """
    try:
        from xiao.mcp_server import run
    except RuntimeError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    run()


err_console = Console(stderr=True)


def _notify(msg: str) -> None:
    """Progress messages go to stderr so stdout stays parseable (--json, MCP)."""
    err_console.print(f"[dim]{msg}[/dim]")


def _vacuum():
    """Build the configured vacuum service, mapping failures to exit codes."""
    try:
        return build_vacuum(notify=_notify)
    except XiaoError as e:
        err_console.print(f"[red]{e}[/red]")
        raise SystemExit(e.exit_code) from e


def _report_action(result, success: str, style: str = "green") -> None:
    """Print success, or print the rejection to stderr and exit non-zero."""
    code = extract_code(result)
    if code == 0:
        rprint(f"[{style}]✓ {success}[/{style}]")
        return
    err_console.print(f"[red]✗ Command rejected by the vacuum (code {code}).[/red]")
    err_console.print(json.dumps(result, indent=2, default=str), markup=False, highlight=False)
    raise typer.Exit(EXIT_GENERIC)


@app.command()
def start():
    """Start a full-house clean (the X20+ always washes the mop first)."""
    _report_action(_vacuum().start(), "Cleaning started.")


@app.command()
def stop():
    """Stop cleaning."""
    _report_action(_vacuum().stop(), "Cleaning stopped.", style="yellow")


@app.command()
def pause():
    """Pause cleaning.

    In cloud mode the X20+ exposes no pause action, so this stops the current
    job; `xiao start` begins a new one rather than resuming.
    """
    vac = _vacuum()
    result = vac.pause()
    if getattr(vac, "PAUSE_IS_STOP", False):
        _report_action(
            result, "Cleaning stopped (cloud mode has no true pause; `xiao start` starts a new run).", "yellow"
        )
    else:
        _report_action(result, "Cleaning paused.", style="yellow")


@app.command()
def dock():
    """Return to charging dock."""
    _report_action(_vacuum().home(), "Returning to dock.")


@app.command()
def status(
    full: bool = typer.Option(False, "--full", "-f", help="Show comprehensive status with all details"),
    as_json: bool = typer.Option(False, "--json", "-j", help="Output raw JSON instead of a Rich panel"),
):
    """Show current vacuum status."""
    vac = _vacuum()
    if full:
        try:
            data = vac.full_status()
        except AttributeError:
            data = vac.status()
    else:
        data = vac.status()

    if as_json:
        sys.stdout.write(json.dumps(data, indent=2, default=str))
        sys.stdout.write("\n")
        return

    if full:
        try:
            render_full_status(data)
        except Exception:
            render_status(data)
    else:
        render_status(data)


@app.command()
def find():
    """Make the vacuum beep to locate it."""
    _report_action(_vacuum().find(), "Beeping...", style="cyan")


# ── Base station commands ─────────────────────────────────────


@app.command()
def wash():
    """Start mop washing at base station."""
    vac = _vacuum()
    _report_action(vac.mop_wash(), "Mop washing started.", style="green")


@app.command()
def dry(
    stop_dry: bool = typer.Option(False, "--stop", help="Stop drying instead of starting"),
):
    """Start or stop mop drying at base station."""
    vac = _vacuum()
    if stop_dry:
        _report_action(vac.stop_dry(), "Drying stopped.", style="yellow")
    else:
        _report_action(vac.start_dry(), "Drying started.", style="green")


@app.command()
def dust():
    """Start dust collection at base station."""
    vac = _vacuum()
    _report_action(vac.dust_collect(), "Dust collection started.", style="green")


@app.command()
def eject():
    """Eject base station tray."""
    vac = _vacuum()
    _report_action(vac.eject_tray(), "Base tray ejected.", style="green")


# ── Report command ────────────────────────────────────────────


@app.command()
def report():
    """Full vacuum report: status + consumables + schedules + history."""
    vac = _vacuum()

    # Gather everything
    sections = {}

    try:
        sections["status"] = vac.status()
    except Exception as e:
        sections["status"] = {"error": str(e)}

    try:
        sections["device"] = vac.device_info()
    except Exception as e:
        sections["device"] = {"error": str(e)}

    try:
        sections["consumables"] = vac.consumable_status()
    except Exception as e:
        sections["consumables"] = {"error": str(e)}

    try:
        sections["history"] = vac.clean_history()
    except Exception as e:
        sections["history"] = {"error": str(e)}

    try:
        sections["dnd"] = vac.dnd_status()
    except Exception as e:
        sections["dnd"] = {"error": str(e)}

    try:
        sections["water"] = vac.water_level()
    except Exception:
        sections["water"] = {}

    try:
        sections["schedules"] = vac.schedules_parsed()
    except (AttributeError, Exception):
        try:
            sections["schedules"] = vac.timer_list()
        except Exception:
            sections["schedules"] = []

    render_report(sections)


@app.command()
def raw(
    siid: int = typer.Argument(help="Service ID"),
    aiid: int = typer.Argument(help="Action ID"),
    params: list[str] = typer.Argument(None, help="Action parameters"),
):
    """Send a raw MIoT command (escape hatch)."""
    vac = _vacuum()
    parsed = [json.loads(p) if p.startswith(("{", "[")) else p for p in (params or [])]
    result = vac.raw_command(siid, aiid, parsed)
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    if extract_code(result) != 0:
        raise typer.Exit(EXIT_GENERIC)


@app.command()
def cloud_login():
    """Login to Xiaomi Cloud and save session (for cloud mode)."""
    from xiao.core.cloud import XiaomiCloud

    cloud_cfg = get_cloud_config()
    username = cloud_cfg.get("username", "")
    password = cloud_cfg.get("password", "")

    if not username:
        rprint("[red]Cloud not configured. Run [bold]xiao setup cloud[/bold] first.[/red]")
        raise SystemExit(EXIT_NOT_CONFIGURED)

    rprint(f"[cyan]Logging into Xiaomi Cloud as {username}...[/cyan]")
    cloud = XiaomiCloud(username, password, on_status=lambda m: rprint(f"  {m}"))

    try:
        ok = cloud.login()
    except Exception as e:
        rprint(f"[red]✗ Login failed: {e}[/red]")
        raise SystemExit(EXIT_TOKEN_EXPIRED) from e

    if ok:
        save_cloud_session(cloud.user_id, cloud.service_token, cloud.ssecurity)
        rprint("[green]✓ Login successful! Session saved.[/green]")
        rprint(f"  userId: {cloud.user_id}")
        rprint(f"  ssecurity: {'yes' if cloud.ssecurity else 'no'}")
    else:
        rprint("[red]✗ Login failed.[/red]")
        raise SystemExit(EXIT_TOKEN_EXPIRED)


_LOOPBACK = ("127.0.0.1", "localhost", "::1")


@app.command()
def web(
    port: int = typer.Option(8120, help="Port to serve on"),
    host: str = typer.Option(
        "127.0.0.1",
        help="Interface to bind. Anything other than localhost exposes vacuum control to the network "
        "and requires an access token (generated automatically unless --token is given).",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        envvar="XIAO_WEB_TOKEN",
        help="Require this access token for the API (open the dashboard with ?token=...).",
    ),
):
    """Launch the Mission Control web dashboard."""
    import secrets

    import uvicorn

    from xiao.dashboard.server import create_app

    loopback = host in _LOOPBACK
    if not loopback and not token:
        token = secrets.token_urlsafe(24)

    shown_host = "localhost" if loopback else host
    url = f"http://{shown_host}:{port}/" + (f"?token={token}" if token else "")
    rprint("[cyan]🤖 XIAOMI X20+ MISSION CONTROL[/cyan]")
    rprint(f"[dim]Starting dashboard on[/dim] {url}")
    if not loopback:
        rprint(
            f"[yellow]⚠ Listening on {host}: anyone on this network with the token above can control the "
            "vacuum. Traffic is plain HTTP.[/yellow]"
        )
    web_app = create_app(auth_token=token, loopback_only=loopback)
    uvicorn.run(web_app, host=host, port=port, log_level="info")


def main():
    app()
