import json
import pytest
import requests
from unittest.mock import patch, MagicMock, call
from scraper import fetch, parse, Ad


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


def test_fetch_returns_response_text():
    with patch("scraper.requests.get", return_value=FakeResponse("<html/>")):
        assert fetch("https://example.com") == "<html/>"


def test_fetch_passes_user_agent_header():
    with patch("scraper.requests.get", return_value=FakeResponse("<html/>")) as mock_get:
        fetch("https://example.com")
    headers = mock_get.call_args[1]["headers"]
    assert "Mozilla" in headers["User-Agent"]


def test_fetch_retries_once_on_connection_error():
    responses = [requests.ConnectionError("timeout"), FakeResponse("<html/>")]
    with patch("scraper.requests.get", side_effect=responses), \
         patch("scraper.time.sleep") as mock_sleep:
        result = fetch("https://example.com")
    assert result == "<html/>"
    mock_sleep.assert_called_once_with(5)


def test_fetch_raises_after_two_failures():
    with patch("scraper.requests.get", side_effect=requests.ConnectionError("fail")), \
         patch("scraper.time.sleep"):
        with pytest.raises(requests.ConnectionError):
            fetch("https://example.com")


def test_fetch_raises_on_http_error():
    with patch("scraper.requests.get", return_value=FakeResponse("", status_code=403)):
        with pytest.raises(requests.HTTPError):
            fetch("https://example.com")
