"""Tests for xiao.core.config module."""

from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Use a temporary config directory."""
    with (
        patch("xiao.core.config.CONFIG_DIR", tmp_path),
        patch("xiao.core.config.CONFIG_FILE", tmp_path / "config.toml"),
    ):
        yield tmp_path


class TestConfig:
    def test_load_empty(self, tmp_config_dir):
        from xiao.core.config import load

        assert load() == {}

    def test_save_and_load(self, tmp_config_dir):
        from xiao.core.config import load, save

        cfg = {"device": {"ip": "192.168.1.100", "token": "abc123", "model": "test.vacuum"}}
        save(cfg)
        loaded = load()
        assert loaded["device"]["ip"] == "192.168.1.100"
        assert loaded["device"]["token"] == "abc123"

    def test_is_cloud_mode_false(self, tmp_config_dir):
        from xiao.core.config import is_cloud_mode, save

        save({})
        assert is_cloud_mode() is False

    def test_is_cloud_mode_true(self, tmp_config_dir):
        from xiao.core.config import is_cloud_mode, save

        save({"cloud": {"enabled": True}})
        assert is_cloud_mode() is True

    def test_save_and_get_cloud_session(self, tmp_config_dir):
        from xiao.core.config import get_cloud_session, save, save_cloud_session

        save({"cloud": {"enabled": True, "username": "test@test.com"}})
        save_cloud_session("uid123", "stoken456", "ssec789")
        session = get_cloud_session()
        assert session is not None
        assert session["user_id"] == "uid123"
        assert session["service_token"] == "stoken456"
        assert session["ssecurity"] == "ssec789"

    def test_get_cloud_session_none(self, tmp_config_dir):
        from xiao.core.config import get_cloud_session, save

        save({})
        assert get_cloud_session() is None

    def test_get_device_raises_without_config(self, tmp_config_dir):
        from xiao.core.config import get_device, save

        save({})
        with pytest.raises(SystemExit):
            get_device()

    def test_get_device_returns_tuple(self, tmp_config_dir):
        from xiao.core.config import get_device, save

        save({"device": {"ip": "10.0.0.1", "token": "abcdef1234567890abcdef1234567890", "model": "vacuum.x20"}})
        ip, token, model = get_device()
        assert ip == "10.0.0.1"
        assert token == "abcdef1234567890abcdef1234567890"
        assert model == "vacuum.x20"

    def test_is_configured_cloud(self, tmp_config_dir):
        from xiao.core.config import is_configured, save

        save({"cloud": {"enabled": True, "username": "user@test.com", "did": "12345"}})
        assert is_configured() is True

    def test_is_configured_local(self, tmp_config_dir):
        from xiao.core.config import is_configured, save

        save({"device": {"ip": "1.2.3.4", "token": "aabbccdd"}})
        assert is_configured() is True
