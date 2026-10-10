from pager.pagination import total_pages


def test_total_pages_exact_multiple():
    assert total_pages(20, per_page=10) == 2
