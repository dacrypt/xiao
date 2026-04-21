"""Vacuum service — unified interface over python-miio."""

from __future__ import annotations

from typing import Any


class VacuumService:
    """Abstraction over python-miio GenericMiot / RoborockVacuum."""

    def __init__(self, ip: str, token: str, model: str, protocol: str = "genericmiot"):
        self._protocol = protocol
        self._ip = ip
        self._token = token
        self._model = model
        self._device: Any = None

    def _get_device(self):
        if self._device is not None:
            return self._device
        if self._protocol == "genericmiot":
            from miio import MiotDevice as GenericMiot

            self._device = GenericMiot(self._ip, self._token, model=self._model)
        else:
            try:
                from miio.integrations.roborock.vacuum import RoborockVacuum
            except ImportError:
                from miio import RoborockVacuum

            self._device = RoborockVacuum(self._ip, self._token)
        return self._device

    # ── Core actions ──────────────────────────────────────────────

    def start(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.call_action("vacuum-extend-start-clean")
        else:
            dev.start()

    def stop(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.call_action("vacuum-extend-stop-clean")
        else:
            dev.stop()

    def pause(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            # Try pause, fall back to stop
            try:
                dev.call_action("sweep-pause")
            except Exception:
                dev.call_action("vacuum-extend-stop-clean")
        else:
            dev.pause()

    def home(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.call_action("battery-start-charge")
        else:
            dev.home()

    def find(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.call_action("identify-identify")
        else:
            dev.find()

    # ── Status ────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            props = dev.status()
            return self._parse_miot_status(props)
        else:
            s = dev.status()
            return {
                "state": str(s.state),
                "battery": s.battery,
                "fan_speed": str(s.fanspeed),
                "clean_area": s.clean_area,
                "clean_time": s.clean_time,
                "error": str(s.error) if s.error_code else None,
                "is_on": s.is_on,
            }

    def _parse_miot_status(self, props) -> dict[str, Any]:
        """Parse GenericMiot status into a friendly dict."""
        data: dict[str, Any] = {}
        for prop in props:
            name = str(prop.name) if hasattr(prop, "name") else str(prop)
            value = prop.value if hasattr(prop, "value") else None
            # Map common MIoT property names
            name_lower = name.lower().replace("-", "_").replace(" ", "_")
            if "battery" in name_lower and "level" in name_lower:
                data["battery"] = value
            elif "status" in name_lower or "state" in name_lower:
                data.setdefault("state", value)
            elif "fan" in name_lower and ("speed" in name_lower or "level" in name_lower):
                data["fan_speed"] = value
            elif "sweep_mode" in name_lower or "mode" in name_lower:
                data.setdefault("mode", value)
            elif "error" in name_lower:
                data.setdefault("error", value)
            else:
                data[name_lower] = value
        return data

    # ── Cleaning modes ────────────────────────────────────────────

    def clean_rooms(self, room_ids: list[int], repeat: int = 1) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            import json

            param = json.dumps({"clean_mop_type": 0, "clean_param": {"repeat_count": repeat, "segments": room_ids}})
            dev.call_action("vacuum-extend-start-room-sweep", [param])
        else:
            dev.segment_clean(room_ids)

    def clean_zone(self, zones: list[list[int]]) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            import json

            param = json.dumps({"zone": zones})
            dev.call_action("vacuum-extend-start-zone-sweep", [param])
        else:
            dev.zoned_clean(zones)

    def spot_clean(self) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.call_action("vacuum-extend-start-spot-sweep")
        else:
            dev.spot()

    # ── Fan speed ─────────────────────────────────────────────────

    FAN_SPEEDS = {
        "silent": 101,
        "standard": 102,
        "medium": 103,
        "turbo": 104,
        "max": 105,
    }

    FAN_SPEED_NAMES = {v: k for k, v in FAN_SPEEDS.items()}

    def set_fan_speed(self, preset: str) -> None:
        dev = self._get_device()
        level = self.FAN_SPEEDS.get(preset.lower())
        if level is None:
            raise ValueError(f"Unknown speed: {preset}. Use: {', '.join(self.FAN_SPEEDS)}")
        if self._protocol == "genericmiot":
            dev.set_property("vacuum-extend-fan-level", level)
        else:
            dev.set_fan_speed(level)

    def fan_speed(self) -> str:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            props = dev.status()
            for prop in props:
                name = str(prop.name).lower().replace("-", "_")
                if "fan" in name and ("speed" in name or "level" in name):
                    return self.FAN_SPEED_NAMES.get(prop.value, str(prop.value))
            return "unknown"
        else:
            return str(dev.fan_speed())

    # ── Consumables ───────────────────────────────────────────────

    def consumable_status(self) -> dict[str, Any]:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            props = dev.status()
            consumables = {}
            for prop in props:
                name = str(prop.name).lower().replace("-", "_")
                if any(k in name for k in ["brush", "filter", "sensor"]):
                    consumables[name] = prop.value
            return consumables
        else:
            c = dev.consumable_status()
            return {
                "main_brush": c.main_brush,
                "side_brush": c.side_brush,
                "filter": c.filter,
                "sensor_dirty": c.sensor_dirty,
            }

    def consumable_reset(self, name: str) -> None:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            dev.consumable_reset(name)
        else:
            # MIoT: try known action names
            action_map = {
                "main_brush": "brush-cleaner-reset-brush-life",
                "side_brush": "side-brush-reset-side-brush-life",
                "filter": "filter-reset-filter-life",
            }
            action = action_map.get(name)
            if action:
                dev.call_action(action)
            else:
                raise ValueError(f"Unknown consumable: {name}")

    # ── DND ───────────────────────────────────────────────────────

    def dnd_status(self) -> dict[str, Any]:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            props = dev.status()
            dnd = {}
            for prop in props:
                name = str(prop.name).lower().replace("-", "_")
                if "dnd" in name or "disturb" in name:
                    dnd[name] = prop.value
            return dnd
        else:
            d = dev.dnd_status()
            return {
                "enabled": d.enabled,
                "start": f"{d.start_hour:02d}:{d.start_minute:02d}",
                "end": f"{d.end_hour:02d}:{d.end_minute:02d}",
            }

    def set_dnd(self, enabled: bool, start: str | None = None, end: str | None = None) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.set_property("do-not-disturb-enable", enabled)
            if start:
                h, m = start.split(":")
                dev.set_property("do-not-disturb-start-time", f"{h}:{m}")
            if end:
                h, m = end.split(":")
                dev.set_property("do-not-disturb-end-time", f"{h}:{m}")
        else:
            if not enabled:
                dev.disable_dnd()
            else:
                sh, sm = (start or "22:00").split(":")
                eh, em = (end or "07:00").split(":")
                dev.set_dnd(int(sh), int(sm), int(eh), int(em))

    # ── Volume ────────────────────────────────────────────────────

    def set_volume(self, level: int) -> None:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            dev.set_property("audio-volume", level)
        else:
            dev.set_sound_volume(level)

    def volume(self) -> int:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            props = dev.status()
            for prop in props:
                name = str(prop.name).lower().replace("-", "_")
                if "volume" in name:
                    return prop.value
            return -1
        else:
            return dev.sound_volume()

    # ── Schedules ─────────────────────────────────────────────────

    def timer_list(self) -> list:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            return dev.timer() or []
        return []

    def timer_add(self, cron: str) -> None:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            dev.add_timer(cron, "start_clean", "")

    def timer_delete(self, timer_id: str) -> None:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            dev.delete_timer(timer_id)

    # ── Rooms / Map ───────────────────────────────────────────────

    def rooms(self) -> list:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            try:
                result = dev.call_action("vacuum-extend-get-map-room-list")
                return result if result else []
            except Exception:
                return []
        else:
            mapping = dev.get_room_mapping()
            return mapping or []

    # ── History ───────────────────────────────────────────────────

    def clean_history(self) -> dict[str, Any]:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            h = dev.clean_history()
            return {
                "total_count": h.count,
                "total_area": h.total_area,
                "total_duration": h.total_duration,
            }
        return {}

    def last_clean(self) -> dict[str, Any]:
        dev = self._get_device()
        if self._protocol != "genericmiot":
            h = dev.clean_history()
            if h.ids:
                details = dev.clean_details(h.ids[0])
                return {
                    "start": str(details.start),
                    "end": str(details.end),
                    "duration": details.duration,
                    "area": details.area,
                }
        return {}

    # ── Device info ───────────────────────────────────────────────

    def device_info(self) -> dict[str, Any]:
        dev = self._get_device()
        info = dev.info()
        return {
            "model": info.model,
            "firmware": info.firmware_version,
            "hardware": info.hardware_version,
            "mac": info.mac_address,
            "network": getattr(info, "network_interface", None),
        }

    # ── Raw command ───────────────────────────────────────────────

    def raw_command(self, siid: int, aiid: int, params: list | None = None) -> Any:
        dev = self._get_device()
        if self._protocol == "genericmiot":
            return dev.call_action_by(siid, aiid, params or [])
        else:
            raise ValueError("Raw commands only supported for genericmiot protocol")


def get_vacuum(ip: str, token: str, model: str, protocol: str = "genericmiot") -> VacuumService:
    return VacuumService(ip, token, model, protocol)
