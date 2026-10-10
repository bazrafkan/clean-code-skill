import math


def paginate(items, page, per_page=10):
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be >= 1")
    start = (page - 1) * per_page
    return items[start:start + per_page]


def total_pages(item_count, per_page=10):
    if per_page < 1 or item_count < 0:
        raise ValueError("invalid arguments")
    return math.ceil(item_count / per_page)
