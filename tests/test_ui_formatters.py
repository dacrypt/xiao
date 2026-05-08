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


class TestRenderFullStatus:
    def test_render_full_status_uses_first_clean_and_totals_for_cloud_history(self, monkeypatch):
        output = StringIO()
        monkeypatch.setattr(
            formatters, "console", Console(file=output, force_terminal=False, color_system=None, width=120)
        )

        formatters.render_full_status(
            {
                "state": "Charging Completed",
                "last_clean": {
                    "first_clean_date": "2024-03-21 05:46 UTC",
                    "total_clean_count": 42,
                    "total_clean_duration": 130,
                    "estimated_cleaning_energy_display": "0.163 kWh @ 75W",
                },
            }
        )

        rendered = output.getvalue()
        assert "Cleaning History" in rendered
        assert "First Clean:" in rendered
        assert "2024-03-21 05:46 UTC" in rendered
        assert "Total Cleans:" in rendered
        assert "42" in rendered
        assert "Total Time:" in rendered
        assert "2h 10m" in rendered
        assert "Est. Energy:" in rendered
        assert "0.163 kWh @ 75W" in rendered
        assert "Last Clean" not in rendered


class TestRenderReport:
    def test_render_report_includes_estimated_cleaning_energy(self, monkeypatch):
        output = StringIO()
        monkeypatch.setattr(
            formatters, "console", Console(file=output, force_terminal=False, color_system=None, width=120)
        )

        formatters.render_report(
            {
                "status": {"state": "Charging Completed", "fan_speed": "standard"},
                "history": {
                    "total_clean_count": 42,
                    "total_clean_duration": 130,
                    "estimated_cleaning_energy_display": "0.163 kWh @ 75W",
                },
            }
        )

        rendered = output.getvalue()
        assert "Cleaning History" in rendered
        assert "Est. Energy:" in rendered
        assert "0.163 kWh @ 75W" in rendered
