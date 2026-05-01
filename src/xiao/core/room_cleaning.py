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
    "Charging",
    "Charging Completed",
    "Go Charging",
    "Paused",
    "Error",
}


def extract_code(result: Any) -> int:
    if isinstance(result, dict):
        return result.get("code", result.get("result", {}).get("code", -1))
    return 0


def start_room_clean(
    vac: Any,
    room_ids: list[int],
    *,
    repeat: int = 1,
    poll_attempts: int = 3,
    poll_delay_seconds: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Start room cleaning and try to verify that the robot actually left rest.

    Returns a structured dict with the raw command result plus:
      - ``accepted``: Xiaomi/cloud call returned code 0
      - ``verified_started``: True / False / None (inconclusive)
      - ``warning``: human-readable diagnostic when accepted != verified
      - ``transport``: ``miot`` or ``cloud_rpc``
    """
    status_before = _safe_status(vac)
    before_state = _status_state(status_before)

    transport = "miot"
    try:
        result = vac.clean_rooms_miot(room_ids)
    except (AttributeError, Exception):
        transport = "cloud_rpc"
        result = vac.clean_rooms(room_ids, repeat=repeat)

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
        if _state_shows_room_clean_progress(state):
            return True, latest_status

    if not saw_status:
        return None, latest_status
    return False, latest_status


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
    return bool(state) and (state in ROOM_CLEAN_IN_PROGRESS_STATES or state not in ROOM_CLEAN_IDLE_STATES)
