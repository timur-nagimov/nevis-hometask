"""A document can be read as soon as its 201 has arrived, checked through a real server: TestClient hands
back a response only after the application has finished, so it cannot see work that still runs once the
response is sent, such as a late commit."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn

from app.config import Settings
from app.main import create_app


@pytest.fixture
def base_url(fresh_dsn: str) -> Iterator[str]:
    """The application served by uvicorn in a thread, as `python -m app` serves it, on a loopback port the OS
    picks. The server is stopped after the test, also when the test or the start fails."""
    app = create_app(Settings(database_url=fresh_dsn))
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_config=None))
    with socket.create_server(('127.0.0.1', 0)) as listener:
        # daemon: a server that does not stop in time must not keep pytest from exiting
        thread = threading.Thread(target=server.run, args=([listener],), daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 60  # the start loads the model
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    pytest.fail('uvicorn did not start')
                time.sleep(0.05)
            host, port = listener.getsockname()
            yield f'http://{host}:{port}'
        finally:
            server.should_exit = True
            thread.join(timeout=10)


def call(method: str, url: str, body: dict[str, str] | None = None) -> tuple[int, Any]:
    """One request on a new connection: the status, and the JSON body of a success (None otherwise)."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, method=method, headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
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
    misses = 0
    for i in range(200):
        title, content = f'Call note {i}', f'Call {i}: the client asked about the pension statement.'
        status, document = call('POST', url, {'title': title, 'content': content})
        assert status == 201
        status, _ = call('GET', f'{url}/{document["id"]}')
        if status != 200:
            misses += 1
    assert misses == 0
