"""LAN (Dreame start-clean) room/zone cleaning for the X20+."""

import json
from unittest.mock import MagicMock, patch

import pytest

from xiao.core.cloud_vacuum import CloudVacuumService
from xiao.core.room_cleaning import LocalUnreachableError, WaitingForWaterError, start_room_clean


def _service(**kwargs) -> CloudVacuumService:
    return CloudVacuumService(MagicMock(), did="1", model="xiaomi.vacuum.c102gl", **kwargs)


def _sent_payload(device: MagicMock) -> tuple[int, dict]:
    method, params = device.send.call_args.args
    assert method == "action"
    assert (params["siid"], params["aiid"]) == (4, 1)
    mode = next(p["value"] for p in params["in"] if p["piid"] == 1)
    data = json.loads(next(p["value"] for p in params["in"] if p["piid"] == 10))
    return mode, data


class TestCloudVacuumLocalHandshake:
    def test_retries_a_dropped_handshake(self):
        svc = _service(local_token="t", local_ip="10.0.0.9")
        svc.network_info = MagicMock(return_value={})
        fake = MagicMock()
        fake.return_value._protocol.send_handshake.side_effect = [OSError("lost"), None]
        with patch("miio.MiotDevice", fake):
            assert svc._local() is fake.return_value
        assert fake.return_value._protocol.send_handshake.call_count == 2


class TestCloudVacuumLocalClean:
    def test_rooms_use_segment_mode_with_ordered_selects(self):
        svc = _service(local_token="t")
        device = MagicMock()
        device.send.return_value = {"code": 0, "out": []}
        svc._local_device = device

        result = svc.clean_rooms_local([8, 3], repeat=2, fan="turbo", water="high")

        assert result["code"] == 0
        mode, data = _sent_payload(device)
        assert mode == 18
        assert data == {"selects": [[8, 2, 3, 3, 1], [3, 2, 3, 3, 2]]}

    def test_rooms_default_to_current_fan_and_water(self):
        svc = _service(local_token="t")
        svc._local_device = MagicMock(send=MagicMock(return_value={"code": 0}))
        with patch(
            "xiao.core.cloud_vacuum.cloud_get_properties",
            return_value=[{"siid": 2, "piid": 3, "value": 0, "code": 0}, {"siid": 4, "piid": 5, "value": 1, "code": 0}],
        ):
            svc.clean_rooms_local([8])
        assert _sent_payload(svc._local_device)[1] == {"selects": [[8, 1, 0, 1, 1]]}

    def test_zones_use_zone_mode_with_areas(self):
        svc = _service(local_token="t")
        svc._local_device = MagicMock(send=MagicMock(return_value={"code": 0}))
        svc.clean_zone_local([[0, 0, 1000, 500]], fan="silent", water="low")
        assert _sent_payload(svc._local_device) == (19, {"areas": [[0, 0, 1000, 500, 1, 0, 1]]})

    def test_rejects_unknown_fan(self):
        svc = _service(local_token="t")
        svc._local_device = MagicMock()
        with pytest.raises(ValueError, match="Unknown speed"):
            svc.clean_rooms_local([8], fan="ludicrous", water="low")
        svc._local_device.send.assert_not_called()

    def test_without_token_the_lan_path_is_unavailable(self):
        svc = _service()
        assert svc.local_clean_available is False
        with pytest.raises(LocalUnreachableError):
            svc._local()

    def test_unreachable_robot_raises_before_sending(self):
        svc = _service(local_token="t", local_ip="10.0.0.9")
        svc.network_info = MagicMock(return_value={"local_ip": "10.0.0.5"})
        fake = MagicMock()
        fake.return_value._protocol.send_handshake.side_effect = OSError("timeout")
        with patch("miio.MiotDevice", fake), pytest.raises(LocalUnreachableError, match=r"10\.0\.0\.5"):
            svc._local()
        fake.return_value.send.assert_not_called()


def _room_vac(**overrides) -> MagicMock:
    vac = MagicMock()
    vac.local_clean_available = True
    vac.status.side_effect = [{"state": "Charging Completed"}, {"state": "Washing mop"}]
    vac.clean_rooms_local.return_value = {"code": 0}
    for key, value in overrides.items():
        setattr(vac, key, value)
    return vac


class TestStartRoomCleanTransport:
    def test_prefers_the_lan_path_and_forwards_fan_water(self):
        vac = _room_vac()
        result = start_room_clean(vac, [8], repeat=2, fan="turbo", water="high", sleep_fn=lambda _s: None)

        vac.clean_rooms_local.assert_called_once_with([8], repeat=2, fan="turbo", water="high")
        vac.clean_rooms_miot.assert_not_called()
        assert result["transport"] == "local"
        assert result["verified_started"] is True
        assert result["warning"] is None

    def test_falls_back_to_cloud_with_a_warning_when_lan_is_unreachable(self):
        vac = _room_vac()
        vac.clean_rooms_local.side_effect = LocalUnreachableError("no route")
        vac.clean_rooms_miot.return_value = {"code": 0}

        result = start_room_clean(vac, [8], sleep_fn=lambda _s: None)

        assert result["transport"] == "miot"
        assert "LAN path unavailable (no route)" in result["warning"]

    def test_lan_errors_after_sending_are_not_retried_on_the_cloud(self):
        vac = _room_vac()
        vac.clean_rooms_local.side_effect = TimeoutError("ack lost")
        with pytest.raises(TimeoutError):
            start_room_clean(vac, [8], sleep_fn=lambda _s: None)
        vac.clean_rooms_miot.assert_not_called()


