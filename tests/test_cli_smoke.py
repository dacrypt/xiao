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


class TestJSONOutput:
    """Verify the --json / -j flag produces valid, parseable JSON.

    These tests are the contract that AGENTS.md promises to agents: any
    read command with --json emits a single JSON document on stdout and
    exits 0. Break this and agents can no longer parse output.
    """

    def test_status_json(self, mock_vacuum):
        import json as _json

        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["state"] == "In Dock"
        assert parsed["battery"] == 100

    def test_status_full_json(self, mock_vacuum):
        """--full --json must also produce valid JSON, falling back to
        vac.status() if full_status() isn't available on the mock."""
        import json as _json

        from xiao.cli.app import app

        # mock_vacuum doesn't have full_status → AttributeError path → falls
        # back to status() dict, which must still serialize.
        mock_vacuum.full_status.side_effect = AttributeError("no full_status")
        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["status", "--full", "--json"])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert "state" in parsed

    def test_status_json_short_flag(self, mock_vacuum):
        """The short -j form should behave identically to --json."""
        import json as _json

        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["status", "-j"])
        assert result.exit_code == 0
        _json.loads(result.output)  # must not raise

    def test_consumables_json(self, mock_vacuum):
        import json as _json

        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["consumables", "--json"])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["main_brush_used"] == 50
        assert parsed["filter_remaining"] == "93%"

    def test_consumables_json_empty(self, mock_vacuum):
        """When the device returns no consumable data, --json must still
        emit valid JSON (an empty object) rather than crash."""
        import json as _json

        from xiao.cli.app import app

        mock_vacuum.consumable_status.return_value = None
        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["consumables", "--json"])
        assert result.exit_code == 0
        assert _json.loads(result.output) == {}


class TestExitCodes:
    """Verify the canonical exit-code contract documented in AGENTS.md."""

    def test_not_configured_exits_2(self):
        """Cloud mode enabled with no username/did → EXIT_NOT_CONFIGURED=2."""
        from xiao.cli.app import app

        with (
            patch("xiao.cli.app.is_cloud_mode", return_value=True),
            patch("xiao.cli.app.get_cloud_config", return_value={}),
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 2

    def test_exit_code_constants_match_docs(self):
        """AGENTS.md pins exit codes 0/1/2/77/78/79/80 — make sure the
        module still defines those exact integers."""
        from xiao.core import exit_codes

        assert exit_codes.EXIT_OK == 0
        assert exit_codes.EXIT_GENERIC == 1
        assert exit_codes.EXIT_NOT_CONFIGURED == 2
        assert exit_codes.EXIT_TOKEN_EXPIRED == 77
        assert exit_codes.EXIT_CDP_UNREACHABLE == 78
        assert exit_codes.EXIT_STATE_21 == 79
        assert exit_codes.EXIT_VACUUM_UNRESPONSIVE == 80


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

    def test_resume_after_charge_get(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.resume_after_charge.return_value = {"enabled": True, "raw": 1}

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "resume-after-charge"])

        assert result.exit_code == 0
        assert "Resume after charge" in result.stdout
        assert "On" in result.stdout

    def test_resume_after_charge_set(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "resume-after-charge", "off"])

        assert result.exit_code == 0
        mock_vacuum.set_resume_after_charge.assert_called_once_with(False)

    def test_carpet_boost_set(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "carpet-boost", "on"])

        assert result.exit_code == 0
        mock_vacuum.set_carpet_boost.assert_called_once_with(True)

    def test_child_lock_get(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.child_lock.return_value = {"enabled": False, "raw": 0}

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "child-lock"])

        assert result.exit_code == 0
        assert "Child lock" in result.stdout
        assert "Off" in result.stdout

    def test_smart_wash_get(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.smart_wash.return_value = {"enabled": True, "raw": 1}

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "smart-wash"])

        assert result.exit_code == 0
        assert "Smart wash" in result.stdout
        assert "On" in result.stdout

    def test_smart_wash_set(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "smart-wash", "off"])

        assert result.exit_code == 0
        mock_vacuum.set_smart_wash.assert_called_once_with(False)

    def test_carpet_avoidance_get(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.carpet_avoidance.return_value = {"mode": "avoid", "raw": 1}

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "carpet-avoidance"])

        assert result.exit_code == 0
        assert "Carpet avoidance" in result.stdout
        assert "Avoid" in result.stdout

    def test_carpet_avoidance_set(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "carpet-avoidance", "auto"])

        assert result.exit_code == 0
        mock_vacuum.set_carpet_avoidance.assert_called_once_with("auto")

    def test_clean_rags_tip_get(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.clean_rags_tip.return_value = {"minutes": 45, "raw": 45}

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "clean-rags-tip"])

        assert result.exit_code == 0
        assert "Clean rags tip" in result.stdout
        assert "45 min" in result.stdout

    def test_clean_rags_tip_set(self, mock_vacuum):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["settings", "clean-rags-tip", "30"])

        assert result.exit_code == 0
        mock_vacuum.set_clean_rags_tip.assert_called_once_with(30)


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

    def test_device_history_full_keeps_first_clean_labels_for_cloud_history(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.clean_history.return_value = {
            "first_clean_date": "2024-03-21 05:46 UTC",
            "total_clean_count": 42,
            "total_clean_duration": 130,
        }
        mock_vacuum.last_clean.return_value = {
            "first_clean_date": "2024-03-21 05:46 UTC",
            "total_clean_count": 42,
            "total_clean_duration": 130,
        }

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["device", "history", "--full"])

        assert result.exit_code == 0
        assert "First Clean Date" in result.stdout
        assert "Last First Clean Date" not in result.stdout


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

    def test_schedule_root_defaults_to_list(self, mock_vacuum):
        from xiao.cli.app import app

        mock_vacuum.schedules_parsed.return_value = [
            {
                "id": "2",
                "enabled": True,
                "time": "09:15",
                "days_display": "Weekdays",
                "repeat": True,
                "mode": "Sweep & Mop",
                "fan": "Medium",
                "water": "Medium",
                "rooms_display": ["Kitchen (3)"],
            }
        ]

        with patch("xiao.cli.app._vacuum", return_value=mock_vacuum):
            result = runner.invoke(app, ["schedule"])

        assert result.exit_code == 0
        assert "Cleaning Schedules" in result.stdout
        assert "Weekdays" in result.stdout
        assert "Kitchen (3)" in result.stdout


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
