"""POST and GET documents through the API: what is stored, the 404s, and the rules for the request body."""

from typing import Any
from uuid import UUID

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select

from app.config import EXTRACTIVE, MAX_BODY_BYTES, MAX_ECHOED_ID_CHARS, TAGS_CHUNK_NO, Services, Settings
from app.db import DocumentChunkRow, DocumentRow
from app.main import create_app
from tests.integration.helpers import post_client, post_document

UTILITY = (
    'British Gas utility bill for March 2025. '
    'Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.'
)
PASSPORT = 'Copy of the passport of John Doe, United Kingdom. Passport number 533401372, expires 12 May 2031.'
UNKNOWN = '00000000-0000-0000-0000-000000000000'


@pytest.fixture(scope='module')
def john(app_client: TestClient) -> dict[str, Any]:
    return post_client(app_client, first_name='John', last_name='Doe', email='john.doe@neviswealth.com')


def chunk_numbers(engine: Engine, document_id: str) -> list[int]:
    """The chunk numbers stored for a document, in order."""
    statement = (
        select(DocumentChunkRow.chunk_no)
        .where(DocumentChunkRow.document_id == UUID(document_id))
        .order_by(DocumentChunkRow.chunk_no)
    )
    with engine.connect() as conn:
        return list(conn.execute(statement).scalars())


def test_post_answers_201_with_location_tags_and_summary(
    app_client: TestClient, john: dict[str, Any]
) -> None:
    response = app_client.post(
        f'/clients/{john["id"]}/documents', json={'title': '  Utility bill ', 'content': UTILITY}
    )

    assert response.status_code == 201
    document = response.json()
    assert response.headers['location'] == f'/clients/{john["id"]}/documents/{document["id"]}'
    assert list(document) == ['id', 'client_id', 'title', 'content', 'created_at', 'tags', 'summary']
    assert document['title'] == 'Utility bill'
    assert (document['client_id'], document['content']) == (john['id'], UTILITY)
    assert document['tags'] == ['proof of address', 'customer due diligence']
    assert document['summary'] == {'text': UTILITY, 'method': EXTRACTIVE}
    assert document['created_at'].endswith('Z')
    assert app_client.get(response.headers['location']).json() == document


def test_a_short_tagged_document_gets_a_content_chunk_and_a_tags_chunk(
    app_client: TestClient, services: Services, john: dict[str, Any]
) -> None:
    document = post_document(app_client, john['id'], 'Utility bill', UTILITY)

    assert chunk_numbers(services.engine, document['id']) == [TAGS_CHUNK_NO, 0]


def test_540_words_give_three_chunks_and_no_tags_chunk(
    app_client: TestClient, services: Services, john: dict[str, Any]
) -> None:
    paragraph = ' '.join(['The adviser reviewed the pension statement with the client.'] * 10)  # 90 words

    document = post_document(app_client, john['id'], 'Annual review notes', '\n\n'.join([paragraph] * 6))

    assert document['tags'] == ['proof of assets', 'retirement planning documents']
    assert chunk_numbers(services.engine, document['id']) == [0, 1, 2]


def test_the_stored_vector_embeds_title_newline_chunk(
    app_client: TestClient, services: Services, john: dict[str, Any]
) -> None:
    document = post_document(app_client, john['id'], 'Passport', PASSPORT)
    expected = services.embedder.embed_documents([f'Passport\n{PASSPORT}'])[0]
    statement = select(DocumentChunkRow.embedding).where(
        DocumentChunkRow.document_id == UUID(document['id']), DocumentChunkRow.chunk_no == 0
    )

    with services.engine.connect() as conn:
        stored = conn.execute(statement).scalar_one()

    assert np.allclose(stored, expected, atol=1e-5)


@pytest.mark.parametrize('client_id', [UNKNOWN, 'x' * (MAX_ECHOED_ID_CHARS + 1)])
def test_an_unknown_or_malformed_client_is_404(app_client: TestClient, client_id: str) -> None:
    response = app_client.post(f'/clients/{client_id}/documents', json={'title': 'Note', 'content': 'Text.'})

    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/problem+json')
    assert response.json()['detail'] == f"Client '{client_id[:MAX_ECHOED_ID_CHARS]}' does not exist."


