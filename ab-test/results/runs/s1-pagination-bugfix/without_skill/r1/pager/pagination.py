def paginate(items, page, per_page=10):
    """Return the items shown on the given 1-based page.

    A page past the end returns an empty list.
    Raises ValueError if page < 1 or per_page < 1.
    """
    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")
    _require_positive_per_page(per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def total_pages(item_count, per_page=10):
    """Return how many pages are needed to show item_count items.

    A partially filled last page counts as a page; zero items need zero pages.
    Raises ValueError if item_count < 0 or per_page < 1.
    """
    if item_count < 0:
        raise ValueError(f"item_count must be >= 0, got {item_count}")
    _require_positive_per_page(per_page)
    return -(-item_count // per_page)


def _require_positive_per_page(per_page):
    if per_page < 1:
        raise ValueError(f"per_page must be >= 1, got {per_page}")
