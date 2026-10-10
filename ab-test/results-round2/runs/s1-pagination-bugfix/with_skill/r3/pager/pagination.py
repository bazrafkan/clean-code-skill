def paginate(items, page, per_page=10):
    """Return the items shown on the given 1-based page; empty past the last page."""
    if page < 1:
        raise ValueError(f"page must be at least 1, got {page}")
    _check_per_page(per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def total_pages(item_count, per_page=10):
    """Return how many pages are needed to show item_count items."""
    if item_count < 0:
        raise ValueError(f"item_count must not be negative, got {item_count}")
    _check_per_page(per_page)
    full_pages, leftover_items = divmod(item_count, per_page)
    return full_pages + 1 if leftover_items else full_pages


def _check_per_page(per_page):
    if per_page < 1:
        raise ValueError(f"per_page must be at least 1, got {per_page}")
