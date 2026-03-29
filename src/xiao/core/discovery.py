"""Local network device discovery."""

from __future__ import annotations

import contextlib


def discover_devices(timeout: int = 5) -> list[dict]:
    """Discover MiIO/MIoT devices on the local network."""
    from miio import Discovery

    devices = []
    for addr, info in Discovery.discover_mdns(timeout=timeout).items():
        devices.append({"ip": addr, "info": info})
    return devices


def discover_miio(timeout: int = 5) -> list[dict]:
    """Discover devices using miIO handshake."""
    from miio import Discovery

    found = {}
    with contextlib.suppress(Exception):
        found = Discovery.discover_mdns(timeout=timeout)
    return [{"ip": addr, "info": str(info)} for addr, info in found.items()]
