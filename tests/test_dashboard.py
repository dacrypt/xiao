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


class TestDashboardState21Copy:
    def test_dashboard_keeps_state_21_as_washing_mop_pause_while_preserving_tank_guidance(self):
        html = _dashboard_html()

        assert "WashingMopPause" in html
        assert "Water Tank Alert" not in html
        assert "clean water" in html
        assert "dirty water" in html


class TestDashboardWaterBoxStatus:
    def test_dashboard_surfaces_waterbox_status_from_live_status_payload(self):
        html = _dashboard_html()

        assert "d.waterbox_status" in html
        assert "Water Box" in html


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


class TestDashboardRoomCleaningWarnings:
    def test_dashboard_surfaces_room_clean_verification_warnings_from_api(self):
        html = _dashboard_html()

        assert "const response = await api('/api/clean/rooms'" in html
        assert "if (response.warning)" in html
        assert "toast(response.warning, 'info')" in html


class TestDashboardHistoryCopy:
    def test_dashboard_history_uses_clean_log_totals_instead_of_stale_last_clean_fields(self):
        html = _dashboard_html()

        assert "label: 'First Clean'" in html
        assert "d.first_clean_date || '--'" in html
        assert "label: 'Last Clean'" not in html
        assert "d.last_clean_date || '--'" not in html

    def test_dashboard_history_exposes_estimated_cleaning_energy_tile(self):
        html = _dashboard_html()

        assert "d.estimated_cleaning_energy_display" in html
        assert "label: 'Est. Energy'" in html
