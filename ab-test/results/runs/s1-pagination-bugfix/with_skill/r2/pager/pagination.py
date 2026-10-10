DEFAULT_PER_PAGE = 10


def paginate(items, page, per_page=DEFAULT_PER_PAGE):
    """Return the items shown on the given 1-based page.

    A page past the end returns an empty list.
    Raises ValueError if page or per_page is less than 1.
    """
    if page < 1:
        raise ValueError(f"page must be at least 1, got {page}")
    _validate_per_page(per_page)
    start = (page - 1) * per_page
    return items[start : start + per_page]


def total_pages(item_count, per_page=DEFAULT_PER_PAGE):
    """Return how many pages are needed to show item_count items.

    A partially filled last page counts as a page.
    Raises ValueError if item_count is negative or per_page is less than 1.
    """
    if item_count < 0:
        raise ValueError(f"item_count must not be negative, got {item_count}")
    _validate_per_page(per_page)
    full_pages, leftover_items = divmod(item_count, per_page)
    return full_pages + 1 if leftover_items else full_pages


def _validate_per_page(per_page):
    if per_page < 1:
        raise ValueError(f"per_page must be at least 1, got {per_page}")
