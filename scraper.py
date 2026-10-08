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
    soup = BeautifulSoup(html, "lxml")

    # Strategy 1: Next.js __NEXT_DATA__
    tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if tag and tag.string:
        try:
            data = json.loads(tag.string)
            raw = (
                _dig(data, ["props", "pageProps", "ads"])
                or _dig(data, ["props", "pageProps", "listings"])
                or _dig(data, ["props", "pageProps", "data", "ads"])
            )
            if raw is not None:
                return _normalize_list(raw, base_url)
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 2: window.initialData = {...};
    for script in soup.find_all("script"):
        text = script.string or ""
        m = re.search(r"window\.initialData\s*=\s*(\{.+?\});", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                raw = data.get("ads") or data.get("listings")
                if raw is not None:
                    return _normalize_list(raw, base_url)
            except json.JSONDecodeError:
                pass

    return None


def _dig(d: dict, keys: list) -> Optional[list]:
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d if isinstance(d, list) else None


def _normalize_list(raw: list, base_url: str) -> list[Ad]:
    ads = []
    for a in raw:
        ad = _normalize_ad(a, base_url)
        if ad is not None:
            ads.append(ad)
    return ads


def _normalize_ad(a: dict, base_url: str) -> Optional[Ad]:
    try:
        slug = str(a.get("slug") or a.get("id") or a.get("hash") or "")
        if not slug:
            return None

        title = str(a.get("title") or a.get("heading") or "")

        price_raw = a.get("price", 0)
        price = int(price_raw["value"]) if isinstance(price_raw, dict) else int(price_raw or 0)

        attrs = a.get("attributes") or {}
        if isinstance(attrs, list):
            attrs = {item.get("key", ""): item.get("value", "") for item in attrs}

        beds = _parse_int(attrs.get("beds") or attrs.get("bedrooms") or a.get("beds", 0))
        baths = _parse_int(attrs.get("baths") or attrs.get("bathrooms") or a.get("baths", 0))

        cat = a.get("category", {})
        category = str(cat.get("name") if isinstance(cat, dict) else cat or "")

        posted_time = str(a.get("postedAt") or a.get("created_at") or a.get("date") or "")

        href = str(a.get("url") or a.get("link") or f"/en/ad/{slug}")
        url = href if href.startswith("http") else f"{base_url}{href}"

        return Ad(slug=slug, title=title, price=price, beds=beds, baths=baths,
                  category=category, posted_time=posted_time, url=url)
    except (TypeError, ValueError, KeyError):
        return None


def _parse_html(html: str, base_url: str) -> list[Ad]:
    soup = BeautifulSoup(html, "lxml")
    cards = (
        soup.select("li.normal-ad, li.top-ad")
        or soup.select("[data-testid='listing-item']")
        or soup.select(".list-item--gallery")
        or soup.select(".ad-item")
    )
    ads = []
    for card in cards:
        try:
            ad = _parse_card(card, base_url)
            if ad:
                ads.append(ad)
        except Exception as exc:
            logger.debug("Skipping malformed HTML card: %s", exc)
    return ads


def _parse_card(card, base_url: str) -> Optional[Ad]:
    link = card.find("a", href=True)
    if not link:
        return None
    href = link["href"]
    slug = card.get("data-slug") or href.rstrip("/").split("/")[-1]

    heading = card.find(re.compile(r"^h[1-6]$"))
    title = heading.get_text(strip=True) if heading else link.get_text(strip=True)

    price_tag = card.find(class_=re.compile(r"price", re.I))
    price = _parse_price(price_tag.get_text(strip=True)) if price_tag else 0

    beds = baths = 0
    for attr in card.find_all(class_=re.compile(r"attribute", re.I)):
        text = attr.get_text(strip=True).lower()
        if "bed" in text:
            beds = _parse_int(text)
        elif "bath" in text:
            baths = _parse_int(text)

    cat_tag = card.find(class_=re.compile(r"category", re.I))
    category = cat_tag.get_text(strip=True) if cat_tag else ""

    time_tag = card.find("time")
    posted_time = (time_tag.get("datetime") or time_tag.get_text(strip=True)) if time_tag else ""

    url = href if href.startswith("http") else f"{base_url}{href}"
    return Ad(slug=slug, title=title, price=price, beds=beds, baths=baths,
              category=category, posted_time=posted_time, url=url)


def _parse_int(value) -> int:
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else 0


def _parse_price(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0
