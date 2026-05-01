"""Dashboard server regression tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from xiao.dashboard.server import create_app


class TestDashboardSettingsSnapshot:
    def test_settings_snapshot_includes_advanced_vacuum_extend_controls(self):
        mock_vacuum = MagicMock()
        mock_vacuum.dnd_status.return_value = {"enabled": True, "start": "22:00", "end": "07:00"}
        mock_vacuum.volume.return_value = 50
        mock_vacuum.fan_speed.return_value = "standard"
        mock_vacuum.water_level.return_value = {"water_level": "medium", "water_level_raw": 2}
        mock_vacuum.resume_after_charge.return_value = {"enabled": True, "raw": 1}
        mock_vacuum.carpet_boost.return_value = {"enabled": False, "raw": 0}
        mock_vacuum.child_lock.return_value = {"enabled": True, "raw": 1}
        mock_vacuum.smart_wash.return_value = {"enabled": True, "raw": 1}
        mock_vacuum.clean_rags_tip.return_value = {"minutes": 45, "raw": 45}
        mock_vacuum.carpet_avoidance.return_value = {"mode": "avoid", "raw": 1}

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = TestClient(create_app())
            response = client.get("/api/settings")

        assert response.status_code == 200
        assert response.json()["resume_after_charge"] == {"enabled": True, "raw": 1}
        assert response.json()["carpet_boost"] == {"enabled": False, "raw": 0}
        assert response.json()["child_lock"] == {"enabled": True, "raw": 1}
        assert response.json()["carpet_avoidance"] == {"mode": "avoid", "raw": 1}


class TestDashboardRoomCleaning:
    def test_room_clean_endpoint_returns_warning_when_accept_succeeds_but_start_is_unverified(self):
        mock_vacuum = MagicMock()
        mock_vacuum.clean_rooms_miot.return_value = {"code": 0}
        mock_vacuum.status.side_effect = [
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
        ]

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = TestClient(create_app())
            response = client.post("/api/clean/rooms", json={"room_ids": [7]})

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["verified_started"] is False
        assert "code=0" in response.json()["warning"]


class TestDashboardSettingWrites:
    @pytest.mark.parametrize(
        ("path", "payload", "method_name", "expected_value"),
        [
            ("/api/settings/resume-after-charge", {"enabled": True}, "set_resume_after_charge", True),
            ("/api/settings/carpet-boost", {"enabled": False}, "set_carpet_boost", False),
            ("/api/settings/child-lock", {"enabled": True}, "set_child_lock", True),
            ("/api/settings/smart-wash", {"enabled": False}, "set_smart_wash", False),
            ("/api/settings/carpet-avoidance", {"mode": "auto"}, "set_carpet_avoidance", "auto"),
            ("/api/settings/clean-rags-tip", {"minutes": 30}, "set_clean_rags_tip", 30),
        ],
    )
    def test_write_endpoints_forward_advanced_settings_to_vacuum(self, path, payload, method_name, expected_value):
        mock_vacuum = MagicMock()
        getattr(mock_vacuum, method_name).return_value = [{"code": 0}]

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = TestClient(create_app())
            response = client.post(path, json=payload)

        assert response.status_code == 200
        getattr(mock_vacuum, method_name).assert_called_once_with(expected_value)

    def test_clean_rags_tip_rejects_invalid_minutes(self):
        mock_vacuum = MagicMock()

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = TestClient(create_app())
            response = client.post("/api/settings/clean-rags-tip", json={"minutes": 121})

        assert response.status_code == 400
        mock_vacuum.set_clean_rags_tip.assert_not_called()
