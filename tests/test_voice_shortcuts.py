"""Siri Shortcuts: /api/voice and the .shortcut builder."""

import plistlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from xiao.core.shortcuts import build_workflow, default_specs, write_shortcuts
from xiao.dashboard.server import create_app

ROOMS = {"8": "Cocina", "2": "Baño", "1": "Habitación Principal"}


def _client(**kwargs) -> TestClient:
    return TestClient(create_app(**kwargs), base_url="http://localhost", headers={"X-Xiao-Client": "dashboard"})


@pytest.fixture
def rooms():
    with patch("xiao.core.config.get_rooms", return_value=ROOMS):
        yield


class TestVoiceEndpoint:
    def test_clean_room_by_id_and_says_its_name(self, rooms):
        vac = MagicMock()
        with (
            patch("xiao.dashboard.server._get_vacuum", return_value=vac),
            patch(
                "xiao.dashboard.server.start_room_clean",
                return_value={"accepted": True, "code": 0, "verified_started": True},
            ) as start,
        ):
            body = _client().post("/api/voice", json={"action": "clean", "room": "8"}).json()
        start.assert_called_once_with(vac, [8])
        assert body == {"ok": True, "say": "Listo, la aspiradora va a limpiar Cocina."}

    def test_room_names_are_accent_insensitive(self, rooms):
        with (
            patch("xiao.dashboard.server._get_vacuum"),
            patch(
                "xiao.dashboard.server.start_room_clean",
                return_value={"accepted": True, "code": 0, "verified_started": None},
            ) as start,
        ):
            body = _client().post("/api/voice", json={"room": "bano, cocina"}).json()
        assert start.call_args.args[1] == [2, 8]
        assert body["say"] == "Listo, la aspiradora va a limpiar Baño y Cocina."

    def test_unknown_room_is_spoken_not_a_500(self, rooms):
        body = _client().post("/api/voice", json={"room": "garaje"}).json()
        assert body == {"ok": False, "say": "No conozco la habitación garaje."}

    def test_empty_room_never_falls_through_to_a_full_clean(self, rooms):
        vac = MagicMock()
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/voice", json={"action": "clean", "room": ""}).json()
        assert body["ok"] is False
        vac.start.assert_not_called()

    def test_robot_that_did_not_move_is_reported(self, rooms):
        with (
            patch("xiao.dashboard.server._get_vacuum"),
            patch(
                "xiao.dashboard.server.start_room_clean",
                return_value={"accepted": True, "code": 0, "verified_started": False},
            ),
        ):
            body = _client().post("/api/voice", json={"room": "8"}).json()
        assert body["ok"] is False
        assert "no se movió" in body["say"]

    @pytest.mark.parametrize(
        ("action", "method", "say"),
        [
            ("clean", "start", "Listo, la aspiradora va a limpiar toda la casa."),
            ("dock", "home", "La aspiradora vuelve a la base."),
            ("stop", "stop", "Aspiradora detenida."),
        ],
    )
    def test_simple_actions(self, rooms, action, method, say):
        vac = MagicMock()
        getattr(vac, method).return_value = {"code": 0}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/voice", json={"action": action}).json()
        assert body == {"ok": True, "say": say}

    def test_zone(self, rooms):
        vac = MagicMock()
        vac.clean_zone.return_value = {"code": 0}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/voice", json={"zone": "100,100,0,0"}).json()
        vac.clean_zone.assert_called_once_with([[0, 0, 100, 100]])
        assert body["ok"] is True

    def test_status_in_spanish_and_english(self, rooms):
        vac = MagicMock()
        vac.status.return_value = {"state": "Charging", "battery": 80}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            es = _client().post("/api/voice", json={"action": "status"}).json()
            en = _client().post("/api/voice", json={"action": "status", "lang": "en"}).json()
        assert es["say"] == "La aspiradora está cargando, con 80% de batería."
        assert en["say"] == "The vacuum is Charging, battery 80%."

    def test_errors_become_a_sentence(self, rooms):
        with patch("xiao.dashboard.server._get_vacuum", side_effect=RuntimeError("cloud down")):
            body = _client().post("/api/voice", json={"action": "dock"}).json()
        assert body == {"ok": False, "say": "No pude hablar con la aspiradora: cloud down"}

    def test_needs_the_token_from_the_network(self, rooms):
        response = _client(auth_token="s3cret", loopback_only=False).post("/api/voice", json={"action": "status"})
        assert response.status_code == 401


class TestLoopbackTokenExemption:
    def _request(self, client_host: str, host_header: str):
        from starlette.testclient import TestClient as StarletteClient

        client = StarletteClient(
            create_app(auth_token="s3cret", loopback_only=False),
            base_url=f"http://{host_header}",
            client=(client_host, 50000),
        )
        with patch("xiao.dashboard.server._get_vacuum") as get_vac:
            get_vac.return_value.status.return_value = {"state": "Charging"}
            return client.get("/api/status")

    def test_local_client_on_localhost_skips_the_token(self):
        assert self._request("127.0.0.1", "localhost:8120").status_code == 200

    def test_dns_rebinding_still_needs_the_token(self):
        assert self._request("127.0.0.1", "evil.example:8120").status_code == 401

    def test_lan_client_needs_the_token(self):
        assert self._request("192.168.1.20", "mac.local:8120").status_code == 401


