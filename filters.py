from scraper import Ad


def apply_filters(
    ads: list[Ad],
    price_min: int,
    price_max: int,
    beds_min: int,
    beds_max: int,
    areas: list[str] | None = None,
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
        result.append(ad)
    return result
