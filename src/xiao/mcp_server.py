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
"""

from __future__ import annotations

from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        'The MCP server requires the `mcp` package. Install it with `pip install "xiao-cli[mcp]"`.'
    ) from exc


def _vac():
    # Imported lazily so `xiao mcp --help` and module import don't
    # trigger a cloud login.
    from xiao.cli.app import _vacuum

    return _vacuum()


def _extract_code(result: Any) -> int:
    if isinstance(result, dict):
        return result.get("code", result.get("result", {}).get("code", -1))
    return 0


mcp = FastMCP("xiao")


@mcp.tool()
def status() -> dict:
    """Get the current vacuum status: state, battery %, fan speed,
    charging state, fault code, and other runtime fields. Returns the
    same dict as `xiao status --json`."""
    return _vac().status()


@mcp.tool()
def start_cleaning() -> dict:
    """Start a full-house cleaning job immediately."""
    return {"code": _extract_code(_vac().start())}


@mcp.tool()
def stop_cleaning() -> dict:
    """Stop the current cleaning job."""
    return {"code": _extract_code(_vac().stop())}


@mcp.tool()
def pause_cleaning() -> dict:
    """Pause (without cancelling) the current cleaning job."""
    return {"code": _extract_code(_vac().pause())}


@mcp.tool()
def return_to_dock() -> dict:
    """Send the vacuum back to its charging dock."""
    return {"code": _extract_code(_vac().home())}


@mcp.tool()
def find_vacuum() -> dict:
    """Make the vacuum beep so a human can locate it in the house."""
    return {"code": _extract_code(_vac().find())}


@mcp.tool()
def consumables() -> dict:
    """Remaining life and hours for brushes, filter, and mop pad."""
    return _vac().consumable_status()


@mcp.tool()
def clean_room(room: str) -> dict:
    """Clean a specific room by alias or numeric id. Aliases are
    configured via `xiao rooms rename <id> <name>`; the MCP tool resolves
    them the same way the CLI does."""
    from xiao.core.config import resolve_room

    room_id = resolve_room(room)
    vac = _vac()
    try:
        result = vac.clean_rooms_miot([room_id])
    except (AttributeError, Exception):
        result = vac.clean_rooms([room_id])
    return {"code": _extract_code(result)}


@mcp.tool()
def list_rooms() -> list[dict]:
    """List configured rooms: {id, name}. Useful before calling
    `clean_room` so the host knows which aliases exist."""
    from xiao.core.config import get_rooms

    return [{"id": int(rid), "name": name} for rid, name in get_rooms().items()]


def run() -> None:
    """Entry point used by `xiao mcp`. Blocks on stdio."""
    mcp.run()


if __name__ == "__main__":
    run()
