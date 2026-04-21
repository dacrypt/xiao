"""Canonical exit codes for the xiao CLI.

Agents and scripts can use these to dispatch retries without parsing stderr.
Any code not listed here implies a generic failure (exit 1).
"""

from __future__ import annotations

EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_NOT_CONFIGURED = 2  # config.toml missing or incomplete — run `xiao setup cloud`
EXIT_TOKEN_EXPIRED = 77  # cloud auth refresh failed — run `xiao cloud-login`
EXIT_CDP_UNREACHABLE = 78  # Chromium on port 18800 not reachable
EXIT_STATE_21 = 79  # vacuum paused on water-tank alert — refill tanks, `xiao start`
EXIT_VACUUM_UNRESPONSIVE = 80  # command accepted (code 0) but robot didn't move
