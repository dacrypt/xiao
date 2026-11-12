"""Build Apple Shortcuts (.shortcut files) that drive `xiao web` from Siri.

Siri only understands robot-vacuum commands for Matter devices in US English,
but it runs any shortcut by its name in any language. Each generated shortcut
is three actions:

  1. "Get Contents of URL": POST {url}/api/voice with the token headers and a
     flat JSON body ({"action", "room" | "zone", "lang"})
  2. "Get Dictionary Value": the response's "say"
  3. "Show Result": Siri speaks that sentence

The files are binary plists in the WFWorkflow format; iOS/macOS only import
them once signed (`shortcuts sign`, macOS only).
"""

from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ShortcutSpec:
    name: str  # what you say after "Oye Siri"; also the file name
    body: dict[str, str]  # JSON body for /api/voice


def _text(value: str) -> dict:
    return {"Value": {"string": value}, "WFSerializationType": "WFTextTokenString"}


def _dictionary(items: dict[str, str]) -> dict:
    return {
        "Value": {
            "WFDictionaryFieldValueItems": [
                {"WFItemType": 0, "WFKey": _text(key), "WFValue": _text(value)} for key, value in items.items()
            ]
        },
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def build_workflow(spec: ShortcutSpec, base_url: str, token: str | None) -> dict:
    """Return the WFWorkflow dictionary for one shortcut."""
    fetch_id, value_id = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    headers = {"X-Xiao-Client": "dashboard"}
    if token:
        headers["X-Xiao-Token"] = token
    actions = [
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
            "WFWorkflowActionParameters": {
                "UUID": fetch_id,
                "WFURL": base_url.rstrip("/") + "/api/voice",
                "WFHTTPMethod": "POST",
                "ShowHeaders": True,
                "WFHTTPHeaders": _dictionary(headers),
                "WFHTTPBodyType": "JSON",
                "WFJSONValues": _dictionary(spec.body),
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": value_id,
                "WFDictionaryKey": "say",
                "WFInput": {
                    "Value": {"OutputUUID": fetch_id, "Type": "ActionOutput", "OutputName": "Contents of URL"},
                    "WFSerializationType": "WFTextTokenAttachment",
                },
            },
        },
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.showresult",
            "WFWorkflowActionParameters": {
                "Text": {
                    "Value": {
                        "string": "￼",
                        "attachmentsByRange": {
                            "{0, 1}": {"OutputUUID": value_id, "Type": "ActionOutput", "OutputName": "Dictionary Value"}
                        },
                    },
                    "WFSerializationType": "WFTextTokenString",
                }
            },
        },
    ]
    return {
        "WFWorkflowClientVersion": "2302.0.4",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": [],
        "WFWorkflowInputContentItemClasses": [],
        "WFQuickActionSurfaces": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowActions": actions,
    }


def _with_article(room: str) -> str:
    """Spanish definite article for a room name: "la cocina", "el baño"."""
    first = room.split()[0].lower() if room.split() else ""
    feminine = first.endswith(("a", "ción", "sión", "dad")) and first not in {"día", "sofá", "mapa"}
    return f"{'la' if feminine else 'el'} {room.lower()}"


def _to_place(room: str) -> str:
    """ "a la cocina" / "al baño" (Spanish contracts "a el" to "al")."""
    with_article = _with_article(room)
    return "al " + with_article[3:] if with_article.startswith("el ") else "a " + with_article


def default_specs(
    rooms: dict[str, str],
    lang: str = "es",
    names: dict[str, str] | None = None,
    zones: dict[str, str] | None = None,
) -> list[ShortcutSpec]:
    """One shortcut per room and zone, plus house / dock / stop / status.

    Every name starts with "Aspiradora": Siri treats a phrase that mentions a Home
    room ("limpia la cocina") as a Home command for that room, such as its light,
    and never gets to the shortcut.
    """
    names = names or {}
    es = lang == "es"
    specs = [
        ShortcutSpec(
            "Aspiradora a toda la casa" if es else "Vacuum the whole house", {"action": "clean", "lang": lang}
        ),
        ShortcutSpec("Aspiradora a la base" if es else "Vacuum go home", {"action": "dock", "lang": lang}),
        ShortcutSpec("Detén la aspiradora" if es else "Stop the vacuum", {"action": "stop", "lang": lang}),
        ShortcutSpec("Cómo está la aspiradora" if es else "Vacuum status", {"action": "status", "lang": lang}),
    ]
    for room_id, alias in sorted(rooms.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 0):
        name = names.get(room_id) or (f"Aspiradora {_to_place(alias)}" if es else f"Vacuum the {alias}")
        specs.append(ShortcutSpec(name, {"action": "clean", "room": room_id, "lang": lang}))
    for zone_name, coords in (zones or {}).items():
        name = f"Aspiradora {_to_place(zone_name)}" if es else f"Vacuum the {zone_name}"
        specs.append(ShortcutSpec(name, {"action": "clean", "zone": coords, "lang": lang}))
    seen: set[str] = set()
    for spec in specs:
        key = spec.name.casefold()
        if key in seen:
            raise ValueError(f'Two shortcuts would be called "{spec.name}"; rename one with --name')
        seen.add(key)
    return specs


def _safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip() or "xiao"


def write_shortcuts(
    specs: list[ShortcutSpec], out_dir: Path, base_url: str, token: str | None, sign: bool = True
) -> list[Path]:
    """Write one .shortcut per spec (signed with `shortcuts sign --mode anyone` when possible)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    signer = shutil.which("shortcuts") if sign else None
    if sign and not signer:
        raise RuntimeError("Signing needs macOS's `shortcuts` command; rerun with --no-sign to write unsigned files.")
    written = []
    for spec in specs:
        target = out_dir / f"{_safe_filename(spec.name)}.shortcut"
        data = plistlib.dumps(build_workflow(spec, base_url, token), fmt=plistlib.FMT_BINARY)
        if signer:
            unsigned = out_dir / f".{target.stem}.unsigned.shortcut"
            unsigned.write_bytes(data)
            try:
                subprocess.run(
                    [signer, "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(target)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            finally:
                unsigned.unlink(missing_ok=True)
        else:
            target.write_bytes(data)
        target.chmod(0o600)  # contains the access token
        written.append(target)
    return written
