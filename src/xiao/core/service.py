"""Build the vacuum service from the saved configuration.

Shared by the CLI, the web dashboard and the MCP server so all three log in,
reuse cached sessions and refresh tokens the same way. Failures are raised as
:class:`XiaoError` subclasses (never ``SystemExit``) so long-running servers
can turn them into HTTP / tool errors; the CLI maps them to exit codes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from xiao.core import config
from xiao.core.exit_codes import EXIT_GENERIC, EXIT_NOT_CONFIGURED, EXIT_TOKEN_EXPIRED

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class XiaoError(Exception):
    """Base error carrying the CLI exit code that represents it."""

    exit_code = EXIT_GENERIC


class NotConfiguredError(XiaoError):
    exit_code = EXIT_NOT_CONFIGURED


class CloudAuthError(XiaoError):
    exit_code = EXIT_TOKEN_EXPIRED


def _noop(_msg: str) -> None:
    return None


def build_cloud_vacuum(notify: Callable[[str], Any] | None = None):
    """Return a logged-in ``CloudVacuumService``.

    Order: cached session → silent browser-profile token refresh → full login
    (captcha / email 2FA). ``notify`` receives human-readable progress lines;
    callers decide where they go (the CLI sends them to stderr so ``--json``
    output and the MCP stdio stream stay clean).
    """
    from xiao.core.cloud import XiaomiCloud
    from xiao.core.cloud_vacuum import CloudVacuumService

    say = notify or _noop
    cloud_cfg = config.get_cloud_config()
    username = cloud_cfg.get("username", "")
    password = cloud_cfg.get("password", "")
    server = cloud_cfg.get("server", "us")
    did = cloud_cfg.get("did", "")
    model = cloud_cfg.get("model", "")

    if not username or not did:
        raise NotConfiguredError("Cloud mode enabled but not configured. Run `xiao setup cloud`.")

    session_data = config.get_cloud_session()
    if session_data:
        cloud = XiaomiCloud.from_session(username, password, session_data)
    else:
        from xiao.core.token_refresh import refresh_tokens

        say("No saved session. Refreshing tokens via the browser profile...")
        tokens = refresh_tokens(username, password)
        if tokens:
            config.save_cloud_session(tokens["userId"], tokens["serviceToken"], tokens["ssecurity"])
            cloud = XiaomiCloud.from_session(
                username,
                password,
                {
                    "user_id": tokens["userId"],
                    "service_token": tokens["serviceToken"],
                    "ssecurity": tokens["ssecurity"],
                },
            )
            say("Tokens refreshed via browser.")
        else:
            say("Browser refresh failed. Trying full login...")
            cloud = XiaomiCloud(username, password, on_status=say)
            try:
                ok = cloud.login()
            except Exception as e:
                raise CloudAuthError(f"Cloud login failed: {e}") from e
            if not ok:
                raise CloudAuthError("Cloud login failed. Run `xiao setup browser-login` or `xiao cloud-login`.")
            config.save_cloud_session(cloud.user_id, cloud.service_token, cloud.ssecurity)
            say("Logged in and session saved.")

    return CloudVacuumService(cloud, did=did, model=model, country=server)


def build_vacuum(notify: Callable[[str], Any] | None = None):
    """Return the configured vacuum service (cloud or local miIO)."""
    if config.is_cloud_mode():
        return build_cloud_vacuum(notify)

    from xiao.core.vacuum import get_vacuum

    device = config.load().get("device", {})
    ip, token = device.get("ip"), device.get("token")
    if not ip or not token:
        raise NotConfiguredError("No device configured. Run `xiao setup cloud` (or `xiao setup init` for local mode).")
    return get_vacuum(ip, token, device.get("model") or "", config.get_protocol())
