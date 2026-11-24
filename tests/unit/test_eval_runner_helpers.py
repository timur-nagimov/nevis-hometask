"""The parts of eval/run_testset.py that need no database and no model."""

import pytest

from app.config import DEFAULT_MAX_CONTENT_CHARS, MAX_DESCRIPTION_CHARS
from app.schemas import ClientCreate, DocumentCreate
from eval.run_testset import api_query, client_payload, document_payload, duration, suite_database_name


def test_the_database_is_named_after_the_suite() -> None:
    assert suite_database_name('existing-clients-skeptic-44') == 'nevis_ts_existing_clients_skeptic_44'


@pytest.mark.parametrize(
    ('raw', 'q'),
    [
        ('  John \t\n Doe ', 'John Doe'),  # collapsed and trimmed, as GET /search does
        (' \t\n ', None),  # 422: nothing is left after collapsing
        ('\ud83d', None),  # 400: a lone surrogate cannot be sent as UTF-8
    ],
)
def test_a_query_is_searched_as_the_api_reads_it_or_not_at_all(raw: str, q: str | None) -> None:
    assert api_query(raw) == q


def test_a_client_is_checked_like_its_upload() -> None:
    ada = {'id': 'c1', 'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.invalid'}
    assert isinstance(client_payload(ada), ClientCreate)
    too_long = {**ada, 'description': 'x' * (MAX_DESCRIPTION_CHARS + 1)}
    assert client_payload(too_long) == 'description'


def test_a_document_is_checked_like_its_upload() -> None:
    bill = {'id': 'd1', 'client_id': 'c1', 'title': ' Utility bill ', 'content': 'Gas, March.'}
    assert isinstance(document_payload(bill, DEFAULT_MAX_CONTENT_CHARS), DocumentCreate)
    blank = {'id': 'd2', 'client_id': 'c1', 'title': ' ', 'content': '   '}
    assert document_payload(blank, DEFAULT_MAX_CONTENT_CHARS) == 'content, title'


def test_content_over_the_limit_is_rejected_as_the_upload_route_does() -> None:
    letter = {'id': 'd3', 'client_id': 'c1', 'title': 'Letter', 'content': 'x' * 11}
    assert isinstance(document_payload(letter, 11), DocumentCreate)  # exactly the limit
    assert document_payload(letter, 10) == 'content'


def test_a_duration_is_shown_in_seconds_or_in_minutes_and_seconds() -> None:
    assert duration(41.2) == '41 s'
    assert duration(125.4) == '2 min 05 s'
