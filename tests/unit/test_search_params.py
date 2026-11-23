"""The /search parameters, the client search item and OpenAPI; no database."""

import asyncio
import inspect
import unicodedata

import pytest
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from starlette.requests import Request

from app.config import Settings
from app.main import create_app, require_utf8_query
from app.schemas import ClientSearchItem, QueryText

QUERY = TypeAdapter(QueryText)
CONTROL = [chr(c) for c in range(0x110000) if unicodedata.category(chr(c)) == 'Cc']
ITEM = {
    'score': 0.85,
    'match_type': 'exact',
    'id': '019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11',
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john.doe@neviswealth.com',
    'description': '',
    'social_links': [],
}


@pytest.mark.parametrize(
    ('raw', 'value'),
    [
        ('NevisWealth', 'NevisWealth'),
        ('\tJohn\n Doe  ', 'John Doe'),
        ('a\x0bb\x0cc', 'a b c'),
        ('x' * 200, 'x' * 200),
        ('a' + ' ' * 300 + 'b', 'a b'),  # the length limit applies after collapsing
        ('Zero\u200bWidth', 'Zero\u200bWidth'),  # category Cf is allowed
        ("' OR 1=1 --", "' OR 1=1 --"),
    ],
)
def test_valid_q_is_collapsed_and_trimmed(raw: str, value: str) -> None:
    assert QUERY.validate_python(raw) == value


@pytest.mark.parametrize('raw', ['', '   ', ' \t\n   ', '\u00a0\u3000', 'x' * 201, 'a ' * 100 + 'b'])
def test_empty_or_too_long_q_is_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        QUERY.validate_python(raw)


@pytest.mark.parametrize('char', CONTROL, ids=lambda c: f'U+{ord(c):04X}')
def test_control_characters_in_q(char: str) -> None:
    raw = f'john{char}doe'
    if char.isspace():  # tab, newline, U+000B-U+000D, U+001C-U+001F, U+0085: collapsed like a space
        assert QUERY.validate_python(raw) == 'john doe'
    else:
        with pytest.raises(ValidationError):
            QUERY.validate_python(raw)


def request_with(query_string: bytes) -> Request:
    scope = {'type': 'http', 'method': 'GET', 'path': '/search', 'headers': [], 'query_string': query_string}
    return Request(scope)


def test_utf8_check_needs_no_worker_thread() -> None:
    assert inspect.iscoroutinefunction(require_utf8_query)


@pytest.mark.parametrize('query_string', [b'q=%FF', b'q=%ED%A0%BD', b'q=John%C3', b'q=ok&type=%FF'])
def test_query_string_not_utf8_is_400(query_string: bytes) -> None:
    with pytest.raises(HTTPException) as info:
        asyncio.run(require_utf8_query(request_with(query_string)))
    assert (info.value.status_code, info.value.detail) == (400, 'The query string is not valid UTF-8.')


@pytest.mark.parametrize(
    'query_string', [b'q=NevisWealth', b'q=Zo%C3%AB+M%C3%BCller', b'q=%25', b'q=100%', b'']
)
def test_utf8_query_string_passes(query_string: bytes) -> None:
    asyncio.run(require_utf8_query(request_with(query_string)))


def test_client_search_item_is_flat_with_the_metadata_first() -> None:
    item = ClientSearchItem.model_validate(ITEM)
    assert item.type == 'client'
    assert list(item.model_dump(mode='json')) == [
        'type',
        'score',
        'match_type',
        'id',
        'first_name',
        'last_name',
        'email',
        'description',
        'social_links',
    ]


@pytest.mark.parametrize(
    'bad', [{'match_type': 'lexical'}, {'score': 1.5}, {'score': -0.1}, {'type': 'document'}]
)
def test_client_search_item_rejects_bad_metadata(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ClientSearchItem.model_validate({**ITEM, **bad})


def test_openapi_declares_the_statuses_of_the_routes() -> None:
    spec = create_app(Settings(database_url='postgresql://unused/x')).openapi()
    paths = spec['paths']
    assert {'201', '400', '413', '415', '422'} <= set(paths['/clients']['post']['responses'])
    assert '404' in paths['/clients/{client_id}']['get']['responses']
    assert {'200', '400', '422'} <= set(paths['/search']['get']['responses'])
    assert [p['name'] for p in paths['/search']['get']['parameters']] == ['q', 'type', 'limit']
    assert 'Problem' in spec['components']['schemas']


def test_openapi_errors_are_problem_json_also_after_a_late_route() -> None:
    app = create_app(Settings(database_url='postgresql://unused/x'))
    spec = app.openapi()
    assert '422' not in spec['paths']['/clients/{client_id}']['get']['responses']  # a string id cannot fail
    for operations in spec['paths'].values():
        for operation in operations.values():
            if '422' in operation['responses']:
                assert set(operation['responses']['422']['content']) == {'application/problem+json'}
    assert not {'HTTPValidationError', 'ValidationError'} & set(spec['components']['schemas'])

    @app.get('/later/{item_id}')
    def later(item_id: str) -> None: ...

    spec = app.openapi()
    assert '422' not in spec['paths']['/later/{item_id}']['get']['responses']
    assert 'HTTPValidationError' not in spec['components']['schemas']
