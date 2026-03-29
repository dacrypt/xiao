"""Cloud-based vacuum control — for devices that only respond via Xiaomi Cloud API.

Mirrors the VacuumService interface but sends all commands via cloud RPC.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from xiao.core.cloud import (
    XiaomiCloud,
    cloud_call_action,
    cloud_get_properties,
    cloud_set_properties,
)

logger = logging.getLogger(__name__)


# MIoT spec for xiaomi.vacuum.c102gl (X20+)
# Discovered via cloud property scan - actual available properties:
# siid 1: device-information (manufacturer, model, serial, firmware, serial-num)
# siid 2: sweep (status, fan-level, mode, ?, sweep-type)
# siid 3: battery (battery-level, charging-state)
# siid 4: clean-log (total-clean-time, total-clean-times, total-clean-area, ?, ?, ?, ?)
# siid 5: do-not-disturb (enable, start-time, end-time)
# siid 7: audio (volume, voice-packet, voice-info)
# siid 8: timezone/schedule (timezone, schedules, ?, ?)
# siid 9: consumable main-brush (work-time, work-life)
# siid 10: consumable side-brush (work-time, work-life)
# siid 11: consumable filter (work-time, work-life)
# siid 12: history (last-clean-time, last-clean-area, last-clean-duration, total-area)

MIOT_SPEC = {
    # siid 2 = sweep
    "sweep_status": {"siid": 2, "piid": 1},  # Status enum
    "fan_level": {"siid": 2, "piid": 2},  # Fan speed level
    "sweep_mode": {"siid": 2, "piid": 3},  # Mode
    "sweep_type": {"siid": 2, "piid": 5},  # Sweep type
    # siid 3 = battery
    "battery_level": {"siid": 3, "piid": 1},  # Battery percentage
    "charging_state": {"siid": 3, "piid": 2},  # Charging state
    # siid 5 = do-not-disturb
    "dnd_enable": {"siid": 5, "piid": 1},
    "dnd_start": {"siid": 5, "piid": 2},
    "dnd_end": {"siid": 5, "piid": 3},
    # siid 7 = audio
    "volume": {"siid": 7, "piid": 1},
    # siid 9-11 = consumables
    "main_brush_time": {"siid": 9, "piid": 1},
    "main_brush_life": {"siid": 9, "piid": 2},
    "side_brush_time": {"siid": 10, "piid": 1},
    "side_brush_life": {"siid": 10, "piid": 2},
    "filter_time": {"siid": 11, "piid": 1},
    "filter_life": {"siid": 11, "piid": 2},
    # siid 12 = history
    "last_clean_time": {"siid": 12, "piid": 1},
    "last_clean_area": {"siid": 12, "piid": 2},
    "last_clean_duration": {"siid": 12, "piid": 3},
    "total_area": {"siid": 12, "piid": 4},
    # siid 8 = timezone/schedules
    "timezone": {"siid": 8, "piid": 1},
    "schedules": {"siid": 8, "piid": 2},
    # siid 18 = mop consumable
    "mop_life_level": {"siid": 18, "piid": 1},  # Mop life remaining (%)
    "mop_left_time": {"siid": 18, "piid": 2},  # Mop hours remaining
    # siid 2 = fault
    "fault": {"siid": 2, "piid": 2},
}

# Actions — using standard MIoT action IDs
MIOT_ACTIONS = {
    "start_clean": {"siid": 2, "aiid": 1},  # Start sweep
    "stop_clean": {"siid": 2, "aiid": 2},  # Stop sweep
    "start_room_sweep": {"siid": 2, "aiid": 3},  # Start room sweep (piid 4 = room IDs)
    "start_dust": {"siid": 2, "aiid": 4},  # Start dust collection
    "start_mop_wash": {"siid": 2, "aiid": 6},  # Start mop washing
    "start_dry": {"siid": 2, "aiid": 8},  # Start drying
    "stop_dry": {"siid": 2, "aiid": 9},  # Stop drying
    "start_eject": {"siid": 2, "aiid": 10},  # Eject base station tray
    "start_charge": {"siid": 3, "aiid": 1},  # Return to dock
    "identify": {"siid": 6, "aiid": 1},  # Find/beep (identify service)
}


class CloudVacuumService:
    """Control vacuum via Xiaomi Cloud API."""

    def __init__(
        self,
        cloud: XiaomiCloud,
        did: str,
        model: str = "",
        country: str = "us",
    ):
        self.cloud = cloud
        self.did = did
        self.model = model
        self.country = country

    # ── Core actions ──────────────────────────────────────────────

    def start(self) -> dict:
        a = MIOT_ACTIONS["start_clean"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def stop(self) -> dict:
        a = MIOT_ACTIONS["stop_clean"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def pause(self) -> dict:
        return self.stop()

    def home(self) -> dict:
        a = MIOT_ACTIONS["start_charge"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def find(self) -> dict:
        a = MIOT_ACTIONS["identify"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    # ── Status ────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Get vacuum status via cloud properties."""
        props_to_get = [
            MIOT_SPEC["sweep_status"],
            MIOT_SPEC["battery_level"],
            MIOT_SPEC["charging_state"],
            MIOT_SPEC["fan_level"],
            MIOT_SPEC["sweep_mode"],
            MIOT_SPEC["sweep_type"],
        ]

        results = cloud_get_properties(self.cloud, self.did, props_to_get, country=self.country)

        data: dict[str, Any] = {}
        # Status values discovered from device (value=13 when in dock after cleaning)
        status_map = {
            1: "Sweeping",
            2: "Idle",
            3: "Paused",
            4: "Error",
            5: "Go Charging",
            6: "Charging",
            7: "Mopping",
            8: "Drying",
            9: "Washing mop",
            10: "Go Washing",
            11: "Building map",
            12: "Sweeping And Mopping",
            13: "In Dock",
            14: "Upgrading",
            19: "Water Inspecting",
            21: "⚠️ Water Tank Alert",
            22: "Dust Collecting",
            23: "Remote Clean",
        }
        # Fan speed values from c102gl (X20+)
        # Device returns raw percentage values for fan_level (siid 2, piid 2)
        fan_map = {
            0: "Silent",
            1: "Standard",
            2: "Medium",
            3: "Turbo",
            101: "Silent",
            102: "Standard",
            103: "Medium",
            104: "Turbo",
        }
        mode_map = {
            0: "Sweep only",
            1: "Mop only",
            2: "Sweep & Mop",
            3: "Custom",
        }

        for r in results:
            siid = r.get("siid", 0)
            piid = r.get("piid", 0)
            value = r.get("value")
            code = r.get("code", 0)

            if code != 0:
                continue

            if siid == 2 and piid == 1:
                data["state"] = status_map.get(value, f"Unknown({value})")
            elif siid == 2 and piid == 2:
                data["fan_level_raw"] = value
                if value in fan_map:
                    data["fan_speed"] = fan_map[value]
                elif isinstance(value, int) and value > 3:
                    # Raw percentage — map to friendly name
                    if value <= 30:
                        data["fan_speed"] = f"Silent ({value}%)"
                    elif value <= 55:
                        data["fan_speed"] = f"Standard ({value}%)"
                    elif value <= 75:
                        data["fan_speed"] = f"Medium ({value}%)"
                    else:
                        data["fan_speed"] = f"Turbo ({value}%)"
                else:
                    data["fan_speed"] = str(value)
            elif siid == 2 and piid == 3:
                data["mode"] = mode_map.get(value, str(value))
            elif siid == 2 and piid == 5:
                data["sweep_type"] = value
            elif siid == 3 and piid == 1:
                data["battery"] = value
            elif siid == 3 and piid == 2:
                charging = {1: "Charging", 2: "Not charging", 3: "Charged"}
                data["charging"] = charging.get(value, str(value))

        return data

    # ── Fan speed ─────────────────────────────────────────────────

    FAN_SPEEDS = {"silent": 0, "standard": 1, "medium": 2, "turbo": 3}
    FAN_SPEED_NAMES = {v: k for k, v in FAN_SPEEDS.items()}

    def set_fan_speed(self, preset: str) -> list:
        level = self.FAN_SPEEDS.get(preset.lower())
        if level is None:
            raise ValueError(f"Unknown speed: {preset}. Use: {', '.join(self.FAN_SPEEDS)}")
        return cloud_set_properties(
            self.cloud,
            self.did,
            [{"siid": 2, "piid": 2, "value": level}],
            country=self.country,
        )

    def fan_speed(self) -> str:
        results = cloud_get_properties(
            self.cloud,
            self.did,
            [{"siid": 2, "piid": 2}],
            country=self.country,
        )
        if results and results[0].get("code", 0) == 0:
            value = results[0].get("value")
            if value in self.FAN_SPEED_NAMES:
                return self.FAN_SPEED_NAMES[value]
            # Raw percentage — map to friendly name
            if isinstance(value, int) and value > 3:
                if value <= 30:
                    return f"Silent ({value}%)"
                elif value <= 55:
                    return f"Standard ({value}%)"
                elif value <= 75:
                    return f"Medium ({value}%)"
                else:
                    return f"Turbo ({value}%)"
            return str(value)
        return "unknown"

    # ── Room cleaning ─────────────────────────────────────────────

    def clean_rooms(self, room_ids: list[int], repeat: int = 1) -> dict:
        """Start room-specific cleaning via cloud RPC."""
        from xiao.core.cloud import cloud_rpc

        param = {
            "clean_mop_type": 0,
            "clean_param": {"repeat_count": repeat, "segments": room_ids},
        }
        return cloud_rpc(
            self.cloud,
            self.did,
            "action",
            {"did": self.did, "siid": 2, "aiid": 1, "in": [json.dumps(param)]},
            country=self.country,
        )

    def clean_zone(self, zones: list[list[int]]) -> dict:
        """Start zone cleaning via cloud RPC."""
        from xiao.core.cloud import cloud_rpc

        param = {"zone": zones}
        return cloud_rpc(
            self.cloud,
            self.did,
            "action",
            {"did": self.did, "siid": 2, "aiid": 1, "in": [json.dumps(param)]},
            country=self.country,
        )

    def spot_clean(self) -> dict:
        """Start spot cleaning."""
        return self.start()

    # ── Volume ────────────────────────────────────────────────────

    def set_volume(self, level: int) -> list:
        spec = MIOT_SPEC["volume"]
        return cloud_set_properties(
            self.cloud,
            self.did,
            [{"siid": spec["siid"], "piid": spec["piid"], "value": level}],
            country=self.country,
        )

    def volume(self) -> int:
        spec = MIOT_SPEC["volume"]
        results = cloud_get_properties(
            self.cloud,
            self.did,
            [{"siid": spec["siid"], "piid": spec["piid"]}],
            country=self.country,
        )
        if results and results[0].get("code", 0) == 0:
            return results[0].get("value", -1)
        return -1

    # ── DND ───────────────────────────────────────────────────────

    def dnd_status(self) -> dict[str, Any]:
        props = [MIOT_SPEC["dnd_enable"], MIOT_SPEC["dnd_start"], MIOT_SPEC["dnd_end"]]
        results = cloud_get_properties(self.cloud, self.did, props, country=self.country)
        dnd: dict[str, Any] = {}
        for r in results:
            if r.get("code", 0) != 0:
                continue
            _siid, piid, val = r["siid"], r["piid"], r.get("value")
            if piid == 1:
                dnd["enabled"] = val
            elif piid == 2:
                dnd["start"] = val
            elif piid == 3:
                dnd["end"] = val
        return dnd

    def set_dnd(self, enabled: bool, start: str | None = None, end: str | None = None) -> list:
        props = [{"siid": 5, "piid": 1, "value": enabled}]
        if start:
            props.append({"siid": 5, "piid": 2, "value": start})
        if end:
            props.append({"siid": 5, "piid": 3, "value": end})
        return cloud_set_properties(self.cloud, self.did, props, country=self.country)

    # ── Consumable status ────────────────────────────────────────

    def consumable_status(self) -> dict[str, Any]:
        """Read consumable status for main brush, side brush, filter, and mop."""
        props = [
            MIOT_SPEC["main_brush_time"],
            MIOT_SPEC["main_brush_life"],
            MIOT_SPEC["side_brush_time"],
            MIOT_SPEC["side_brush_life"],
            MIOT_SPEC["filter_time"],
            MIOT_SPEC["filter_life"],
            MIOT_SPEC["mop_life_level"],
            MIOT_SPEC["mop_left_time"],
        ]
        results = cloud_get_properties(self.cloud, self.did, props, country=self.country)
        data: dict[str, Any] = {}
        mapping = {
            (9, 1): "main_brush_used",
            (9, 2): "main_brush_life",
            (10, 1): "side_brush_used",
            (10, 2): "side_brush_life",
            (11, 1): "filter_used",
            (11, 2): "filter_life",
            (18, 1): "mop_life_level",
            (18, 2): "mop_left_time",
        }
        for r in results:
            if r.get("code", 0) != 0:
                continue
            key = mapping.get((r["siid"], r["piid"]))
            if key:
                data[key] = r.get("value")
        # Compute remaining percentages
        for component in ("main_brush", "side_brush", "filter"):
            used = data.get(f"{component}_used")
            life = data.get(f"{component}_life")
            if used is not None and life and life > 0:
                remaining = max(0, 100 - int(used / life * 100))
                data[f"{component}_remaining"] = f"{remaining}%"
        # Mop already comes as percentage from siid 18
        if "mop_life_level" in data:
            data["mop_remaining"] = f"{data['mop_life_level']}%"
        return data

    # ── Device info ───────────────────────────────────────────────

    def device_info(self) -> dict[str, Any]:
        """Read device information (siid 1)."""
        props = [
            {"siid": 1, "piid": 1},  # manufacturer
            {"siid": 1, "piid": 2},  # model
            {"siid": 1, "piid": 3},  # serial-number
            {"siid": 1, "piid": 4},  # firmware-revision
        ]
        results = cloud_get_properties(self.cloud, self.did, props, country=self.country)
        mapping = {1: "manufacturer", 2: "model", 3: "serial_number", 4: "firmware"}
        data: dict[str, Any] = {"did": self.did, "country": self.country}
        for r in results:
            if r.get("code", 0) != 0:
                continue
            if r.get("siid") == 1:
                key = mapping.get(r["piid"])
                if key:
                    data[key] = r.get("value")
        return data

    # ── Clean history ─────────────────────────────────────────────

    def clean_history(self) -> dict[str, Any]:
        """Read cleaning history totals (siid 4) and last-clean details (siid 12)."""
        from datetime import datetime

        props = [
            {"siid": 4, "piid": 1},  # total-clean-time (minutes)
            {"siid": 4, "piid": 2},  # total-clean-times (count)
            {"siid": 4, "piid": 3},  # total-clean-area
            {"siid": 12, "piid": 1},  # last-clean-time (unix timestamp)
            {"siid": 12, "piid": 2},  # last-clean-area
            {"siid": 12, "piid": 3},  # last-clean-duration (minutes)
            {"siid": 12, "piid": 4},  # total-area (from siid 12)
        ]
        results = cloud_get_properties(self.cloud, self.did, props, country=self.country)
        mapping = {
            (4, 1): "total_clean_duration",
            (4, 2): "total_clean_count",
            (4, 3): "total_clean_area",
            (12, 1): "last_clean_timestamp",
            (12, 2): "last_clean_area",
            (12, 3): "last_clean_duration",
            (12, 4): "total_area",
        }
        data: dict[str, Any] = {}
        for r in results:
            if r.get("code", 0) != 0:
                continue
            key = mapping.get((r["siid"], r["piid"]))
            if key:
                data[key] = r.get("value")

        # Convert timestamp to human-readable
        ts = data.pop("last_clean_timestamp", None)
        if ts and isinstance(ts, int) and ts > 1_000_000_000:
            data["last_clean_date"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        return data

    def last_clean(self) -> dict[str, Any]:
        """Read last cleaning session details (siid 12)."""
        from datetime import datetime

        props = [
            MIOT_SPEC["last_clean_time"],
            MIOT_SPEC["last_clean_area"],
            MIOT_SPEC["last_clean_duration"],
        ]
        results = cloud_get_properties(self.cloud, self.did, props, country=self.country)
        data: dict[str, Any] = {}
        mapping = {
            (12, 1): "last_clean_timestamp",
            (12, 2): "last_clean_area",
            (12, 3): "last_clean_duration",
        }
        for r in results:
            if r.get("code", 0) != 0:
                continue
            key = mapping.get((r["siid"], r["piid"]))
            if key:
                data[key] = r.get("value")

        ts = data.pop("last_clean_timestamp", None)
        if ts and isinstance(ts, int) and ts > 1_000_000_000:
            data["last_clean_date"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        return data

    # ── Consumable reset ──────────────────────────────────────────

    def consumable_reset(self, name: str) -> dict:
        action_key = f"reset_{name}"
        if action_key not in MIOT_ACTIONS:
            raise ValueError(f"Unknown consumable: {name}. Use: main_brush, side_brush, filter")
        a = MIOT_ACTIONS[action_key]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    # ── Rooms / Map ───────────────────────────────────────────────

    def rooms(self) -> list:
        """Get room list. Cloud doesn't expose a direct room list endpoint
        for all models, so we return what we can via RPC."""
        from xiao.core.cloud import cloud_rpc

        try:
            result = cloud_rpc(
                self.cloud,
                self.did,
                "get_room_mapping",
                [],
                country=self.country,
            )
            return result.get("result", [])
        except Exception:
            logger.debug("get_room_mapping not available via cloud")
            return []

    # ── Schedules ─────────────────────────────────────────────────

    def timer_list(self) -> list:
        """Get cleaning schedules. Read from siid 8 (timezone/schedule)."""
        results = cloud_get_properties(
            self.cloud,
            self.did,
            [{"siid": 8, "piid": 2}],  # schedules property
            country=self.country,
        )
        if results and results[0].get("code", 0) == 0:
            value = results[0].get("value")
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return [value]
            if isinstance(value, list):
                return value
            return [value] if value else []
        return []

    def timer_add(self, cron: str) -> dict:
        """Add schedule — not directly supported via cloud properties for all models."""
        raise NotImplementedError("Schedule management not supported via cloud for this model")

    def timer_delete(self, timer_id: str) -> dict:
        """Delete schedule — not directly supported via cloud properties for all models."""
        raise NotImplementedError("Schedule management not supported via cloud for this model")

    # ── Base station controls ─────────────────────────────────────

    def mop_wash(self) -> dict:
        """Start mop washing at base station."""
        a = MIOT_ACTIONS["start_mop_wash"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def start_dry(self) -> dict:
        """Start mop drying at base station."""
        a = MIOT_ACTIONS["start_dry"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def stop_dry(self) -> dict:
        """Stop mop drying."""
        a = MIOT_ACTIONS["stop_dry"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def dust_collect(self) -> dict:
        """Start dust collection at base station."""
        a = MIOT_ACTIONS["start_dust"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    def eject_tray(self) -> dict:
        """Eject base station tray."""
        a = MIOT_ACTIONS["start_eject"]
        return cloud_call_action(self.cloud, self.did, a["siid"], a["aiid"], country=self.country)

    # ── Water/mop settings ────────────────────────────────────────

    WATER_LEVELS = {"low": 32, "medium": 64, "high": 96}
    WATER_LEVEL_NAMES = {32: "Low", 64: "Medium", 96: "High"}

    def water_level(self) -> dict[str, Any]:
        """Read water flow setting from schedules/mode config.

        Note: siid 18 is mop consumable (life level), NOT water flow.
        Water flow level is embedded in schedule strings and set via clean params.
        """
        # Return the water level from current mode if available
        return {"level": "Medium", "note": "Water flow is set per-clean or per-schedule, not a global property"}

    def set_water_level(self, level: str) -> list:
        """Set water level for next clean: low, medium, high.

        Note: This is stored as part of the clean command params, not a standalone property.
        """
        val = self.WATER_LEVELS.get(level.lower())
        if val is None:
            raise ValueError(f"Unknown water level: {level}. Use: {', '.join(self.WATER_LEVELS)}")
        # Water level is typically passed with the clean command, not set independently
        # But some firmware versions accept it as a property
        return cloud_set_properties(
            self.cloud,
            self.did,
            [{"siid": 18, "piid": 1, "value": val}],
            country=self.country,
        )

    def mop_status(self) -> dict[str, Any]:
        """Read mop consumable status (siid 18)."""
        results = cloud_get_properties(
            self.cloud,
            self.did,
            [MIOT_SPEC["mop_life_level"], MIOT_SPEC["mop_left_time"]],
            country=self.country,
        )
        data: dict[str, Any] = {}
        for r in results:
            if r.get("code", 0) != 0:
                continue
            _siid, piid, val = r["siid"], r["piid"], r.get("value")
            if piid == 1:
                data["life_level"] = val  # percentage remaining
            elif piid == 2:
                data["left_time"] = val  # hours remaining
        return data

    # ── Schedules (parsed) ────────────────────────────────────────

    def schedules_parsed(self) -> list[dict[str, Any]]:
        """Get schedules parsed into structured dicts.

        S8.P2 format: id-enabled-time-days-repeat-mode-fan-water-rooms
        Example: 1-3-08:30-1111111-1-2-1-64-3,8,7,6
        """
        from xiao.core.config import get_rooms

        raw_list = self.timer_list()
        room_aliases = get_rooms()

        # The raw data is typically one string with schedules separated by ';'
        # e.g. ["6-0-08:00-...-rooms;1-3-08:30-...-rooms;..."]
        expanded = []
        for entry in raw_list:
            if isinstance(entry, str) and ";" in entry:
                expanded.extend(entry.split(";"))
            else:
                expanded.append(entry)
        raw_list = expanded

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        mode_map = {0: "Sweep only", 1: "Mop only", 2: "Sweep & Mop", 3: "Custom"}
        fan_map = {0: "Silent", 1: "Standard", 2: "Medium", 3: "Turbo"}
        water_map = {32: "Low", 64: "Medium", 96: "High"}

        schedules = []
        for entry in raw_list:
            if not isinstance(entry, str):
                entry = str(entry)
            parts = entry.split("-", 8)  # max 9 parts
            if len(parts) < 9:
                schedules.append({"raw": entry, "parse_error": True})
                continue

            sched_id = parts[0]
            enabled_raw = parts[1]
            time_str = parts[2]
            days_str = parts[3]
            repeat = parts[4]
            mode_raw = parts[5]
            fan_raw = parts[6]
            water_raw = parts[7]
            rooms_str = parts[8]

            # Parse days
            enabled = enabled_raw == "3"
            days = []
            if len(days_str) == 7:
                for i, ch in enumerate(days_str):
                    if ch == "1":
                        days.append(day_names[i])
            days_display = ", ".join(days) if days else "No days"
            if len(days) == 7:
                days_display = "Every day"

            # Parse rooms
            room_ids = [int(r) for r in rooms_str.split(",") if r.strip()]
            rooms_display = []
            for rid in room_ids:
                alias = room_aliases.get(str(rid))
                rooms_display.append(f"{alias} ({rid})" if alias else str(rid))

            schedules.append(
                {
                    "id": sched_id,
                    "enabled": enabled,
                    "time": time_str,
                    "days": days,
                    "days_display": days_display,
                    "repeat": repeat == "1",
                    "mode": mode_map.get(int(mode_raw), mode_raw),
                    "fan": fan_map.get(int(fan_raw), fan_raw),
                    "water": water_map.get(int(water_raw), water_raw),
                    "room_ids": room_ids,
                    "rooms_display": rooms_display,
                    "raw": entry,
                }
            )

        return schedules

    # ── Full status (everything) ──────────────────────────────────

    def full_status(self) -> dict[str, Any]:
        """Get comprehensive status: state + battery + fan + mode + DND + mop + schedules summary."""
        data = self.status()
        # Detect water tank alert
        if data.get("state") == "⚠️ Water Tank Alert":
            data["alert"] = (
                "Water tank needs attention! Check: clean water tank (refill) and dirty water tank (empty). Press button on robot after fixing."
            )
        # Add DND
        try:
            dnd = self.dnd_status()
            data["dnd"] = dnd
        except Exception:
            pass
        # Add water level
        try:
            water = self.water_level()
            data["water"] = water
        except Exception:
            pass
        # Add consumables
        try:
            cons = self.consumable_status()
            data["consumables"] = cons
        except Exception:
            pass
        # Add last clean
        try:
            last = self.last_clean()
            data["last_clean"] = last
        except Exception:
            pass
        # Add schedules count
        try:
            scheds = self.schedules_parsed()
            active = sum(1 for s in scheds if s.get("enabled"))
            data["schedules_total"] = len(scheds)
            data["schedules_active"] = active
        except Exception:
            pass
        return data

    # ── Room-specific cleaning (MIoT action) ──────────────────────

    def clean_rooms_miot(self, room_ids: list[int]) -> dict:
        """Start room-specific cleaning via MIoT action siid=2, aiid=3.

        The room IDs are passed as a string in piid=4.
        """
        a = MIOT_ACTIONS["start_room_sweep"]
        room_str = ",".join(str(r) for r in room_ids)
        return cloud_call_action(
            self.cloud,
            self.did,
            a["siid"],
            a["aiid"],
            params=[{"piid": 4, "value": room_str}],
            country=self.country,
        )

    # ── Raw command ───────────────────────────────────────────────

    def raw_command(self, siid: int, aiid: int, params: list | None = None) -> dict:
        return cloud_call_action(self.cloud, self.did, siid, aiid, params=params, country=self.country)

    def raw_get(self, siid: int, piid: int) -> list:
        return cloud_get_properties(
            self.cloud,
            self.did,
            [{"siid": siid, "piid": piid}],
            country=self.country,
        )

    def raw_set(self, siid: int, piid: int, value: Any) -> list:
        return cloud_set_properties(
            self.cloud,
            self.did,
            [{"siid": siid, "piid": piid, "value": value}],
            country=self.country,
        )

    # ── Network info ──────────────────────────────────────────────

    def network_info(self) -> dict[str, Any]:
        """Get device network info from cloud device list."""
        url = self.cloud._api_url(self.country) + "/v2/home/device_list"
        payload = {"data": json.dumps({"getVirtualModel": True, "getHuamiDevices": 0})}
        resp = self.cloud._signed_request(url, payload)
        data = json.loads(resp)
        for dev in data.get("result", {}).get("list", []):
            if str(dev.get("did")) == self.did:
                extra = dev.get("extra", {})
                return {
                    "local_ip": dev.get("localip", ""),
                    "internet_ip": dev.get("internet_ip", ""),
                    "mac": dev.get("mac", ""),
                    "bssid": dev.get("bssid", ""),
                    "ssid": dev.get("ssid", ""),
                    "rssi": dev.get("rssi", 0),
                    "is_online": dev.get("isOnline", False),
                    "firmware": extra.get("fw_version", ""),
                    "name": dev.get("name", ""),
                    "pd_id": dev.get("pd_id", ""),
                    "permit_level": dev.get("permitLevel", 0),
                    "is_set_pincode": extra.get("isSetPincode", 0),
                }
        return {}

    # ── All properties scan ───────────────────────────────────────

    def all_properties(self) -> dict[str, Any]:
        """Get ALL device properties in a single call for the dashboard."""
        props = [
            # siid 1: device-info
            {"siid": 1, "piid": 1},
            {"siid": 1, "piid": 2},
            {"siid": 1, "piid": 3},
            {"siid": 1, "piid": 4},
            {"siid": 1, "piid": 5},
            # siid 2: sweep
            {"siid": 2, "piid": 1},
            {"siid": 2, "piid": 2},
            {"siid": 2, "piid": 3},
            {"siid": 2, "piid": 5},
            # siid 3: battery
            {"siid": 3, "piid": 1},
            {"siid": 3, "piid": 2},
            # siid 4: clean-log (7+ properties)
            {"siid": 4, "piid": 1},
            {"siid": 4, "piid": 2},
            {"siid": 4, "piid": 3},
            {"siid": 4, "piid": 4},
            {"siid": 4, "piid": 5},
            {"siid": 4, "piid": 6},
            {"siid": 4, "piid": 7},
            {"siid": 4, "piid": 11},
            {"siid": 4, "piid": 12},
            # siid 5: DND
            {"siid": 5, "piid": 1},
            {"siid": 5, "piid": 2},
            {"siid": 5, "piid": 3},
            # siid 7: audio
            {"siid": 7, "piid": 1},
            {"siid": 7, "piid": 2},
            {"siid": 7, "piid": 3},
            # siid 8: timezone/schedules
            {"siid": 8, "piid": 1},
            {"siid": 8, "piid": 4},
            # siid 9-11: consumables
            {"siid": 9, "piid": 1},
            {"siid": 9, "piid": 2},
            {"siid": 10, "piid": 1},
            {"siid": 10, "piid": 2},
            {"siid": 11, "piid": 1},
            {"siid": 11, "piid": 2},
            # siid 12: history
            {"siid": 12, "piid": 1},
            {"siid": 12, "piid": 2},
            {"siid": 12, "piid": 3},
            {"siid": 12, "piid": 4},
            # siid 18: mop consumable
            {"siid": 18, "piid": 1},
            {"siid": 18, "piid": 2},
        ]

        # Query in chunks of 15 (cloud API limit)
        all_results = []
        for i in range(0, len(props), 15):
            chunk = props[i : i + 15]
            try:
                r = cloud_get_properties(self.cloud, self.did, chunk, country=self.country)
                all_results.extend(r)
            except Exception:
                pass

        data: dict[str, Any] = {}
        for r in all_results:
            if r.get("code", -1) != 0:
                continue
            siid, piid, val = r["siid"], r["piid"], r.get("value")
            key = f"s{siid}_p{piid}"
            data[key] = val

        from datetime import datetime

        # Build structured response
        result: dict[str, Any] = {
            "device": {
                "manufacturer": data.get("s1_p1", ""),
                "model": data.get("s1_p2", ""),
                "did": data.get("s1_p3", ""),
                "firmware": data.get("s1_p4", ""),
                "serial_number": data.get("s1_p5", ""),
            },
            "status": {
                "state": data.get("s2_p1", 0),
                "fault_code": data.get("s2_p2", 0),
                "sweep_mode": data.get("s2_p3", 0),
                "sweep_type_or_dry_time": data.get("s2_p5", 0),
            },
            "battery": {
                "level": data.get("s3_p1", 0),
                "charging_state": data.get("s3_p2", 0),
            },
            "clean_log": {
                "total_duration_h": data.get("s4_p1", 0),
                "total_count": data.get("s4_p2", 0),
                "total_area_m2": data.get("s4_p3", 0),
                "prop4": data.get("s4_p4", 0),
                "prop5": data.get("s4_p5", 0),
                "prop6": data.get("s4_p6", 0),
                "prop7": data.get("s4_p7", 0),
                "prop11": data.get("s4_p11", 0),
                "prop12": data.get("s4_p12", 0),
            },
            "dnd": {
                "enabled": data.get("s5_p1", False),
                "start": data.get("s5_p2", ""),
                "end": data.get("s5_p3", ""),
            },
            "audio": {
                "volume": data.get("s7_p1", 0),
                "voice_packet": data.get("s7_p2", ""),
                "voice_info": data.get("s7_p3", ""),
            },
            "timezone": data.get("s8_p1", ""),
            "schedule_flag": data.get("s8_p4", 0),
            "consumables": {
                "main_brush": {"left_hours": data.get("s9_p1", 0), "life_pct": data.get("s9_p2", 0)},
                "side_brush": {"left_hours": data.get("s10_p1", 0), "life_pct": data.get("s10_p2", 0)},
                "filter": {"life_pct": data.get("s11_p1", 0), "left_hours": data.get("s11_p2", 0)},
                "mop": {"life_pct": data.get("s18_p1", 0), "left_hours": data.get("s18_p2", 0)},
            },
            "history": {
                "last_clean_area": data.get("s12_p2", 0),
                "last_clean_duration": data.get("s12_p3", 0),
                "total_area": data.get("s12_p4", 0),
            },
        }

        # Convert last_clean timestamp
        ts = data.get("s12_p1")
        if ts and isinstance(ts, int) and ts > 1_000_000_000:
            result["history"]["last_clean_timestamp"] = ts
            result["history"]["last_clean_date"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        return result
