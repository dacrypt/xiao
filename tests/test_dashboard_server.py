"""Dashboard server regression tests."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from xiao.dashboard.server import create_app


class TestDashboardSettingsSnapshot:
    def test_settings_snapshot_includes_carpet_avoidance(self):
        mock_vacuum = MagicMock()
        mock_vacuum.dnd_status.return_value = {"enabled": True, "start": "22:00", "end": "07:00"}
        mock_vacuum.volume.return_value = 50
        mock_vacuum.fan_speed.return_value = "standard"
        mock_vacuum.water_level.return_value = {"water_level": "medium", "water_level_raw": 2}
        mock_vacuum.smart_wash.return_value = {"enabled": True, "raw": 1}
        mock_vacuum.clean_rags_tip.return_value = {"minutes": 45, "raw": 45}
        mock_vacuum.carpet_avoidance.return_value = {"mode": "avoid", "raw": 1}

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = TestClient(create_app())
            response = client.get("/api/settings")

        assert response.status_code == 200
        assert response.json()["carpet_avoidance"] == {"mode": "avoid", "raw": 1}
