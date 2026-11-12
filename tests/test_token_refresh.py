"""Tests for xiao.core.token_refresh module."""

from unittest.mock import MagicMock, patch

from xiao.core import token_refresh


class TestRefreshTokens:
    def test_returns_none_without_playwright(self, monkeypatch):
        """If playwright isn't installed, both paths return None cleanly."""
        with patch.dict("sys.modules", {"playwright.sync_api": None}):
            assert token_refresh.refresh_tokens("user", "pass") is None

    def test_default_path_uses_persistent_context(self, monkeypatch):
        """With XIAO_CDP_PORT unset, refresh_tokens routes to the
        persistent-context path (not CDP)."""
        monkeypatch.delenv("XIAO_CDP_PORT", raising=False)
        with (
            patch.object(token_refresh, "_refresh_via_cdp") as m_cdp,
            patch.object(token_refresh, "_refresh_via_persistent", return_value=None) as m_pers,
        ):
            token_refresh.refresh_tokens("u", "p")
            m_cdp.assert_not_called()
            m_pers.assert_called_once_with("u", "p")

    def test_cdp_path_triggered_when_env_set(self, monkeypatch):
        """XIAO_CDP_PORT=N routes refresh through the CDP path first."""
        monkeypatch.setenv("XIAO_CDP_PORT", "9222")
        sentinel = {"userId": "1", "serviceToken": "tok", "ssecurity": "sec"}
        with (
            patch.object(token_refresh, "_refresh_via_cdp", return_value=sentinel) as m_cdp,
            patch.object(token_refresh, "_refresh_via_persistent") as m_pers,
        ):
            assert token_refresh.refresh_tokens("u", "p") is sentinel
            m_cdp.assert_called_once_with(9222, "u", "p")
            m_pers.assert_not_called()

    def test_cdp_falls_back_to_persistent_on_failure(self, monkeypatch):
        """If the CDP path returns None, refresh_tokens falls back to persistent."""
        monkeypatch.setenv("XIAO_CDP_PORT", "9222")
        with (
            patch.object(token_refresh, "_refresh_via_cdp", return_value=None) as m_cdp,
            patch.object(token_refresh, "_refresh_via_persistent", return_value=None) as m_pers,
        ):
            token_refresh.refresh_tokens("u", "p")
            m_cdp.assert_called_once()
            m_pers.assert_called_once()

    def test_cdp_ignores_non_numeric_env(self, monkeypatch):
        """Junk values of XIAO_CDP_PORT are ignored (not a crash)."""
        monkeypatch.setenv("XIAO_CDP_PORT", "nope")
        with (
            patch.object(token_refresh, "_refresh_via_cdp") as m_cdp,
            patch.object(token_refresh, "_refresh_via_persistent", return_value=None),
        ):
            token_refresh.refresh_tokens("u", "p")
            m_cdp.assert_not_called()


class TestProfileDir:
    def test_profile_dir_under_config_dir(self):
        """The managed Chromium profile lives under CONFIG_DIR/chromium."""
        from xiao.core.config import CONFIG_DIR

        assert token_refresh.PROFILE_DIR == CONFIG_DIR / "chromium"


class TestCdpPathBehavior:
    """Legacy CDP path still works when explicitly opted in."""

    def test_returns_none_on_cdp_connection_failure(self):
        mock_pw_ctx = MagicMock()
        mock_pw_ctx.chromium.connect_over_cdp.side_effect = ConnectionRefusedError()

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            assert token_refresh._refresh_via_cdp(18800, "u", "p") is None

    def test_returns_none_on_no_contexts(self):
        mock_pw_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_browser.contexts = []
        mock_pw_ctx.chromium.connect_over_cdp.return_value = mock_browser

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            assert token_refresh._refresh_via_cdp(18800, "u", "p") is None


class TestSeedBrowserSession:
    def test_launches_headed_persistent_context(self):
        """seed_browser_session must open a visible window, not headless."""
        mock_pw_ctx = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies.return_value = [{"name": "passToken", "value": "abc"}]
        mock_pw_ctx.chromium.launch_persistent_context.return_value = mock_context

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            assert token_refresh.seed_browser_session() is True

        kwargs = mock_pw_ctx.chromium.launch_persistent_context.call_args.kwargs
        assert kwargs.get("headless") is False
        assert kwargs.get("user_data_dir") == str(token_refresh.PROFILE_DIR)

    def _run(self, context):
        mock_pw_ctx = MagicMock()
        mock_pw_ctx.chromium.launch_persistent_context.return_value = context
        with (
            patch("playwright.sync_api.sync_playwright") as mock_sp,
            patch.object(token_refresh.time, "sleep"),
        ):
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            return token_refresh.seed_browser_session(), context

    def test_opens_account_root_not_dead_pass_login(self):
        """/pass/login returns 404 now; the landing must be the account root."""
        page = MagicMock()
        context = MagicMock(pages=[page])
        context.cookies.return_value = [{"name": "passToken", "value": "abc"}]
        self._run(context)
        page.goto.assert_called_once()
        assert page.goto.call_args.args[0] == "https://account.xiaomi.com/"

    def test_success_url_without_cookie_is_not_logged_in(self):
        """i.mi.com renders without a session; only passToken means logged in.
        Closing the window (page closed) ends the wait with False."""
        page = MagicMock()
        page.url = "https://i.mi.com/"
        page.is_closed.side_effect = [False, True]
        context = MagicMock(pages=[page])
        context.cookies.return_value = [{"name": "deviceId", "value": "x"}]
        ok, ctx = self._run(context)
        assert ok is False
        ctx.close.assert_called_once()

    def test_waits_until_cookie_appears(self):
        page = MagicMock()
        page.is_closed.return_value = False
        context = MagicMock(pages=[page])
        context.cookies.side_effect = [[], [], [{"name": "passToken", "value": "abc"}]]
        ok, _ = self._run(context)
        assert ok is True
        assert context.cookies.call_count == 3

    def test_returns_false_when_playwright_missing(self):
        with patch.dict("sys.modules", {"playwright.sync_api": None}):
            assert token_refresh.seed_browser_session() is False
