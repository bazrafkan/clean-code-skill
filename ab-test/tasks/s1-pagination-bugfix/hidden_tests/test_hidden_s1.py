import pytest

from pager.pagination import paginate, total_pages

ITEMS = list(range(1, 26))


def test_first_page():
    assert paginate(ITEMS, 1, 10) == list(range(1, 11))


def test_second_page():
    assert paginate(ITEMS, 2, 10) == list(range(11, 21))


def test_last_partial_page():
    assert paginate(ITEMS, 3, 10) == [21, 22, 23, 24, 25]


def test_page_past_end_is_empty():
    assert paginate(ITEMS, 4, 10) == []


def test_default_per_page():
    assert paginate(ITEMS, 1) == list(range(1, 11))


def test_total_pages_partial():
    assert total_pages(25, 10) == 3


def test_total_pages_exact():
    assert total_pages(20, 10) == 2


def test_total_pages_zero():
    assert total_pages(0, 10) == 0


@pytest.mark.parametrize("page", [0, -1])
def test_invalid_page(page):
    with pytest.raises(ValueError):
        paginate(ITEMS, page, 10)


@pytest.mark.parametrize("per_page", [0, -5])
def test_invalid_per_page_paginate(per_page):
    with pytest.raises(ValueError):
        paginate(ITEMS, 1, per_page)


@pytest.mark.parametrize("per_page", [0, -5])
def test_invalid_per_page_total(per_page):
    with pytest.raises(ValueError):
        total_pages(10, per_page)


def test_negative_item_count():
    with pytest.raises(ValueError):
        total_pages(-1, 10)
