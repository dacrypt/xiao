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


class TestDashboardThemeToggle:
    def test_dashboard_exposes_persistent_dark_light_theme_toggle(self):
        html = _dashboard_html()

        assert 'class="theme-toggle"' in html
        assert 'data-theme-option="dark"' in html
        assert 'data-theme-option="light"' in html
        assert "const THEME_STORAGE_KEY = 'xiao-theme';" in html
        assert "document.documentElement.dataset.theme = theme;" in html
        assert "localStorage.setItem(THEME_STORAGE_KEY, theme);" in html


class TestDashboardDryTimeCopy:
    def test_dashboard_uses_dry_time_wording_instead_of_stale_sweep_type_labels(self):
        html = _dashboard_html()

        assert "const dryLeftTimeMin = d.dry_left_time_min;" in html
        assert "Dry Time Left" in html
        assert "d.sweep_type" not in html
        assert "Sweep Type / Dry Time" not in html


class TestDashboardAdvancedSettings:
    def test_dashboard_exposes_advanced_setting_controls_and_api_hooks(self):
        html = _dashboard_html()

        assert 'id="resumeAfterChargeToggle"' in html
        assert 'id="carpetBoostToggle"' in html
        assert 'id="childLockToggle"' in html
        assert 'id="smartWashToggle"' in html
        assert 'id="carpetAvoidanceBtns"' in html
        assert 'id="cleanRagsTipSlider"' in html
        assert "/api/settings/resume-after-charge" in html
        assert "/api/settings/carpet-boost" in html
        assert "/api/settings/child-lock" in html
        assert "/api/settings/smart-wash" in html
        assert "/api/settings/carpet-avoidance" in html
        assert "/api/settings/clean-rags-tip" in html
