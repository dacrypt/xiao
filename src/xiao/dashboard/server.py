"""FastAPI server for the Mission Control dashboard."""

from __future__ import annotations

import contextlib
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from xiao.core.room_cleaning import start_room_clean

logger = logging.getLogger(__name__)

# ── Request models ────────────────────────────────────────────────


class SpeedRequest(BaseModel):
    level: int  # 0=silent, 1=standard, 2=medium, 3=turbo


class VolumeRequest(BaseModel):
    level: int  # 0-100


class DNDRequest(BaseModel):
    enabled: bool
    start: str | None = None  # "HH:MM"
    end: str | None = None  # "HH:MM"


class ToggleSettingRequest(BaseModel):
    enabled: bool


class ModeSettingRequest(BaseModel):
    mode: str


class MinutesSettingRequest(BaseModel):
    minutes: int


class WaterRequest(BaseModel):
    level: str  # low, medium, high


class RoomCleanRequest(BaseModel):
    room_ids: list[int]
    fan: str | None = None  # silent, standard, medium, turbo
    water: str | None = None  # low, medium, high


# ── Vacuum singleton ─────────────────────────────────────────────

_vacuum_instance = None


def _get_vacuum():
    """Lazy-init the vacuum service (reuse across requests)."""
    global _vacuum_instance
    if _vacuum_instance is None:
        from xiao.cli.app import _vacuum

        _vacuum_instance = _vacuum()
    return _vacuum_instance


def _reset_vacuum():
    """Force re-creation on next call (e.g. after auth failure)."""
    global _vacuum_instance
    _vacuum_instance = None


# ── App factory ───────────────────────────────────────────────────


def _is_state_21_pause(state: Any) -> bool:
    state_text = str(state)
    return state_text == "WashingMopPause" or state_text == "Unknown(21)"


def _state_21_alert(cta: str) -> str:
    return f"⚠️ Washing mop paused. Check clean water (refill) and dirty water (empty), then {cta}."


