"""Token refresh via a persistent Chromium browser over CDP.

Reuses an existing logged-in Xiaomi session in a Chromium-based browser
(launched with --remote-debugging-port=18800) to obtain fresh ssecurity +
serviceToken WITHOUT email verification or captcha.

Requires: a Chromium/Chrome instance listening on port 18800 with an
active Xiaomi account session (httpOnly cookies).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time

logger = logging.getLogger(__name__)

CDP_PORT = 18800


def refresh_tokens(username: str, password: str) -> dict[str, str] | None:
    """Refresh Xiaomi Cloud tokens using the persistent Chromium session.

    Returns dict with userId, serviceToken, ssecurity on success, None on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed")
        return None

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}", timeout=5000)
            except Exception as e:
                logger.error("Cannot connect to browser CDP on port %d: %s", CDP_PORT, e)
                return None
            contexts = browser.contexts
            if not contexts:
                logger.error("No browser contexts found")
                return None

            context = contexts[0]
            page = context.pages[0] if context.pages else context.new_page()

            # Step 1: serviceLogin (GET) — uses httpOnly cookies, no verification
            logger.info("Step 1: Getting sign from serviceLogin...")
            page.goto(
                "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
                wait_until="domcontentloaded",
            )
            time.sleep(1)
            body = page.inner_text("body")
            data1 = json.loads(body.replace("&&&START&&&", ""))

            if data1.get("code") != 0:
                logger.error("serviceLogin failed: code=%s", data1.get("code"))
                return None

            sign = data1.get("_sign", "")

            # Step 2: serviceLoginAuth2 (POST via form navigation)
            # Form submit sends httpOnly cookies — XHR/fetch do NOT
            logger.info("Step 2: Getting ssecurity via form POST...")
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
                logger.error(
                    "serviceLoginAuth2 failed: code=%s ssecurity=%s",
                    data2.get("code"),
                    bool(ssecurity),
                )
                return None

            # Step 3: Follow location to get serviceToken
            logger.info("Step 3: Following location for serviceToken...")
            page.goto(location, wait_until="domcontentloaded")
            time.sleep(2)

            cookies_str = page.evaluate("() => document.cookie")
            cookies = {}
            for c in cookies_str.split(";"):
                parts = c.strip().split("=", 1)
                if len(parts) == 2:
                    cookies[parts[0]] = parts[1]

            service_token = cookies.get("serviceToken", "")

            browser.close()

            if not service_token:
                logger.error("No serviceToken in cookies after redirect")
                return None

            logger.info("Token refresh successful!")
            return {
                "userId": user_id,
                "serviceToken": service_token,
                "ssecurity": ssecurity,
            }

    except Exception as e:
        logger.error("Token refresh failed: %s", e)
        return None
