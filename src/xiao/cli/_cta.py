"""GitHub star CTA helpers.

Three CTA surfaces:
1. Static banner printed after `xiao setup init` succeeds.
2. One-shot first-run banner printed before any command on first invocation.
3. Epilog line in the top-level `--help` output.

Honors `XIAO_NO_CTA=1` and `NO_COLOR`/non-TTY to stay quiet in CI/scripts.
"""

from __future__ import annotations

import os
import sys

from xiao.core.config import CONFIG_DIR, ensure_config_dir

REPO_URL = "https://github.com/dacrypt/xiao"
STAR_URL = f"{REPO_URL}/stargazers"
FLAG_FILE = CONFIG_DIR / ".star-cta-shown"

_HELP_EPILOG = f"If xiao helps you, consider starring the repo: {REPO_URL}"


def _suppressed() -> bool:
    if os.environ.get("XIAO_NO_CTA") == "1":
        return True
    return not sys.stdout.isatty()


def help_epilog() -> str:
    """Epilog string for Typer's top-level help."""
    return _HELP_EPILOG


def _mark_shown() -> None:
    try:
        ensure_config_dir()
        FLAG_FILE.touch(exist_ok=True)
    except OSError:
        pass


def _already_shown() -> bool:
    return FLAG_FILE.exists()


def show_star_banner(*, mark: bool = True) -> None:
    """Print a static 'star the repo' banner. Safe in non-TTY (no-op)."""
    if _suppressed():
        if mark:
            _mark_shown()
        return

    from rich.console import Console
    from rich.panel import Panel

    Console().print(
        Panel(
            f"[bold]Enjoying xiao?[/bold]\n"
            f"Star the repo on GitHub — it helps other users find it.\n\n"
            f"  [cyan]{STAR_URL}[/cyan]\n\n"
            f"[dim]Silence this with [bold]XIAO_NO_CTA=1[/bold].[/dim]",
            title="⭐ Support xiao",
            border_style="yellow",
        )
    )
    if mark:
        _mark_shown()


def maybe_show_first_run_cta() -> None:
    """Show the banner once per installation, then persist a flag."""
    if _already_shown() or _suppressed():
        return
    show_star_banner(mark=True)
