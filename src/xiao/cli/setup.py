"""Setup commands — init wizard, token extraction, discovery, test."""

from __future__ import annotations

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from xiao.cli._cta import show_star_banner
from xiao.core import config

console = Console()
app = typer.Typer(no_args_is_help=True)


@app.command()
def init():
    """Interactive setup wizard. Configures your vacuum step by step."""
    console.print(
        Panel(
            "[bold cyan]Welcome to xiao![/bold cyan]\nLet's configure your Xiaomi/Roborock vacuum.",
            border_style="cyan",
        )
    )

    has_token = Confirm.ask("Do you already have the device token?", default=False)

    if has_token:
        ip = Prompt.ask("Device IP address")
        token = Prompt.ask("Device token (32 hex chars)")
        model = Prompt.ask("Device model (e.g. xiaomi.vacuum.b108gl)", default="")
        protocol = Prompt.ask("Protocol", choices=["genericmiot", "roborock"], default="genericmiot")
    else:
        rprint("\n[bold]Extracting token from Xiaomi cloud...[/bold]")
        server_choices = {"1": "cn", "2": "de", "3": "us", "4": "ru", "5": "sg", "6": "in"}
        rprint("Cloud servers: 1=China, 2=Europe, 3=US, 4=Russia, 5=Singapore, 6=India")
        server_num = Prompt.ask("Select server", default="2")
        server = server_choices.get(server_num, "de")

        username = Prompt.ask("Xiaomi account (email/phone)")
        password = Prompt.ask("Password", password=True)

        try:
            from xiao.core.cloud import extract_device_info, find_vacuums, get_cloud_devices

            with console.status("Logging into Xiaomi cloud..."):
                all_devices = get_cloud_devices(username, password, server)

            vacuums = find_vacuums(all_devices)

            if not vacuums:
                rprint("[yellow]No vacuums found. Showing all devices:[/yellow]")
                vacuums = all_devices

            if not vacuums:
                rprint("[red]No devices found in your account.[/red]")
                raise typer.Exit(1)

            table = Table(title="Found Devices", border_style="cyan")
            table.add_column("#", style="bold")
            table.add_column("Name")
            table.add_column("Model")
            table.add_column("IP")

            device_list = []
            for i, d in enumerate(vacuums, 1):
                info = extract_device_info(d)
                device_list.append(info)
                table.add_row(str(i), info["name"], info["model"], info["ip"])

            console.print(table)

            choice = Prompt.ask(
                "Select device number",
                default="1",
            )
            selected = device_list[int(choice) - 1]
            ip = selected["ip"] or Prompt.ask("Device IP (not found in cloud, enter manually)")
            token = selected["token"]
            model = selected["model"]
            protocol = "genericmiot"

            rprint(f"\n[green]Token extracted:[/green] {token[:8]}...{token[-4:]}")

        except ImportError as exc:
            rprint("[red]micloud not installed. Install with: uv add python-miio[cloud][/red]")
            raise typer.Exit(1) from exc
        except Exception as e:
            rprint(f"[red]Cloud login failed: {e}[/red]")
            rprint("You can try entering the token manually.")
            ip = Prompt.ask("Device IP address")
            token = Prompt.ask("Device token (32 hex chars)")
            model = Prompt.ask("Device model", default="")
            protocol = "genericmiot"

    # Save config
    cfg = config.load()
    cfg["device"] = {
        "ip": ip,
        "token": token,
        "model": model,
        "name": model,
        "protocol": {"type": protocol},
    }
    config.save(cfg)

    rprint(f"\n[green]Config saved to {config.CONFIG_FILE}[/green]")

    # Test connection
    if Confirm.ask("Test connection now?", default=True):
        _test_connection(ip, token, model, protocol)

    show_star_banner()


