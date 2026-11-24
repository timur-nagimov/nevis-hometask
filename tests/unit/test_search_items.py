"""DocumentSearchItem and the SearchItem union: flat items, discriminated by `type`."""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.config import EXTRACTIVE
from app.schemas import ClientSearchItem, DocumentSearchItem, SearchItem

ITEM = TypeAdapter(SearchItem)
DOCUMENT = {
    'type': 'document',
    'score': 0.7382,
    'match_type': 'concept',
    'id': '019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e12',
    'client_id': '019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11',
    'title': 'Utility bill',
    'content': 'British Gas utility bill for March 2025.',
    'created_at': '2026-11-22T10:00:00Z',
    'tags': ['proof of address', 'customer due diligence'],
    'summary': {'text': 'British Gas utility bill for March 2025.', 'method': EXTRACTIVE},
}
CLIENT = {
    'type': 'client',
    'score': 0.85,
    'match_type': 'exact',
    'id': '019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11',
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john.doe@neviswealth.com',
    'description': '',
    'social_links': [],
}


def test_document_item_is_flat_with_the_search_fields_first() -> None:
    item = DocumentSearchItem.model_validate(DOCUMENT)
    assert list(item.model_dump(mode='json')) == [
        'type',
        'score',
        'match_type',
        'id',
        'client_id',
        'title',
        'content',
        'created_at',
        'tags',
        'summary',
    ]


def test_type_picks_the_model() -> None:
    assert isinstance(ITEM.validate_python(DOCUMENT), DocumentSearchItem)
    assert isinstance(ITEM.validate_python(CLIENT), ClientSearchItem)


@pytest.mark.parametrize('bad', [{'match_type': 'exact'}, {'score': 1.5}, {'type': 'folder'}])
def test_document_item_rejects_bad_metadata(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ITEM.validate_python({**DOCUMENT, **bad})
