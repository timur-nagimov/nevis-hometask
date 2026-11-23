"""Which path ids name a client: only a canonical UUID, in either letter case."""

import uuid

import pytest

from app.main import parse_id

ID = '019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11'


@pytest.mark.parametrize('raw', [ID, ID.upper()])
def test_canonical_uuid_is_parsed_in_either_case(raw: str) -> None:
    assert parse_id(raw) == uuid.UUID(ID)


@pytest.mark.parametrize(
    'raw',
    ['{' + ID + '}', 'urn:uuid:' + ID, ID.replace('-', ''), ' ' + ID, ID + ' ', '123', ''],
)
def test_other_spellings_are_unknown_ids(raw: str) -> None:
    assert parse_id(raw) is None
