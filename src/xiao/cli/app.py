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
from xiao.core.config import (
    get_cloud_config,
    get_cloud_session,
    get_device,
    get_protocol,
    is_cloud_mode,
    save_cloud_session,
)
from xiao.core.exit_codes import EXIT_NOT_CONFIGURED, EXIT_TOKEN_EXPIRED
from xiao.core.vacuum import get_vacuum
from xiao.ui.formatters import render_full_status, render_report, render_status

console = Console()

app = typer.Typer(
    name="xiao",
    help="Control your Xiaomi/Roborock vacuum from the terminal.",
    epilog=help_epilog(),
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
def _root_callback(ctx: typer.Context) -> None:
    """Run on every CLI invocation. Shows the first-run CTA; sets up
    debug logging when XIAO_DEBUG=1; when no subcommand is given, prints
    vacuum status if configured, or help otherwise."""
    if os.environ.get("XIAO_DEBUG") == "1":
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(levelname)s %(name)s] %(message)s",
        )

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


def _cloud_vacuum():
    """Get a CloudVacuumService, logging in if needed."""
    import requests
    from micloud.miutils import get_random_agent_id

    from xiao.core.cloud import XiaomiCloud
    from xiao.core.cloud_vacuum import CloudVacuumService

    cloud_cfg = get_cloud_config()
    username = cloud_cfg.get("username", "")
    password = cloud_cfg.get("password", "")
    server = cloud_cfg.get("server", "us")
    did = cloud_cfg.get("did", "")
    model = cloud_cfg.get("model", "")

    if not username or not did:
        rprint("[red]Cloud mode enabled but not configured. Run [bold]xiao setup cloud[/bold].[/red]")
        raise SystemExit(EXIT_NOT_CONFIGURED)

    def _build_cloud_from_session(sd):
        c = XiaomiCloud.__new__(XiaomiCloud)
        c.username = username
        c.password = password
        c.user_id = sd["user_id"]
        c.service_token = sd["service_token"]
        c.ssecurity = sd["ssecurity"]
        c.on_status = None
        aid = get_random_agent_id()
        ua = f"Android-7.1.1-1.0.0-ONEPLUS A3010-136-{aid} APP/xiaomi.smarthome APPV/62830"
        c.session = requests.Session()
        c.session.headers.update({"User-Agent": ua})
        return c

    # Try to reuse saved session
    session_data = get_cloud_session()
    if session_data:
        cloud = _build_cloud_from_session(session_data)
    else:
        # Try browser-based token refresh first (no email verification needed)
        from xiao.core.token_refresh import refresh_tokens

        rprint("[yellow]No saved session. Refreshing via Chromium CDP session...[/yellow]")
        tokens = refresh_tokens(username, password)
        if tokens:
            save_cloud_session(tokens["userId"], tokens["serviceToken"], tokens["ssecurity"])
            cloud = _build_cloud_from_session(
                {
                    "user_id": tokens["userId"],
                    "service_token": tokens["serviceToken"],
                    "ssecurity": tokens["ssecurity"],
                }
            )
            rprint("[green]Tokens refreshed via browser.[/green]")
        else:
            # Fall back to full login
            rprint("[yellow]Browser refresh failed. Trying full login...[/yellow]")
            cloud = XiaomiCloud(username, password, on_status=lambda m: rprint(f"  [dim]{m}[/dim]"))
            if not cloud.login():
                rprint("[red]Cloud login failed.[/red]")
                raise SystemExit(EXIT_TOKEN_EXPIRED)
            save_cloud_session(cloud.user_id, cloud.service_token, cloud.ssecurity)
            rprint("[green]Logged in and session saved.[/green]")

    return CloudVacuumService(cloud, did=did, model=model, country=server)


def _vacuum():
    if is_cloud_mode():
        return _cloud_vacuum()
    ip, token, model = get_device()
    protocol = get_protocol()
    return get_vacuum(ip, token, model, protocol)


@app.command()
def start():
    """Start cleaning."""
    vac = _vacuum()
    result = vac.start()
    if isinstance(result, dict):
        code = result.get("code", result.get("result", {}).get("code", -1))
        if code == 0:
            rprint("[green]✓ Cleaning started.[/green]")
        else:
            rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")
    else:
        rprint("[green]✓ Cleaning started.[/green]")


