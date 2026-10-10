import pytest

from pager.pagination import paginate, total_pages

ITEMS = list(range(25))


def test_first_page_returns_first_items():
    assert paginate(ITEMS, 1, per_page=10) == list(range(10))


def test_middle_page():
    assert paginate(ITEMS, 2, per_page=10) == list(range(10, 20))


def test_partial_last_page():
    assert paginate(ITEMS, 3, per_page=10) == [20, 21, 22, 23, 24]


def test_page_past_end_is_empty():
    assert paginate(ITEMS, 4, per_page=10) == []


def test_empty_items():
    assert paginate([], 1, per_page=10) == []


@pytest.mark.parametrize("page", [0, -1])
def test_paginate_rejects_page_below_one(page):
    with pytest.raises(ValueError):
        paginate(ITEMS, page, per_page=10)


@pytest.mark.parametrize("per_page", [0, -5])
def test_paginate_rejects_per_page_below_one(per_page):
    with pytest.raises(ValueError):
        paginate(ITEMS, 1, per_page=per_page)


def test_total_pages_exact_multiple():
    assert total_pages(20, per_page=10) == 2


def test_total_pages_counts_partial_last_page():
    assert total_pages(25, per_page=10) == 3


def test_total_pages_fewer_items_than_one_page():
    assert total_pages(1, per_page=10) == 1


def test_total_pages_zero_items():
    assert total_pages(0, per_page=10) == 0


def test_total_pages_rejects_negative_item_count():
    with pytest.raises(ValueError):
        total_pages(-1, per_page=10)


@pytest.mark.parametrize("per_page", [0, -5])
def test_total_pages_rejects_per_page_below_one(per_page):
    with pytest.raises(ValueError):
        total_pages(10, per_page=per_page)


def test_every_item_appears_on_exactly_one_page():
    per_page = 7
    pages = range(1, total_pages(len(ITEMS), per_page) + 1)
    shown = [item for page in pages for item in paginate(ITEMS, page, per_page)]
    assert shown == ITEMS
