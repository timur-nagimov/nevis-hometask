"""A document can be read as soon as its 201 has arrived. The check needs a real server: TestClient hands
back a response only after the application has finished, so it cannot see work that still runs once the
response is sent, such as a late commit."""

import json
import urllib.error
import urllib.request
from typing import Any


def call(method: str, url: str, body: dict[str, str] | None = None) -> tuple[int, Any]:
    """One request on a new connection: the status, and the JSON body of a success (None otherwise)."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, method=method, headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        error.close()
        return error.code, None


def test_get_right_after_post_finds_the_document_200_times(base_url: str) -> None:
    status, john = call(
        'POST',
        f'{base_url}/clients',
        {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'},
    )
    assert status == 201
    url = f'{base_url}/clients/{john["id"]}/documents'
    note = {'title': 'Call note', 'content': 'The client asked about the pension statement.'}
    for _ in range(200):
        status, document = call('POST', url, note)
        assert status == 201
        status, _ = call('GET', f'{url}/{document["id"]}')
        assert status == 200
