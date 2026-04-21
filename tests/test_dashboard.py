"""Dashboard UI regression tests."""

from pathlib import Path


def _dashboard_html() -> str:
    return (Path(__file__).resolve().parents[1] / "src" / "xiao" / "dashboard" / "index.html").read_text()


class TestDashboardCollapsibleSections:
    def test_dashboard_marks_diagnostics_sections_as_collapsible_and_closed_by_default(self):
        html = _dashboard_html()

        assert 'data-collapsible-section="audio"' in html
        assert 'data-collapsible-section="clean-log"' in html
        assert 'data-collapsible-section="all-properties"' in html
        assert '<summary class="collapsible-summary">🔊 AUDIO & VOICE</summary>' in html
        assert (
            '<summary class="collapsible-summary">📋 CLEAN LOG (RAW) <span class="badge">siid 4</span></summary>'
            in html
        )
        assert (
            '<summary class="collapsible-summary">🔬 ALL PROPERTIES <span class="badge" id="propCountBadge">--</span></summary>'
            in html
        )
        assert 'data-collapsible-section="audio" open' not in html
        assert 'data-collapsible-section="clean-log" open' not in html
        assert 'data-collapsible-section="all-properties" open' not in html
