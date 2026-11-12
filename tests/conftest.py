"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep_in_room_clean_verification(monkeypatch):
    """start_room_clean polls the robot with real sleeps; tests don't need to wait."""
    monkeypatch.setattr("xiao.core.room_cleaning.time.sleep", lambda _s: None)
