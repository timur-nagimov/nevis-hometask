"""POST latency of document uploads against a running API.

Creates one client, posts the 86 documents of testset/suites/existing-documents-86.json one after another
and prints p50 / p95 / max of the POST time and how many summaries each method produced. The client and the
documents stay in the API's database, so point it at a throw-away stack, for example a second compose project:

    API_PORT=8001 docker compose -p nevis-latency up --build -d
    uv run python -m eval.post_latency --base-url http://127.0.0.1:8001
    docker compose -p nevis-latency down -v

Standard library only.
"""

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path
from typing import Any

SUITE = Path(__file__).resolve().parents[1] / 'testset' / 'suites' / 'existing-documents-86.json'
TIMEOUT_SECONDS = 60  # per request


def post(base_url: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result: dict[str, Any] = json.load(response)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='POST latency of document uploads')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    corpus = json.loads(SUITE.read_text(encoding='utf-8'))['corpus']
    owner = {'first_name': 'Latency', 'last_name': 'Probe', 'email': 'latency.probe@example.test'}
    client_id = post(args.base_url, '/clients', owner)['id']
    timings: list[float] = []
    methods: dict[str, int] = {}
    for doc in corpus['documents']:
        body = {'title': doc['title'], 'content': doc['content']}
        started = time.perf_counter()
        created = post(args.base_url, f'/clients/{client_id}/documents', body)
        timings.append((time.perf_counter() - started) * 1000)
        method = created['summary']['method']
        methods[method] = methods.get(method, 0) + 1
    cuts = statistics.quantiles(timings, n=20, method='inclusive')  # cuts[9] = p50, cuts[18] = p95
    print(
        f'documents {len(timings)}  p50 {cuts[9]:.0f} ms  p95 {cuts[18]:.0f} ms'
        f'  max {max(timings):.0f} ms  summaries {methods}'
    )


if __name__ == '__main__':
    main()
