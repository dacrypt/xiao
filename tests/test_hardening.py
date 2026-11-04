"""Regression tests for the security / correctness fixes from the project review."""

from __future__ import annotations

import asyncio
import stat
import threading
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def tmp_config_dir(tmp_path):
    with (
        patch("xiao.core.config.CONFIG_DIR", tmp_path),
        patch("xiao.core.config.CONFIG_FILE", tmp_path / "config.toml"),
        patch("xiao.core.config.TANK_STATE_FILE", tmp_path / "tank_state.json"),
    ):
        yield tmp_path


# ── Config file permissions ──────────────────────────────────────


class TestConfigPermissions:
    def test_config_is_written_owner_only(self, tmp_config_dir):
        from xiao.core import config

        config.save({"cloud": {"username": "u", "password": "p"}})
        mode = stat.S_IMODE((tmp_config_dir / "config.toml").stat().st_mode)
        assert mode == 0o600

    def test_tank_state_is_written_owner_only(self, tmp_config_dir):
        from xiao.core import config

        config.save_tank_state({"area_since_clean_reset": 1})
        mode = stat.S_IMODE((tmp_config_dir / "tank_state.json").stat().st_mode)
        assert mode == 0o600

    def test_harden_permissions_fixes_legacy_world_readable_file(self, tmp_config_dir):
        from xiao.core import config

        path = tmp_config_dir / "config.toml"
        path.write_text('[cloud]\npassword = "p"\n')
        path.chmod(0o644)
        config.harden_permissions()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_save_is_atomic_and_leaves_no_temp_files(self, tmp_config_dir):
        from xiao.core import config

        config.save({"a": 1})
        config.save({"a": 2})
        assert config.load() == {"a": 2}
        assert [p.name for p in tmp_config_dir.iterdir()] == ["config.toml"]


# ── Response code normalization ──────────────────────────────────


class TestExtractCode:
    @pytest.mark.parametrize(
        ("result", "expected"),
        [
            ({"code": 0}, 0),
            ({"code": -8}, -8),
            ({"code": 0, "result": {"code": -4004}}, -4004),
            ({"result": {"code": 7}}, 7),
            ({"result": {}}, -1),
            ({"result": [1, 2]}, -1),
            ([{"code": 0}, {"code": -4001}], -4001),
            ([{"code": 0}], 0),
            (None, 0),
            ("ok", 0),
        ],
    )
    def test_cases(self, result, expected):
        from xiao.core.room_cleaning import extract_code

        assert extract_code(result) == expected


# ── Room-clean verification ──────────────────────────────────────


