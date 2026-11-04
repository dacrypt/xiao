"""Dashboard server regression tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from xiao.dashboard.server import create_app


def _client(**kwargs) -> TestClient:
    """A client that looks like the dashboard's own JS on localhost."""
    return TestClient(create_app(**kwargs), base_url="http://localhost", headers={"X-Xiao-Client": "dashboard"})


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
            client = _client()
            response = client.get("/api/settings")

        assert response.status_code == 200
        assert response.json()["resume_after_charge"] == {"enabled": True, "raw": 1}
        assert response.json()["carpet_boost"] == {"enabled": False, "raw": 0}
        assert response.json()["child_lock"] == {"enabled": True, "raw": 1}
        assert response.json()["carpet_avoidance"] == {"mode": "avoid", "raw": 1}


class TestDashboardStatusAlerts:
    def test_status_endpoint_keeps_state_21_name_but_adds_tank_guidance(self):
        mock_vacuum = MagicMock()
        mock_vacuum.status.return_value = {"state": "WashingMopPause"}

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = _client()
            response = client.get("/api/status")

        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "WashingMopPause"
        assert "clean water" in body["alert"]
        assert "dirty water" in body["alert"]

    def test_tank_update_auto_resets_when_leaving_washing_mop_pause_state(self, tmp_path):
        mock_vacuum = MagicMock()
        mock_vacuum.clean_history.return_value = {"total_area": 120}
        mock_vacuum.status.return_value = {"state": "Charging Completed"}

        prior_state = {
            "clean_tank_reset_at": None,
            "dirty_tank_reset_at": None,
            "area_since_clean_reset": 33,
            "area_since_dirty_reset": 44,
            "last_total_area": 120,
            "last_seen_state": "WashingMopPause",
        }
        reset_state = {
            **prior_state,
            "area_since_clean_reset": 0,
            "area_since_dirty_reset": 0,
        }

        with (
            patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum),
            patch("xiao.core.config.CONFIG_DIR", tmp_path),
            patch("xiao.core.config.CONFIG_FILE", tmp_path / "config.toml"),
            patch("xiao.core.config.TANK_STATE_FILE", tmp_path / "tank_state.json"),
            patch("xiao.core.config.get_tank_state", return_value=prior_state),
            patch("xiao.core.config.reset_tanks", return_value=reset_state) as mock_reset,
            patch("xiao.core.config.save_tank_state") as mock_save,
        ):
            client = _client()
            response = client.post("/api/tanks/update")

        assert response.status_code == 200
        mock_reset.assert_called_once_with("both")
        saved_state = mock_save.call_args.args[0]
        assert saved_state["last_seen_state"] == "Charging Completed"


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
            client = _client()
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
            client = _client()
            response = client.post(path, json=payload)

        assert response.status_code == 200
        getattr(mock_vacuum, method_name).assert_called_once_with(expected_value)

    def test_clean_rags_tip_rejects_invalid_minutes(self):
        mock_vacuum = MagicMock()

        with patch("xiao.dashboard.server._get_vacuum", return_value=mock_vacuum):
            client = _client()
            response = client.post("/api/settings/clean-rags-tip", json={"minutes": 121})

        assert response.status_code == 400
        mock_vacuum.set_clean_rags_tip.assert_not_called()


class TestDashboardSecurity:
    def _vac(self):
        vac = MagicMock()
        vac.start.return_value = {"code": 0}
        vac.status.return_value = {"state": "Idle"}
        return vac

    def test_rejects_non_loopback_host_header(self):
        """DNS rebinding: a page on evil.example resolving to 127.0.0.1 sends Host: evil.example."""
        with patch("xiao.dashboard.server._get_vacuum", return_value=self._vac()):
            client = TestClient(create_app(), base_url="http://evil.example:8120")
            assert client.get("/api/status").status_code == 403

    def test_post_requires_dashboard_header(self):
        vac = self._vac()
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            client = TestClient(create_app(), base_url="http://localhost")
            assert client.post("/api/start").status_code == 403
        vac.start.assert_not_called()

    def test_post_rejects_cross_origin(self):
        vac = self._vac()
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            response = _client().post("/api/start", headers={"Origin": "https://evil.example"})
        assert response.status_code == 403
        vac.start.assert_not_called()

    def test_same_origin_post_succeeds(self):
        vac = self._vac()
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            response = _client().post("/api/start", headers={"Origin": "http://localhost"})
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_token_required_when_configured(self):
        vac = self._vac()
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            client = _client(auth_token="s3cret", loopback_only=False)
            assert client.get("/api/status").status_code == 401
            assert client.get("/api/status", headers={"X-Xiao-Token": "wrong"}).status_code == 401
            assert client.get("/api/status", headers={"X-Xiao-Token": "s3cret"}).status_code == 200
            assert client.get("/api/health").status_code == 200

    def test_rejected_action_is_reported_not_ok(self):
        vac = self._vac()
        vac.start.return_value = {"code": 0, "result": {"code": -4004}}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/start").json()
        assert body["ok"] is False
        assert body["code"] == -4004

    def test_auth_failure_drops_cached_client(self):
        from xiao.core.cloud import TokenExpiredError
        from xiao.dashboard import server

        vac = self._vac()
        vac.status.side_effect = TokenExpiredError("expired")
        with (
            patch("xiao.dashboard.server._get_vacuum", return_value=vac),
            patch.object(server, "_reset_vacuum") as reset,
        ):
            response = _client().get("/api/status")
        assert response.status_code == 503
        reset.assert_called_once()

    def test_endpoints_run_off_the_event_loop(self):
        """Blocking vacuum calls (requests + Playwright sync API) must not run on the loop."""
        import asyncio

        seen = {}
        vac = self._vac()

        def _status():
            try:
                asyncio.get_running_loop()
                seen["loop"] = True
            except RuntimeError:
                seen["loop"] = False
            return {"state": "Idle"}

        vac.status.side_effect = _status
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            assert _client().get("/api/status").status_code == 200
        assert seen["loop"] is False

    def test_rooms_come_from_device_not_hardcoded_ids(self):
        vac = self._vac()
        vac.rooms.return_value = []
        vac.schedules_parsed.return_value = [{"room_ids": [5]}]
        with (
            patch("xiao.dashboard.server._get_vacuum", return_value=vac),
            patch("xiao.core.config.get_rooms", return_value={"9": "Kitchen"}),
        ):
            rooms = _client().get("/api/rooms").json()
        assert [r["id"] for r in rooms] == [5, 9]
        assert rooms[1]["name"] == "Kitchen"
