"""Latency of /search and /health while the documents of existing-documents-86 are uploaded in parallel.

A measurement, not a benchmark gate: it prints one LOAD line and asserts only that every request under load
succeeded and that /health kept answering. A plain run deselects it; run it with -m slow -s.

The limit on concurrent uploads, the embedder's own lane for queries and the async /health show their effect
only over real HTTP, so the requests go to the uvicorn server of the base_url fixture, on a fresh database.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings

pytestmark = pytest.mark.slow

SUITE = Path(__file__).resolve().parents[2] / 'testset' / 'suites' / 'existing-documents-86.json'
QUERIES = ['address proof', 'utility bill', 'pension transfer value', 'owner']  # searched in turn
UPLOADERS = 16  # uploads sent at once
REQUEST_TIMEOUT_S = 120  # an upload may wait for its turn
HEALTH_PAUSE_S = 0.02  # between two /health requests
MIN_PROBES = 5  # requests each probe must have measured during the uploads
IDLE_CALLS = 20  # searches, and as many /health requests, one after another once the uploads are done
HEALTH_P95_LIMIT_MS = 1000


def call(method: str, url: str, body: dict[str, Any] | None = None) -> tuple[int, float, bytes]:
    """One request on a new connection: the status, the latency in milliseconds and the response body."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, method=method, headers={'Content-Type': 'application/json'}
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as error:  # an error status is a result to record, not a failure here
        status, payload = error.code, error.read()
        error.close()
    return status, (time.perf_counter() - started) * 1000, payload


def search_url(base_url: str, n: int) -> str:
    """The n-th search of a series: the queries in turn."""
    return f'{base_url}/search?q={urllib.parse.quote(QUERIES[n % len(QUERIES)])}'


def percentile(values: list[float], share: float) -> float:
    """The value that `share` of the values lie below, to 0.1 ms."""
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * share))], 1)


def test_search_and_health_keep_answering_during_parallel_uploads(base_url: str, fresh_dsn: str) -> None:
    corpus = json.loads(SUITE.read_text(encoding='utf-8'))['corpus']
    (owner,) = corpus['clients']
    status, _, body = call('POST', f'{base_url}/clients', owner)  # the API ignores the suite's id
    assert status == 201, body
    documents_url = f'{base_url}/clients/{json.loads(body)["id"]}/documents'
    health_url = f'{base_url}/health'

    stop = threading.Event()
    search_ms: list[float] = []
    health_ms: list[float] = []
    probe_statuses: list[int] = []

    def probe_search() -> None:
        n = 0
        while not stop.is_set():
            status, ms, _ = call('GET', search_url(base_url, n))
            probe_statuses.append(status)
            search_ms.append(ms)
            n += 1

    def probe_health() -> None:
        while not stop.is_set():
            status, ms, _ = call('GET', health_url)
            probe_statuses.append(status)
            health_ms.append(ms)
            time.sleep(HEALTH_PAUSE_S)

    def upload(document: dict[str, Any]) -> tuple[int, float]:
        payload = {'title': document['title'], 'content': document['content']}
        status, ms, _ = call('POST', documents_url, payload)
        return status, ms

    probes = [threading.Thread(target=probe_search), threading.Thread(target=probe_health)]
    for probe in probes:
        probe.start()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=UPLOADERS) as uploaders:
            uploads = list(uploaders.map(upload, corpus['documents']))
        upload_wall_s = time.perf_counter() - started
    finally:
        stop.set()
        for probe in probes:
            probe.join()

    idle_search_ms = [call('GET', search_url(base_url, n))[1] for n in range(IDLE_CALLS)]
    idle_health_ms = [call('GET', health_url)[1] for _ in range(IDLE_CALLS)]

    assert len(search_ms) >= MIN_PROBES, 'the uploads ended before the probes had measured enough'
    assert len(health_ms) >= MIN_PROBES, 'the uploads ended before the probes had measured enough'
    upload_statuses = [status for status, _ in uploads]
    upload_ms = [ms for _, ms in uploads]
    health_p95_ms = percentile(health_ms, 0.95)
    result = {
        'condition': f'{UPLOADERS} parallel uploads of the {len(uploads)} documents of {SUITE.stem}, '
        'uvicorn with one worker',
        'statuses': sorted(set(upload_statuses) | set(probe_statuses)),
        'cpus': os.cpu_count(),
        'embed_threads': Settings(database_url=fresh_dsn).embed_threads,  # the settings base_url serves with
        'upload_wall_s': round(upload_wall_s, 1),
        'upload_p50_ms': percentile(upload_ms, 0.5),
        'upload_p95_ms': percentile(upload_ms, 0.95),
        'search_n': len(search_ms),
        'search_p50_ms': percentile(search_ms, 0.5),
        'search_p95_ms': percentile(search_ms, 0.95),
        'search_max_ms': round(max(search_ms), 1),
        'health_n': len(health_ms),
        'health_p50_ms': percentile(health_ms, 0.5),
        'health_p95_ms': health_p95_ms,
        'health_max_ms': round(max(health_ms), 1),
        'idle_search_p50_ms': percentile(idle_search_ms, 0.5),
        'idle_search_p95_ms': percentile(idle_search_ms, 0.95),
        'idle_health_p50_ms': percentile(idle_health_ms, 0.5),
    }
    print('\nLOAD ' + json.dumps(result))
    assert set(upload_statuses) == {201}
    assert set(probe_statuses) == {200}
    assert health_p95_ms < HEALTH_P95_LIMIT_MS, '/health must keep answering during uploads (async, no I/O)'
