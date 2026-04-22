"""Tests for the top-level Typer callback on `xiao`."""

import logging
import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return ANSI_RE.sub("", text)


class TestNoArgsBehavior:
    def test_no_args_renders_status_when_configured(self):
        from xiao.cli.app import app

        vac = MagicMock()
        vac.status.return_value = {"state": "Docked", "battery": 90}
        with (
            patch("xiao.core.config.is_configured", return_value=True),
            patch("xiao.cli.app._vacuum", return_value=vac),
        ):
            result = runner.invoke(app, [], env={"XIAO_NO_CTA": "1"})
        assert result.exit_code == 0
        vac.status.assert_called_once()

    def test_no_args_prints_help_when_unconfigured(self):
        from xiao.cli.app import app

        with (
            patch("xiao.core.config.is_configured", return_value=False),
            patch("xiao.cli.app._vacuum") as m_vac,
        ):
            result = runner.invoke(app, [], env={"XIAO_NO_CTA": "1"})
        assert result.exit_code == 0
        m_vac.assert_not_called()
        # The help output lists some subcommands we know exist.
        assert "setup" in result.stdout
        assert "doctor" in result.stdout


class TestDebugEnv:
    def test_debug_env_calls_basic_config_at_debug_level(self):
        """Setting XIAO_DEBUG=1 must invoke logging.basicConfig(level=DEBUG).
        (We assert the call rather than the root-logger level because pytest
        may have handlers already attached, which makes basicConfig a no-op
        on level.)"""
        from xiao.cli.app import app

        with (
            patch("xiao.core.config.is_configured", return_value=False),
            patch("xiao.cli.app.logging.basicConfig") as m_basic,
        ):
            runner.invoke(app, [], env={"XIAO_NO_CTA": "1", "XIAO_DEBUG": "1"})
        m_basic.assert_called_once()
        assert m_basic.call_args.kwargs.get("level") == logging.DEBUG

    def test_no_debug_env_does_not_call_basic_config(self):
        from xiao.cli.app import app

        with (
            patch("xiao.core.config.is_configured", return_value=False),
            patch("xiao.cli.app.logging.basicConfig") as m_basic,
        ):
            runner.invoke(app, [], env={"XIAO_NO_CTA": "1", "XIAO_DEBUG": ""})
        m_basic.assert_not_called()


class TestDoctorCommand:
    def test_doctor_registered(self):
        from xiao.cli.app import app

        result = runner.invoke(app, ["doctor", "--help"], env={"XIAO_NO_CTA": "1"})
        assert result.exit_code == 0
        assert "skip-network" in _plain(result.stdout)


class TestMcpCommand:
    def test_mcp_registered(self):
        from xiao.cli.app import app

        result = runner.invoke(app, ["mcp", "--help"], env={"XIAO_NO_CTA": "1"})
        assert result.exit_code == 0
        assert "MCP" in result.stdout or "mcp" in result.stdout
