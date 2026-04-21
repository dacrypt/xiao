"""Token refresh via a self-managed Chromium profile.

Uses Playwright's `launch_persistent_context` so xiao owns a Chromium profile
under the user's config dir (`~/Library/Application Support/xiao/chromium` on
macOS, `~/.config/xiao/chromium` on Linux). No external browser required.

First-time flow: the user runs `xiao setup browser-login`, which launches a
headed Chromium pointed at account.xiaomi.com. They log in once, close the
window, and the session cookies stick in the profile.

Subsequent token refreshes (`xiao` cloud commands) launch the same profile
headless, hit the serviceLogin/serviceLoginAuth2 endpoints using the stored
cookies, and return fresh ssecurity + serviceToken — no captcha/2FA.

Power-user opt-in: set `XIAO_CDP_PORT=18800` to reuse an already-running
Chromium exposed over CDP instead. Useful when you already maintain such a
session for other tooling.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time

from xiao.core.config import CONFIG_DIR

logger = logging.getLogger(__name__)

PROFILE_DIR = CONFIG_DIR / "chromium"
LOGIN_LANDING = "https://account.xiaomi.com/pass/login"
LOGIN_SUCCESS_HOSTS = ("home.mi.com", "i.mi.com", "account.xiaomi.com/success")


def _ensure_profile_dir() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _do_refresh_flow(page, username: str, password: str) -> dict[str, str] | None:
    """Run the 3-step serviceLogin flow on an already-navigated page."""
    page.goto(
        "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
        wait_until="domcontentloaded",
    )
    time.sleep(1)
    body = page.inner_text("body")
    data1 = json.loads(body.replace("&&&START&&&", ""))

    if data1.get("code") != 0:
        logger.info("serviceLogin code=%s — profile has no active session", data1.get("code"))
        return None

    sign = data1.get("_sign", "")
    pwd_hash = hashlib.md5(password.encode()).hexdigest().upper()

    page.evaluate(
        f"""() => {{
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = 'https://account.xiaomi.com/pass/serviceLoginAuth2';
        const fields = {{
            sid: 'xiaomiio',
            hash: '{pwd_hash}',
            callback: 'https://sts.api.io.mi.com/sts',
            qs: '%3Fsid%3Dxiaomiio%26_json%3Dtrue',
            user: '{username}',
            _sign: '{sign}',
            _json: 'true'
        }};
        for (const [k,v] of Object.entries(fields)) {{
            const i = document.createElement('input');
            i.type = 'hidden'; i.name = k; i.value = v;
            form.appendChild(i);
        }}
        document.body.appendChild(form);
        form.submit();
    }}"""
    )
    time.sleep(3)

    body2 = page.inner_text("body")
    data2 = json.loads(body2.replace("&&&START&&&", ""))

    ssecurity = data2.get("ssecurity", "")
    location = data2.get("location", "")
    user_id = str(data2.get("userId", ""))

    if not ssecurity or not location:
        logger.error("serviceLoginAuth2 failed: code=%s", data2.get("code"))
        return None

    page.goto(location, wait_until="domcontentloaded")
    time.sleep(2)

    cookies_str = page.evaluate("() => document.cookie")
    cookies = dict(c.strip().split("=", 1) for c in cookies_str.split(";") if "=" in c)
    service_token = cookies.get("serviceToken", "")

    if not service_token:
        logger.error("No serviceToken in cookies after redirect")
        return None

    return {"userId": user_id, "serviceToken": service_token, "ssecurity": ssecurity}


def _refresh_via_cdp(port: int, username: str, password: str) -> dict[str, str] | None:
    """Opt-in path: reuse an existing Chromium over CDP (XIAO_CDP_PORT)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed")
        return None

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=5000)
            except Exception as e:
                logger.info("CDP port %d unreachable: %s", port, e)
                return None
            contexts = browser.contexts
            if not contexts:
                return None
            context = contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            result = _do_refresh_flow(page, username, password)
            browser.close()
            return result
    except Exception as e:
        logger.error("CDP refresh failed: %s", e)
        return None


def _refresh_via_persistent(username: str, password: str) -> dict[str, str] | None:
    """Default path: xiao's own persistent Chromium profile, headless."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed — run `playwright install chromium`")
        return None

    _ensure_profile_dir()
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=True,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                return _do_refresh_flow(page, username, password)
            finally:
                context.close()
    except Exception as e:
        logger.error("Persistent-context refresh failed: %s", e)
        return None


def refresh_tokens(username: str, password: str) -> dict[str, str] | None:
    """Refresh Xiaomi Cloud tokens using the persistent Chromium profile.

    Returns {userId, serviceToken, ssecurity} on success, None on failure.
    On first run (empty profile), returns None; the caller should run
    `seed_browser_session()` or `xiao setup browser-login` to populate the
    profile, then retry.
    """
    cdp_port_env = os.environ.get("XIAO_CDP_PORT", "").strip()
    if cdp_port_env.isdigit():
        via_cdp = _refresh_via_cdp(int(cdp_port_env), username, password)
        if via_cdp:
            return via_cdp
    return _refresh_via_persistent(username, password)


def seed_browser_session() -> bool:
    """Launch a headed Chromium against the login page and wait for the user
    to finish logging in. Stores cookies in `PROFILE_DIR` so future token
    refreshes can run headless.

    Returns True once the user lands on a logged-in host (home.mi.com,
    i.mi.com, or account.xiaomi.com/success) or closes the window manually.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed — run `playwright install chromium`")
        return False

    _ensure_profile_dir()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(LOGIN_LANDING, wait_until="domcontentloaded")

        logged_in = False
        try:
            # Poll the URL every second; exit on success redirect or window close.
            while True:
                try:
                    url = page.url
                except Exception:
                    break  # window closed
                if any(h in url for h in LOGIN_SUCCESS_HOSTS) and "/pass/login" not in url:
                    logged_in = True
                    break
                time.sleep(1)
        finally:
            context.close()
    return logged_in