@app.command()
def stop():
    """Stop cleaning."""
    vac = _vacuum()
    result = vac.stop()
    if isinstance(result, dict):
        code = result.get("code", -1)
        if code == 0:
            rprint("[yellow]✓ Cleaning stopped.[/yellow]")
        else:
            rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")
    else:
        rprint("[yellow]✓ Cleaning stopped.[/yellow]")


@app.command()
def pause():
    """Pause cleaning."""
    vac = _vacuum()
    result = vac.pause()
    if isinstance(result, dict):
        rprint("[yellow]✓ Cleaning paused.[/yellow]")
    else:
        rprint("[yellow]✓ Cleaning paused.[/yellow]")


@app.command()
def dock():
    """Return to charging dock."""
    vac = _vacuum()
    result = vac.home()
    if isinstance(result, dict):
        code = result.get("code", -1)
        if code == 0:
            rprint("[green]✓ Returning to dock.[/green]")
        else:
            rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")
    else:
        rprint("[green]✓ Returning to dock.[/green]")


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
    vac = _vacuum()
    result = vac.find()
    if isinstance(result, dict):
        rprint("[cyan]✓ Beeping...[/cyan]")
    else:
        rprint("[cyan]✓ Beeping...[/cyan]")


# ── Base station commands ─────────────────────────────────────


@app.command()
def wash():
    """Start mop washing at base station."""
    vac = _vacuum()
    result = vac.mop_wash()
    code = _extract_code(result)
    if code == 0:
        rprint("[green]✓ Mop washing started.[/green]")
    else:
        rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")


@app.command()
def dry(
    stop_dry: bool = typer.Option(False, "--stop", help="Stop drying instead of starting"),
):
    """Start or stop mop drying at base station."""
    vac = _vacuum()
    if stop_dry:
        result = vac.stop_dry()
        code = _extract_code(result)
        if code == 0:
            rprint("[yellow]✓ Drying stopped.[/yellow]")
        else:
            rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")
    else:
        result = vac.start_dry()
        code = _extract_code(result)
        if code == 0:
            rprint("[green]✓ Drying started.[/green]")
        else:
            rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")


@app.command()
def dust():
    """Start dust collection at base station."""
    vac = _vacuum()
    result = vac.dust_collect()
    code = _extract_code(result)
    if code == 0:
        rprint("[green]✓ Dust collection started.[/green]")
    else:
        rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")


@app.command()
def eject():
    """Eject base station tray."""
    vac = _vacuum()
    result = vac.eject_tray()
    code = _extract_code(result)
    if code == 0:
        rprint("[green]✓ Base tray ejected.[/green]")
    else:
        rprint(f"[yellow]Response: {json.dumps(result, indent=2)}[/yellow]")


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
    rprint(result)


@app.command()
def cloud_login():
    """Login to Xiaomi Cloud and save session (for cloud mode)."""
    from xiao.core.cloud import XiaomiCloud

    cloud_cfg = get_cloud_config()
    username = cloud_cfg.get("username", "")
    password = cloud_cfg.get("password", "")

    if not username:
        rprint("[red]Cloud not configured. Run [bold]xiao setup cloud[/bold] first.[/red]")
        raise SystemExit(1)

    rprint(f"[cyan]Logging into Xiaomi Cloud as {username}...[/cyan]")
    cloud = XiaomiCloud(username, password, on_status=lambda m: rprint(f"  {m}"))

    if cloud.login():
        save_cloud_session(cloud.user_id, cloud.service_token, cloud.ssecurity)
        rprint("[green]✓ Login successful! Session saved.[/green]")
        rprint(f"  userId: {cloud.user_id}")
        rprint(f"  ssecurity: {'yes' if cloud.ssecurity else 'no'}")
    else:
        rprint("[red]✗ Login failed.[/red]")
        raise SystemExit(1)


@app.command()
def web(port: int = typer.Option(8120, help="Port to serve on")):
    """Launch the Mission Control web dashboard."""
    import uvicorn

    from xiao.dashboard.server import create_app

    rprint("[cyan]🤖 XIAOMI X20+ MISSION CONTROL[/cyan]")
    rprint(f"[dim]Starting dashboard on http://localhost:{port}[/dim]")
    web_app = create_app()
    uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="info")


def _extract_code(result) -> int:
    """Pull the response code from a cloud API result."""
    if isinstance(result, dict):
        return result.get("code", result.get("result", {}).get("code", -1))
    return 0


def main():
    app()