class TestShortcutBuilder:
    def test_default_specs_cover_house_controls_and_each_room(self):
        names = [s.name for s in default_specs(ROOMS)]
        assert names[:5] == [
            "Aspiradora a toda la casa",
            "Aspiradora a la base",
            "Detén la aspiradora",
            "Aspiradora continúa",
            "Cómo está la aspiradora",
        ]
        assert "Aspiradora a la cocina" in names
        assert "Aspiradora al baño" in names
        assert "Aspiradora a la habitación principal" in names

    def test_room_shortcuts_send_the_room_id(self):
        spec = next(s for s in default_specs(ROOMS) if s.name == "Aspiradora a la cocina")
        assert spec.body == {"action": "clean", "room": "8", "lang": "es"}

    def test_overrides_and_zones(self):
        specs = default_specs(ROOMS, names={"8": "Limpia la cocina vieja"}, zones={"comedor": "0,0,10,10"})
        names = {s.name: s.body for s in specs}
        assert "Limpia la cocina vieja" in names
        assert names["Aspiradora al comedor"] == {"action": "clean", "zone": "0,0,10,10", "lang": "es"}

    def test_duplicate_names_are_rejected(self):
        with pytest.raises(ValueError, match="Two shortcuts"):
            default_specs({"7": "Cocina", "8": "cocina"})

    def test_workflow_posts_to_voice_with_headers_and_speaks_say(self):
        spec = default_specs(ROOMS)[0]
        wf = build_workflow(spec, "http://mac.local:8120/", "tok")
        fetch, get_value, show = wf["WFWorkflowActions"]
        params = fetch["WFWorkflowActionParameters"]
        assert params["WFURL"] == "http://mac.local:8120/api/voice"
        assert params["WFHTTPMethod"] == "POST"
        assert params["WFHTTPBodyType"] == "JSON"
        headers = {
            item["WFKey"]["Value"]["string"]: item["WFValue"]["Value"]["string"]
            for item in params["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"]
        }
        assert headers == {"X-Xiao-Client": "dashboard", "X-Xiao-Token": "tok"}
        assert get_value["WFWorkflowActionParameters"]["WFDictionaryKey"] == "say"
        assert get_value["WFWorkflowActionParameters"]["WFInput"]["Value"]["OutputUUID"] == params["UUID"]
        attachment = show["WFWorkflowActionParameters"]["Text"]["Value"]["attachmentsByRange"]["{0, 1}"]
        assert attachment["OutputUUID"] == get_value["WFWorkflowActionParameters"]["UUID"]

    def test_write_unsigned_files_are_private_binary_plists(self, tmp_path):
        files = write_shortcuts(default_specs({"8": "Cocina"}), tmp_path, "http://x:8120", "tok", sign=False)
        target = tmp_path / "Aspiradora a la cocina.shortcut"
        assert target in files
        assert target.stat().st_mode & 0o777 == 0o600
        assert plistlib.loads(target.read_bytes())["WFWorkflowActions"][0]["WFWorkflowActionIdentifier"] == (
            "is.workflow.actions.downloadurl"
        )


class TestVoiceWaterPause:
    def test_resume_confirms_the_refill(self, rooms):
        vac = MagicMock()
        vac.status.return_value = {"state": "WashingMopPause"}
        vac.start.return_value = {"code": 0, "resumed": True}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/voice", json={"action": "resume"}).json()
        vac.start.assert_called_once()
        assert body == {"ok": True, "say": "Listo, la aspiradora continúa la limpieza que había pausado."}

    def test_resume_does_not_start_a_full_clean_when_nothing_is_paused(self, rooms):
        vac = MagicMock()
        vac.status.return_value = {"state": "Charging Completed"}
        with patch("xiao.dashboard.server._get_vacuum", return_value=vac):
            body = _client().post("/api/voice", json={"action": "resume"}).json()
        vac.start.assert_not_called()
        assert body["ok"] is False

    def test_room_clean_during_the_water_pause_explains_what_to_do(self, rooms):
        from xiao.core.room_cleaning import WaitingForWaterError

        with (
            patch("xiao.dashboard.server._get_vacuum"),
            patch("xiao.dashboard.server.start_room_clean", side_effect=WaitingForWaterError("state 21")),
        ):
            body = _client().post("/api/voice", json={"room": "8"}).json()
        assert body["ok"] is False
        assert "Aspiradora continúa" in body["say"]

    def test_room_endpoint_answers_409_during_the_water_pause(self, rooms):
        from xiao.core.room_cleaning import WaitingForWaterError

        with (
            patch("xiao.dashboard.server._get_vacuum"),
            patch("xiao.dashboard.server.start_room_clean", side_effect=WaitingForWaterError("state 21")),
        ):
            response = _client().post("/api/clean/rooms", json={"room_ids": [8]})
        assert response.status_code == 409
