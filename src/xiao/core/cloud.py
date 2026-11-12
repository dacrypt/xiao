"""Xiaomi cloud client with captcha & email verification (2FA) support.

Uses Playwright browser automation to handle:
- Image captcha on login
- Email verification (identity check)
Then extracts cookies to make signed API calls via micloud utils.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

import requests as req_lib
from micloud.miutils import (
    decrypt_rc4,
    gen_nonce,
    generate_enc_params,
    get_random_agent_id,
    get_random_string,
    signed_nonce,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email verification code reader (via gog CLI)
# ---------------------------------------------------------------------------


# One alternation so matches come back in document order (latest code last).
_CODE_RE = re.compile(r"(?:verification code is:?|code:|验证码[：:])\s*(\d{6})", re.IGNORECASE)


def _extract_code_from_text(body: str) -> str | None:
    """Return the most recent 6-digit Xiaomi verification code in ``body``.

    Only explicit "verification code" phrasings are accepted: a bare 6-digit
    number could be anything (an order id, a date) and submitting it burns
    one of Xiaomi's limited verification attempts.
    """
    codes = _CODE_RE.findall(body)
    return codes[-1] if codes else None


def _read_code_via_gog(max_wait: int, poll_interval: int, after_ts: float) -> str | None:
    """Poll Gmail through the optional `gog` CLI for a Xiaomi verification code.

    Only emails received after ``after_ts`` (Unix seconds) are searched, so a
    stale code from an earlier login attempt is never reused.
    """
    query = f"xiaomi verification after:{int(after_ts)}"
    deadline = time.time() + max_wait

    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["gog", "gmail", "search", query, "--limit", "3", "--json"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                threads = data.get("threads", data) if isinstance(data, dict) else data
                if threads:
                    # Threads are newest-first.
                    thread = threads[0] if isinstance(threads, list) else threads
                    thread_id = thread.get("id") or thread.get("ID") or ""
                    read_result = subprocess.run(
                        ["gog", "gmail", "read", str(thread_id)],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    if read_result.returncode == 0:
                        code = _extract_code_from_text(read_result.stdout)
                        if code:
                            logger.info("Found Xiaomi verification code in Gmail")
                            return code
            else:
                logger.debug("gog search failed: %s", result.stderr)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            logger.debug("Error reading verification email: %s", e)

        logger.info("Waiting for verification email... %ds remaining", int(deadline - time.time()))
        time.sleep(poll_interval)

    return None


def _prompt_for_code() -> str | None:
    """Ask the human for the emailed code (interactive terminals only)."""
    if not sys.stdin.isatty():
        return None
    try:
        sys.stderr.write("Enter the 6-digit verification code Xiaomi emailed you: ")
        sys.stderr.flush()
        code = sys.stdin.readline().strip()
    except (OSError, KeyboardInterrupt):
        return None
    return code if re.fullmatch(r"\d{4,8}", code) else None


def _read_verification_code(max_wait: int = 120, poll_interval: int = 8, after_ts: float | None = None) -> str | None:
    """Obtain the Xiaomi email verification code.

    Uses the optional `gog` Gmail CLI when it is installed (fully automatic),
    otherwise falls back to prompting on an interactive terminal. Returns None
    when neither is possible.
    """
    if after_ts is None:
        after_ts = time.time() - 300  # last 5 minutes

    if shutil.which("gog"):
        code = _read_code_via_gog(max_wait, poll_interval, after_ts)
        if code:
            return code
        logger.info("No code found via gog; falling back to manual entry")
    return _prompt_for_code()


def _debug_screenshot(page, name: str) -> str | None:
    """Save a login screenshot only when XIAO_DEBUG=1.

    Screenshots of the Xiaomi login flow can show account details, so they go
    to a private (0700) directory under the config dir — never a predictable,
    world-readable path in /tmp.
    """
    if os.environ.get("XIAO_DEBUG") != "1":
        return None
    try:
        from xiao.core.config import CONFIG_DIR, PRIVATE_DIR_MODE

        debug_dir = CONFIG_DIR / "debug"
        debug_dir.mkdir(mode=PRIVATE_DIR_MODE, parents=True, exist_ok=True)
        path = debug_dir / f"{name}.png"
        page.screenshot(path=str(path))
        os.chmod(path, 0o600)
        return str(path)
    except Exception as e:
        logger.debug("Could not save debug screenshot: %s", e)
        return None


# ---------------------------------------------------------------------------
# Playwright-based full login flow
# ---------------------------------------------------------------------------


def _playwright_login(
    username: str,
    password: str,
    on_status: Callable[[str], Any] | None = None,
) -> dict[str, str]:
    """Complete Xiaomi login via Playwright, handling Terms dialog & email 2FA.

    Observed flow:
    1. Login page → fill credentials → click "Sign in"
    2. "User Agreement" modal → click "Agree"
    3. Redirects to verifyEmail page → click "Send" → wait for code → enter code → click "Next"
    4. Redirects to STS → serviceToken in cookies

    Returns dict with: userId, serviceToken, ssecurity (if available)
    """
    from playwright.sync_api import sync_playwright

    def status(msg: str):
        logger.info(msg)
        if on_status:
            on_status(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 11; ONEPLUS A3010) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
        )
        page = context.new_page()

        # ── Step 1: Navigate to login ──────────────────────────────────────
        status("Opening Xiaomi login page...")
        page.goto(
            "https://account.xiaomi.com/fe/service/login/password"
            "?sid=xiaomiio&callback=https%3A%2F%2Fsts.api.io.mi.com%2Fsts&_locale=en",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(3)

        # ── Step 2: Fill credentials ───────────────────────────────────────
        status("Entering credentials...")
        page.locator('input[name="account"]').fill(username)
        time.sleep(0.5)
        page.locator('input[name="password"]').fill(password)
        time.sleep(0.5)

        # Check terms checkbox if unchecked
        try:
            cb = page.locator('input[type="checkbox"]').first
            if cb.is_visible(timeout=2000) and not cb.is_checked():
                cb.click()
                time.sleep(0.3)
                status("Checked terms checkbox")
        except Exception:
            pass

        # ── Step 3: Submit ─────────────────────────────────────────────────
        status("Submitting login...")
        page.locator('button[type="submit"]').first.click()
        time.sleep(8)

        # ── Step 4: Handle "User Agreement" modal ─────────────────────────
        try:
            agree = page.locator('button:has-text("Agree")').first
            if agree.is_visible(timeout=3000):
                agree.click()
                status("Agreed to User Agreement modal")
                time.sleep(6)
        except Exception:
            pass

        current_url = page.url
        status(f"URL after login: {current_url[:100]}")

        # ── Step 5: Handle email verification (verifyEmail) ───────────────
        for _attempt in range(3):
            current_url = page.url

            if "verifyEmail" in current_url or "identity" in current_url:
                status("Email verification required, sending code...")
                # Click "Send" button
                try:
                    send = page.locator('button:has-text("Send")').first
                    if send.is_visible(timeout=5000):
                        send.click()
                        status("Clicked Send — waiting for email...")
                        time.sleep(5)
                except Exception as e:
                    status(f"Send button not found: {e}")

                # Read code from Gmail
                send_ts = time.time()
                code = _read_verification_code(max_wait=120, poll_interval=8, after_ts=send_ts - 60)
                if not code:
                    raise RuntimeError(
                        "No verification code available. Install the `gog` Gmail CLI for automatic "
                        "retrieval, or run `xiao cloud-login` from an interactive terminal to type it in."
                    )

                status("Got verification code")

                # Find the text input for the code
                code_input = None
                for sel in [
                    'input[type="text"]',
                    'input[type="number"]',
                    'input[type="tel"]',
                    'input[placeholder*="code"]',
                    'input[placeholder*="验证"]',
                ]:
                    try:
                        inp = page.locator(sel).first
                        if inp.is_visible(timeout=2000):
                            code_input = inp
                            break
                    except Exception:
                        continue

                if code_input is None:
                    # Try all visible inputs
                    inputs = page.locator("input:visible").all()
                    if inputs:
                        code_input = inputs[0]

                if code_input:
                    code_input.fill(code)
                    status("Entered verification code")
                    time.sleep(0.5)
                else:
                    status("WARNING: could not find code input field")
                    _debug_screenshot(page, "login_no_code_input")

                # Click submit button
                for submit_text in ["Next", "Verify", "Submit", "OK", "Confirm", "下一步", "确认"]:
                    try:
                        btn = page.locator(f'button:has-text("{submit_text}")').first
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            status(f"Clicked '{submit_text}'")
                            break
                    except Exception:
                        continue

                time.sleep(8)

            elif "sts.api.io.mi.com" in current_url:
                status("Reached STS endpoint — login successful!")
                break
            elif "/login" not in current_url:
                # Some other redirect — might have succeeded
                status(f"Redirected to: {current_url[:80]}")
                time.sleep(3)
                break
            else:
                time.sleep(3)

        # ── Step 6: Extract credentials ───────────────────────────────────
        final_shot = _debug_screenshot(page, "login_final")
        all_cookies = context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in all_cookies}

        status(f"Final URL: {page.url[:80]}")
        logger.debug("Cookies present: %s", list(cookie_dict.keys()))

        result = {
            "userId": cookie_dict.get("userId", ""),
            "serviceToken": cookie_dict.get("serviceToken", ""),
            "cUserId": cookie_dict.get("cUserId", ""),
            "ssecurity": cookie_dict.get("ssecurity", ""),
        }

        # ssecurity might be in page content
        if not result["ssecurity"]:
            page_content = page.content()
            m = re.search(r'"ssecurity"\s*:\s*"([^"]+)"', page_content)
            if m:
                result["ssecurity"] = m.group(1)

        browser.close()

        if not result.get("serviceToken"):
            raise RuntimeError(
                f"Login completed but no serviceToken found in cookies. "
                f"Present cookies: {list(cookie_dict.keys())}. "
                + (f"Debug screenshot: {final_shot}" if final_shot else "Re-run with XIAO_DEBUG=1 for a screenshot.")
            )

        return result


# ---------------------------------------------------------------------------
# Hybrid approach: API login with Playwright fallback for captcha
# ---------------------------------------------------------------------------


def _make_session() -> req_lib.Session:
    agent_id = get_random_agent_id()
    client_id = get_random_string(6)
    useragent = "Android-7.1.1-1.0.0-ONEPLUS A3010-136-" + agent_id + " APP/xiaomi.smarthome APPV/62830"
    session = req_lib.Session()
    session.headers.update({"User-Agent": useragent})
    session.cookies.update({"sdkVersion": "3.8.6", "deviceId": client_id})
    return session


class XiaomiCloud:
    """Xiaomi Cloud client with captcha + email verification support."""

    def __init__(self, username: str, password: str, on_status: Callable[[str], Any] | None = None):
        self.username = username
        self.password = password
        self.on_status = on_status
        self.user_id: str | None = None
        self.service_token: str | None = None
        self.ssecurity: str | None = None
        self.session = _make_session()

    @classmethod
    def from_session(
        cls,
        username: str,
        password: str,
        session: dict[str, str],
        on_status: Callable[[str], Any] | None = None,
    ) -> XiaomiCloud:
        """Rebuild a logged-in client from a saved ``{user_id, service_token, ssecurity}`` session."""
        cloud = cls(username, password, on_status=on_status)
        cloud.user_id = session.get("user_id") or None
        cloud.service_token = session.get("service_token") or None
        cloud.ssecurity = session.get("ssecurity") or None
        return cloud

    def _status(self, msg: str):
        logger.info(msg)
        if self.on_status:
            self.on_status(msg)

    def login(self) -> bool:
        """Login with API first, fall back to Playwright for captcha/2FA."""
        # Try API login first
        self._status("Attempting API login...")
        api_result = self._try_api_login()

        if api_result == "success":
            return True
        elif api_result == "captcha":
            self._status("Captcha required — switching to browser login...")
            return self._browser_login()
        elif api_result == "verification":
            self._status("Email verification required — switching to browser login...")
            return self._browser_login()
        else:
            self._status(f"API login failed ({api_result}), trying browser login...")
            return self._browser_login()

    def _try_api_login(self) -> str:
        """Attempt pure API login. Returns: 'success', 'captcha', 'verification', or error string."""
        try:
            # Step 1
            url = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
            self.session.cookies.update({"userId": self.username})
            resp = self.session.get(url)
            data = json.loads(resp.text.replace("&&&START&&&", ""))
            sign = data.get("_sign", "")

            # Step 2
            post_data = {
                "sid": "xiaomiio",
                "hash": hashlib.md5(self.password.encode()).hexdigest().upper(),
                "callback": "https://sts.api.io.mi.com/sts",
                "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
                "user": self.username,
                "_json": "true",
            }
            if sign:
                post_data["_sign"] = sign

            resp = self.session.post(
                "https://account.xiaomi.com/pass/serviceLoginAuth2",
                data=post_data,
            )
            auth = json.loads(resp.text.replace("&&&START&&&", ""))
            code = auth.get("code", -1)

            if code == 87001 or auth.get("captchaUrl"):
                return "captcha"

            if auth.get("notificationUrl"):
                self.user_id = str(auth.get("userId", ""))
                self.ssecurity = auth.get("ssecurity", "")
                return "verification"

            location = auth.get("location", "")
            if not location:
                return f"no_location_code_{code}"

            self.user_id = str(auth.get("userId", ""))
            self.ssecurity = auth.get("ssecurity", "")

            # Step 3
            resp = self.session.get(location)
            if resp.status_code == 403:
                return "access_denied_step3"

            st = resp.cookies.get("serviceToken")
            if st:
                self.service_token = st
                return "success"

            return "no_service_token"
        except Exception as e:
            return str(e)

    def _browser_login(self) -> bool:
        """Full browser-based login with captcha + 2FA handling."""
        from xiao.core.token_refresh import run_outside_event_loop

        creds = run_outside_event_loop(_playwright_login, self.username, self.password, self.on_status)
        self.user_id = creds.get("userId", "")
        self.service_token = creds.get("serviceToken", "")
        self.ssecurity = creds.get("ssecurity", "")

        # If we don't have ssecurity, we need it for API calls.
        # Try to get it by re-doing a quick API login with the existing session cookies
        if not self.ssecurity and self.service_token:
            self._status("Have serviceToken but need ssecurity, attempting API extraction...")
            self._extract_ssecurity()

        return bool(self.service_token)

    def _extract_ssecurity(self):
        """Try to extract ssecurity via API using existing session cookies."""
        try:
            session = _make_session()
            session.cookies.update({"userId": self.username})
            url = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
            resp = session.get(url)
            data = json.loads(resp.text.replace("&&&START&&&", ""))

            # If we have a valid session, _sign might redirect us
            sign = data.get("_sign", "")
            if sign and sign.startswith("http"):
                # Already have a valid session, the sign IS a location
                resp3 = session.get(sign)
                # ssecurity might be in the response
                try:
                    resp_data = json.loads(resp3.text.replace("&&&START&&&", ""))
                    if "ssecurity" in resp_data:
                        self.ssecurity = resp_data["ssecurity"]
                        return
                except Exception:
                    pass

            # Try step2 again - might work without captcha now
            post_data = {
                "sid": "xiaomiio",
                "hash": hashlib.md5(self.password.encode()).hexdigest().upper(),
                "callback": "https://sts.api.io.mi.com/sts",
                "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
                "user": self.username,
                "_json": "true",
                "_sign": sign,
            }
            resp = session.post(
                "https://account.xiaomi.com/pass/serviceLoginAuth2",
                data=post_data,
            )
            auth = json.loads(resp.text.replace("&&&START&&&", ""))
            if auth.get("ssecurity"):
                self.ssecurity = auth["ssecurity"]
                self._status("Got ssecurity from API")
        except Exception as e:
            self._status(f"Could not extract ssecurity: {e}")

    def get_devices(self, country: str = "sg") -> list[dict[str, Any]]:
        """Fetch device list from Xiaomi cloud."""
        if not self.service_token or not self.user_id:
            raise RuntimeError("Not logged in")

        url = self._api_url(country) + "/home/device_list"
        params = {
            "data": '{"getVirtualModel":true,"getHuamiDevices":1,"get_split_device":false,"support_smart_home":true}'
        }

        try:
            if self.ssecurity:
                resp_text = self._signed_request(url, params)
            else:
                resp_text = self._simple_request(url, params)
        except TokenExpiredError:
            logger.info("Token expired while fetching device list, attempting refresh...")
            if _refresh_cloud_session(self):
                logger.info("Token refreshed, retrying device list request...")
                if self.ssecurity:
                    resp_text = self._signed_request(url, params)
                else:
                    resp_text = self._simple_request(url, params)
            else:
                raise

        data = json.loads(resp_text)
        return data.get("result", {}).get("list", [])

    def _api_url(self, country: str) -> str:
        c = country.strip().lower()
        if c == "cn":
            return "https://api.io.mi.com/app"
        return f"https://{c}.api.io.mi.com/app"

    def _signed_request(self, url: str, params: dict[str, str]) -> str:
        """Make RC4-signed request (requires ssecurity)."""
        nonce = gen_nonce()
        s_nonce = signed_nonce(self.ssecurity, nonce)
        enc_params = generate_enc_params(url, "POST", s_nonce, nonce, params, self.ssecurity)

        resp = self.session.post(
            url,
            data=enc_params,
            timeout=30,
            cookies={
                "userId": str(self.user_id),
                "yetAnotherServiceToken": self.service_token or "",
                "serviceToken": self.service_token or "",
                "locale": "en_US",
                "timezone": "GMT+00:00",
                "is_daylight": "0",
                "dst_offset": "0",
                "channel": "MI_APP_STORE",
            },
        )

        if resp.status_code == 200:
            decoded = decrypt_rc4(s_nonce, resp.text)
            return decoded.decode("utf-8")
        if resp.status_code in TOKEN_EXPIRED_STATUSES:
            raise TokenExpiredError(f"Token expired (HTTP {resp.status_code})")
        raise RuntimeError(f"Signed request failed: {resp.status_code}")

    def _simple_request(self, url: str, params: dict[str, str]) -> str:
        """Make simple request with serviceToken (no RC4)."""
        resp = self.session.post(
            url,
            data=params,
            timeout=30,
            cookies={
                "userId": str(self.user_id),
                "serviceToken": self.service_token or "",
            },
        )
        if resp.status_code == 200:
            return resp.text
        if resp.status_code in TOKEN_EXPIRED_STATUSES:
            raise TokenExpiredError(f"Token expired (HTTP {resp.status_code})")
        raise RuntimeError(f"Simple request failed: {resp.status_code}")


# HTTP statuses the Xiaomi API uses to signal a dead serviceToken. Besides the
# classic 401/403, the API answers 426 with {"message": "SERVICETOKEN_EXPIRED"}.
TOKEN_EXPIRED_STATUSES = (401, 403, 426)


class TokenExpiredError(Exception):
    """Raised when the Xiaomi Cloud token has expired."""

    pass


# ---------------------------------------------------------------------------
# Public API (used by CLI)
# ---------------------------------------------------------------------------


def get_cloud_devices(
    username: str,
    password: str,
    server: str = "sg",
    on_status: Callable[[str], Any] | None = None,
) -> list[dict[str, Any]]:
    """Fetch all devices from Xiaomi cloud account.

    Handles captcha and email verification automatically.
    """
    cloud = XiaomiCloud(username, password, on_status=on_status)
    cloud.login()
    devices = cloud.get_devices(country=server)
    return devices or []


def _retry_on_token_expired(func):
    """Decorator that retries once with token refresh on TokenExpiredError."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TokenExpiredError:
            logger.info("Token expired, attempting refresh...")
            # First arg is always `cloud`
            cloud = args[0]
            if _refresh_cloud_session(cloud):
                logger.info("Token refreshed, retrying request...")
                return func(*args, **kwargs)
            raise

    return wrapper


