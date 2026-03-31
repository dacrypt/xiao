"""Tests for xiao.core.cloud_vacuum module."""

from unittest.mock import MagicMock, patch

import pytest

from xiao.core.cloud_vacuum import CloudVacuumService


@pytest.fixture
def mock_cloud():
    cloud = MagicMock()
    cloud.ssecurity = "test_ssecurity"
    cloud.user_id = "123"
    cloud.service_token = "test_token"
    cloud.username = "test@test.com"
    cloud.password = "testpass"
    return cloud


@pytest.fixture
def vacuum(mock_cloud):
    return CloudVacuumService(mock_cloud, did="device123", model="xiaomi.vacuum.c102gl", country="us")


class TestCloudVacuumStatus:
    def test_status_parsing(self, vacuum):
        """Test that status correctly parses cloud property responses.

        MIoT spec for c102gl:
          siid 2 piid 1 = status
          siid 2 piid 2 = fault (read-only, 0-255) — NOT fan speed
          siid 2 piid 3 = mode (0=Silent, 1=Basic, 2=Strong, 3=Full Speed) = fan speed
          siid 2 piid 5 = dry-left-time (minutes)
        """
        mock_results = [
            {"siid": 2, "piid": 1, "code": 0, "value": 5},   # status = Go Charging
            {"siid": 3, "piid": 1, "code": 0, "value": 85},  # Battery 85%
            {"siid": 3, "piid": 2, "code": 0, "value": 1},   # Charging state
            {"siid": 2, "piid": 3, "code": 0, "value": 1},   # mode = Basic/Standard (fan speed)
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        assert data["state"] == "Go Charging"
        assert data["battery"] == 85
        assert data["charging"] == "Charging"
        assert data["fan_speed"] == "standard"

    def test_status_skips_errors(self, vacuum):
        """Properties with non-zero code are skipped."""
        mock_results = [
            {"siid": 2, "piid": 1, "code": -1, "value": None},
            {"siid": 3, "piid": 1, "code": 0, "value": 50},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        assert "state" not in data
        assert data["battery"] == 50

    def test_status_fault_code_not_fan(self, vacuum):
        """siid 2 piid 2 is device fault (read-only), not fan speed. Status should NOT map it to fan."""
        mock_results = [
            {"siid": 2, "piid": 2, "code": 0, "value": 80},  # fault code 80 — some error
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        # fan_speed should NOT appear for piid=2 data
        assert "fan_speed" not in data, \
            "siid 2 piid 2 is device fault, not fan speed — should not populate fan_speed"


class TestCloudVacuumConsumables:
    def test_consumable_status(self, vacuum):
        mock_results = [
            {"siid": 9, "piid": 1, "code": 0, "value": 100},  # main brush used
            {"siid": 9, "piid": 2, "code": 0, "value": 300},  # main brush life
            {"siid": 10, "piid": 1, "code": 0, "value": 50},  # side brush used
            {"siid": 10, "piid": 2, "code": 0, "value": 200},  # side brush life
            {"siid": 11, "piid": 1, "code": 0, "value": 30},  # filter used
            {"siid": 11, "piid": 2, "code": 0, "value": 150},  # filter life
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.consumable_status()
        assert data["main_brush_used"] == 100
        assert data["main_brush_life"] == 300
        assert data["main_brush_remaining"] == "67%"
        assert data["side_brush_remaining"] == "75%"
        assert data["filter_remaining"] == "80%"


class TestCloudVacuumDND:
    def test_dnd_status(self, vacuum):
        mock_results = [
            {"siid": 5, "piid": 1, "code": 0, "value": True},
            {"siid": 5, "piid": 2, "code": 0, "value": "22:00"},
            {"siid": 5, "piid": 3, "code": 0, "value": "07:00"},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.dnd_status()
        assert data["enabled"] is True
        assert data["start"] == "22:00"
        assert data["end"] == "07:00"


class TestCloudVacuumActions:
    def test_start_calls_correct_action(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_call_action", return_value={"code": 0}) as mock:
            vacuum.start()
        mock.assert_called_once_with(vacuum.cloud, "device123", 2, 1, country="us")

    def test_stop_calls_correct_action(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_call_action", return_value={"code": 0}) as mock:
            vacuum.stop()
        mock.assert_called_once_with(vacuum.cloud, "device123", 2, 2, country="us")

    def test_home_calls_correct_action(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_call_action", return_value={"code": 0}) as mock:
            vacuum.home()
        mock.assert_called_once_with(vacuum.cloud, "device123", 3, 1, country="us")

    def test_find_calls_correct_action(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_call_action", return_value={"code": 0}) as mock:
            vacuum.find()
        mock.assert_called_once_with(vacuum.cloud, "device123", 6, 1, country="us")


class TestCloudVacuumDeviceInfo:
    def test_device_info(self, vacuum):
        mock_results = [
            {"siid": 1, "piid": 1, "code": 0, "value": "Xiaomi"},
            {"siid": 1, "piid": 2, "code": 0, "value": "xiaomi.vacuum.c102gl"},
            {"siid": 1, "piid": 3, "code": 0, "value": "SN123456"},
            {"siid": 1, "piid": 4, "code": 0, "value": "1.2.3"},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.device_info()
        assert data["manufacturer"] == "Xiaomi"
        assert data["model"] == "xiaomi.vacuum.c102gl"
        assert data["serial_number"] == "SN123456"
        assert data["firmware"] == "1.2.3"
        assert data["did"] == "device123"


class TestCloudVacuumHistory:
    def test_clean_history(self, vacuum):
        mock_results = [
            {"siid": 4, "piid": 1, "code": 0, "value": 120},
            {"siid": 4, "piid": 2, "code": 0, "value": 5},
            {"siid": 4, "piid": 3, "code": 0, "value": 250000000},
            {"siid": 12, "piid": 1, "code": 0, "value": 1711000000},
            {"siid": 12, "piid": 2, "code": 0, "value": 50000000},
            {"siid": 12, "piid": 3, "code": 0, "value": 30},
            {"siid": 12, "piid": 4, "code": 0, "value": 300000000},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert data["total_clean_duration"] == 120
        assert data["total_clean_count"] == 5
        assert "last_clean_date" in data


class TestCloudVacuumFanSpeed:
    # According to official MIoT spec for xiaomi.vacuum.c102gl:
    # siid 2, piid 2 = 'fault' (read-only, uint8 0-255) — NOT fan speed
    # siid 2, piid 3 = 'mode' (0=Silent, 1=Basic, 2=Strong, 3=Full Speed) — this IS fan speed

    def test_fan_speed_reads_from_siid2_piid3_not_piid2(self, vacuum):
        """fan_speed() must read from siid=2 piid=3 (mode), not piid=2 (fault)."""
        mock_results = [{"siid": 2, "piid": 3, "code": 0, "value": 1}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results) as mock_get:
            speed = vacuum.fan_speed()
        # Verify it queried piid=3
        called_props = mock_get.call_args[0][2]  # third positional arg = props list
        assert any(p.get("piid") == 3 for p in called_props), "fan_speed() should read piid=3 (mode), not piid=2 (fault)"
        assert speed == "standard"

    def test_fan_speed_named(self, vacuum):
        mock_results = [{"siid": 2, "piid": 3, "code": 0, "value": 1}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            assert vacuum.fan_speed() == "standard"

    def test_fan_speed_all_named_values(self, vacuum):
        """Verify all 4 official MIoT mode values decode correctly."""
        cases = [(0, "silent"), (1, "standard"), (2, "medium"), (3, "turbo")]
        for val, expected in cases:
            mock_results = [{"siid": 2, "piid": 3, "code": 0, "value": val}]
            with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
                assert vacuum.fan_speed() == expected, f"value={val} should map to '{expected}'"

    def test_set_fan_speed_writes_to_siid2_piid3(self, vacuum):
        """set_fan_speed() must write to siid=2 piid=3 (mode), not piid=2 (fault)."""
        with patch("xiao.core.cloud_vacuum.cloud_set_properties", return_value=[{"code": 0}]) as mock_set:
            vacuum.set_fan_speed("turbo")
        called_props = mock_set.call_args[0][2]  # third positional arg = props list
        assert any(p.get("piid") == 3 for p in called_props), "set_fan_speed() should write piid=3 (mode), not piid=2 (fault)"
        assert all(p.get("piid") != 2 for p in called_props), "set_fan_speed() must NOT write to piid=2 (fault — read-only!)"

    def test_set_fan_speed_valid(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_set_properties", return_value=[{"code": 0}]) as mock:
            vacuum.set_fan_speed("turbo")
        mock.assert_called_once()

    def test_set_fan_speed_invalid(self, vacuum):
        with pytest.raises(ValueError, match="Unknown speed"):
            vacuum.set_fan_speed("ultramax")

    def test_status_fan_speed_reads_from_piid3(self, vacuum):
        """status() fan_speed parsing must come from siid=2 piid=3 (mode), not piid=2 (fault)."""
        mock_results = [
            {"siid": 2, "piid": 1, "code": 0, "value": 6},   # status = Charging
            {"siid": 2, "piid": 3, "code": 0, "value": 2},   # mode (fan) = Medium/Strong
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        # siid 2, piid 3, value=2 should be "Medium" or "Strong" fan speed
        assert "fan_speed" in data, "status() should include fan_speed from piid=3"
        assert data["fan_speed"] in ("medium", "Medium", "Strong", "strong"), \
            f"value=2 should decode to medium/strong, got: {data['fan_speed']}"


class TestCloudVacuumVolume:
    def test_get_volume(self, vacuum):
        mock_results = [{"siid": 7, "piid": 1, "code": 0, "value": 50}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            assert vacuum.volume() == 50

    def test_set_volume(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_set_properties", return_value=[{"code": 0}]) as mock:
            vacuum.set_volume(75)
        mock.assert_called_once()


class TestCloudVacuumHistoryDisplay:
    """Tests for human-readable history display fields (fixes dashboard '--' bug)."""

    def test_clean_history_includes_duration_display_hours_and_minutes(self, vacuum):
        """total_clean_duration (minutes) should produce a human-readable display field."""
        mock_results = [
            {"siid": 4, "piid": 1, "code": 0, "value": 130},  # 130 minutes = 2h 10min
            {"siid": 4, "piid": 2, "code": 0, "value": 5},
            {"siid": 4, "piid": 3, "code": 0, "value": 25},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert "total_clean_duration_display" in data, "Missing duration display field"
        assert data["total_clean_duration_display"] == "2h 10min"

    def test_clean_history_duration_display_exact_hours(self, vacuum):
        """120 minutes = 2h 0min (no fractional confusion)."""
        mock_results = [
            {"siid": 4, "piid": 1, "code": 0, "value": 120},
            {"siid": 4, "piid": 2, "code": 0, "value": 3},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert data["total_clean_duration_display"] == "2h 0min"

    def test_clean_history_duration_display_less_than_one_hour(self, vacuum):
        """45 minutes should show as '45min', not '0h 45min'."""
        mock_results = [
            {"siid": 4, "piid": 1, "code": 0, "value": 45},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert data["total_clean_duration_display"] == "45min"

    def test_clean_history_last_clean_area_formatted(self, vacuum):
        """last_clean_area from siid 12 piid 2 should be included as m² value."""
        mock_results = [
            {"siid": 12, "piid": 1, "code": 0, "value": 1711000000},
            {"siid": 12, "piid": 2, "code": 0, "value": 35},  # 35 m²
            {"siid": 12, "piid": 3, "code": 0, "value": 42},  # 42 minutes
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert data.get("last_clean_area") == 35
        # last_clean_duration should also be present
        assert data.get("last_clean_duration") == 42

    def test_clean_history_zero_count_not_hidden(self, vacuum):
        """Zero values should be explicitly 0 (not None/missing) so the dashboard can display '0'."""
        mock_results = [
            {"siid": 4, "piid": 1, "code": 0, "value": 0},
            {"siid": 4, "piid": 2, "code": 0, "value": 0},
            {"siid": 4, "piid": 3, "code": 0, "value": 0},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.clean_history()
        assert data["total_clean_duration"] == 0
        assert data["total_clean_count"] == 0
        assert data["total_clean_duration_display"] == "0min"
