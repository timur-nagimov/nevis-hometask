"""The 57 HTTP checks of the test set (`http_cases` in testset/suites/*.json) against the real app.

The corpora of the suites with checks are posted through the API first, and a suite's client id in a check's
path (c10, c02) is replaced by the id the API created. A check passes when the response status is one of its
`expected_status`. The corpora share the module's database: no status depends on another suite's records.
Bodies are not compared: codex-mixed's expected bodies hold the suite's own ids (h14 wants `client_id` "c02"),
which an API that creates its own ids cannot return.
"""

import json
import urllib.parse
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from tests.integration.helpers import post_client, post_document

SUITES_DIR = Path(__file__).resolve().parents[2] / 'testset' / 'suites'
# Left out of the corpus: existing-clients-skeptic-44's c_long, whose description of 5,147 characters is
# longer than the API accepts.
LEFT_OUT = 'c_long'
# The test set's authors disagree on a blank q (testset/README.md): codex-mixed expects 200 and [], while
# claude-mixed (h22, h23) and existing-clients-fixture-42 (h-blank-1 to h-blank-4) expect 400 or 422.
XFAIL = {
    ('codex-mixed', 'h23'): 'codex-mixed expects 200 and [] for an empty q; the API answers 422',
    ('codex-mixed', 'h24'): 'codex-mixed expects 200 and [] for a whitespace-only q; the API answers 422',
}


def suites_with_checks() -> dict[str, dict[str, Any]]:
    """Suite name -> suite, for the suites that have HTTP checks."""
    suites = {}
    for path in sorted(SUITES_DIR.glob('*.json')):
        suite = json.loads(path.read_text(encoding='utf-8'))
        if suite['http_cases']:
            suites[path.stem] = suite
    return suites


SUITES = suites_with_checks()


def post_corpus(app_client: TestClient, corpus: dict[str, Any]) -> dict[str, str]:
    """Posts a suite's clients and documents; returns the API id of each client by its suite id."""
    ids = {}
    for record in corpus['clients']:
        if record['id'] != LEFT_OUT:
            ids[record['id']] = post_client(app_client, **record)['id']  # the API ignores the suite's id
    for record in corpus['documents']:
        post_document(app_client, ids[record['client_id']], record['title'], record['content'])
    return ids


@pytest.fixture(scope='module')
def client_ids(app_client: TestClient) -> dict[str, dict[str, str]]:
    """Suite name -> the API id of each of its clients by suite id; every suite's corpus is posted once."""
    return {name: post_corpus(app_client, suite['corpus']) for name, suite in SUITES.items()}


def send(app_client: TestClient, ids: dict[str, str], check: dict[str, Any]) -> Response:
    """Sends one check as written, with the suite's client ids in the path replaced by the API's."""
    path = '/'.join(ids.get(segment, segment) for segment in check['path'].split('/'))
    # A lone surrogate in q goes out as its (invalid) UTF-8 bytes, as a raw HTTP client would send it.
    query = urllib.parse.urlencode(check['query'], errors='surrogatepass')
    url = f'{path}?{query}' if query else path
    body = check.get('raw_body', check['body'])
    if body is None:
        return app_client.request(check['method'], url)
    text = body if isinstance(body, str) else json.dumps(body)  # a text is malformed JSON on purpose
    headers = {'Content-Type': 'application/json', **check.get('headers', {})}
    return app_client.request(check['method'], url, content=text.encode(), headers=headers)


def test_the_test_set_holds_57_http_checks() -> None:
    counts = {name: len(suite['http_cases']) for name, suite in SUITES.items()}
    assert counts == {
        'claude-mixed': 25,
        'codex-mixed': 25,
        'existing-clients-fixture-42': 4,
        'existing-clients-skeptic-44': 3,
    }


def check_params() -> list[Any]:
    """One test per check; the checks in XFAIL are expected to fail."""
    params: list[Any] = []
    for name, suite in SUITES.items():
        for check in suite['http_cases']:
            reason = XFAIL.get((name, check['id']))
            marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
            params.append(pytest.param(name, check, id=f'{name}-{check["id"]}', marks=marks))
    return params


@pytest.mark.parametrize(('suite_name', 'check'), check_params())
def test_http_check(
    app_client: TestClient, client_ids: dict[str, dict[str, str]], suite_name: str, check: dict[str, Any]
) -> None:
    response = send(app_client, client_ids[suite_name], check)
    assert response.status_code in check['expected_status'], (
        f'{check["method"]} {check["path"]}: {response.status_code} {response.text}'
    )
