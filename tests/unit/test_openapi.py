"""docs/openapi.json is the application's schema, and it declares every status each operation can return."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.main import create_app

OPENAPI_FILE = Path(__file__).resolve().parents[2] / 'docs' / 'openapi.json'
PROBLEM_JSON = 'application/problem+json'
PROBLEM_REF = {'$ref': '#/components/schemas/Problem'}
# 500 and 503 on every operation that uses the database; /health does not use it
EXPECTED = {
    ('/clients', 'post'): {'201', '400', '413', '415', '422', '500', '503'},
    ('/clients/{}', 'get'): {'200', '404', '500', '503'},
    ('/clients/{}/documents', 'post'): {'201', '400', '404', '413', '415', '422', '500', '503'},
    ('/clients/{}/documents/{}', 'get'): {'200', '404', '500', '503'},
    ('/search', 'get'): {'200', '400', '422', '500', '503'},
    ('/health', 'get'): {'200'},
}


def _schema() -> dict[str, Any]:
    """The app's schema as JSON sees it: the file holds JSON, so JSON is compared with JSON."""
    schema: dict[str, Any] = json.loads(json.dumps(create_app().openapi()))
    return schema


def _operations(schema: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Operations keyed by (path with every {parameter} written as {}, method)."""
    return {
        (re.sub(r'\{[^}]+\}', '{}', path), method): operation
        for path, item in schema['paths'].items()
        for method, operation in item.items()
    }


def test_committed_file_is_the_app_schema() -> None:
    committed = json.loads(OPENAPI_FILE.read_text(encoding='utf-8'))
    assert committed == _schema(), 'docs/openapi.json is stale: run `uv run python scripts/export_openapi.py`'


def test_the_operations_are_the_six_of_the_contract() -> None:
    assert set(_operations(_schema())) == set(EXPECTED)


@pytest.mark.parametrize('key', sorted(EXPECTED), ids=lambda key: f'{key[1]} {key[0]}')
def test_every_status_is_declared(key: tuple[str, str]) -> None:
    assert set(_operations(_schema())[key]['responses']) == EXPECTED[key]


def test_errors_are_problem_details() -> None:
    for key, operation in _operations(_schema()).items():
        for status, response in operation['responses'].items():
            if status[0] in '45':
                assert response['content'][PROBLEM_JSON]['schema'] == PROBLEM_REF, (key, status)


def test_every_reference_resolves() -> None:
    schema = _schema()
    references = set(re.findall(r'"#/components/schemas/([^"]+)"', json.dumps(schema)))
    assert 'Problem' in references
    assert references <= set(schema['components']['schemas'])


def test_413_may_be_plain_text() -> None:
    operations = _operations(_schema())
    for key in [('/clients', 'post'), ('/clients/{}/documents', 'post')]:
        assert {'text/plain', PROBLEM_JSON} <= set(operations[key]['responses']['413']['content'])


def test_location_and_retry_after_headers_are_declared() -> None:
    operations = _operations(_schema())
    for key in [('/clients', 'post'), ('/clients/{}/documents', 'post')]:
        assert 'Location' in operations[key]['responses']['201']['headers']
    for key, statuses in EXPECTED.items():
        if '503' in statuses:
            assert 'Retry-After' in operations[key]['responses']['503']['headers']


def test_search_offers_both_assignment_examples() -> None:
    operation = _operations(_schema())[('/search', 'get')]
    q = next(parameter for parameter in operation['parameters'] if parameter['name'] == 'q')
    assert {example['value'] for example in q['examples'].values()} == {'NevisWealth', 'address proof'}
    answers = operation['responses']['200']['content']['application/json']['examples']
    assert {example['value'][0]['type'] for example in answers.values()} == {'client', 'document'}
