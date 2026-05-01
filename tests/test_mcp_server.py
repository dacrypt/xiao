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
            assert mcp_server.start_cleaning() == {"code": 0}

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
        vac.clean_rooms_miot.assert_called_once_with([17])
        vac.clean_rooms.assert_not_called()
        assert result == {"code": 0}

    def test_falls_back_to_clean_rooms_on_attribute_error(self):
        vac = MagicMock()
        vac.clean_rooms_miot.side_effect = AttributeError
        vac.clean_rooms.return_value = {"code": 0}
        with (
            patch.object(mcp_server, "_vac", return_value=vac),
            patch("xiao.core.config.resolve_room", return_value=3),
        ):
            mcp_server.clean_room("bedroom")
        vac.clean_rooms.assert_called_once_with([3])

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
    def test_returns_id_name_pairs(self):
        with patch("xiao.core.config.get_rooms", return_value={"17": "kitchen", "3": "bedroom"}):
            rooms = mcp_server.list_rooms()
        assert {"id": 17, "name": "kitchen"} in rooms
        assert {"id": 3, "name": "bedroom"} in rooms


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
