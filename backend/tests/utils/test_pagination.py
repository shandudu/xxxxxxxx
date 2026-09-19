from dataclasses import dataclass

from backend.common.pagination import _CustomCursorPage, _CustomPage, _page_data_with_raw_items


@dataclass
class _MappedRow:
    id: int
    category_id: int


def test_page_serialization_preserves_orm_like_items() -> None:
    row = _MappedRow(id=1, category_id=7)
    page = _CustomPage(
        items=[row], total=1, page=1, size=20, total_pages=1,
        links={'first': '/?page=1', 'last': '/?page=1', 'self': '/?page=1'},
    )

    data = _page_data_with_raw_items(page)

    assert data['items'][0] is row
    assert data['items'][0].category_id == 7
    assert data['total'] == 1
    assert data['page'] == 1


def test_cursor_page_serialization_preserves_orm_like_items() -> None:
    row = _MappedRow(id=2, category_id=9)
    page = _CustomCursorPage(items=[row], next_cursor='next-token', has_more=True)

    data = _page_data_with_raw_items(page)

    assert data['items'][0] is row
    assert data['items'][0].id == 2
    assert data['next_cursor'] == 'next-token'
    assert data['has_more'] is True
