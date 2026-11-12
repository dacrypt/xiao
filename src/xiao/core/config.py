"""Configuration manager for xiao CLI."""

from __future__ import annotations

import contextlib
import os
import tempfile
import tomllib
from pathlib import Path

import tomli_w
from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("xiao"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


# config.toml holds the Xiaomi account password and live session tokens, so it
# (and every other state file xiao writes) is created owner-read/write only.
PRIVATE_FILE_MODE = 0o600
PRIVATE_DIR_MODE = 0o700


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(mode=PRIVATE_DIR_MODE, parents=True, exist_ok=True)


def write_private_file(path: Path, data: bytes) -> None:
    """Atomically write ``data`` to ``path`` with 0600 permissions.

    Writes to a temp file in the same directory and renames it over the
    target, so a concurrent reader (CLI + dashboard) never sees a truncated
    file and a crash mid-write never corrupts the existing one.
    """
    path.parent.mkdir(mode=PRIVATE_DIR_MODE, parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, PRIVATE_FILE_MODE)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def harden_permissions() -> None:
    """Tighten permissions on config files written by older xiao versions (0644)."""
    for path in (CONFIG_FILE, TANK_STATE_FILE):
        with contextlib.suppress(OSError):
            if path.exists() and path.stat().st_mode & 0o077:
                os.chmod(path, PRIVATE_FILE_MODE)


def load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return tomllib.loads(CONFIG_FILE.read_text())


def save(config: dict) -> None:
    ensure_config_dir()
    write_private_file(CONFIG_FILE, tomli_w.dumps(config).encode())


def get_device() -> tuple[str, str, str]:
    """Return (ip, token, model) or raise with helpful message."""
    config = load()
    device = config.get("device", {})
    ip = device.get("ip")
    token = device.get("token")
    model = device.get("model")
    if not ip or not token:
        from rich import print as rprint

        from xiao.core.exit_codes import EXIT_NOT_CONFIGURED

        rprint(
            "[red]No device configured.[/red] Run [bold]xiao setup cloud[/bold] (or [bold]xiao setup init[/bold] for local mode) first."
        )
        raise SystemExit(EXIT_NOT_CONFIGURED)
    return ip, token, model or ""


def get_protocol() -> str:
    config = load()
    return config.get("device", {}).get("protocol", {}).get("type", "genericmiot")


def is_cloud_mode() -> bool:
    """Check if device is configured for cloud-only control."""
    cfg = load()
    return cfg.get("cloud", {}).get("enabled", False)


def get_cloud_config() -> dict:
    """Return cloud config: username, server, did, session data."""
    cfg = load()
    return cfg.get("cloud", {})


def save_cloud_session(
    user_id: str | None,
    service_token: str | None,
    ssecurity: str | None,
) -> None:
    """Persist cloud session tokens so we don't re-login every time.

    Accepts `None` on any field for caller convenience (dict.get / attribute
    access may return None during login); empty strings are coerced so the
    TOML writer doesn't choke on `None`.
    """
    cfg = load()
    if "cloud" not in cfg:
        cfg["cloud"] = {}
    cfg["cloud"]["session"] = {
        "user_id": user_id or "",
        "service_token": service_token or "",
        "ssecurity": ssecurity or "",
    }
    save(cfg)


def get_cloud_session() -> dict | None:
    """Load saved cloud session tokens."""
    cfg = load()
    session = cfg.get("cloud", {}).get("session")
    if session and session.get("service_token"):
        return session
    return None


def get_web_token() -> str | None:
    """Persistent access token for `xiao web` when it listens beyond localhost."""
    token = load().get("web", {}).get("token")
    return token if isinstance(token, str) and token else None


def ensure_web_token() -> str:
    """Return the saved web token, creating and saving one on first use."""
    token = get_web_token()
    if token:
        return token
    import secrets

    token = secrets.token_urlsafe(24)
    cfg = load()
    cfg.setdefault("web", {})["token"] = token
    save(cfg)
    return token


def get_rooms() -> dict[str, str]:
    """Return room aliases: {room_id_str: name}."""
    cfg = load()
    return cfg.get("rooms", {})


def set_room_alias(room_id: int, name: str) -> None:
    """Set a room alias."""
    cfg = load()
    if "rooms" not in cfg:
        cfg["rooms"] = {}
    cfg["rooms"][str(room_id)] = name
    save(cfg)


def _fold(text: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def resolve_room(identifier: str) -> int:
    """Resolve a room name or ID to a numeric room ID."""
    # Try as integer first
    try:
        return int(identifier)
    except ValueError:
        pass
    # Search aliases (case- and accent-insensitive, so "bano" or "BAÑO" find "Baño")
    rooms = get_rooms()
    wanted = _fold(identifier)
    for rid, name in rooms.items():
        if _fold(name) == wanted:
            return int(rid)
    raise ValueError(f"Unknown room: '{identifier}'. Use 'xiao rooms' to see available rooms.")


def is_configured() -> bool:
    config = load()
    device = config.get("device", {})
    # Either local or cloud mode
    if is_cloud_mode():
        cloud = config.get("cloud", {})
        return bool(cloud.get("username") and cloud.get("did"))
    return bool(device.get("ip") and device.get("token"))


# ── Water Tank Level Estimation ──────────────────────────────

TANK_STATE_FILE = CONFIG_DIR / "tank_state.json"


def get_tank_state() -> dict:
    """Load tank state from JSON file."""
    import json

    if TANK_STATE_FILE.exists():
        return json.loads(TANK_STATE_FILE.read_text())
    return {
        "clean_tank_reset_at": None,
        "dirty_tank_reset_at": None,
        "area_since_clean_reset": 0,
        "area_since_dirty_reset": 0,
        "last_total_area": 0,
    }


def save_tank_state(state: dict) -> None:
    """Save tank state to JSON file."""
    import json

    ensure_config_dir()
    write_private_file(TANK_STATE_FILE, json.dumps(state, indent=2).encode())


def reset_tanks(which: str = "both") -> dict:
    """Reset tank tracking. which: 'clean', 'dirty', or 'both'."""
    from datetime import datetime

    state = get_tank_state()
    now = datetime.now().isoformat()
    if which in ("clean", "both"):
        state["clean_tank_reset_at"] = now
        state["area_since_clean_reset"] = 0
    if which in ("dirty", "both"):
        state["dirty_tank_reset_at"] = now
        state["area_since_dirty_reset"] = 0
    save_tank_state(state)
    return state
