import re

from scraper import Ad


def _age_in_days(posted_time: str) -> float:
    t = (posted_time or "").lower().strip()
    if not t or "bump" in t or "boost" in t:
        return float("inf")
    m = re.match(r"(\d+)\s*(minute|hour|day|week|month)", t)
    if not m:
        return float("inf")
    n, unit = int(m.group(1)), m.group(2)
    if unit == "minute":
        return n / 1440
    if unit == "hour":
        return n / 24
    if unit == "day":
        return float(n)
    if unit == "week":
        return n * 7.0
    if unit == "month":
        return n * 30.0
    return float("inf")


def apply_filters(
    ads: list[Ad],
    price_min: int,
    price_max: int,
    beds_min: int,
    beds_max: int,
    areas: list[str] | None = None,
    max_age_days: int | None = None,
) -> list[Ad]:
    result = []
    for ad in ads:
        if not (price_min <= ad.price <= price_max and beds_min <= ad.beds <= beds_max):
            continue
        if areas:
            haystack = (ad.slug + " " + ad.title).lower()
            expanded = []
            for a in areas:
                al = a.lower()
                expanded.append(al)
                if al in ("wellawatte", "wellawatt"):
                    expanded.append("wellawatha")
                    expanded.append("wellawatte")
                    expanded.append("wellawatt")
            if not any(a in haystack for a in expanded):
                continue
        if max_age_days is not None and _age_in_days(ad.posted_time) > max_age_days:
            continue
        result.append(ad)
    return result
