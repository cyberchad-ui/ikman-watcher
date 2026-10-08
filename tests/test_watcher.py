import pytest
import yaml
from unittest.mock import patch, MagicMock
from scraper import Ad
import watcher


@pytest.fixture(autouse=True)
def patch_state_path(tmp_path, monkeypatch):
    import state
    monkeypatch.setattr(state, "STATE_PATH", tmp_path / "seen.json")


@pytest.fixture
def cfg(tmp_path):
    config = {
        "filters": {"price_min": 50000, "price_max": 75000, "beds_min": 1, "beds_max": 2},
        "sources": ["https://example.com/rentals"],
        "gmail": {"enabled": True},
        "whatsapp": {"enabled": False},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(config))
    return str(path)


def _good_ad(slug="ad-1"):
    return Ad(slug=slug, title="Nice House", price=60000, beds=2, baths=1,
              category="Houses", posted_time="Today", url=f"https://ikman.lk/en/ad/{slug}")


def test_first_run_marks_all_seen_without_emailing(cfg):
    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[_good_ad()]), \
         patch("watcher.notifier.send_new_ads") as mock_email:
        watcher.run(config_path=cfg)
    mock_email.assert_not_called()


def test_first_run_sets_first_run_done_flag(cfg):
    import state
    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[_good_ad()]):
        watcher.run(config_path=cfg)
    s = state.load()
    assert s["first_run_done"] is True


def test_second_run_emails_new_ads(cfg):
    import state
    s = state.load()
    s["first_run_done"] = True
    state.save(s)

    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[_good_ad("new-ad")]), \
         patch("watcher.notifier.send_new_ads") as mock_email, \
         patch.dict("os.environ", {"GMAIL_USER": "u", "GMAIL_APP_PASSWORD": "p", "GMAIL_TO": "t"}):
        watcher.run(config_path=cfg)
    mock_email.assert_called_once()
    ads_sent = mock_email.call_args[0][0]
    assert ads_sent[0].slug == "new-ad"


def test_already_seen_ads_are_not_re_emailed(cfg):
    import state
    s = state.load()
    s["first_run_done"] = True
    state.mark_seen(s, "existing-ad")
    state.save(s)

    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[_good_ad("existing-ad")]), \
         patch("watcher.notifier.send_new_ads") as mock_email:
        watcher.run(config_path=cfg)
    mock_email.assert_not_called()


def test_filtered_out_ads_are_not_emailed(cfg):
    import state
    s = state.load()
    s["first_run_done"] = True
    state.save(s)
    expensive_ad = Ad(slug="expensive", title="x", price=200000, beds=5,
                      baths=3, category="Houses", posted_time="", url="")
    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[expensive_ad]), \
         patch("watcher.notifier.send_new_ads") as mock_email:
        watcher.run(config_path=cfg)
    mock_email.assert_not_called()


def test_zero_ads_sends_error_alert_once_per_day(cfg):
    import state
    s = state.load()
    s["first_run_done"] = True
    state.save(s)

    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[]), \
         patch("watcher.notifier.send_error") as mock_error, \
         patch.dict("os.environ", {"GMAIL_USER": "u", "GMAIL_APP_PASSWORD": "p", "GMAIL_TO": "t"}):
        watcher.run(config_path=cfg)
    mock_error.assert_called_once()


def test_zero_ads_does_not_repeat_error_within_24h(cfg):
    import state
    from datetime import datetime, timezone, timedelta
    s = state.load()
    s["first_run_done"] = True
    s["last_zero_alert"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    state.save(s)

    with patch("watcher.scraper.fetch", return_value="<html/>"), \
         patch("watcher.scraper.parse", return_value=[]), \
         patch("watcher.notifier.send_error") as mock_error:
        watcher.run(config_path=cfg)
    mock_error.assert_not_called()
