"""Tests for xiao.core.token_refresh module."""

from unittest.mock import MagicMock, patch


class TestRefreshTokens:
    def test_returns_none_without_playwright(self):
        """If playwright import fails, returns None."""
        with patch.dict("sys.modules", {"playwright.sync_api": None}):
            import importlib

            from xiao.core import token_refresh

            importlib.reload(token_refresh)
            result = token_refresh.refresh_tokens("user", "pass")
            assert result is None
            # Reload to restore
            importlib.reload(token_refresh)

    def test_returns_none_on_cdp_connection_failure(self):
        """If CDP connection fails, returns None gracefully."""
        mock_pw_ctx = MagicMock()
        MagicMock()
        mock_pw_ctx.chromium.connect_over_cdp.side_effect = ConnectionRefusedError("refused")

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            from xiao.core.token_refresh import refresh_tokens

            result = refresh_tokens("user", "pass")
            assert result is None

    def test_returns_none_on_no_contexts(self):
        """If browser has no contexts, returns None."""
        mock_pw_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_browser.contexts = []
        mock_pw_ctx.chromium.connect_over_cdp.return_value = mock_browser

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw_ctx)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            from xiao.core.token_refresh import refresh_tokens

            result = refresh_tokens("user", "pass")
            assert result is None

    def test_cdp_port_constant(self):
        """Verify CDP_PORT is set correctly."""
        from xiao.core.token_refresh import CDP_PORT

        assert CDP_PORT == 18800
