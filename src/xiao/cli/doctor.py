"""`xiao doctor` — environment & configuration health check."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from xiao.core.config import CONFIG_DIR, CONFIG_FILE, get_cloud_config, is_cloud_mode, is_configured

Status = Literal["ok", "warn", "fail"]
console = Console()


def _row(check: str, status: Status, detail: str = "") -> tuple[str, str, str]:
    icon = {"ok": "[green]✓[/green]", "warn": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}[status]
    return icon, check, detail


def _check_python() -> tuple[str, str, str]:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 12):
        return _row("Python ≥ 3.12", "ok", f"{v.major}.{v.minor}.{v.micro}")
    return _row("Python ≥ 3.12", "fail", f"found {v.major}.{v.minor}.{v.micro}")


def _check_package(name: str) -> tuple[str, str, str]:
    if importlib.util.find_spec(name) is not None:
        return _row(f"`{name}` importable", "ok", "")
    return _row(f"`{name}` importable", "fail", "run `pip install xiao-cli`")


def _check_playwright_browser() -> tuple[str, str, str]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = p.chromium.executable_path
    except Exception as e:
        return _row("Playwright chromium installed", "fail", str(e))
    if path and Path(path).exists():
        return _row("Playwright chromium installed", "ok", path)
    return _row(
        "Playwright chromium installed",
        "fail",
        "run `playwright install chromium`",
    )


def _check_config() -> tuple[str, str, str]:
    if not CONFIG_FILE.exists():
        return _row("Config file", "fail", f"{CONFIG_FILE} missing — run `xiao setup cloud`")
    return _row("Config file", "ok", str(CONFIG_FILE))


def _check_configured() -> tuple[str, str, str]:
    if is_configured():
        mode = "cloud" if is_cloud_mode() else "local"
        return _row("Device configured", "ok", f"{mode} mode")
    return _row("Device configured", "fail", "run `xiao setup cloud`")


def _check_browser_profile() -> tuple[str, str, str]:
    profile = CONFIG_DIR / "chromium"
    if not profile.exists():
        return _row(
            "Browser profile seeded",
            "warn",
            "empty — run `xiao setup browser-login` for silent token refresh",
        )
    # A seeded profile has Default/Cookies (SQLite) among other files.
    if (profile / "Default" / "Cookies").exists():
        return _row("Browser profile seeded", "ok", str(profile))
    return _row(
        "Browser profile seeded",
        "warn",
        "profile exists but no cookies — rerun `xiao setup browser-login`",
    )


def _check_cloud_session() -> tuple[str, str, str]:
    cfg = get_cloud_config()
    session = cfg.get("session", {})
    if session.get("service_token"):
        return _row("Saved cloud session", "ok", "service_token present")
    return _row(
        "Saved cloud session",
        "warn",
        "no cached session — next command will refresh tokens",
    )


def _check_vacuum_reachable() -> tuple[str, str, str]:
    if not is_configured():
        return _row("Vacuum reachable", "warn", "skipped (not configured)")
    try:
        from xiao.cli.app import _vacuum

        vac = _vacuum()
        data = vac.status()
        state = (data or {}).get("state", "?")
        return _row("Vacuum reachable", "ok", f"state={state}")
    except Exception as e:
        return _row("Vacuum reachable", "fail", str(e)[:80])


def _check_tool(name: str) -> tuple[str, str, str]:
    path = shutil.which(name)
    if path:
        return _row(f"`{name}` on PATH", "ok", path)
    return _row(f"`{name}` on PATH", "warn", "not found (optional)")


def run(skip_network: bool = False) -> int:
    checks = [
        _check_python(),
        _check_package("xiao"),
        _check_package("playwright"),
        _check_package("micloud"),
        _check_playwright_browser(),
        _check_config(),
        _check_configured(),
        _check_browser_profile(),
        _check_cloud_session(),
        _check_tool("xiao"),
    ]
    if not skip_network:
        checks.append(_check_vacuum_reachable())

    table = Table(title="xiao doctor", border_style="cyan", show_lines=False)
    table.add_column("", width=2)
    table.add_column("Check", style="bold")
    table.add_column("Detail", overflow="fold")
    for row in checks:
        table.add_row(*row)
    console.print(table)

    fails = sum(1 for r in checks if "[red]" in r[0])
    warns = sum(1 for r in checks if "[yellow]" in r[0])
    if fails:
        console.print(f"[red]{fails} check(s) failed.[/red]")
        return 1
    if warns:
        console.print(f"[yellow]{warns} warning(s). xiao should still work.[/yellow]")
    else:
        console.print("[green]All checks passed.[/green]")
    return 0


def doctor(
    skip_network: bool = typer.Option(False, "--skip-network", help="Skip the live vacuum-reachable check."),
) -> None:
    """Check your xiao install, config, and connectivity. Reports a green
    check / yellow warning / red failure for each step, with remediation
    hints. Exit 1 if any check failed."""
    raise typer.Exit(run(skip_network=skip_network))