def _refresh_cloud_session(cloud: XiaomiCloud) -> bool:
    """Attempt to refresh the cloud session tokens."""
    try:
        from xiao.core.config import save_cloud_session
        from xiao.core.token_refresh import refresh_tokens

        tokens = refresh_tokens(cloud.username, cloud.password)
        if tokens:
            cloud.user_id = tokens["userId"]
            cloud.service_token = tokens["serviceToken"]
            cloud.ssecurity = tokens["ssecurity"]
            save_cloud_session(tokens["userId"], tokens["serviceToken"], tokens["ssecurity"])
            return True
    except Exception as e:
        logger.error("Token refresh failed: %s", e)
    return False


@_retry_on_token_expired
def cloud_rpc(
    cloud: XiaomiCloud,
    did: str,
    method: str,
    params: Any,
    country: str = "us",
) -> dict[str, Any]:
    """Send an RPC command to a device via Xiaomi Cloud.

    This is the core method for controlling devices that don't respond locally.
    Uses /home/rpc/<did> endpoint with RC4-signed requests.
    """
    url = cloud._api_url(country) + f"/home/rpc/{did}"
    payload = {"data": json.dumps({"method": method, "params": params})}

    if cloud.ssecurity:
        resp_text = cloud._signed_request(url, payload)
    else:
        resp_text = cloud._simple_request(url, payload)

    return json.loads(resp_text)


