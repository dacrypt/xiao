"""Shared room-clean command helpers.

X20+ room-clean MIoT actions sometimes return ``code=0`` even when the robot
stays docked. These helpers centralize the safer "accepted vs. actually
started" verification path so the CLI, dashboard, and MCP surfaces stay
consistent.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

ROOM_CLEAN_IN_PROGRESS_STATES = {
    "Sweeping",
    "Mopping",
    "Sweeping And Mopping",
    "Go Washing",
    "Washing mop",
    "Building map",
    "Water Inspecting",
    "Remote Clean",
}

ROOM_CLEAN_IDLE_STATES = {
    "Idle",
    "Drying",  # at rest in the dock drying the mop; a new job interrupts it
    "WashingMopPause",
    "Charging",
    "Charging Completed",
    "Go Charging",
    "Paused",
    "Error",
}


class LocalUnreachableError(RuntimeError):
    """The LAN path to the vacuum is unavailable; nothing was sent to the robot."""


def normalize_zone(coords: list[int]) -> list[int]:
    """Validate a ``[x1, y1, x2, y2]`` rectangle (mm) and return it as ``[min_x, min_y, max_x, max_y]``."""
    if len(coords) != 4:
        raise ValueError(f"Zone must have 4 coords x1,y1,x2,y2 (got {coords!r})")
    x1, y1, x2, y2 = (int(c) for c in coords)
    if x1 == x2 or y1 == y2:
        raise ValueError(f"Zone {coords!r} has zero width or height")
    return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]


def extract_code(result: Any) -> int:
    """Normalize a Xiaomi cloud / miIO response to a single status code.

    - ``{"code": 0, "result": {"code": -4004}}`` → ``-4004``: the outer code is
      the cloud transport, the nested one is what the device itself answered.
    - ``{"result": {"code": 7}}`` → ``7``; a dict without any code → ``-1``.
    - ``[{"code": 0}, {"code": -4001}]`` (property set/get) → first non-zero.
    - ``None`` / anything else (local miIO calls return nothing) → ``0``.
    """
    if isinstance(result, dict):
        nested = result.get("result")
        nested_code = nested.get("code") if isinstance(nested, dict) else None
        if "code" in result:
            outer = _as_int(result.get("code"))
            if outer == 0 and nested_code is not None:
                return _as_int(nested_code)
            return outer
        return _as_int(nested_code) if nested_code is not None else -1
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                code = _as_int(item.get("code", 0))
                if code != 0:
                    return code
        return 0
    return 0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def start_room_clean(
    vac: Any,
    room_ids: list[int],
    *,
    repeat: int = 1,
    fan: str | None = None,
    water: str | None = None,
    poll_attempts: int = 4,
    poll_delay_seconds: float = 3.0,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Start room cleaning and try to verify that the robot actually left rest.

    Returns a structured dict with the raw command result plus:
      - ``accepted``: Xiaomi/cloud call returned code 0
      - ``verified_started``: True / False / None (inconclusive)
      - ``warning``: human-readable diagnostic when accepted != verified
      - ``transport``: ``local``, ``miot`` or ``cloud_rpc``

    On the X20+ only the ``local`` transport (Dreame start-clean over the LAN)
    actually moves the robot; the cloud room actions are acknowledged and ignored.
    ``fan`` / ``water`` are only honoured by the ``local`` transport.
    """
    sleep_fn = sleep_fn or time.sleep
    status_before = _safe_status(vac)
    before_state = _status_state(status_before)
    fallback_warning: str | None = None

    if getattr(vac, "local_clean_available", False) is True:
        try:
            result = vac.clean_rooms_local(room_ids, repeat=repeat, fan=fan, water=water)
        except LocalUnreachableError as e:
            fallback_warning = (
                f"LAN path unavailable ({e}); fell back to the cloud room action, which the X20+ may ignore."
            )
        else:
            # The service cancels mop drying first (CloudVacuumService.cancel_drying),
            # so a robot that was drying is verified like one that was docked.
            return _finish_room_clean(
                vac, room_ids, result, "local", status_before, before_state, poll_attempts, poll_delay_seconds, sleep_fn
            )

    # Prefer the official MIoT action; fall back to the legacy RPC only when the
    # service doesn't implement it. Any other error (timeout, auth, rejected
    # params) is re-raised: the first command may already have reached the
    # robot, and blindly sending a second, different command is unsafe.
    clean_rooms_miot = getattr(vac, "clean_rooms_miot", None)
    if callable(clean_rooms_miot):
        transport = "miot"
        try:
            result = clean_rooms_miot(room_ids, repeat=repeat)
        except NotImplementedError:
            transport = "cloud_rpc"
            result = vac.clean_rooms(room_ids, repeat=repeat)
    else:
        transport = "cloud_rpc"
        result = vac.clean_rooms(room_ids, repeat=repeat)

    clean_result = _finish_room_clean(
        vac, room_ids, result, transport, status_before, before_state, poll_attempts, poll_delay_seconds, sleep_fn
    )
    if fallback_warning:
        clean_result["warning"] = " ".join(w for w in (fallback_warning, clean_result["warning"]) if w)
    return clean_result


