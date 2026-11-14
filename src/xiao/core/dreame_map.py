"""Read the room list (segment IDs and names) from a Dreame-built map.

The X20+ is Dreame-built. Its map is not readable as a MIoT property; the robot
pushes the map's object name to the cloud's property history (siid 6, piid 3) as
``"<uid>/<did>/<n>,<key>"``. The file behind ``get_interim_file_url`` is URL-safe
base64 of AES-256-CBC(zlib(frame)), where the AES key is
``sha256(<key>).hexdigest()[:32]`` and the IV is a per-model constant.

A frame is a 27-byte header, a ``width x height`` pixel grid, then a JSON
trailer. The rooms live in the saved map (``rism``, itself an encoded frame),
under ``seg_inf``: ``{"<segment id>": {"name": base64(utf-8 name), ...}}``.
Unnamed segments have no ``name``; the Mi Home app shows them as "Room N".

Format and per-model IVs from Tasshack/dreame-vacuum (MIT).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import struct
import zlib
from typing import Any

HEADER_SIZE = 27

# Per-model AES IVs for encrypted map frames (Tasshack/dreame-vacuum device table).
MAP_IVS: dict[str, str] = {
    "xiaomi.vacuum.c102gl": "OFULk9To37qRdXY3",
}


class MapDecodeError(ValueError):
    """The map payload could not be decrypted or parsed."""


def _b64decode(text: str) -> bytes:
    text = text.strip().replace("_", "/").replace("-", "+")
    return base64.b64decode(text + "=" * (-len(text) % 4))


def _decrypt(data: bytes, key: str, iv: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    aes_key = hashlib.sha256(key.encode()).hexdigest()[:32].encode()
    decryptor = Cipher(algorithms.AES(aes_key), modes.CBC(iv.encode())).decryptor()
    return decryptor.update(data) + decryptor.finalize()


def decode_frame(text: str, key: str | None = None, iv: str | None = None) -> dict[str, Any]:
    """Decode one map frame (``base64[,key]``) and return its JSON trailer."""
    if "," in text and key is None:
        text, key = text.split(",", 1)
    try:
        data = _b64decode(text)
    except (binascii.Error, ValueError) as e:
        raise MapDecodeError(f"map is not base64: {e}") from e
    try:
        raw = zlib.decompress(data)
    except zlib.error:
        if not (key and iv):
            raise MapDecodeError("map frame is encrypted and no key/IV is known for this model") from None
        try:
            raw = zlib.decompress(_decrypt(data, key, iv))
        except (zlib.error, ValueError) as e:
            raise MapDecodeError(f"could not decrypt the map frame: {e}") from e
    if len(raw) < HEADER_SIZE:
        raise MapDecodeError("map frame is shorter than its header")
    width, height = struct.unpack_from("<HH", raw, 19)
    trailer = raw[HEADER_SIZE + width * height :]
    try:
        payload = json.loads(trailer.decode("utf-8")) if trailer else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise MapDecodeError(f"map trailer is not JSON: {e}") from e
    return payload if isinstance(payload, dict) else {}


def _decode_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8").strip() or None
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return value.strip() or None


def rooms_from_trailer(trailer: dict[str, Any], key: str | None = None, iv: str | None = None) -> list[dict[str, Any]]:
    """``[{"id": int, "name": str | None}]`` from a frame trailer (or its saved map)."""
    segments = trailer.get("seg_inf")
    if not segments and isinstance(trailer.get("rism"), str):
        segments = decode_frame(trailer["rism"], key=key, iv=iv).get("seg_inf")
    rooms = []
    for segment_id, info in (segments or {}).items():
        try:
            room_id = int(segment_id)
        except (TypeError, ValueError):
            continue
        name = _decode_name(info.get("name")) if isinstance(info, dict) else None
        rooms.append({"id": room_id, "name": name})
    return sorted(rooms, key=lambda room: room["id"])


def rooms_from_map_file(text: str, key: str | None, model: str) -> list[dict[str, Any]]:
    """Decode a downloaded map file and return its rooms."""
    iv = MAP_IVS.get(model)
    trailer = decode_frame(text, key=key, iv=iv)
    return rooms_from_trailer(trailer, key=key, iv=iv)