@_retry_on_token_expired
def cloud_get_properties(
    cloud: XiaomiCloud,
    did: str,
    props: list[dict[str, int]],
    country: str = "us",
) -> list[dict[str, Any]]:
    """Get MIoT properties via cloud.

    props: list of {"did": did, "siid": X, "piid": Y}
    """
    url = cloud._api_url(country) + "/miotspec/prop/get"
    params_list = [{"did": did, "siid": p["siid"], "piid": p["piid"]} for p in props]
    payload = {"data": json.dumps({"params": params_list})}

    if cloud.ssecurity:
        resp_text = cloud._signed_request(url, payload)
    else:
        resp_text = cloud._simple_request(url, payload)

    data = json.loads(resp_text)
    return data.get("result", [])


@_retry_on_token_expired
def cloud_set_properties(
    cloud: XiaomiCloud,
    did: str,
    props: list[dict[str, Any]],
    country: str = "us",
) -> list[dict[str, Any]]:
    """Set MIoT properties via cloud.

    props: list of {"did": did, "siid": X, "piid": Y, "value": V}
    """
    url = cloud._api_url(country) + "/miotspec/prop/set"
    params_list = [{"did": did, "siid": p["siid"], "piid": p["piid"], "value": p["value"]} for p in props]
    payload = {"data": json.dumps({"params": params_list})}

    if cloud.ssecurity:
        resp_text = cloud._signed_request(url, payload)
    else:
        resp_text = cloud._simple_request(url, payload)

    data = json.loads(resp_text)
    return data.get("result", [])