@app.command()
def token():
    """Extract device token from Xiaomi cloud."""
    server_choices = {"1": "cn", "2": "de", "3": "us", "4": "ru", "5": "sg", "6": "in"}
    rprint("Cloud servers: 1=China, 2=Europe, 3=US, 4=Russia, 5=Singapore, 6=India")
    server_num = Prompt.ask("Select server", default="2")
    server = server_choices.get(server_num, "de")

    username = Prompt.ask("Xiaomi account (email/phone)")
    password = Prompt.ask("Password", password=True)

    try:
        from xiao.core.cloud import extract_device_info, get_cloud_devices

        with console.status("Fetching devices..."):
            devices = get_cloud_devices(username, password, server)

        table = Table(title="All Devices", border_style="cyan")
        table.add_column("Name")
        table.add_column("Model")
        table.add_column("IP")
        table.add_column("Token")

        for d in devices:
            info = extract_device_info(d)
            table.add_row(info["name"], info["model"], info["ip"], info["token"])

        console.print(table)
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")


@app.command()
def discover():
    """Discover Xiaomi devices on the local network."""
    from xiao.core.discovery import discover_miio

    with console.status("Scanning network..."):
        devices = discover_miio(timeout=5)

    if not devices:
        rprint("[yellow]No devices found on the local network.[/yellow]")
        return

    table = Table(title="Discovered Devices", border_style="cyan")
    table.add_column("IP")
    table.add_column("Info")

    for d in devices:
        table.add_row(d["ip"], str(d.get("info", "")))

    console.print(table)


@app.command()
def test():
    """Test connectivity to the configured vacuum."""
    if not config.is_configured():
        rprint("[red]No device configured. Run [bold]xiao setup init[/bold] first.[/red]")
        raise typer.Exit(1)

    ip, token, model = config.get_device()
    protocol = config.get_protocol()
    _test_connection(ip, token, model, protocol)


@app.command()
def show():
    """Show current configuration."""
    cfg = config.load()
    if not cfg:
        rprint("[yellow]No configuration found.[/yellow]")
        return

    device = cfg.get("device", {})
    lines = []
    lines.append(f"  [bold]IP:[/bold]       {device.get('ip', '—')}")
    lines.append(f"  [bold]Token:[/bold]    {_mask_token(device.get('token', ''))}")
    lines.append(f"  [bold]Model:[/bold]    {device.get('model', '—')}")
    lines.append(f"  [bold]Protocol:[/bold] {device.get('protocol', {}).get('type', '—')}")
    lines.append(f"  [bold]Config:[/bold]   {config.CONFIG_FILE}")

    console.print(Panel("\n".join(lines), title="Configuration", border_style="cyan"))


