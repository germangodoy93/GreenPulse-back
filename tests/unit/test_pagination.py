"""Unit tests for shared/utils/pagination.py."""

from src.shared.utils.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PaginationParams


class TestPaginationParams:
    def test_offset_first_page_is_zero(self) -> None:
        params = PaginationParams(page=1, page_size=10)
        assert params.offset == 0

    def test_offset_second_page(self) -> None:
        params = PaginationParams(page=2, page_size=10)
        assert params.offset == 10

    def test_offset_third_page(self) -> None:
        params = PaginationParams(page=3, page_size=20)
        assert params.offset == 40

    def test_limit_equals_page_size(self) -> None:
        params = PaginationParams(page=1, page_size=25)
        assert params.limit == 25

    def test_large_page(self) -> None:
        params = PaginationParams(page=100, page_size=50)
        assert params.offset == 4950

    def test_default_constants_are_valid(self) -> None:
        assert DEFAULT_PAGE_SIZE > 0
        assert MAX_PAGE_SIZE >= DEFAULT_PAGE_SIZE
