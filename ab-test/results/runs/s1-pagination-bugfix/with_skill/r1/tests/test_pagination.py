import pytest

from pager.pagination import paginate, total_pages

ITEMS = list(range(1, 26))  # 25 items: pages of 10, 10 and 5


def test_paginate_first_page_returns_first_items():
    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))


def test_paginate_middle_page_returns_following_items():
    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))


def test_paginate_last_partial_page_returns_remaining_items():
    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]


def test_paginate_page_past_the_end_returns_empty_list():
    assert paginate(ITEMS, 4, per_page=10) == []


def test_paginate_empty_items_returns_empty_list():
    assert paginate([], 1, per_page=10) == []


def test_paginate_uses_default_page_size():
    assert paginate(ITEMS, 1) == list(range(1, 11))


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


def test_total_pages_single_item_needs_one_page():
    assert total_pages(1, per_page=10) == 1


def test_total_pages_no_items_needs_no_pages():
    assert total_pages(0, per_page=10) == 0


@pytest.mark.parametrize("per_page", [0, -1])
def test_total_pages_rejects_per_page_below_one(per_page):
    with pytest.raises(ValueError, match="per_page"):
        total_pages(20, per_page=per_page)


def test_total_pages_rejects_negative_item_count():
    with pytest.raises(ValueError, match="item_count"):
        total_pages(-1, per_page=10)


def test_total_pages_matches_number_of_non_empty_pages():
    page_count = total_pages(len(ITEMS), per_page=10)

    assert paginate(ITEMS, page_count, per_page=10) != []
    assert paginate(ITEMS, page_count + 1, per_page=10) == []
