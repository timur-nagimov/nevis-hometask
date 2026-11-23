"""Every error is an RFC 9457 problem document.

`make_app` adds test-only routes to the real application, so that every error can be produced without a
database: a JSON body model, a query parameter, and routes that crash, raise database errors or return an
invalid response. The lifespan is not started (no `with TestClient(...)`).
"""

import json
import logging
from collections.abc import Iterator
from typing import Annotated, Any, get_args

import psycopg
import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import IntegrityError

from app.config import MAX_BODY_BYTES, RETRY_AFTER_SECONDS
from app.db import DatabaseUnavailable, Reason
from app.main import UNAVAILABLE_DETAIL, create_app, problem_doc
from app.schemas import Client

JSON = {'content-type': 'application/json'}
# Private data in error texts. Module constants, because a traceback prints the source line of the raise.
PRIVATE_ROW = (
    'null value in column "email" of relation "clients" violates not-null constraint\n'
    'DETAIL:  Failing row contains (Ann, Private-Surname).'
)
PRIVATE_CLIENT = {'id': 'not-a-uuid', 'last_name': 'Private-Surname'}


class Item(BaseModel):
    name: Annotated[str, StringConstraints(max_length=100)]
    size: int = 0


def make_app() -> FastAPI:
    app = create_app()

    @app.post('/items')
    def create_item(item: Item) -> Item:
        return item

    @app.get('/items/{item_id}')
    def get_item(item_id: str) -> Item:
        raise HTTPException(404, f"Item '{item_id}' does not exist.")

    @app.get('/find')
    def find(q: str, limit: Annotated[int, Query(ge=1, le=50)] = 10) -> list[str]:
        return []

    @app.get('/broken')
    def broken() -> None:
        raise RuntimeError('secret internals')

    @app.get('/unavailable/{reason}')
    def unavailable(reason: Reason) -> None:
        raise DatabaseUnavailable(reason)

    @app.get('/db-error')
    def db_error() -> None:
        raise IntegrityError(
            'INSERT INTO clients ...', {}, psycopg.errors.NotNullViolation(PRIVATE_ROW), hide_parameters=True
        )

    @app.get('/bad-response', response_model=Client)
    def bad_response() -> dict[str, str]:
        return PRIVATE_CLIENT

    @app.get('/down/{name}')
    def down(name: str) -> None:
        raise DatabaseUnavailable(
            'unreachable', 'InvalidPassword 28P01 password authentication failed for user "nevis"'
        )

    return app


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False: the 500 is returned to the test instead of re-raised in it
    return TestClient(make_app(), raise_server_exceptions=False)


def assert_problem(response: Response, status: int, title: str) -> dict[str, Any]:
    """The parts every problem document shares; returns the body."""
    assert response.status_code == status
    assert response.headers['content-type'] == 'application/problem+json'
    body: dict[str, Any] = response.json()
    assert (body['type'], body['title'], body['status']) == ('about:blank', title, status)
    return body


def item_of_size(size: int) -> bytes:
    """A valid JSON item of exactly `size` bytes, padded with a member the model ignores."""
    frame = len(json.dumps({'name': 'x', 'padding': ''}))
    return json.dumps({'name': 'x', 'padding': 'x' * (size - frame)}).encode()


def test_unknown_path_is_404(client: TestClient) -> None:
    body = assert_problem(client.get('/nope'), 404, 'Not Found')

    assert body == {'type': 'about:blank', 'title': 'Not Found', 'status': 404}


def test_404_raised_by_a_route_keeps_its_detail(client: TestClient) -> None:
    body = assert_problem(client.get('/items/123'), 404, 'Not Found')

    assert body['detail'] == "Item '123' does not exist."


def test_wrong_method_is_405_and_names_the_allowed_one(client: TestClient) -> None:
    response = client.delete('/items')

    assert_problem(response, 405, 'Method Not Allowed')
    assert response.headers['allow'] == 'POST'


def test_invalid_body_is_422_and_never_echoes_the_input(client: TestClient) -> None:
    response = client.post('/items', json={'name': 'a' * 101, 'size': 'a-secret-value'})

    body = assert_problem(response, 422, 'Unprocessable Content')
    assert [(e['loc'], e['type']) for e in body['errors']] == [
        (['body', 'name'], 'string_too_long'),
        (['body', 'size'], 'int_parsing'),
    ]
    assert all(set(e) == {'loc', 'msg', 'type'} for e in body['errors'])
    assert 'a-secret-value' not in response.text
    assert 'a' * 101 not in response.text


def test_invalid_query_is_422(client: TestClient) -> None:
    missing = assert_problem(client.get('/find'), 422, 'Unprocessable Content')
    too_big = assert_problem(client.get('/find?q=x&limit=51'), 422, 'Unprocessable Content')

    assert missing['errors'] == [{'loc': ['query', 'q'], 'msg': 'Field required', 'type': 'missing'}]
    assert [(e['loc'], e['type']) for e in too_big['errors']] == [(['query', 'limit'], 'less_than_equal')]


@pytest.mark.parametrize(
    'payload',
    [b'{"name": NaN}', b'{"name": "ok", "size": Infinity}', b'{"name": "Jo\\ud800hn"}'],
    ids=['NaN', 'Infinity', 'lone surrogate'],
)
def test_values_json_cannot_echo_are_422_not_500(client: TestClient, payload: bytes) -> None:
    body = assert_problem(client.post('/items', content=payload, headers=JSON), 422, 'Unprocessable Content')

    assert body['errors'][0]['loc'][0] == 'body'


