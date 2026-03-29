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
        """Test that status correctly parses cloud property responses."""
        mock_results = [
            {"siid": 2, "piid": 1, "code": 0, "value": 5},  # Charging
            {"siid": 3, "piid": 1, "code": 0, "value": 85},  # Battery 85%
            {"siid": 3, "piid": 2, "code": 0, "value": 1},  # Charging
            {"siid": 2, "piid": 2, "code": 0, "value": 1},  # Standard fan
            {"siid": 2, "piid": 3, "code": 0, "value": 2},  # Sweep & Mop
            {"siid": 2, "piid": 5, "code": 0, "value": 0},  # sweep_type
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        assert data["state"] == "Go Charging"
        assert data["battery"] == 85
        assert data["charging"] == "Charging"
        assert data["fan_speed"] == "Standard"
        assert data["mode"] == "Sweep & Mop"

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

    def test_status_high_fan_percentage(self, vacuum):
        """Fan level > 3 maps to percentage-based name."""
        mock_results = [
            {"siid": 2, "piid": 2, "code": 0, "value": 80},
        ]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            data = vacuum.status()
        assert "Turbo" in data["fan_speed"]


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
    def test_fan_speed_named(self, vacuum):
        mock_results = [{"siid": 2, "piid": 2, "code": 0, "value": 1}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            assert vacuum.fan_speed() == "standard"

    def test_fan_speed_percentage(self, vacuum):
        mock_results = [{"siid": 2, "piid": 2, "code": 0, "value": 60}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            speed = vacuum.fan_speed()
            assert "Medium" in speed

    def test_set_fan_speed_valid(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_set_properties", return_value=[{"code": 0}]) as mock:
            vacuum.set_fan_speed("turbo")
        mock.assert_called_once()

    def test_set_fan_speed_invalid(self, vacuum):
        with pytest.raises(ValueError, match="Unknown speed"):
            vacuum.set_fan_speed("ultramax")


class TestCloudVacuumVolume:
    def test_get_volume(self, vacuum):
        mock_results = [{"siid": 7, "piid": 1, "code": 0, "value": 50}]
        with patch("xiao.core.cloud_vacuum.cloud_get_properties", return_value=mock_results):
            assert vacuum.volume() == 50

    def test_set_volume(self, vacuum):
        with patch("xiao.core.cloud_vacuum.cloud_set_properties", return_value=[{"code": 0}]) as mock:
            vacuum.set_volume(75)
        mock.assert_called_once()
