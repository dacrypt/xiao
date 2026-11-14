"""Decoding room segments from the X20+ (Dreame) map."""

import base64
import hashlib
import json
import struct
import zlib
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from xiao.core.dreame_map import MAP_IVS, MapDecodeError, decode_frame, rooms_from_map_file
from xiao.core.room_cleaning import known_rooms

IV = MAP_IVS["xiaomi.vacuum.c102gl"]


def _frame(trailer: dict, width: int = 3, height: int = 2) -> bytes:
    header = bytearray(27)
    struct.pack_into("<HH", header, 19, width, height)
    return bytes(header) + bytes(width * height) + json.dumps(trailer).encode()


def _encode(raw: bytes, key: str | None = None) -> str:
    data = zlib.compress(raw)
    if key:
        padder = padding.PKCS7(128).padder()
        data = padder.update(data) + padder.finalize()
        aes_key = hashlib.sha256(key.encode()).hexdigest()[:32].encode()
        encryptor = Cipher(algorithms.AES(aes_key), modes.CBC(IV.encode())).encryptor()
        data = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(data).decode().replace("/", "_").replace("+", "-").rstrip("=")


def _name(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


SAVED_MAP = {
    "seg_inf": {"3": {"name": _name("Cocina"), "type": 0}, "10": {"name": _name("Sala")}, "5": {"nei_id": [8]}}
}


def test_reads_room_names_from_the_encrypted_map_and_its_saved_map():
    outer = _frame({"timestamp_ms": 1, "rism": _encode(_frame(SAVED_MAP))})
    rooms = rooms_from_map_file(_encode(outer, key="f4LEkey"), "f4LEkey", "xiaomi.vacuum.c102gl")
    assert rooms == [{"id": 3, "name": "Cocina"}, {"id": 5, "name": None}, {"id": 10, "name": "Sala"}]


def test_reads_seg_inf_directly_when_present():
    assert decode_frame(_encode(_frame(SAVED_MAP)))["seg_inf"]["10"]["name"] == _name("Sala")


def test_encrypted_map_without_a_known_iv_fails_clearly():
    with pytest.raises(MapDecodeError, match="encrypted"):
        rooms_from_map_file(_encode(_frame(SAVED_MAP), key="k"), "k", "xiaomi.vacuum.unknown")


def test_garbage_is_a_decode_error():
    with pytest.raises(MapDecodeError):
        decode_frame("%%%not-base64%%%")


class TestKnownRoomsAgainstTheMap:
    def _vac(self, rooms):
        vac = MagicMock()
        vac.rooms.return_value = rooms
        vac.schedules_parsed.return_value = [{"room_ids": [3, 99]}]
        return vac

    def test_map_names_are_used_and_contradicting_aliases_are_flagged(self):
        vac = self._vac([{"id": 3, "name": "Cocina"}, {"id": 10, "name": "Sala"}, {"id": 5, "name": None}])
        rooms = {r["id"]: r for r in known_rooms(vac, {"3": "Sala", "10": "sala"})}
        assert rooms[3]["name"] == "Sala"  # an alias still wins…
        assert rooms[3]["alias_differs"] is True  # …but is flagged
        assert rooms[10]["alias_differs"] is False  # same name, different case
        assert rooms[5]["name"] == "Room 5"
        assert rooms[5]["map_name"] is None

    def test_ids_missing_from_the_map_are_marked(self):
        rooms = {r["id"]: r for r in known_rooms(self._vac([{"id": 3, "name": "Cocina"}]), {})}
        assert rooms[3]["on_map"] is True
        assert rooms[99]["on_map"] is False

    def test_without_a_map_nothing_is_flagged(self):
        rooms = known_rooms(self._vac([]), {"3": "Sala"})
        assert all("on_map" not in r and "alias_differs" not in r for r in rooms)
