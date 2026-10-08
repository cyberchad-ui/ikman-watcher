import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 15
RETRY_BACKOFF = 5


@dataclass
class Ad:
    slug: str
    title: str
    price: int
    beds: int
    baths: int
    category: str
    posted_time: str
    url: str


def fetch(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            if attempt == 0:
                logger.warning("Fetch failed (attempt 1), retrying in %ds: %s", RETRY_BACKOFF, exc)
                time.sleep(RETRY_BACKOFF)
            else:
                raise


def parse(html: str, base_url: str = "https://ikman.lk") -> list[Ad]:
    ads = _parse_json(html, base_url)
    if ads is not None:
        return ads
    return _parse_html(html, base_url)


def _parse_json(html: str, base_url: str) -> Optional[list[Ad]]:
    pass  # implemented in Task 4


def _parse_html(html: str, base_url: str) -> list[Ad]:
    return []  # implemented in Task 5


def _parse_int(value) -> int:
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else 0


def _parse_price(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0
