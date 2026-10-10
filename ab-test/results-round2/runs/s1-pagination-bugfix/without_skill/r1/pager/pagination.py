def paginate(items, page, per_page=10):
    """Return the items shown on the given 1-based page.

    A page past the end returns an empty list.
    Raises ValueError if page or per_page is less than 1.
    """
    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")
    if per_page < 1:
        raise ValueError(f"per_page must be >= 1, got {per_page}")
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def total_pages(item_count, per_page=10):
    """Return how many pages are needed to show item_count items.

    A partially filled last page counts as a page; 0 items need 0 pages.
    Raises ValueError if per_page is less than 1 or item_count is negative.
    """
    if per_page < 1:
        raise ValueError(f"per_page must be >= 1, got {per_page}")
    if item_count < 0:
        raise ValueError(f"item_count must be >= 0, got {item_count}")
    return -(-item_count // per_page)
