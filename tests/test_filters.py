import pytest
from scraper import Ad
from filters import apply_filters


def _ad(**kwargs):
    defaults = dict(slug="x", title="t", price=60000, beds=2, baths=1,
                    category="Houses", posted_time="", url="")
    defaults.update(kwargs)
    return Ad(**defaults)


def test_keeps_ad_within_all_bounds():
    ad = _ad(price=60000, beds=2)
    assert apply_filters([ad], 50000, 75000, 1, 2) == [ad]


def test_excludes_ad_above_price_max():
    assert apply_filters([_ad(price=80000, beds=1)], 50000, 75000, 1, 2) == []


def test_excludes_ad_below_price_min():
    assert apply_filters([_ad(price=40000, beds=1)], 50000, 75000, 1, 2) == []


def test_excludes_ad_at_price_min_boundary():
    ad = _ad(price=50000, beds=1)
    assert apply_filters([ad], 50000, 75000, 1, 2) == [ad]


def test_excludes_ad_at_price_max_boundary():
    ad = _ad(price=75000, beds=2)
    assert apply_filters([ad], 50000, 75000, 1, 2) == [ad]


def test_excludes_ad_with_too_many_beds():
    assert apply_filters([_ad(price=60000, beds=3)], 50000, 75000, 1, 2) == []


def test_excludes_ad_with_zero_beds():
    assert apply_filters([_ad(price=60000, beds=0)], 50000, 75000, 1, 2) == []


def test_keeps_ad_with_one_bed():
    ad = _ad(price=60000, beds=1)
    assert apply_filters([ad], 50000, 75000, 1, 2) == [ad]


def test_filters_mixed_list():
    good = _ad(slug="good", price=60000, beds=2)
    bad_price = _ad(slug="bad-price", price=90000, beds=1)
    bad_beds = _ad(slug="bad-beds", price=60000, beds=4)
    result = apply_filters([good, bad_price, bad_beds], 50000, 75000, 1, 2)
    assert result == [good]
