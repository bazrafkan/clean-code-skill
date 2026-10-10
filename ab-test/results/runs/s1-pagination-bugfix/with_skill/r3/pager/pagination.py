def paginate(items, page, per_page=10):
    """Return the items shown on the given 1-based page.

    A page past the end returns an empty list.
    Raises ValueError if page or per_page is less than 1.
    """
    _require_at_least_one("page", page)
    _require_at_least_one("per_page", per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def total_pages(item_count, per_page=10):
    """Return how many pages are needed to show item_count items.

    A partially filled last page counts as a page.
    Raises ValueError if per_page is less than 1 or item_count is negative.
    """
    _require_at_least_one("per_page", per_page)
    if item_count < 0:
        raise ValueError(f"item_count must not be negative, got {item_count}")
    full_pages, leftover_items = divmod(item_count, per_page)
    return full_pages + (1 if leftover_items else 0)


def _require_at_least_one(name, value):
    if value < 1:
        raise ValueError(f"{name} must be at least 1, got {value}")
