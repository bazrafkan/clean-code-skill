import pytest

from pager.pagination import paginate, total_pages


ITEMS = list(range(25))


def test_total_pages_exact_multiple():
    assert total_pages(20, per_page=10) == 2


def test_total_pages_counts_partial_last_page():
    assert total_pages(25, per_page=10) == 3
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
    assert paginate(ITEMS, 1, per_page=10) == list(range(10))


def test_paginate_middle_page():
    assert paginate(ITEMS, 2, per_page=10) == list(range(10, 20))


def test_paginate_partial_last_page():
    assert paginate(ITEMS, 3, per_page=10) == list(range(20, 25))


def test_paginate_past_the_end_is_empty():
    assert paginate(ITEMS, 4, per_page=10) == []


def test_paginate_empty_items():
    assert paginate([], 1, per_page=10) == []


@pytest.mark.parametrize("page", [0, -1])
def test_paginate_rejects_invalid_page(page):
    with pytest.raises(ValueError):
        paginate(ITEMS, page, per_page=10)


@pytest.mark.parametrize("per_page", [0, -1])
def test_paginate_rejects_invalid_per_page(per_page):
    with pytest.raises(ValueError):
        paginate(ITEMS, 1, per_page=per_page)


def test_every_page_up_to_total_is_non_empty_and_covers_all_items():
    pages = total_pages(len(ITEMS), per_page=10)
    collected = []
    for page in range(1, pages + 1):
        chunk = paginate(ITEMS, page, per_page=10)
        assert chunk
        collected.extend(chunk)
    assert collected == ITEMS