def _finish_room_clean(
    vac: Any,
    room_ids: list[int],
    result: Any,
    transport: str,
    status_before: dict[str, Any] | None,
    before_state: str,
    poll_attempts: int,
    poll_delay_seconds: float,
    sleep_fn: Callable[[float], None],
) -> dict[str, Any]:
    code = extract_code(result)
    accepted = code == 0
    verified_started: bool | None = None
    status_after: dict[str, Any] | None = None
    warning: str | None = None

    if accepted:
        if _state_is_busy(before_state):
            warning = (
                "Room-clean command was accepted, but the vacuum was already busy, "
                "so Xiaomi cloud could not confirm that it switched to the requested rooms."
            )
        else:
            verified_started, status_after = _verify_room_clean_started(
                vac,
                poll_attempts=poll_attempts,
                poll_delay_seconds=poll_delay_seconds,
                sleep_fn=sleep_fn,
            )
            if verified_started is False:
                warning = (
                    "Room-clean command was accepted (code=0), but the vacuum still looked idle/charging "
                    "after verification. X20+ room actions can no-op even when Xiaomi accepts them; "
                    "verify room IDs or fall back to `xiao start`."
                )
            elif verified_started is None:
                warning = (
                    "Room-clean command was accepted, but xiao could not verify movement from the current status yet."
                )

    return {
        "accepted": accepted,
        "code": code,
        "result": result,
        "rooms": room_ids,
        "transport": transport,
        "status_before": status_before,
        "status_after": status_after,
        "verified_started": verified_started,
        "warning": warning,
    }


def _verify_room_clean_started(
    vac: Any,
    *,
    poll_attempts: int,
    poll_delay_seconds: float,
    sleep_fn: Callable[[float], None],
) -> tuple[bool | None, dict[str, Any] | None]:
    saw_status = False
    last_state = ""
    latest_status: dict[str, Any] | None = None

    for attempt in range(max(1, poll_attempts)):
        if attempt > 0 and poll_delay_seconds > 0:
            sleep_fn(poll_delay_seconds)
        latest_status = _safe_status(vac)
        if latest_status is None:
            continue
        saw_status = True
        state = _status_state(latest_status)
        if not state:
            continue
        last_state = state
        if _state_shows_room_clean_progress(state):
            return True, latest_status

    # Only a robot that is still visibly at rest counts as "did not start";
    # an unknown/unrecognised final state is inconclusive.
    if saw_status and last_state in ROOM_CLEAN_IDLE_STATES:
        return False, latest_status
    return None, latest_status


def _safe_status(vac: Any) -> dict[str, Any] | None:
    try:
        status = vac.status()
    except Exception:
        return None
    if isinstance(status, dict):
        return status
    return None


def _status_state(status: dict[str, Any] | None) -> str:
    if not status:
        return ""
    state = status.get("state")
    return state.strip() if isinstance(state, str) else ""


def _state_is_busy(state: str) -> bool:
    return bool(state) and state not in ROOM_CLEAN_IDLE_STATES


def _state_shows_room_clean_progress(state: str) -> bool:
    # Only known working states count as proof of movement. An unrecognised
    # state (e.g. "Unknown(17)") must not be reported as a verified start.
    return state in ROOM_CLEAN_IN_PROGRESS_STATES


def known_rooms(vac: Any | None, aliases: dict[str, str]) -> list[dict[str, Any]]:
    """Collect the room IDs this vacuum actually knows about.

    Sources, merged: the device room mapping (when the model exposes one),
    room IDs referenced by the device's own schedules, and the user's aliases.
    Room IDs are per-map, so nothing here is hard-coded.

    Returns ``[{"id": int, "name": str, "sources": [...]}, ...]`` sorted by id.
    """
    rooms: dict[int, dict[str, Any]] = {}

    def add(rid: Any, source: str, name: str | None = None) -> None:
        try:
            room_id = int(rid)
        except (TypeError, ValueError):
            return
        entry = rooms.setdefault(room_id, {"id": room_id, "name": None, "sources": []})
        if source not in entry["sources"]:
            entry["sources"].append(source)
        if name and not entry["name"]:
            entry["name"] = str(name)

    if vac is not None:
        try:
            for room in vac.rooms() or []:
                if isinstance(room, (list, tuple)) and room:
                    add(room[0], "device", room[1] if len(room) > 1 else None)
                elif isinstance(room, dict):
                    add(room.get("id"), "device", room.get("name"))
                else:
                    add(room, "device")
        except Exception:
            pass
        try:
            for sched in vac.schedules_parsed() or []:
                for rid in sched.get("room_ids", []) if isinstance(sched, dict) else []:
                    add(rid, "schedule")
        except Exception:
            pass

    for rid in aliases:
        add(rid, "alias")

    result = []
    for room_id in sorted(rooms):
        entry = rooms[room_id]
        entry["name"] = aliases.get(str(room_id)) or entry["name"] or f"Room {room_id}"
        result.append(entry)
    return result
