import pytest
from unittest.mock import patch, MagicMock
from scraper import Ad
import notifier


SMTP_KWARGS = dict(smtp_user="sender@gmail.com", smtp_password="apppass", to="dest@example.com")


def _make_ad(slug="house-1", title="Nice 2BR House", price=60000, beds=2,
             baths=1, url="https://ikman.lk/en/ad/house-1"):
    return Ad(slug=slug, title=title, price=price, beds=beds, baths=baths,
              category="Houses", posted_time="Today", url=url)


@pytest.fixture
def mock_smtp():
    with patch("notifier.smtplib.SMTP") as cls:
        instance = MagicMock()
        cls.return_value.__enter__ = lambda s: instance
        cls.return_value.__exit__ = MagicMock(return_value=False)
        yield instance


def test_send_new_ads_calls_sendmail(mock_smtp):
    notifier.send_new_ads([_make_ad()], **SMTP_KWARGS)
    mock_smtp.sendmail.assert_called_once()


def test_send_new_ads_email_contains_title(mock_smtp):
    notifier.send_new_ads([_make_ad(title="Sunny Apartment")], **SMTP_KWARGS)
    _, _, msg = mock_smtp.sendmail.call_args[0]
    assert "Sunny Apartment" in msg


def test_send_new_ads_email_contains_price(mock_smtp):
    notifier.send_new_ads([_make_ad(price=62000)], **SMTP_KWARGS)
    _, _, msg = mock_smtp.sendmail.call_args[0]
    assert "62" in msg


def test_send_new_ads_email_contains_link(mock_smtp):
    notifier.send_new_ads([_make_ad(url="https://ikman.lk/en/ad/house-99")], **SMTP_KWARGS)
    _, _, msg = mock_smtp.sendmail.call_args[0]
    assert "house-99" in msg


def test_send_new_ads_subject_includes_count(mock_smtp):
    ads = [_make_ad(slug=f"ad-{i}") for i in range(3)]
    notifier.send_new_ads(ads, **SMTP_KWARGS)
    _, _, msg = mock_smtp.sendmail.call_args[0]
    assert "3" in msg


def test_send_new_ads_logs_to_correct_addresses(mock_smtp):
    notifier.send_new_ads([_make_ad()], **SMTP_KWARGS)
    from_addr, to_addr, _ = mock_smtp.sendmail.call_args[0]
    assert from_addr == "sender@gmail.com"
    assert to_addr == "dest@example.com"


def test_send_error_calls_sendmail(mock_smtp):
    notifier.send_error("watcher may be broken", **SMTP_KWARGS)
    mock_smtp.sendmail.assert_called_once()


def test_send_error_subject_contains_warning(mock_smtp):
    notifier.send_error("watcher may be broken", **SMTP_KWARGS)
    _, _, msg = mock_smtp.sendmail.call_args[0]
    assert "broken" in msg.lower() or "warning" in msg.lower() or "watcher" in msg.lower()
