"""Tests for the MCP server wrapper."""

from unittest.mock import MagicMock, patch

import pytest

# The `mcp` extra may not be installed — skip the whole module if so.
mcp_sdk = pytest.importorskip("mcp")

from xiao import mcp_server


class TestExtractCode:
    def test_dict_with_code(self):
        assert mcp_server._extract_code({"code": 0}) == 0

    def test_dict_with_nested_result(self):
        assert mcp_server._extract_code({"result": {"code": 7}}) == 7

    def test_dict_without_code_returns_minus_one(self):
        assert mcp_server._extract_code({"result": {}}) == -1

    def test_non_dict_returns_zero(self):
        assert mcp_server._extract_code("ok") == 0
        assert mcp_server._extract_code(None) == 0


class TestToolDelegation:
    """Each MCP tool should delegate to the vacuum service. We patch _vac()
    so the tools run without a real device."""

    def test_status_returns_vacuum_status(self):
        vac = MagicMock()
        vac.status.return_value = {"state": "Docked", "battery": 95}
        with patch.object(mcp_server, "_vac", return_value=vac):
            assert mcp_server.status() == {"state": "Docked", "battery": 95}

    def test_start_cleaning_extracts_code(self):
        vac = MagicMock()
        vac.start.return_value = {"code": 0}
        with patch.object(mcp_server, "_vac", return_value=vac):
            assert mcp_server.start_cleaning() == {"ok": True, "code": 0}

    def test_rejected_action_reports_not_ok(self):
        vac = MagicMock()
        vac.stop.return_value = {"code": 0, "result": {"code": -4004}}
        with patch.object(mcp_server, "_vac", return_value=vac):
            assert mcp_server.stop_cleaning() == {"ok": False, "code": -4004}

    def test_pause_reports_stop_semantics_in_cloud_mode(self):
        vac = MagicMock()
        vac.PAUSE_IS_STOP = True
        vac.pause.return_value = {"code": 0}
        with patch.object(mcp_server, "_vac", return_value=vac):
            result = mcp_server.pause_cleaning()
        assert result["ok"] is True
        assert result["stopped_instead_of_paused"] is True

    def test_return_to_dock_calls_home(self):
        vac = MagicMock()
        vac.home.return_value = {"code": 0}
        with patch.object(mcp_server, "_vac", return_value=vac):
            mcp_server.return_to_dock()
        vac.home.assert_called_once()

    def test_consumables_returns_dict(self):
        vac = MagicMock()
        vac.consumable_status.return_value = {"main_brush_life": 80}
        with patch.object(mcp_server, "_vac", return_value=vac):
            assert mcp_server.consumables() == {"main_brush_life": 80}


class TestCleanRoom:
    def test_resolves_alias_and_prefers_miot(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        with (
            patch.object(mcp_server, "_vac", return_value=vac),
            patch("xiao.core.config.resolve_room", return_value=17),
        ):
            result = mcp_server.clean_room("kitchen")
        vac.clean_rooms_miot.assert_called_once_with([17], repeat=1)
        vac.clean_rooms.assert_not_called()
        assert result["ok"] is True
        assert result["code"] == 0
        assert result["room_id"] == 17
        assert result["transport"] == "miot"

    def test_falls_back_to_clean_rooms_when_miot_not_implemented(self):
        vac = MagicMock()
        vac.clean_rooms_miot.side_effect = NotImplementedError
        vac.clean_rooms.return_value = {"code": 0}
        with (
            patch.object(mcp_server, "_vac", return_value=vac),
            patch("xiao.core.config.resolve_room", return_value=3),
        ):
            mcp_server.clean_room("bedroom")
        vac.clean_rooms.assert_called_once_with([3], repeat=1)

    def test_surfaces_room_clean_warning_when_command_is_accepted_but_not_verified(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        vac.status.side_effect = [
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
        ]
        with (
            patch.object(mcp_server, "_vac", return_value=vac),
            patch("xiao.core.config.resolve_room", return_value=17),
        ):
            result = mcp_server.clean_room("kitchen")
        assert result["code"] == 0
        assert result["verified_started"] is False
        assert "code=0" in result["warning"]


class TestListRooms:
    def test_merges_aliases_and_schedule_rooms(self):
        vac = MagicMock()
        vac.rooms.return_value = []
        vac.schedules_parsed.return_value = [{"room_ids": [3, 8]}]
        with (
            patch.object(mcp_server, "_vac", return_value=vac),
            patch("xiao.core.config.get_rooms", return_value={"17": "kitchen", "3": "bedroom"}),
        ):
            rooms = {r["id"]: r for r in mcp_server.list_rooms()}
        assert rooms[17]["name"] == "kitchen"
        assert rooms[3]["name"] == "bedroom"
        assert set(rooms[3]["sources"]) == {"schedule", "alias"}
        assert rooms[8]["name"] == "Room 8"

    def test_lists_aliases_when_vacuum_unavailable(self):
        with (
            patch.object(mcp_server, "_vac", side_effect=RuntimeError("offline")),
            patch("xiao.core.config.get_rooms", return_value={"17": "kitchen"}),
        ):
            rooms = mcp_server.list_rooms()
        assert rooms == [{"id": 17, "name": "kitchen", "sources": ["alias"]}]


class TestServerRegistration:
    def test_expected_tools_are_registered(self):
        """Guard against accidentally dropping a tool in a refactor."""
        # FastMCP exposes registered tools via its internal tool manager.
        registered = set(mcp_server.mcp._tool_manager._tools.keys())
        expected = {
            "status",
            "start_cleaning",
            "stop_cleaning",
            "pause_cleaning",
            "return_to_dock",
            "find_vacuum",
            "consumables",
            "clean_room",
            "list_rooms",
        }
        assert expected.issubset(registered), registered


class TestAsyncRegistration:
    def test_registered_tools_are_async_and_offload(self):
        """Registered tools must be coroutines so blocking vacuum calls (and
        Playwright token refresh) never run on the MCP event loop."""
        import asyncio
        import threading

        tool = mcp_server.mcp._tool_manager._tools["status"]
        assert tool.is_async

        main_thread = threading.get_ident()
        seen = {}
        vac = MagicMock()

        def _status():
            seen["thread"] = threading.get_ident()
            return {"state": "Idle"}

        vac.status.side_effect = _status
        with patch.object(mcp_server, "_vac", return_value=vac):
            result = asyncio.run(tool.run({}))
        assert result == {"state": "Idle"}
        assert seen["thread"] != main_thread

    def test_nothing_is_printed_to_stdout_while_building_vacuum(self, capsys, monkeypatch):
        """stdout is the JSON-RPC channel: progress must not leak into it."""
        from xiao.core import service

        def fake_build(notify=None):
            notify("No saved session. Refreshing tokens via the browser profile...")
            return MagicMock()

        monkeypatch.setattr(service, "build_vacuum", fake_build)
        mcp_server._reset_vac()
        try:
            mcp_server._vac()
        finally:
            mcp_server._reset_vac()
        assert capsys.readouterr().out == ""