@pytest.mark.parametrize(
    'body',
    [
        {'title': 'Two\nlines', 'content': 'Text.'},
        {'title': 'Note', 'content': 'secret\x00text'},
        {'content': 'Text.'},
    ],
)
def test_invalid_bodies_are_422_and_not_echoed(
    app_client: TestClient, john: dict[str, Any], body: dict[str, str]
) -> None:
    response = app_client.post(f'/clients/{john["id"]}/documents', json=body)

    assert response.status_code == 422
    assert response.json()['errors']
    assert 'secret' not in response.text and 'lines' not in response.text


def test_validation_comes_before_the_client_lookup(app_client: TestClient, services: Services) -> None:
    too_long = 'x' * (services.settings.max_content_chars + 1)

    for body in ({'title': '', 'content': 'Text.'}, {'title': 'Long', 'content': too_long}):
        assert app_client.post(f'/clients/{UNKNOWN}/documents', json=body).status_code == 422


def test_content_over_max_content_chars_is_422(
    app_client: TestClient, services: Services, john: dict[str, Any]
) -> None:
    url = f'/clients/{john["id"]}/documents'
    limit = services.settings.max_content_chars
    longest = ('word ' * limit)[:limit]  # words, exactly `limit` characters

    accepted = app_client.post(url, json={'title': 'Long', 'content': longest})
    rejected = app_client.post(url, json={'title': 'Long', 'content': longest + 'x'})

    assert accepted.status_code == 201
    assert rejected.status_code == 422
    [error] = rejected.json()['errors']
    assert (error['loc'], error['type']) == (['body', 'content'], 'string_too_long')
    assert 'word' not in rejected.text


def test_media_type_json_syntax_and_size(app_client: TestClient, john: dict[str, Any]) -> None:
    url = f'/clients/{john["id"]}/documents'
    as_text = {'Content-Type': 'text/plain'}
    as_json = {'Content-Type': 'application/json'}
    big = b'{"title": "x", "content": "' + b'y' * MAX_BODY_BYTES + b'"}'

    assert app_client.post(url, content=b'{"title": "x"}', headers=as_text).status_code == 415
    assert app_client.post(url, content=b'{"title": ', headers=as_json).status_code == 400
    assert app_client.post(url, content=big, headers=as_json).status_code == 413


def test_get_is_404_for_another_client_and_for_unknown_ids(
    app_client: TestClient, john: dict[str, Any]
) -> None:
    document = post_document(app_client, john['id'], 'Passport', PASSPORT)
    jane = post_client(app_client, first_name='Jane', last_name='Smith', email='jane@example.com')
    assert app_client.get(f'/clients/{john["id"]}/documents/{document["id"]}').status_code == 200

    long_id = 'x' * (MAX_ECHOED_ID_CHARS + 1)
    for client_id, document_id in [
        (jane['id'], document['id']),  # another client's document
        (john['id'], UNKNOWN),
        (john['id'], long_id),
        ('not-a-uuid', document['id']),
    ]:
        response = app_client.get(f'/clients/{client_id}/documents/{document_id}')
        assert response.status_code == 404
        assert response.json()['detail'] == f"Document '{document_id[:MAX_ECHOED_ID_CHARS]}' does not exist."


def test_an_empty_concepts_file_setting_disables_tagging(fresh_dsn: str) -> None:
    app = create_app(Settings(database_url=fresh_dsn, concepts_file=''))
    with TestClient(app) as client:
        owner = post_client(client, first_name='John', last_name='Doe', email='john.doe@neviswealth.com')
        document = post_document(client, owner['id'], 'Utility bill', UTILITY)
        engine = app.state.services.engine
        chunks = chunk_numbers(engine, document['id'])
        statement = select(DocumentRow.tags_text).where(DocumentRow.id == UUID(document['id']))
        with engine.connect() as conn:
            tags_text = conn.execute(statement).scalar_one()

    assert document['tags'] == []
    assert (chunks, tags_text) == ([0], '')
