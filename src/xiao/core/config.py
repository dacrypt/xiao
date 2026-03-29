"""Configuration manager for xiao CLI."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w
from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("xiao"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return tomllib.loads(CONFIG_FILE.read_text())


def save(config: dict) -> None:
    ensure_config_dir()
    CONFIG_FILE.write_bytes(tomli_w.dumps(config).encode())


def get_device() -> tuple[str, str, str]:
    """Return (ip, token, model) or raise with helpful message."""
    config = load()
    device = config.get("device", {})
    ip = device.get("ip")
    token = device.get("token")
    model = device.get("model")
    if not ip or not token:
        from rich import print as rprint

        rprint("[red]No device configured.[/red] Run [bold]xiao setup init[/bold] first.")
        raise SystemExit(1)
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


def save_cloud_session(user_id: str, service_token: str, ssecurity: str) -> None:
    """Persist cloud session tokens so we don't re-login every time."""
    cfg = load()
    if "cloud" not in cfg:
        cfg["cloud"] = {}
    cfg["cloud"]["session"] = {
        "user_id": user_id,
        "service_token": service_token,
        "ssecurity": ssecurity,
    }
    save(cfg)


def get_cloud_session() -> dict | None:
    """Load saved cloud session tokens."""
    cfg = load()
    session = cfg.get("cloud", {}).get("session")
    if session and session.get("service_token"):
        return session
    return None


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


def resolve_room(identifier: str) -> int:
    """Resolve a room name or ID to a numeric room ID."""
    # Try as integer first
    try:
        return int(identifier)
    except ValueError:
        pass
    # Search aliases (case-insensitive)
    rooms = get_rooms()
    for rid, name in rooms.items():
        if name.lower() == identifier.lower():
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
    TANK_STATE_FILE.write_text(json.dumps(state, indent=2))


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
