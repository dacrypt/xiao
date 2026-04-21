"""Tests for `xiao doctor` health check."""

from unittest.mock import MagicMock, patch

from xiao.cli import doctor


class TestIndividualChecks:
    def test_python_version_ok(self):
        icon, name, _ = doctor._check_python()
        assert "✓" in icon or "✗" in icon
        assert "Python" in name

    def test_package_check_hit(self):
        icon, _, _ = doctor._check_package("sys")  # builtin → hit
        assert "✓" in icon

    def test_package_check_miss(self):
        icon, _, detail = doctor._check_package("definitely_not_a_real_package_xyz")
        assert "✗" in icon
        assert "xiao-cli" in detail

    def test_config_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "CONFIG_FILE", tmp_path / "nope.toml")
        icon, _, detail = doctor._check_config()
        assert "✗" in icon
        assert "missing" in detail

    def test_config_present(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.toml"
        cfg.write_text("")
        monkeypatch.setattr(doctor, "CONFIG_FILE", cfg)
        icon, _, _ = doctor._check_config()
        assert "✓" in icon

    def test_profile_warn_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "CONFIG_DIR", tmp_path)
        icon, _, detail = doctor._check_browser_profile()
        assert "⚠" in icon
        assert "browser-login" in detail

    def test_profile_ok_when_cookies_exist(self, tmp_path, monkeypatch):
        profile = tmp_path / "chromium"
        (profile / "Default").mkdir(parents=True)
        (profile / "Default" / "Cookies").touch()
        monkeypatch.setattr(doctor, "CONFIG_DIR", tmp_path)
        icon, _, _ = doctor._check_browser_profile()
        assert "✓" in icon

    def test_cloud_session_warn_without_token(self, monkeypatch):
        monkeypatch.setattr(doctor, "get_cloud_config", lambda: {})
        icon, _, _ = doctor._check_cloud_session()
        assert "⚠" in icon

    def test_cloud_session_ok_with_token(self, monkeypatch):
        monkeypatch.setattr(
            doctor,
            "get_cloud_config",
            lambda: {"session": {"service_token": "abc"}},
        )
        icon, _, _ = doctor._check_cloud_session()
        assert "✓" in icon


class TestRun:
    def test_skip_network_does_not_call_vacuum(self, monkeypatch, tmp_path):
        """Passing skip_network=True should never touch the cloud."""
        monkeypatch.setattr(doctor, "CONFIG_FILE", tmp_path / "config.toml")
        monkeypatch.setattr(doctor, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(doctor, "is_configured", lambda: False)
        # If the vacuum path were called despite skip_network, this would fail.
        with patch("xiao.cli.app._vacuum") as mock_vac:
            rc = doctor.run(skip_network=True)
            mock_vac.assert_not_called()
        assert rc in (0, 1)  # depends on other checks; just prove no crash


class TestVacuumReachable:
    def test_ok_when_status_returns_state(self, monkeypatch):
        monkeypatch.setattr(doctor, "is_configured", lambda: True)
        vac = MagicMock()
        vac.status.return_value = {"state": "Docked"}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            icon, _, detail = doctor._check_vacuum_reachable()
        assert "✓" in icon
        assert "Docked" in detail

    def test_fail_on_exception(self, monkeypatch):
        monkeypatch.setattr(doctor, "is_configured", lambda: True)
        with patch("xiao.cli.app._vacuum", side_effect=RuntimeError("boom")):
            icon, _, detail = doctor._check_vacuum_reachable()
        assert "✗" in icon
        assert "boom" in detail
