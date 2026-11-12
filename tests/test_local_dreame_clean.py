"""LAN (Dreame start-clean) room/zone cleaning for the X20+."""

import json
from unittest.mock import MagicMock, patch

import pytest

from xiao.core.cloud_vacuum import CloudVacuumService
from xiao.core.room_cleaning import LocalUnreachableError, start_room_clean


def _service(**kwargs) -> CloudVacuumService:
    return CloudVacuumService(MagicMock(), did="1", model="xiaomi.vacuum.c102gl", **kwargs)


def _sent_payload(device: MagicMock) -> tuple[int, dict]:
    method, params = device.send.call_args.args
    assert method == "action"
    assert (params["siid"], params["aiid"]) == (4, 1)
    mode = next(p["value"] for p in params["in"] if p["piid"] == 1)
    data = json.loads(next(p["value"] for p in params["in"] if p["piid"] == 10))
    return mode, data


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
