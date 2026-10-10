import pytest

from pager.pagination import paginate, total_pages


ITEMS = list(range(1, 26))  # 25 items: 1..25


def test_total_pages_exact_multiple():
    assert total_pages(20, per_page=10) == 2


def test_total_pages_counts_partial_last_page():
    assert total_pages(21, per_page=10) == 3
    assert total_pages(1, per_page=10) == 1


def test_total_pages_zero_items():
    assert total_pages(0, per_page=10) == 0


@pytest.mark.parametrize("per_page", [0, -1])
def test_total_pages_rejects_invalid_per_page(per_page):
    with pytest.raises(ValueError):
        total_pages(10, per_page=per_page)


def test_total_pages_rejects_negative_item_count():
    with pytest.raises(ValueError):
        total_pages(-1, per_page=10)


def test_paginate_first_page_starts_at_first_item():
    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))


def test_paginate_middle_page():
    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))


def test_paginate_partial_last_page():
    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]


def test_paginate_past_the_end_is_empty():
    assert paginate(ITEMS, 4, per_page=10) == []


def test_every_item_appears_on_exactly_one_page():
    pages = total_pages(len(ITEMS), per_page=10)
    collected = [x for p in range(1, pages + 1) for x in paginate(ITEMS, p, 10)]
    assert collected == ITEMS


@pytest.mark.parametrize("page", [0, -1])
def test_paginate_rejects_invalid_page(page):
    with pytest.raises(ValueError):
        paginate(ITEMS, page, per_page=10)


@pytest.mark.parametrize("per_page", [0, -1])
def test_paginate_rejects_invalid_per_page(per_page):
    with pytest.raises(ValueError):
        paginate(ITEMS, 1, per_page=per_page)
