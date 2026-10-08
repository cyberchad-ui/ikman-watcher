import json
import pytest
from datetime import datetime, timezone, timedelta
import state


@pytest.fixture(autouse=True)
def patch_state_path(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", tmp_path / "seen.json")


def test_load_returns_default_when_file_missing():
    result = state.load()
    assert result == {"first_run_done": False, "last_zero_alert": None, "seen": {}}


def test_save_and_load_roundtrip():
    s = {"first_run_done": True, "last_zero_alert": None, "seen": {"abc": "2026-10-08T00:00:00+00:00"}}
    state.save(s)
    loaded = state.load()
    assert loaded["first_run_done"] is True
    assert "abc" in loaded["seen"]


def test_prune_removes_entries_older_than_60_days():
    old_ts = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
    recent_ts = datetime.now(timezone.utc).isoformat()
    s = {"seen": {"old-slug": old_ts, "new-slug": recent_ts}}
    result = state.prune(s, days=60)
    assert "old-slug" not in result["seen"]
    assert "new-slug" in result["seen"]


def test_prune_keeps_entries_exactly_at_60_days():
    boundary_ts = (datetime.now(timezone.utc) - timedelta(days=60, seconds=-1)).isoformat()
    s = {"seen": {"boundary": boundary_ts}}
    result = state.prune(s, days=60)
    assert "boundary" in result["seen"]


def test_is_first_run_true_when_flag_false():
    assert state.is_first_run({"first_run_done": False}) is True


def test_is_first_run_false_when_flag_true():
    assert state.is_first_run({"first_run_done": True}) is False


def test_mark_seen_adds_slug_with_iso_timestamp():
    s = {"seen": {}}
    state.mark_seen(s, "slug-xyz")
    assert "slug-xyz" in s["seen"]
    datetime.fromisoformat(s["seen"]["slug-xyz"])  # must be valid ISO string


def test_is_seen_true_for_known_slug():
    s = {"seen": {"slug-abc": "2026-10-08T00:00:00+00:00"}}
    assert state.is_seen(s, "slug-abc") is True


def test_is_seen_false_for_unknown_slug():
    assert state.is_seen({"seen": {}}, "missing") is False


def test_should_send_zero_alert_true_when_never_sent():
    assert state.should_send_zero_alert({"last_zero_alert": None}) is True


def test_should_send_zero_alert_false_within_24h():
    recent = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    assert state.should_send_zero_alert({"last_zero_alert": recent}) is False


def test_should_send_zero_alert_true_after_24h():
    old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert state.should_send_zero_alert({"last_zero_alert": old}) is True


def test_mark_zero_alert_sent_sets_timestamp():
    s = {"last_zero_alert": None}
    state.mark_zero_alert_sent(s)
    assert s["last_zero_alert"] is not None
    datetime.fromisoformat(s["last_zero_alert"])
