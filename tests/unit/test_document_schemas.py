"""DocumentCreate validation and the Document built from a stored row; no database."""

import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.config import EXTRACTIVE, MAX_TITLE_CHARS
from app.schemas import Document, DocumentCreate

BILL = {'title': 'Utility bill', 'content': 'British Gas bill.'}
# Every character of Unicode category Cc: the "control characters" that the API rejects.
CONTROL = [chr(c) for c in range(sys.maxunicode + 1) if unicodedata.category(chr(c)) == 'Cc']


def rejected(**fields: object) -> set[object]:
    """Validate BILL updated with `fields`; return the top-level field of every error."""
    with pytest.raises(ValidationError) as info:
        DocumentCreate.model_validate({**BILL, **fields})
    return {error['loc'][0] for error in info.value.errors()}


def test_the_title_is_trimmed_and_the_content_kept_as_sent() -> None:
    body = DocumentCreate.model_validate({'title': '  Utility bill \t', 'content': '  padded\r\n  '})
    assert (body.title, body.content) == ('Utility bill', '  padded\r\n  ')


def test_the_longest_title_is_accepted() -> None:
    title = 'x' * MAX_TITLE_CHARS
    assert DocumentCreate.model_validate({**BILL, 'title': title}).title == title


@pytest.mark.parametrize(
    'title',
    [
        '',
        '   ',
        'x' * (MAX_TITLE_CHARS + 1),
        'Utility\nbill',
        'Utility\tbill',
        'Utility\x00bill',
        'Utility\x85bill',
    ],
)
def test_bad_titles_are_rejected(title: str) -> None:
    assert rejected(title=title) == {'title'}


@pytest.mark.parametrize('content', ['', ' \n\t '])
def test_empty_or_blank_content_is_rejected(content: str) -> None:
    assert rejected(content=content) == {'content'}


@pytest.mark.parametrize('char', [c for c in CONTROL if c not in '\t\n\r'], ids=lambda c: f'U+{ord(c):04X}')
def test_other_control_characters_in_content_are_rejected(char: str) -> None:
    assert rejected(content=f'bi{char}ll') == {'content'}


@pytest.mark.parametrize('content', ['one\ntwo', 'a\tb', 'windows\r\nline', 'zero\N{ZERO WIDTH SPACE}width'])
def test_tab_line_feed_carriage_return_and_format_characters_are_allowed_in_content(content: str) -> None:
    assert DocumentCreate.model_validate({**BILL, 'content': content}).content == content


def test_unknown_members_are_ignored() -> None:
    body = DocumentCreate.model_validate({**BILL, 'id': '123', 'tags': ['vip']})
    assert set(body.model_dump()) == {'title', 'content'}


def test_a_stored_row_becomes_the_api_shape_with_a_utc_timestamp() -> None:
    row = {
        'id': uuid4(),
        'client_id': uuid4(),
        'title': 'Utility bill',
        'content': 'Text.',
        'created_at': datetime(2026, 11, 22, 11, 0, tzinfo=timezone(timedelta(hours=1))),
        'tags': ['proof of address'],
        'summary': 'Text.',
        'summary_method': EXTRACTIVE,
    }

    data = Document.from_row(row).model_dump(mode='json')

    assert list(data) == ['id', 'client_id', 'title', 'content', 'created_at', 'tags', 'summary']
    assert data['created_at'] == '2026-11-22T10:00:00Z'
    assert data['summary'] == {'text': 'Text.', 'method': EXTRACTIVE}
