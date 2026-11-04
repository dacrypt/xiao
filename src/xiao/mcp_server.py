"""MCP server wrapper around xiao.

Exposes vacuum control as a Model Context Protocol server so MCP-aware
hosts (Claude Desktop, Cursor, mcp.so, etc.) can drive the vacuum as a
structured tool instead of shelling out to the CLI.

Run via `xiao mcp` (stdio transport). Add to a host by pointing it at:

    {
      "mcpServers": {
        "xiao": {
          "command": "xiao",
          "args": ["mcp"]
        }
      }
    }

The server reuses the same `config.toml` / browser profile / cached
session the CLI uses, so the one-time `xiao setup cloud` +
`xiao setup browser-login` flow works for MCP too.

Two rules keep the stdio transport healthy:
  * nothing is ever printed to stdout (progress goes to the logger/stderr);
  * the blocking vacuum calls run in a worker thread, never on the event loop.
"""

from __future__ import annotations

import functools
import logging
import threading
from typing import TYPE_CHECKING, Any

from xiao.core.room_cleaning import extract_code, known_rooms, start_room_clean

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    import anyio
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        'The MCP server requires the `mcp` package. Install it with `pip install "xiao-cli[mcp]"`.'
    ) from exc

logger = logging.getLogger(__name__)

_vac_instance: Any = None
_vac_lock = threading.Lock()


def _vac():
    """Return a cached vacuum service (built lazily, so `xiao mcp` starts without logging in)."""
    global _vac_instance
    with _vac_lock:
        if _vac_instance is None:
            from xiao.core.service import build_vacuum

            _vac_instance = build_vacuum(notify=lambda m: logger.info("%s", m))
        return _vac_instance


def _reset_vac() -> None:
    global _vac_instance
    with _vac_lock:
        _vac_instance = None


def _extract_code(result: Any) -> int:
    return extract_code(result)


mcp = FastMCP("xiao")


def _tool[F: Callable[..., Any]](fn: F) -> F:
    """Register ``fn`` as an MCP tool that runs in a worker thread.

    FastMCP calls synchronous tools directly on its event loop, which would
    block the stdio transport and make Playwright's sync API (token refresh)
    refuse to run. The registered wrapper is async and offloads the call; the
    plain function is returned unchanged so it stays directly callable.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
        except Exception as e:
            from xiao.core.cloud import TokenExpiredError
            from xiao.core.service import CloudAuthError

            if isinstance(e, (TokenExpiredError, CloudAuthError)):
                _reset_vac()
            raise

    mcp.tool()(wrapper)
    return fn


def _action(result: Any) -> dict:
    code = _extract_code(result)
    return {"ok": code == 0, "code": code}


@_tool
def status() -> dict:
    """Get the current vacuum status: state, battery %, fan speed,
    charging state, fault code, and other runtime fields. Returns the
    same dict as `xiao status --json`."""
    return _vac().status()


@_tool
def start_cleaning() -> dict:
    """Start a full-house cleaning job immediately (the X20+ washes the mop first)."""
    return _action(_vac().start())


@_tool
def stop_cleaning() -> dict:
    """Stop the current cleaning job."""
    return _action(_vac().stop())


@_tool
def pause_cleaning() -> dict:
    """Pause the current cleaning job. In cloud mode the X20+ has no pause
    action, so this STOPS the job (`stopped_instead_of_paused: true`);
    `start_cleaning` then begins a new run rather than resuming."""
    vac = _vac()
    result = _action(vac.pause())
    result["stopped_instead_of_paused"] = bool(getattr(vac, "PAUSE_IS_STOP", False))
    return result


@_tool
def return_to_dock() -> dict:
    """Send the vacuum back to its charging dock."""
    return _action(_vac().home())


@_tool
def find_vacuum() -> dict:
    """Make the vacuum beep so a human can locate it in the house."""
    return _action(_vac().find())


@_tool
def consumables() -> dict:
    """Remaining life and hours for brushes, filter, and mop pad."""
    return _vac().consumable_status()


@_tool
def clean_room(room: str) -> dict:
    """Clean a specific room by alias or numeric id. Call `list_rooms`
    first: room IDs are per-map. `verified_started: false` means Xiaomi
    accepted the command but the robot stayed docked."""
    from xiao.core.config import resolve_room

    room_id = resolve_room(room)
    vac = _vac()
    clean_result = start_room_clean(vac, [room_id])
    return {
        "ok": clean_result["accepted"],
        "code": clean_result["code"],
        "room_id": room_id,
        "verified_started": clean_result["verified_started"],
        "warning": clean_result["warning"],
        "transport": clean_result["transport"],
    }


@_tool
def list_rooms() -> list[dict]:
    """List rooms the vacuum knows about: {id, name, sources}. Sources are
    the device room mapping, its schedules, and user aliases."""
    from xiao.core.config import get_rooms

    vac = None
    try:
        vac = _vac()
    except Exception as e:
        logger.info("list_rooms: vacuum unavailable, listing aliases only (%s)", e)
    return known_rooms(vac, get_rooms())


def run() -> None:
    """Entry point used by `xiao mcp`. Blocks on stdio."""
    mcp.run()


if __name__ == "__main__":
    run()