class TestCloudZoneClean:
    def test_clean_zone_goes_over_the_lan(self):
        svc = _service(local_token="t")
        svc._local_device = MagicMock(send=MagicMock(return_value={"code": 0}))
        with patch(
            "xiao.core.cloud_vacuum.cloud_get_properties",
            return_value=[{"siid": 2, "piid": 3, "value": 1, "code": 0}, {"siid": 4, "piid": 5, "value": 2, "code": 0}],
        ):
            svc.clean_zone([[0, 0, 10, 10]], repeat=2)
        assert _sent_payload(svc._local_device) == (19, {"areas": [[0, 0, 10, 10, 2, 1, 2]]})

    def test_clean_zone_never_falls_back_to_a_full_house_clean(self):
        svc = _service()
        with (
            patch("xiao.core.cloud.cloud_rpc") as rpc,
            patch("xiao.core.cloud_vacuum.cloud_call_action") as action,
            pytest.raises(RuntimeError, match="LAN path"),
        ):
            svc.clean_zone([[0, 0, 10, 10]])
        rpc.assert_not_called()
        action.assert_not_called()


class TestCancelDrying:
    def _svc(self, states):
        svc = _service(local_token="t")
        svc.status = MagicMock(side_effect=[{"state": st} for st in states])
        svc.stop_dry = MagicMock(return_value={"code": 0})
        return svc

    def test_stops_drying_and_waits_until_it_ends(self):
        svc = self._svc(["Drying", "Drying", "Charging Completed"])
        assert svc.cancel_drying(sleep_fn=lambda _s: None) is True
        svc.stop_dry.assert_called_once()
        assert svc.status.call_count == 3

    def test_leaves_a_robot_that_is_not_drying_alone(self):
        svc = self._svc(["Charging Completed"])
        assert svc.cancel_drying(sleep_fn=lambda _s: None) is False
        svc.stop_dry.assert_not_called()

    def test_gives_up_waiting_after_the_poll_budget(self):
        svc = self._svc(["Drying"] * 20)
        assert svc.cancel_drying(sleep_fn=lambda _s: None) is True
        assert svc.status.call_count == 1 + svc.DRYING_POLL_ATTEMPTS

    def test_room_and_zone_cleans_cancel_drying_before_sending(self):
        svc = _service(local_token="t")
        calls = []
        svc._local_device = MagicMock(send=MagicMock(side_effect=lambda *a, **k: calls.append("send") or {"code": 0}))
        svc.cancel_drying = MagicMock(side_effect=lambda: calls.append("cancel") or True)
        svc.clean_rooms_local([8], fan="turbo", water="high")
        svc.clean_zone_local([[0, 0, 10, 10]], fan="turbo", water="high")
        assert calls == ["cancel", "send", "cancel", "send"]

    def test_full_start_cancels_drying_first(self):
        svc = _service()
        calls = []
        svc.cancel_drying = MagicMock(side_effect=lambda: calls.append("cancel"))
        with patch(
            "xiao.core.cloud_vacuum.cloud_call_action", side_effect=lambda *a, **k: calls.append("start") or {"code": 0}
        ):
            svc.start()
        assert calls == ["cancel", "start"]


class TestLocalSendSafety:
    def test_start_clean_disables_miio_resends_and_drops_the_cached_device_on_error(self):
        svc = _service(local_token="t")
        device = MagicMock()
        device.send.side_effect = OSError("no reply")
        svc._local_device = device
        with pytest.raises(OSError):
            svc.start_clean_local(18, {"selects": []})
        assert device.send.call_args.kwargs == {"retry_count": 0}
        assert svc._local_device is None


class TestWaterPause:
    def test_start_resumes_a_job_paused_for_water_over_the_lan(self):
        svc = _service(local_token="t")
        svc.status = MagicMock(return_value={"state": "WashingMopPause"})
        device = MagicMock(send=MagicMock(return_value={"code": 0, "out": []}))
        svc._local_device = device
        with patch("xiao.core.cloud_vacuum.cloud_call_action") as cloud:
            result = svc.start()
        cloud.assert_not_called()
        assert result["resumed"] is True
        method, params = device.send.call_args.args
        assert (method, params["siid"], params["aiid"], params["in"]) == (
            "action",
            4,
            4,
            [{"piid": 10, "value": "1,1"}],
        )
        assert device.send.call_args.kwargs == {"retry_count": 0}

    def test_start_is_a_normal_full_clean_otherwise(self):
        svc = _service()
        svc.status = MagicMock(return_value={"state": "Charging Completed"})
        with patch("xiao.core.cloud_vacuum.cloud_call_action", return_value={"code": 0}) as cloud:
            result = svc.start()
        cloud.assert_called_once()
        assert "resumed" not in result

    def test_new_room_and_zone_jobs_are_refused_during_the_water_pause(self):
        svc = _service(local_token="t")
        svc.status = MagicMock(return_value={"state": "WashingMopPause"})
        svc._local_device = MagicMock()
        with pytest.raises(WaitingForWaterError, match="state 21"):
            svc.clean_rooms_local([8], fan="turbo", water="high")
        with pytest.raises(WaitingForWaterError):
            svc.clean_zone_local([[0, 0, 10, 10]], fan="turbo", water="high")
        svc._local_device.send.assert_not_called()
