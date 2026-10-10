def paginate(items, page, per_page=10):
    """Return the items shown on the given page."""
    start = page * per_page
    end = start + per_page
    return items[start:end]


def total_pages(item_count, per_page=10):
    """Return how many pages are needed to show item_count items."""
    return item_count // per_page