def create_app() -> FastAPI:
    app = FastAPI(title="Xiaomi X20+ Mission Control", version="2.0.0")

    # ── Static frontend ──────────────────────────────────────────

    index_html = Path(__file__).parent / "index.html"

    @app.get("/", response_class=FileResponse)
    async def root():
        return FileResponse(index_html, media_type="text/html")

    # ── Health ───────────────────────────────────────────────────

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "ts": int(time.time())}

    # ── Status ───────────────────────────────────────────────────

    @app.get("/api/status")
    async def status():
        try:
            vac = _get_vacuum()
            data = vac.status()
            # Add friendly fan name
            fan_names = {0: "Silent", 1: "Standard", 2: "Medium", 3: "Turbo"}
            raw = data.get("fan_level_raw")
            if raw is not None and raw in fan_names:
                data["fan"] = fan_names[raw]
            elif "fan_speed" in data:
                data["fan"] = data["fan_speed"]
            # Add alert field (same logic as /api/status/live)
            state = data.get("state", "Unknown")
            if _is_state_21_pause(state):
                data["alert"] = _state_21_alert("press Resume after fixing")
            return data
        except Exception as e:
            logger.exception("status failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Full status ──────────────────────────────────────────────

    @app.get("/api/status/full")
    async def full_status():
        try:
            vac = _get_vacuum()
            data = vac.full_status()
            return data
        except Exception as e:
            logger.exception("full status failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Live status (lightweight, frequent polling) ─────────────

    @app.get("/api/status/live")
    async def status_live():
        try:
            vac = _get_vacuum()
            data = vac.status()
            state = data.get("state", "Unknown")
            alert = None
            if _is_state_21_pause(state):
                alert = _state_21_alert("press the button on the robot after fixing")
            return {
                "state": state,
                "battery": data.get("battery", 0),
                "charging": data.get("charging", ""),
                "alert": alert,
                "ts": int(time.time()),
            }
        except Exception as e:
            logger.exception("live status failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Consumables ──────────────────────────────────────────────

    @app.get("/api/consumables")
    async def consumables():
        try:
            vac = _get_vacuum()
            raw = vac.consumable_status()
            # CORRECT mapping based on MIoT spec:
            # siid 9 (main brush): piid1 = left_time(hours), piid2 = life_level(%)
            # siid 10 (side brush): piid1 = left_time(hours), piid2 = life_level(%)
            # siid 11 (filter): piid1 = life_level(%), piid2 = left_time(hours)
            # siid 18 (mop): piid1 = life_level(%), piid2 = left_time(hours)
            data = {
                "main_brush": {
                    "remaining": f"{raw.get('main_brush_life', 0)}%",
                    "left_hours": raw.get("main_brush_used"),
                    "life_pct": raw.get("main_brush_life"),
                },
                "side_brush": {
                    "remaining": f"{raw.get('side_brush_life', 0)}%",
                    "left_hours": raw.get("side_brush_used"),
                    "life_pct": raw.get("side_brush_life"),
                },
                "filter": {
                    "remaining": f"{raw.get('filter_used', 0)}%",  # filter piid1 IS life_level
                    "left_hours": raw.get("filter_life"),  # filter piid2 IS left_time
                    "life_pct": raw.get("filter_used"),
                },
            }
            # Add mop consumable
            if raw.get("mop_life_level") is not None:
                data["mop"] = {
                    "remaining": f"{raw.get('mop_life_level')}%",
                    "left_hours": raw.get("mop_left_time"),
                    "life_pct": raw.get("mop_life_level"),
                }
            return data
        except Exception as e:
            logger.exception("consumables failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Device info ──────────────────────────────────────────────

    @app.get("/api/device")
    async def device_info():
        try:
            vac = _get_vacuum()
            data = vac.device_info()
            return data
        except Exception as e:
            logger.exception("device info failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── History ──────────────────────────────────────────────────

    @app.get("/api/history")
    async def history():
        try:
            vac = _get_vacuum()
            data = vac.clean_history()
            return data
        except Exception as e:
            logger.exception("history failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Settings (read) ──────────────────────────────────────────

    @app.get("/api/settings")
    async def settings_get():
        try:
            vac = _get_vacuum()
            dnd = vac.dnd_status()
            vol = vac.volume()
            fan = vac.fan_speed()
            water = {}
            resume_after_charge = {}
            carpet_boost = {}
            child_lock = {}
            smart_wash = {}
            carpet_avoidance = {}
            clean_rags_tip = {}
            with contextlib.suppress(Exception):
                water = vac.water_level()
            with contextlib.suppress(Exception):
                resume_after_charge = vac.resume_after_charge()
            with contextlib.suppress(Exception):
                carpet_boost = vac.carpet_boost()
            with contextlib.suppress(Exception):
                child_lock = vac.child_lock()
            with contextlib.suppress(Exception):
                smart_wash = vac.smart_wash()
            with contextlib.suppress(Exception):
                carpet_avoidance = vac.carpet_avoidance()
            with contextlib.suppress(Exception):
                clean_rags_tip = vac.clean_rags_tip()
            return {
                "dnd": dnd,
                "volume": vol,
                "fan_speed": fan,
                "water": water,
                "resume_after_charge": resume_after_charge,
                "carpet_boost": carpet_boost,
                "child_lock": child_lock,
                "smart_wash": smart_wash,
                "carpet_avoidance": carpet_avoidance,
                "clean_rags_tip": clean_rags_tip,
            }
        except Exception as e:
            logger.exception("settings failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Rooms ────────────────────────────────────────────────────

    @app.get("/api/rooms")
    async def rooms_list():
        from xiao.core.config import get_rooms

        aliases = get_rooms()
        # Known room IDs from device schedules
        known_ids: set[int] = {1, 2, 3, 4, 6, 7, 8, 10, 12}
        for alias_id in aliases:
            known_ids.add(int(alias_id))
        rooms = []
        for rid in sorted(known_ids):
            rooms.append({"id": rid, "name": aliases.get(str(rid), f"Room {rid}")})
        return rooms

    # ── Schedules ────────────────────────────────────────────────

    @app.get("/api/schedules")
    async def schedules_list():
        try:
            vac = _get_vacuum()
            scheds = vac.schedules_parsed()
            return scheds
        except Exception as e:
            logger.exception("schedules failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Water level ──────────────────────────────────────────────

    @app.get("/api/water")
    async def water_get():
        try:
            vac = _get_vacuum()
            return vac.water_level()
        except Exception as e:
            logger.exception("water get failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/water")
    async def water_set(req: WaterRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_water_level(req.level)
            return {"ok": True, "level": req.level, "result": result}
        except ValueError as e:
            raise HTTPException(400, detail=str(e)) from e
        except Exception as e:
            logger.exception("water set failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Network info ─────────────────────────────────────────

    @app.get("/api/network")
    async def network_info():
        try:
            vac = _get_vacuum()
            return vac.network_info()
        except Exception as e:
            logger.exception("network info failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── All properties ───────────────────────────────────────

    @app.get("/api/all-properties")
    async def all_properties():
        try:
            vac = _get_vacuum()
            return vac.all_properties()
        except Exception as e:
            logger.exception("all properties failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Control actions ──────────────────────────────────────────

    @app.post("/api/start")
    async def start_clean():
        try:
            vac = _get_vacuum()
            result = vac.start()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("start failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/stop")
    async def stop_clean():
        try:
            vac = _get_vacuum()
            result = vac.stop()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("stop failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/dock")
    async def dock():
        try:
            vac = _get_vacuum()
            result = vac.home()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("dock failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/find")
    async def find():
        try:
            vac = _get_vacuum()
            result = vac.find()
            return {"ok": True, "result": result}
        except Exception as e:
            logger.exception("find failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Room cleaning ────────────────────────────────────────────

    @app.post("/api/clean/rooms")
    async def clean_rooms(req: RoomCleanRequest):
        try:
            vac = _get_vacuum()
            # Set fan/water if requested
            if req.fan:
                vac.set_fan_speed(req.fan)
            if req.water:
                vac.set_water_level(req.water)
            clean_result = start_room_clean(vac, req.room_ids)
            return {
                "ok": clean_result["accepted"],
                "rooms": req.room_ids,
                "result": clean_result["result"],
                "verified_started": clean_result["verified_started"],
                "warning": clean_result["warning"],
                "transport": clean_result["transport"],
            }
        except Exception as e:
            logger.exception("room clean failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Base station controls ────────────────────────────────────

    @app.post("/api/wash")
    async def wash():
        try:
            vac = _get_vacuum()
            result = vac.mop_wash()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("wash failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/dry")
    async def dry():
        try:
            vac = _get_vacuum()
            result = vac.start_dry()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("dry failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/dry/stop")
    async def dry_stop():
        try:
            vac = _get_vacuum()
            result = vac.stop_dry()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("dry stop failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/dust")
    async def dust():
        try:
            vac = _get_vacuum()
            result = vac.dust_collect()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("dust failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/eject")
    async def eject():
        try:
            vac = _get_vacuum()
            result = vac.eject_tray()
            code = _extract_code(result)
            return {"ok": code == 0, "result": result}
        except Exception as e:
            logger.exception("eject failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Settings (write) ─────────────────────────────────────────

    @app.post("/api/settings/speed")
    async def set_speed(req: SpeedRequest):
        try:
            vac = _get_vacuum()
            speed_names = {0: "silent", 1: "standard", 2: "medium", 3: "turbo"}
            name = speed_names.get(req.level)
            if name is None:
                raise HTTPException(400, detail="level must be 0-3")
            result = vac.set_fan_speed(name)
            return {"ok": True, "level": req.level, "name": name, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("set speed failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/volume")
    async def set_volume(req: VolumeRequest):
        try:
            vac = _get_vacuum()
            if not (0 <= req.level <= 100):
                raise HTTPException(400, detail="level must be 0-100")
            result = vac.set_volume(req.level)
            return {"ok": True, "level": req.level, "result": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("set volume failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/dnd")
    async def set_dnd(req: DNDRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_dnd(req.enabled, req.start, req.end)
            return {"ok": True, "enabled": req.enabled, "result": result}
        except Exception as e:
            logger.exception("set DND failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/resume-after-charge")
    async def set_resume_after_charge(req: ToggleSettingRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_resume_after_charge(req.enabled)
            return {"ok": True, "enabled": req.enabled, "result": result}
        except Exception as e:
            logger.exception("set resume after charge failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/carpet-boost")
    async def set_carpet_boost(req: ToggleSettingRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_carpet_boost(req.enabled)
            return {"ok": True, "enabled": req.enabled, "result": result}
        except Exception as e:
            logger.exception("set carpet boost failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/child-lock")
    async def set_child_lock(req: ToggleSettingRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_child_lock(req.enabled)
            return {"ok": True, "enabled": req.enabled, "result": result}
        except Exception as e:
            logger.exception("set child lock failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/smart-wash")
    async def set_smart_wash(req: ToggleSettingRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_smart_wash(req.enabled)
            return {"ok": True, "enabled": req.enabled, "result": result}
        except Exception as e:
            logger.exception("set smart wash failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/carpet-avoidance")
    async def set_carpet_avoidance(req: ModeSettingRequest):
        try:
            vac = _get_vacuum()
            result = vac.set_carpet_avoidance(req.mode)
            return {"ok": True, "mode": req.mode, "result": result}
        except ValueError as e:
            raise HTTPException(400, detail=str(e)) from e
        except Exception as e:
            logger.exception("set carpet avoidance failed")
            raise HTTPException(500, detail=str(e)) from e

    @app.post("/api/settings/clean-rags-tip")
    async def set_clean_rags_tip(req: MinutesSettingRequest):
        try:
            if not (0 <= req.minutes <= 120):
                raise HTTPException(400, detail="clean rags tip must be between 0 and 120 minutes")
            vac = _get_vacuum()
            result = vac.set_clean_rags_tip(req.minutes)
            return {"ok": True, "minutes": req.minutes, "result": result}
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(400, detail=str(e)) from e
        except Exception as e:
            logger.exception("set clean rags tip failed")
            raise HTTPException(500, detail=str(e)) from e

    # ── Water Tank Level Estimation ─────────────────────────────

    @app.get("/api/tanks")
    async def tank_levels():
        """Get estimated water tank levels."""
        from xiao.core.config import get_tank_state

        state = get_tank_state()

        clean_capacity_m2 = 280  # 4L tank, official spec: up to 280m² per fill
        dirty_capacity_m2 = 250  # dirty tank slightly smaller, fills faster

        clean_area = state.get("area_since_clean_reset", 0)
        dirty_area = state.get("area_since_dirty_reset", 0)

        clean_pct = max(0, round(100 - (clean_area / clean_capacity_m2 * 100)))
        dirty_pct = min(100, round(dirty_area / dirty_capacity_m2 * 100))

        return {
            "clean_tank": {
                "level_pct": clean_pct,
                "area_used": clean_area,
                "capacity_m2": clean_capacity_m2,
                "reset_at": state.get("clean_tank_reset_at"),
            },
            "dirty_tank": {
                "level_pct": dirty_pct,
                "area_used": dirty_area,
                "capacity_m2": dirty_capacity_m2,
                "reset_at": state.get("dirty_tank_reset_at"),
            },
            "is_estimate": True,
        }

    @app.post("/api/tanks/reset")
    async def reset_tank_tracking(req: dict | None = None):
        """Reset tank tracking after refilling/emptying."""
        from xiao.core.config import reset_tanks as _reset_tanks

        which = "both"
        if req and "which" in req:
            which = req["which"]  # "clean", "dirty", or "both"
        state = _reset_tanks(which)
        return {"ok": True, "state": state}

    @app.post("/api/tanks/update")
    async def update_tank_tracking():
        """Called periodically to update tank estimates based on cleaning history.

        Auto-resets tanks when vacuum exits state 21 (WashingMopPause).
        We keep the existing tank-reset heuristic because that pause still tends
        to coincide with servicing the clean/dirty water tanks on X20+ setups.
        """
        from xiao.core.config import get_tank_state, save_tank_state
        from xiao.core.config import reset_tanks as _reset_tanks

        try:
            vac = _get_vacuum()
            history = vac.clean_history()
            data = vac.status()

            state = get_tank_state()
            current_state = data.get("state", "")
            prev_state = state.get("last_seen_state", "")

            # Auto-reset: if previous state was WashingMopPause and now it's not
            was_tank_alert = _is_state_21_pause(prev_state)
            is_tank_alert = _is_state_21_pause(current_state)
            if was_tank_alert and not is_tank_alert:
                logger.info("State 21 pause resolved — auto-resetting tank estimates")
                state = _reset_tanks("both")

            # Track current state for next comparison
            state["last_seen_state"] = current_state

            current_total = history.get("total_area", 0)
            last_total = state.get("last_total_area", 0)

            if last_total == 0:
                state["last_total_area"] = current_total
                save_tank_state(state)
                return {"ok": True, "delta": 0, "auto_reset": False}

            delta = max(0, current_total - last_total)
            if delta > 0:
                # Only count water usage if mode involves mopping
                mode = data.get("mode", "")
                uses_water = "sweep only" not in mode.lower() if mode else True

                if uses_water:
                    state["area_since_clean_reset"] = state.get("area_since_clean_reset", 0) + delta
                    state["area_since_dirty_reset"] = state.get("area_since_dirty_reset", 0) + delta

                state["last_total_area"] = current_total
                save_tank_state(state)
                return {"ok": True, "delta": delta, "water_counted": uses_water}

            save_tank_state(state)
            return {"ok": True, "delta": 0}
        except Exception as e:
            logger.exception("tank update failed")
            raise HTTPException(500, detail=str(e)) from e

    return app


def _extract_code(result: Any) -> int:
    """Pull the response code from a cloud API result."""
    if isinstance(result, dict):
        return result.get("code", result.get("result", {}).get("code", -1))
    return 0
