"""Smoke tests for CLI commands — verify they don't crash on import."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_vacuum():
    """Mock the _vacuum() function so CLI doesn't need real device."""
    vac = MagicMock()
    vac.status.return_value = {"state": "In Dock", "battery": 100, "charging": "Charged", "fan_speed": "Standard"}
    vac.consumable_status.return_value = {
        "main_brush_used": 50,
        "main_brush_life": 300,
        "main_brush_remaining": "83%",
        "side_brush_used": 20,
        "side_brush_life": 200,
        "side_brush_remaining": "90%",
        "filter_used": 10,
        "filter_life": 150,
        "filter_remaining": "93%",
    }
    vac.fan_speed.return_value = "standard"
    vac.dnd_status.return_value = {"enabled": True, "start": "22:00", "end": "07:00"}
    vac.volume.return_value = 50
    vac.device_info.return_value = {"model": "xiaomi.vacuum.c102gl", "firmware": "1.0.0", "did": "123"}
    vac.clean_history.return_value = {"total_clean_count": 10, "total_clean_duration": 600}
    vac.last_clean.return_value = {"last_clean_date": "2025-01-01 12:00", "last_clean_duration": 30}
    vac.rooms.return_value = []
    vac.timer_list.return_value = []
    return vac


class TestCLIStatus:
    def test_status(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    def test_help(self):
        from xiao.cli.app import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "xiao" in result.output.lower() or "vacuum" in result.output.lower()


class TestCLIConsumables:
    def test_consumables(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["consumables"])
        assert result.exit_code == 0


class TestCLISettings:
    def test_speed_get(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "speed"])
        assert result.exit_code == 0

    def test_dnd_get(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "dnd"])
        assert result.exit_code == 0

    def test_volume_get(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "volume"])
        assert result.exit_code == 0


class TestCLIDevice:
    def test_device_info(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["device", "info"])
        assert result.exit_code == 0

    def test_device_history(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["device", "history"])
        assert result.exit_code == 0


class TestCLIMap:
    def test_map_rooms(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["map", "rooms"])
        assert result.exit_code == 0


class TestCLISchedule:
    def test_schedule_list(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["schedule", "list"])
        assert result.exit_code == 0


class TestCLIRooms:
    def test_rooms_rename(self):
        from xiao.cli.app import app

        with patch("xiao.cli.rooms.set_room_alias") as mock_set_room_alias:
            result = runner.invoke(app, ["rooms", "rename", "7", "Kitchen"])

        assert result.exit_code == 0
        mock_set_room_alias.assert_called_once_with(7, "Kitchen")


class TestCLISetup:
    def test_setup_show(self):
        from xiao.cli.app import app

        with patch(
            "xiao.core.config.load",
            return_value={
                "device": {
                    "ip": "1.2.3.4",
                    "token": "abcdef1234567890",
                    "model": "test",
                    "protocol": {"type": "cloud"},
                },
                "cloud": {"enabled": True},
            },
        ):
            result = runner.invoke(app, ["setup", "show"])
        assert result.exit_code == 0