@pytest.mark.parametrize(
    ('payload', 'reason'),
    [
        (b'{"name": "x",', 'Expecting property name enclosed in double quotes (character 13)'),
        (b'name=x', 'Expecting value (character 0)'),
    ],
)
def test_malformed_json_is_400(client: TestClient, payload: bytes, reason: str) -> None:
    body = assert_problem(client.post('/items', content=payload, headers=JSON), 400, 'Bad Request')

    assert body['detail'] == f'Request body is not valid JSON: {reason}.'
    assert 'errors' not in body


@pytest.mark.parametrize('content_type', ['application/x-www-form-urlencoded', 'text/plain', None])
def test_post_without_json_media_type_is_415(client: TestClient, content_type: str | None) -> None:
    headers = {'content-type': content_type} if content_type else {}

    response = client.post('/items', content=b'{"name": "x"}', headers=headers)

    body = assert_problem(response, 415, 'Unsupported Media Type')
    assert body['detail'] == 'Send the body as application/json.'
    assert response.headers['accept'] == 'application/json'


@pytest.mark.parametrize(
    'content_type', ['application/json', 'application/json; charset=utf-8', 'Application/JSON']
)
def test_json_media_type_is_accepted(client: TestClient, content_type: str) -> None:
    response = client.post('/items', content=b'{"name": "x"}', headers={'content-type': content_type})

    assert response.status_code == 200
    assert response.json() == {'name': 'x', 'size': 0}


def test_body_of_exactly_2_mib_is_accepted(client: TestClient) -> None:
    payload = item_of_size(MAX_BODY_BYTES)

    response = client.post('/items', content=payload, headers=JSON)

    assert len(payload) == 2 * 1024 * 1024
    assert response.status_code == 200


def test_body_over_2_mib_is_413(client: TestClient) -> None:
    response = client.post('/items', content=item_of_size(MAX_BODY_BYTES + 1), headers=JSON)

    # With Content-Length over the cap the framework answers before any handler, possibly as text/plain
    assert response.status_code == 413


def test_chunked_body_over_2_mib_is_413(client: TestClient) -> None:
    def pieces() -> Iterator[bytes]:  # no Content-Length: the server counts while it reads
        yield b'{"name": "x", "padding": "'
        for _ in range(40):
            yield b'x' * 65536
        yield b'"}'

    response = client.post('/items', content=pieces(), headers=JSON)

    assert response.status_code == 413


def test_unexpected_error_is_500_without_internals(client: TestClient) -> None:
    response = client.get('/broken')

    body = assert_problem(response, 500, 'Internal Server Error')
    assert body['detail'] == 'Unexpected server error.'
    assert 'secret' not in response.text
    assert 'RuntimeError' not in response.text


@pytest.mark.parametrize(
    ('reason', 'detail'),
    [
        ('unreachable', 'The database is unreachable; retry shortly.'),
        ('busy', 'The service is busy; retry shortly.'),
        ('timeout', 'The database did not answer in time; retry shortly.'),
    ],
)
def test_database_unavailable_is_503_with_retry_after(client: TestClient, reason: str, detail: str) -> None:
    response = client.get(f'/unavailable/{reason}')

    body = assert_problem(response, 503, 'Service Unavailable')
    assert body['detail'] == detail
    assert response.headers['retry-after'] == str(RETRY_AFTER_SECONDS)


def test_problem_doc_declares_a_problem_json_response_with_an_example() -> None:
    doc = problem_doc('Client does not exist', "Client '123' does not exist.", 404)

    assert doc == {
        'description': 'Client does not exist',
        'content': {
            'application/problem+json': {
                'schema': {'$ref': '#/components/schemas/Problem'},
                'example': {
                    'type': 'about:blank',
                    'title': 'Not Found',
                    'status': 404,
                    'detail': "Client '123' does not exist.",
                },
            }
        },
    }


def test_every_reason_has_a_503_detail() -> None:
    # a reason without a text would be a KeyError inside the 503 handler, that is a 500
    assert set(UNAVAILABLE_DETAIL) == set(get_args(Reason))


def test_the_503_log_line_names_the_cause_and_quotes_the_path(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger='app')

    response = client.get('/down/a%1Bb')  # an escape character in the path

    assert_problem(response, 503, 'Service Unavailable')
    assert response.headers['retry-after'] == str(RETRY_AFTER_SECONDS)
    [line] = [r.getMessage() for r in caplog.records if r.name == 'app.main']
    assert line == (
        'database unavailable (unreachable) on GET /down/a%1Bb: '
        'InvalidPassword 28P01 password authentication failed for user "nevis"'
    )


@pytest.mark.parametrize('path', ['/db-error', '/bad-response'])
def test_database_and_response_errors_are_500_and_logged_without_private_values(
    path: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    response = TestClient(make_app()).get(path)  # raise_server_exceptions on: the handler must answer itself

    body = assert_problem(response, 500, 'Internal Server Error')
    assert body['detail'] == 'Unexpected server error.'
    assert 'Private-Surname' not in caplog.text
    if path == '/db-error':
        assert 'SQLSTATE 23502' in caplog.text
