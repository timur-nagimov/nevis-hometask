"""eval/run_testset.py on the real database and model: a tiny hand-made suite, and tools-mini-6."""

import json
from typing import Any

import psycopg

from app.config import MAX_DESCRIPTION_CHARS, Services
from eval.metrics import Scoreboard
from eval.run_testset import SUITES_DIR, run_suite, suite_database_name

TINY: dict[str, Any] = {
    'suite': 'eval-selftest',
    'corpus': {
        'clients': [
            {
                'id': 'c1',
                'first_name': 'Ada',
                'last_name': 'Lovelace',
                'email': 'ada@example.invalid',
                'description': 'Pays the utility bill by direct debit.',  # q3 asks for documents only
            },
            {
                'id': 'c2',
                'first_name': 'Too',
                'last_name': 'Long',
                'email': 'too.long@example.com',
                'description': 'x' * (MAX_DESCRIPTION_CHARS + 1),  # the API rejects it
            },
        ],
        'documents': [
            {'id': 'd1', 'client_id': 'c1', 'title': 'Utility bill', 'content': 'Electricity bill, March.'},
            {'id': 'd2', 'client_id': 'c2', 'title': 'Orphan', 'content': 'Its client was skipped.'},
        ],
    },
    'queries': [
        {'id': 'q1', 'q': 'Lovelace', 'level': 'required', 'scope': 'clients', 'relevant': ['c1']},
        {'id': 'q2', 'q': '   ', 'level': 'expected', 'empty': True},  # the API answers 422
        {'id': 'q3', 'q': 'utility bill', 'level': 'required', 'scope': 'documents', 'relevant': ['d1']},
    ],
}


def database_exists(admin_dsn: str, name: str) -> bool:
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        row = conn.execute('SELECT 1 FROM pg_database WHERE datname = %s', (name,)).fetchone()
    return row is not None


def test_run_suite_skips_what_the_api_rejects_and_maps_ids_back(services: Services, admin_dsn: str) -> None:
    run = run_suite(TINY, admin_dsn, services.settings, services.embedder, services.concepts)

    assert run.skipped == ['eval-selftest/c2 (description)', 'eval-selftest/d2 (client not loaded)']
    assert (run.clients, run.documents) == (1, 1)
    assert run.results == {'q1': ['c1'], 'q2': [], 'q3': ['d1']}
    assert not database_exists(admin_dsn, suite_database_name('eval-selftest'))


def test_tools_mini_6_gives_the_measured_result(services: Services, admin_dsn: str) -> None:
    suite = json.loads((SUITES_DIR / 'tools-mini-6.json').read_text(encoding='utf-8'))
    run = run_suite(suite, admin_dsn, services.settings, services.embedder, services.concepts)
    tally, failed = Scoreboard().add_suite(suite, run.results)

    # address proof and proof of address (q010, q011) also find the courier's proof of delivery, the typo
    # utilty bill (q013) misses the scanned bill, and proof of income (q015) also finds the tax return
    assert sorted(query['id'] for query, _ in failed) == ['q010', 'q011', 'q013', 'q015']
    assert (tally.passed, tally.total) == (12, 16)
