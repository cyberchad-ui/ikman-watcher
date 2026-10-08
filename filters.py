from scraper import Ad


def apply_filters(
    ads: list[Ad],
    price_min: int,
    price_max: int,
    beds_min: int,
    beds_max: int,
) -> list[Ad]:
    return [
        ad for ad in ads
        if price_min <= ad.price <= price_max
        and beds_min <= ad.beds <= beds_max
    ]