@app.command()
def cloud():
    """Configure cloud-only mode (for vacuums not accessible locally)."""
    console.print(
        Panel(
            "[bold cyan]Cloud Mode Setup[/bold cyan]\nFor devices only reachable via Xiaomi Cloud API.",
            border_style="cyan",
        )
    )

    username = Prompt.ask("Xiaomi account (email)")
    password = Prompt.ask("Password", password=True)

    server_choices = {"1": "cn", "2": "de", "3": "us", "4": "ru", "5": "sg", "6": "in"}
    rprint("Cloud servers: 1=China, 2=Europe, 3=US, 4=Russia, 5=Singapore, 6=India")
    server_num = Prompt.ask("Select server", default="3")
    server = server_choices.get(server_num, "us")

    # Login and fetch devices
    try:
        from xiao.core.cloud import XiaomiCloud, extract_device_info, find_vacuums

        cloud_client = XiaomiCloud(username, password, on_status=lambda m: rprint(f"  {m}"))

        with console.status("Logging into Xiaomi cloud..."):
            if not cloud_client.login():
                rprint("[red]Login failed.[/red]")
                raise typer.Exit(1)

        with console.status("Fetching devices..."):
            devices = cloud_client.get_devices(country=server)

        vacuums = find_vacuums(devices)
        device_list = vacuums if vacuums else devices

        if not device_list:
            rprint("[red]No devices found.[/red]")
            raise typer.Exit(1)

        from rich.table import Table

        table = Table(title="Found Devices", border_style="cyan")
        table.add_column("#", style="bold")
        table.add_column("Name")
        table.add_column("Model")
        table.add_column("DID")
        table.add_column("IP")

        infos = []
        for i, d in enumerate(device_list, 1):
            info = extract_device_info(d)
            info["did"] = d.get("did", "")
            infos.append(info)
            table.add_row(str(i), info["name"], info["model"], info["did"], info["ip"])

        console.print(table)

        choice = Prompt.ask("Select device number", default="1")
        selected = infos[int(choice) - 1]

        # Save cloud config
        cfg = config.load()
        cfg["cloud"] = {
            "enabled": True,
            "username": username,
            "password": password,
            "server": server,
            "did": selected["did"],
            "model": selected["model"],
        }
        # Also save device info for reference
        cfg["device"] = {
            "ip": selected["ip"] or "",
            "token": selected["token"] or "",
            "model": selected["model"],
            "name": selected["name"],
            "protocol": {"type": "cloud"},
        }
        config.save(cfg)

        # Save session tokens
        from xiao.core.config import save_cloud_session

        save_cloud_session(cloud_client.user_id, cloud_client.service_token, cloud_client.ssecurity)

        rprint("\n[green]✓ Cloud mode configured![/green]")
        rprint(f"  Device: {selected['name']} ({selected['model']})")
        rprint(f"  DID: {selected['did']}")
        rprint(f"  Server: {server}")
        rprint(f"  Config: {config.CONFIG_FILE}")

        # Quick test
        if Confirm.ask("Test cloud connection now?", default=True):
            from xiao.core.cloud_vacuum import CloudVacuumService

            try:
                cv = CloudVacuumService(cloud_client, did=selected["did"], model=selected["model"], country=server)
                with console.status("Getting vacuum status..."):
                    status = cv.status()
                from xiao.ui.formatters import render_status

                render_status(status)
            except Exception as e:
                rprint(f"[red]Test failed: {e}[/red]")

        rprint("")
        if Confirm.ask(
            "Seed the browser session now so future token refreshes are silent (no captcha)?",
            default=True,
        ):
            _run_browser_login()

        show_star_banner()

    except ImportError as e:
        rprint(f"[red]Missing dependency: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def _mask_token(token: str) -> str:
    if len(token) > 12:
        return f"{token[:8]}...{token[-4:]}"
    return token or "—"


def _run_browser_login() -> None:
    """Open the Xiaomi login page in a managed Chromium and wait for the
    user to finish logging in. Seeds the persistent profile so later token
    refreshes run headless."""
    from xiao.core.token_refresh import PROFILE_DIR, seed_browser_session

    rprint(
        Panel(
            "[bold]A Chromium window will open at account.xiaomi.com.[/bold]\n"
            "Log in (solve captcha / 2FA if prompted), then close the window.\n"
            f"Session data is stored privately under [cyan]{PROFILE_DIR}[/cyan].",
            border_style="cyan",
        )
    )
    try:
        ok = seed_browser_session()
    except Exception as e:
        rprint(f"[red]Browser seeding failed: {e}[/red]")
        rprint(
            "[yellow]If you haven't installed Playwright's browser yet, run:[/yellow]\n"
            "  [bold]playwright install chromium[/bold]"
        )
        return
    if ok:
        rprint("[green]✓ Browser session saved. Token refresh will be silent from now on.[/green]")
    else:
        rprint(
            "[yellow]Window closed before a logged-in URL was detected. "
            "You can rerun [bold]xiao setup browser-login[/bold] anytime.[/yellow]"
        )


@app.command("browser-login")
def browser_login():
    """Open a Chromium window to log into account.xiaomi.com; seeds the
    persistent profile so future cloud commands can refresh tokens silently."""
    _run_browser_login()


def _test_connection(ip: str, token: str, model: str, protocol: str) -> None:
    from xiao.core.vacuum import get_vacuum

    try:
        with console.status(f"Connecting to {ip}..."):
            vac = get_vacuum(ip, token, model, protocol)
            info = vac.device_info()

        rprint("[green]Connection successful![/green]")
        for k, v in info.items():
            if v is not None:
                rprint(f"  [bold]{k}:[/bold] {v}")
    except Exception as e:
        rprint(f"[red]Connection failed: {e}[/red]")
        rprint("Check that the vacuum is on the same network and the token is correct.")
