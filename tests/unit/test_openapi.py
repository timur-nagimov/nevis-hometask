"""docs/openapi.json is the application's schema, and it declares every status each operation can return."""

import json
import re
from pathlib import Path
from typing import Any

from app.main import create_app

OPENAPI_FILE = Path(__file__).resolve().parents[2] / 'docs' / 'openapi.json'
PROBLEM_JSON = 'application/problem+json'
PROBLEM_REF = {'$ref': '#/components/schemas/Problem'}
# 500 and 503 on every operation that uses the database; /health does not use it
EXPECTED = {
    ('/clients', 'post'): {'201', '400', '413', '415', '422', '500', '503'},
    ('/clients/{client_id}', 'get'): {'200', '404', '500', '503'},
    ('/clients/{client_id}/documents', 'post'): {'201', '400', '404', '413', '415', '422', '500', '503'},
    ('/clients/{client_id}/documents/{document_id}', 'get'): {'200', '404', '500', '503'},
    ('/search', 'get'): {'200', '400', '422', '500', '503'},
    ('/health', 'get'): {'200'},
}


def _schema() -> dict[str, Any]:
    return create_app().openapi()


def _operations(schema: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Operations keyed by (path, method)."""
    return {
        (path, method): operation
        for path, item in schema['paths'].items()
        for method, operation in item.items()
    }


def test_committed_file_is_the_app_schema() -> None:
    committed = json.loads(OPENAPI_FILE.read_text(encoding='utf-8'))
    assert committed == _schema(), 'docs/openapi.json is stale: run `uv run python scripts/export_openapi.py`'


def test_each_operation_declares_exactly_the_statuses_it_can_return() -> None:
    declared = {key: set(operation['responses']) for key, operation in _operations(_schema()).items()}
    assert declared == EXPECTED


def test_errors_are_problem_details() -> None:
    for key, operation in _operations(_schema()).items():
        for status, response in operation['responses'].items():
            if status[0] in '45':
                assert response['content'][PROBLEM_JSON]['schema'] == PROBLEM_REF, (key, status)
            if status == '422':
                assert set(response['content']) == {PROBLEM_JSON}, key


def test_every_reference_resolves() -> None:
    schema = _schema()
    references = set(re.findall(r'"#/components/schemas/([^"]+)"', json.dumps(schema)))
    assert 'Problem' in references
    assert references <= set(schema['components']['schemas'])


def test_413_may_be_plain_text() -> None:
    operations = _operations(_schema())
    for key in [('/clients', 'post'), ('/clients/{client_id}/documents', 'post')]:
        assert {'text/plain', PROBLEM_JSON} <= set(operations[key]['responses']['413']['content'])


def test_location_and_retry_after_headers_are_declared() -> None:
    operations = _operations(_schema())
    for key in [('/clients', 'post'), ('/clients/{client_id}/documents', 'post')]:
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
