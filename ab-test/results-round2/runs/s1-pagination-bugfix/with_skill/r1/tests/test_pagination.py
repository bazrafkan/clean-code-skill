import pytest

from pager.pagination import paginate, total_pages

ITEMS = list(range(1, 26))


def test_paginate_first_page_starts_at_first_item():
    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))


def test_paginate_second_page_follows_first():
    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))


def test_paginate_last_page_is_partially_filled():
    assert paginate(ITEMS, 3, per_page=10) == list(range(21, 26))


def test_paginate_page_past_the_end_is_empty():
    assert paginate(ITEMS, 4, per_page=10) == []


@pytest.mark.parametrize("page", [0, -1])
def test_paginate_rejects_page_below_one(page):
    with pytest.raises(ValueError, match="page"):
        paginate(ITEMS, page, per_page=10)


@pytest.mark.parametrize("per_page", [0, -1])
def test_paginate_rejects_per_page_below_one(per_page):
    with pytest.raises(ValueError, match="per_page"):
        paginate(ITEMS, 1, per_page=per_page)


def test_total_pages_exact_multiple():
    assert total_pages(20, per_page=10) == 2


def test_total_pages_counts_partially_filled_last_page():
    assert total_pages(25, per_page=10) == 3


def test_total_pages_fewer_items_than_one_page():
    assert total_pages(1, per_page=10) == 1


def test_total_pages_no_items_is_zero():
    assert total_pages(0, per_page=10) == 0


@pytest.mark.parametrize("per_page", [0, -1])
def test_total_pages_rejects_per_page_below_one(per_page):
    with pytest.raises(ValueError, match="per_page"):
        total_pages(20, per_page=per_page)


def test_total_pages_rejects_negative_item_count():
    with pytest.raises(ValueError, match="item_count"):
        total_pages(-1, per_page=10)
