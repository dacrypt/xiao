"""Regression tests for room-clean command verification helpers."""

from unittest.mock import MagicMock

from xiao.core import room_cleaning


class TestStartRoomClean:
    def test_marks_room_clean_unresponsive_when_accept_succeeds_but_status_stays_docked(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        vac.status.side_effect = [
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
            {"state": "Charging Completed"},
        ]

        result = room_cleaning.start_room_clean(
            vac,
            [7],
            poll_attempts=3,
            poll_delay_seconds=0,
            sleep_fn=lambda _: None,
        )

        assert result["accepted"] is True
        assert result["transport"] == "miot"
        assert result["verified_started"] is False
        assert "code=0" in result["warning"]
        vac.clean_rooms.assert_not_called()

    def test_marks_room_clean_verified_when_status_enters_progress_state(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        vac.status.side_effect = [
            {"state": "Charging Completed"},
            {"state": "Go Washing"},
        ]

        result = room_cleaning.start_room_clean(
            vac,
            [7],
            poll_attempts=3,
            poll_delay_seconds=0,
            sleep_fn=lambda _: None,
        )

        assert result["accepted"] is True
        assert result["verified_started"] is True
        assert result["warning"] is None
        assert result["status_after"]["state"] == "Go Washing"

    def test_skips_hard_failure_when_vacuum_was_already_busy(self):
        vac = MagicMock()
        vac.clean_rooms_miot.return_value = {"code": 0}
        vac.status.return_value = {"state": "Sweeping"}

        result = room_cleaning.start_room_clean(
            vac,
            [7],
            poll_attempts=3,
            poll_delay_seconds=0,
            sleep_fn=lambda _: None,
        )

        assert result["accepted"] is True
        assert result["verified_started"] is None
        assert "already busy" in result["warning"]
