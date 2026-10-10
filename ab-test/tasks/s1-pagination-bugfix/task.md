Users report two bugs in `pager/pagination.py`: page 1 skips the first items, and the last, partially filled page is never counted. Fix them.

Expected behavior:
- `page` is 1-based: `paginate(items, 1, per_page)` returns the first `per_page` items.
- A page past the end returns an empty list.
- `total_pages(item_count, per_page)` counts a partially filled last page. `total_pages(0, per_page)` is 0.
- Invalid input raises `ValueError`: `page < 1` or `per_page < 1` in `paginate`; `per_page < 1` or a negative `item_count` in `total_pages`.
