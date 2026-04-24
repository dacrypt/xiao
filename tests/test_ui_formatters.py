"""UI formatter regression tests."""

from io import StringIO

from rich.console import Console

from xiao.ui import formatters


class TestRenderStatus:
    def test_render_status_labels_dry_left_time_minutes(self, monkeypatch):
        output = StringIO()
        monkeypatch.setattr(
            formatters, "console", Console(file=output, force_terminal=False, color_system=None, width=120)
        )

        formatters.render_status({"state": "Drying", "dry_left_time_min": 47})

        rendered = output.getvalue()
        assert "Dry Left:" in rendered
        assert "47m" in rendered