@_retry_on_token_expired
def cloud_call_action(
    cloud: XiaomiCloud,
    did: str,
    siid: int,
    aiid: int,
    params: list | None = None,
    country: str = "us",
) -> dict[str, Any]:
    """Call a MIoT action via cloud.

    Uses /miotspec/action endpoint.
    """
    url = cloud._api_url(country) + "/miotspec/action"
    action_params = {"did": did, "siid": siid, "aiid": aiid, "in": params or []}
    payload = {"data": json.dumps({"params": action_params})}

    if cloud.ssecurity:
        resp_text = cloud._signed_request(url, payload)
    else:
        resp_text = cloud._simple_request(url, payload)

    return json.loads(resp_text)


def find_vacuums(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter cloud devices to vacuum-like models."""
    keywords = ["vacuum", "roborock", "dreame", "viomi", "sweep"]
    results = []
    for d in devices:
        model = (d.get("model") or "").lower()
        if any(k in model for k in keywords):
            results.append(d)
    return results


def extract_device_info(device: dict[str, Any]) -> dict[str, str]:
    """Extract relevant fields from a cloud device entry."""
    return {
        "name": device.get("name", "Unknown"),
        "model": device.get("model", ""),
        "ip": device.get("localip", ""),
        "token": device.get("token", ""),
        "mac": device.get("mac", ""),
        "did": device.get("did", ""),
    }
