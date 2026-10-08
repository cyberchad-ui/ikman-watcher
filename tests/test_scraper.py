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


# --- JSON parsing ---

SAMPLE_AD_NEXT = {
    "slug": "nice-house-col5-123",
    "title": "2BR House in Colombo 5",
    "price": {"value": 60000},
    "attributes": [
        {"key": "beds", "value": "2"},
        {"key": "baths", "value": "1"},
    ],
    "category": {"name": "Houses for Rent"},
    "postedAt": "2026-10-08T10:00:00Z",
    "url": "/en/ad/nice-house-col5-123",
}


def _make_next_data_html(ads: list) -> str:
    data = {"props": {"pageProps": {"ads": ads}}}
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'


def test_parse_extracts_ad_from_next_data():
    html = _make_next_data_html([SAMPLE_AD_NEXT])
    ads = parse(html)
    assert len(ads) == 1
    ad = ads[0]
    assert ad.slug == "nice-house-col5-123"
    assert ad.title == "2BR House in Colombo 5"
    assert ad.price == 60000
    assert ad.beds == 2
    assert ad.baths == 1
    assert ad.category == "Houses for Rent"
    assert ad.posted_time == "2026-10-08T10:00:00Z"
    assert ad.url == "https://ikman.lk/en/ad/nice-house-col5-123"


def test_parse_handles_price_as_plain_int():
    ad_data = {**SAMPLE_AD_NEXT, "price": 65000}
    html = _make_next_data_html([ad_data])
    ads = parse(html)
    assert ads[0].price == 65000


def test_parse_handles_attributes_as_dict():
    ad_data = {**SAMPLE_AD_NEXT, "attributes": {"beds": "2", "baths": "1"}}
    html = _make_next_data_html([ad_data])
    ads = parse(html)
    assert ads[0].beds == 2


def test_parse_skips_malformed_ad_but_keeps_good_ones():
    bad_ad = {"no_slug": True, "no_price": True}
    html = _make_next_data_html([SAMPLE_AD_NEXT, bad_ad])
    ads = parse(html)
    assert len(ads) == 1
    assert ads[0].slug == "nice-house-col5-123"


def test_parse_falls_back_to_html_when_no_json():
    with patch("scraper._parse_html", return_value=[]) as mock_html:
        parse("<html><body>no embedded json</body></html>")
    mock_html.assert_called_once()


def test_parse_returns_empty_list_for_blank_html():
    assert parse("<html></html>") == []


# --- HTML fallback ---

SAMPLE_HTML_CARD = """
<html><body><ul>
<li class="normal-ad" data-slug="house-html-456">
  <a href="/en/ad/house-html-456">
    <h2 class="heading--2mPag">Cozy 1BR Apartment</h2>
  </a>
  <div class="price--3NTpl">Rs 55,000</div>
  <span class="attribute--2xEMc">1 bed</span>
  <span class="attribute--2xEMc">1 bath</span>
  <span class="category--1aB2c">Apartments for Rent</span>
  <time datetime="2026-10-08T08:00:00Z">Today</time>
</li>
</ul></body></html>
"""


def test_html_fallback_extracts_price():
    from scraper import _parse_html
    ads = _parse_html(SAMPLE_HTML_CARD, "https://ikman.lk")
    assert any(a.price == 55000 for a in ads)


def test_html_fallback_extracts_url():
    from scraper import _parse_html
    ads = _parse_html(SAMPLE_HTML_CARD, "https://ikman.lk")
    assert any("house-html-456" in a.url for a in ads)


def test_html_fallback_returns_list_on_unrecognised_structure():
    from scraper import _parse_html
    result = _parse_html("<html><body><p>nothing here</p></body></html>", "https://ikman.lk")
    assert isinstance(result, list)