class TestRoomCleanVerification:
    def _run(self, vac):
        from xiao.core.room_cleaning import start_room_clean

        return start_room_clean(vac, [7], poll_attempts=2, poll_delay_seconds=0, sleep_fn=lambda _: None)

    def test_unknown_state_is_inconclusive_not_verified(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        vac.status.side_effect = [{"state": "Charging"}, {"state": "Unknown(17)"}, {"state": "Unknown(17)"}]
        result = self._run(vac)
        assert result["verified_started"] is None

    def test_network_error_does_not_fire_second_command(self):
        """A timeout on the MIoT call may mean the robot already got it; never re-send via RPC."""
        vac = MagicMock()
        vac.status.return_value = {"state": "Charging"}
        vac.clean_rooms_miot.side_effect = TimeoutError("read timed out")
        with pytest.raises(TimeoutError):
            self._run(vac)
        vac.clean_rooms.assert_not_called()

    def test_service_without_miot_uses_legacy_path(self):
        vac = MagicMock(spec=["clean_rooms", "status"])
        vac.status.return_value = {"state": "Charging"}
        vac.clean_rooms.return_value = None  # local miIO returns nothing
        result = self._run(vac)
        assert result["transport"] == "cloud_rpc"
        vac.clean_rooms.assert_called_once_with([7], repeat=1)


class TestKnownRooms:
    def test_merges_sources_without_hardcoded_ids(self):
        from xiao.core.room_cleaning import known_rooms

        vac = MagicMock()
        vac.rooms.return_value = [[2, "Living"]]
        vac.schedules_parsed.return_value = [{"room_ids": [2, 4]}, {"raw": "x", "parse_error": True}]
        rooms = known_rooms(vac, {"4": "Office"})
        assert rooms == [
            {"id": 2, "name": "Living", "sources": ["device", "schedule"]},
            {"id": 4, "name": "Office", "sources": ["schedule", "alias"]},
        ]

    def test_no_vacuum_and_no_aliases_is_empty(self):
        from xiao.core.room_cleaning import known_rooms

        assert known_rooms(None, {}) == []


# ── Cloud vacuum semantics ───────────────────────────────────────


class TestCloudVacuumSemantics:
    def _svc(self):
        from xiao.core.cloud_vacuum import CloudVacuumService

        return CloudVacuumService(MagicMock(), did="1")

    def test_spot_clean_no_longer_starts_full_house(self):
        svc = self._svc()
        with patch("xiao.core.cloud_vacuum.cloud_call_action") as call, pytest.raises(NotImplementedError):
            svc.spot_clean()
        call.assert_not_called()

    def test_pause_is_declared_as_stop(self):
        assert self._svc().PAUSE_IS_STOP is True

    def test_malformed_schedule_entry_does_not_break_parsing(self):
        svc = self._svc()
        with (
            patch.object(
                svc, "timer_list", return_value=["1-3-08:30-1111111-1-x-1-64-3,8;2-3-09:00-1111100-1-2-1-64-4"]
            ),
            patch("xiao.core.config.get_rooms", return_value={}),
        ):
            parsed = svc.schedules_parsed()
        assert parsed[0]["parse_error"] is True
        assert parsed[1]["room_ids"] == [4]


# ── CLI exit codes & validation ──────────────────────────────────


class TestCliExitCodes:
    @pytest.mark.parametrize(
        ("argv", "method"),
        [
            (["start"], "start"),
            (["stop"], "stop"),
            (["dock"], "home"),
            (["find"], "find"),
            (["wash"], "mop_wash"),
            (["dust"], "dust_collect"),
        ],
    )
    def test_rejected_command_exits_non_zero(self, argv, method):
        from xiao.cli.app import app

        vac = MagicMock()
        getattr(vac, method).return_value = {"code": 0, "result": {"code": -4004}}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, argv)
        assert result.exit_code == 1

    def test_accepted_command_exits_zero(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.start.return_value = {"code": 0}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["start"])
        assert result.exit_code == 0

    def test_pause_in_cloud_mode_says_it_stops(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.PAUSE_IS_STOP = True
        vac.pause.return_value = {"code": 0}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["pause"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_progress_messages_do_not_pollute_json_stdout(self):
        """`status --json` must stay parseable even when a login happens first."""
        import json

        from xiao.cli.app import app

        def fake_build(notify=None):
            notify("No saved session. Refreshing tokens via the browser profile...")
            vac = MagicMock()
            vac.status.return_value = {"state": "Idle"}
            return vac

        with patch("xiao.cli.app.build_vacuum", side_effect=fake_build):
            result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == {"state": "Idle"}


class TestCleanCommand:
    def test_zone_parsing(self):
        from xiao.cli.clean import parse_zone

        assert parse_zone("100, 200, 50, 400") == [50, 200, 100, 400]
        with pytest.raises(ValueError):
            parse_zone("1,2,3")
        with pytest.raises(ValueError):
            parse_zone("a,b,c,d")
        with pytest.raises(ValueError):
            parse_zone("1,2,1,5")

    def test_bad_zone_fails_before_contacting_vacuum(self):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum") as m_vac:
            result = runner.invoke(app, ["clean", "-z", "1,2,x,4"])
        assert result.exit_code == 1
        m_vac.assert_not_called()

    def test_multiple_zones(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.clean_zone.return_value = {"code": 0}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["clean", "-z", "0,0,10,10", "-z", "20,20,30,30"])
        assert result.exit_code == 0
        vac.clean_zone.assert_called_once_with([[0, 0, 10, 10], [20, 20, 30, 30]])

    def test_invalid_speed_fails_before_contacting_vacuum(self):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum") as m_vac:
            result = runner.invoke(app, ["clean", "--speed", "ludicrous"])
        assert result.exit_code == 1
        m_vac.assert_not_called()

    def test_spot_unsupported_exits_non_zero_without_full_clean(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.spot_clean.side_effect = NotImplementedError("no spot")
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["clean", "--spot"])
        assert result.exit_code == 1
        vac.start.assert_not_called()

    def test_rejected_room_clean_exits_non_zero(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.status.return_value = {"state": "Charging"}
        vac.clean_rooms_miot.return_value = {"code": -4004}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["clean", "-r", "7"])
        assert result.exit_code == 1


class TestWebCommand:
    def test_defaults_to_loopback(self):
        from xiao.cli.app import app

        with patch("uvicorn.run") as run, patch("xiao.dashboard.server.create_app") as create:
            result = runner.invoke(app, ["web"])
        assert result.exit_code == 0
        assert run.call_args.kwargs["host"] == "127.0.0.1"
        assert create.call_args.kwargs == {"auth_token": None, "loopback_only": True}

    def test_public_bind_generates_token(self, monkeypatch):
        from xiao.cli.app import app

        monkeypatch.delenv("XIAO_WEB_TOKEN", raising=False)
        with patch("uvicorn.run"), patch("xiao.dashboard.server.create_app") as create:
            result = runner.invoke(app, ["web", "--host", "0.0.0.0"])
        assert result.exit_code == 0
        kwargs = create.call_args.kwargs
        assert kwargs["loopback_only"] is False
        assert kwargs["auth_token"]
        assert f"?token={kwargs['auth_token']}" in result.output


# ── Token refresh / login ────────────────────────────────────────


class TestTokenRefreshSafety:
    def test_credentials_are_passed_as_argument_not_interpolated(self):
        from xiao.core import token_refresh

        page = MagicMock()
        page.inner_text.side_effect = [
            '&&&START&&&{"code": 0, "_sign": "s"}',
            '&&&START&&&{"code": 70016}',
        ]
        evil = "x'}; alert(1); //"
        with patch("xiao.core.token_refresh.time.sleep"):
            token_refresh._do_refresh_flow(page, evil, "pw")
        script, fields = page.evaluate.call_args_list[0].args
        assert evil not in script
        assert fields["user"] == evil

    def test_run_outside_event_loop_inline_without_loop(self):
        from xiao.core.token_refresh import run_outside_event_loop

        assert run_outside_event_loop(threading.get_ident) == threading.get_ident()

    def test_run_outside_event_loop_uses_worker_thread_inside_loop(self):
        from xiao.core.token_refresh import run_outside_event_loop

        async def main():
            return run_outside_event_loop(threading.get_ident), threading.get_ident()

        worker, loop_thread = asyncio.run(main())
        assert worker != loop_thread


class TestVerificationCode:
    def test_only_explicit_code_phrases_are_accepted(self):
        from xiao.core.cloud import _extract_code_from_text

        assert _extract_code_from_text("Order 123456 shipped") is None
        assert _extract_code_from_text("Your verification code is: 654321") == "654321"
        assert _extract_code_from_text("code: 111111 ... code: 222222") == "222222"

    def test_gog_search_is_limited_to_recent_mail(self):
        from xiao.core import cloud

        calls = []

        def fake_run(cmd, **_kw):
            calls.append(cmd)
            return MagicMock(returncode=1, stdout="", stderr="")

        with (
            patch("xiao.core.cloud.subprocess.run", side_effect=fake_run),
            patch("xiao.core.cloud.time.sleep"),
        ):
            cloud._read_code_via_gog(max_wait=0.01, poll_interval=0, after_ts=1_700_000_000)
        assert calls
        assert "after:1700000000" in calls[0][3]

    def test_falls_back_to_prompt_without_gog(self, monkeypatch):
        from xiao.core import cloud

        monkeypatch.setattr(cloud.shutil, "which", lambda _name: None)
        monkeypatch.setattr(cloud, "_prompt_for_code", lambda: "123456")
        assert cloud._read_verification_code() == "123456"

    def test_debug_screenshot_disabled_by_default(self, monkeypatch):
        from xiao.core import cloud

        monkeypatch.delenv("XIAO_DEBUG", raising=False)
        page = MagicMock()
        assert cloud._debug_screenshot(page, "x") is None
        page.screenshot.assert_not_called()


# ── Service builder ──────────────────────────────────────────────


class TestServiceBuilder:
    def test_not_configured_raises_typed_error(self, tmp_config_dir):
        from xiao.core import config
        from xiao.core.service import NotConfiguredError, build_vacuum

        config.save({"cloud": {"enabled": True}})
        with pytest.raises(NotConfiguredError) as exc:
            build_vacuum()
        assert exc.value.exit_code == 2

    def test_reuses_saved_session_without_login(self, tmp_config_dir):
        from xiao.core import config
        from xiao.core.service import build_vacuum

        config.save({"cloud": {"enabled": True, "username": "u", "password": "p", "did": "42", "server": "de"}})
        config.save_cloud_session("1", "tok", "sec")
        with patch("xiao.core.token_refresh.refresh_tokens") as refresh:
            vac = build_vacuum()
        refresh.assert_not_called()
        assert vac.did == "42"
        assert vac.country == "de"
        assert vac.cloud.service_token == "tok"

    def test_login_failure_raises_auth_error(self, tmp_config_dir):
        from xiao.core import config
        from xiao.core.service import CloudAuthError, build_vacuum

        config.save({"cloud": {"enabled": True, "username": "u", "password": "p", "did": "42"}})
        with (
            patch("xiao.core.token_refresh.refresh_tokens", return_value=None),
            patch("xiao.core.cloud.XiaomiCloud.login", return_value=False),
            pytest.raises(CloudAuthError) as exc,
        ):
            build_vacuum()
        assert exc.value.exit_code == 77


class TestSettingsCommands:
    def test_volume_out_of_range_fails_before_contacting_vacuum(self):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum") as m_vac:
            result = runner.invoke(app, ["settings", "volume", "150"])
        assert result.exit_code == 1
        m_vac.assert_not_called()

    def test_dnd_rejects_bad_time(self):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum") as m_vac:
            result = runner.invoke(app, ["settings", "dnd", "on", "--start", "25:00"])
        assert result.exit_code == 1
        m_vac.assert_not_called()

    def test_dnd_rejects_unknown_toggle(self):
        from xiao.cli.app import app

        with patch("xiao.cli.app._vacuum") as m_vac:
            result = runner.invoke(app, ["settings", "dnd", "maybe"])
        assert result.exit_code == 1
        m_vac.assert_not_called()

    def test_rejected_property_write_exits_non_zero(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.set_fan_speed.return_value = [{"code": -4001}]
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["settings", "speed", "turbo"])
        assert result.exit_code == 1

    def test_accepted_property_write_exits_zero(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.set_child_lock.return_value = [{"code": 0}]
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["settings", "child-lock", "on"])
        assert result.exit_code == 0
        vac.set_child_lock.assert_called_once_with(True)


class TestConsumablesReset:
    def test_partial_failure_exits_non_zero(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.consumable_reset_all.return_value = {"filter": {"ok": True}, "mop": {"ok": False, "code": -1}}
        with patch("xiao.cli.app._vacuum", return_value=vac):
            result = runner.invoke(app, ["consumables", "reset", "all"])
        assert result.exit_code == 1
        assert "All consumables reset" not in result.output


class TestDoctor:
    def test_flags_world_readable_config(self, tmp_path, monkeypatch):
        from xiao.cli import doctor

        cfg = tmp_path / "config.toml"
        cfg.write_text("")
        cfg.chmod(0o644)
        monkeypatch.setattr(doctor, "CONFIG_FILE", cfg)
        icon, _, _ = doctor._check_config_permissions()
        assert "✗" in icon
        cfg.chmod(0o600)
        icon, _, _ = doctor._check_config_permissions()
        assert "✓" in icon

    def test_vacuum_check_survives_system_exit(self, monkeypatch):
        from xiao.cli import doctor

        monkeypatch.setattr(doctor, "is_configured", lambda: True)
        with patch("xiao.cli.app._vacuum", side_effect=SystemExit(77)):
            icon, _, detail = doctor._check_vacuum_reachable()
        assert "✗" in icon
        assert "77" in detail


def test_latest_code_wins_regardless_of_phrasing():
    from xiao.core.cloud import _extract_code_from_text

    body = "Your verification code is 111111\n...\nCode: 222222"
    assert _extract_code_from_text(body) == "222222"
    body = "Code: 222222\n...\nYour verification code is 333333"
    assert _extract_code_from_text(body) == "333333"
