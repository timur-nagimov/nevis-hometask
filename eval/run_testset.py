"""Run the test set (testset/) against the service code and print the quality tables.

In the tests container, with the database (or the whole stack) up:

    docker compose --profile test run --rm --no-deps tests python -m eval.run_testset  # concept map on
    docker compose --profile test run --rm --no-deps tests python -m eval.run_testset --no-concepts
    docker compose --profile test run --rm --no-deps tests python -m eval.run_testset --failures tools-mini-6

Every suite gets a fresh database nevis_ts_<suite> on the server of NEVIS_DATABASE_URL, dropped afterwards.
Its clients and documents are loaded through app.db.insert_client and app.ingest.create_document; a record the
API would reject is skipped and logged. Each query is validated like `q` of GET /search (a query the API
refuses counts as an empty answer) and answered by app.search.search with the largest limit and the `type` of
the query's scope. The answers are mapped back to suite ids and scored by eval.metrics. The tables go to
stdout, progress and warnings to stderr.

Two runs of the same suite on one server must not overlap: the second drops the first one's database.
"""

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter, ValidationError

from app.config import MAX_LIMIT, MODEL_REVISION, SHORT_REVISION_CHARS, Services, Settings
from app.db import create_schema, insert_client, open_engine
from app.embedding import Embedder
from app.ingest import Concepts, create_document, load_concepts
from app.schemas import ClientCreate, DocumentCreate, QueryText
from app.search import ResultType, search
from eval.metrics import Scoreboard, kinds_of, render

log = logging.getLogger('eval')

SUITES_DIR = Path(__file__).resolve().parents[1] / 'testset' / 'suites'
# the `type` of GET /search for a query's scope
TYPE_OF_SCOPE: dict[str, ResultType | None] = {'all': None, 'clients': 'client', 'documents': 'document'}
QUERY: TypeAdapter[str] = TypeAdapter(QueryText)
SHOWN_Q_CHARS = 80  # --failures shows a query up to this many characters


@dataclass
class SuiteRun:
    results: dict[str, list[str]]  # query id -> suite ids, best first
    skipped: list[str]  # '<suite>/<record id> (<why>)'
    clients: int  # loaded
    documents: int  # loaded
    load_s: float
    query_s: float


def suite_database_name(suite_name: str) -> str:
    """existing-clients-skeptic-44 -> nevis_ts_existing_clients_skeptic_44"""
    return 'nevis_ts_' + re.sub(r'[^a-z0-9]+', '_', suite_name)


def rejected_fields(exc: ValidationError) -> str:
    """The fields a validation error names, e.g. 'content, title'; never the submitted values."""
    fields = {str(error['loc'][0]) for error in exc.errors()}
    return ', '.join(sorted(fields))


def client_payload(record: dict[str, Any]) -> ClientCreate | str:
    """The body POST /clients accepts, or the fields it would reject with 422."""
    try:
        return ClientCreate.model_validate(record)
    except ValidationError as exc:
        return rejected_fields(exc)


def document_payload(record: dict[str, Any], max_chars: int) -> DocumentCreate | str:
    """The body POST /clients/{client_id}/documents accepts, or the fields it would reject with 422.

    `max_chars` is NEVIS_MAX_CONTENT_CHARS, which the route checks after the model.
    """
    try:
        payload = DocumentCreate.model_validate(record)
    except ValidationError as exc:
        return rejected_fields(exc)
    if len(payload.content) > max_chars:
        return 'content'
    return payload


def api_query(raw: str) -> str | None:
    """The q that GET /search searches for, or None when the API refuses the query.

    QueryText also refuses a lone surrogate, which the API answers with 400: the query string is not UTF-8.
    """
    try:
        return QUERY.validate_python(raw)
    except ValidationError:
        return None


def load_corpus(services: Services, suite: dict[str, Any]) -> tuple[dict[UUID, str], list[str]]:
    """Load the suite's clients and documents through the service code, skipping what the API would reject.

    Returns (created id -> suite id, skipped records).
    """
    name = suite['suite']
    to_suite: dict[UUID, str] = {}
    client_ids: dict[str, UUID] = {}  # suite id -> created id
    skipped: list[str] = []
    for record in suite['corpus']['clients']:
        client_body = client_payload(record)
        if isinstance(client_body, str):
            skipped.append(f'{name}/{record["id"]} ({client_body})')
            continue
        client = insert_client(services.engine, **client_body.model_dump())
        client_ids[record['id']] = client['id']
        to_suite[client['id']] = record['id']
    for record in suite['corpus']['documents']:
        if record['client_id'] not in client_ids:
            skipped.append(f'{name}/{record["id"]} (client not loaded)')
            continue
        document_body = document_payload(record, services.settings.max_content_chars)
        if isinstance(document_body, str):
            skipped.append(f'{name}/{record["id"]} ({document_body})')
            continue
        document = create_document(services, client_ids[record['client_id']], document_body)
        to_suite[document.id] = record['id']
    for note in skipped:
        log.warning('skipped %s: the API would reject it', note)
    return to_suite, skipped


def run_queries(services: Services, suite: dict[str, Any], to_suite: dict[UUID, str]) -> dict[str, list[str]]:
    """Every query as GET /search answers it with the largest limit, mapped back to suite ids, best first."""
    results: dict[str, list[str]] = {}
    for query in suite['queries']:
        q = api_query(query['q'])
        if q is None:
            results[query['id']] = []
            continue
        items = search(services, q, TYPE_OF_SCOPE[query.get('scope', 'all')], MAX_LIMIT)
        results[query['id']] = [to_suite[item['id']] for item in items]
    return results


def recreate_database(admin_dsn: str, name: str) -> None:
    """An empty database `name`; one left behind by an interrupted run is dropped first."""
    drop_database(admin_dsn, name)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))


def drop_database(admin_dsn: str, name: str) -> None:
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))


def run_suite(
    suite: dict[str, Any], admin_dsn: str, base: Settings, embedder: Embedder, concepts: Concepts | None
) -> SuiteRun:
    """One suite on a fresh database of its own, dropped afterwards, also after an error.

    The settings are `base` with that database.
    """
    database = suite_database_name(suite['suite'])
    url = make_conninfo(admin_dsn, dbname=database)
    settings = Settings(**{**base.model_dump(), 'database_url': url})
    recreate_database(admin_dsn, database)
    try:
        create_schema(settings)
        engine = open_engine(settings)
        try:
            services = Services(settings=settings, engine=engine, embedder=embedder, concepts=concepts)
            started = time.perf_counter()
            to_suite, skipped = load_corpus(services, suite)
            loaded = time.perf_counter()
            results = run_queries(services, suite, to_suite)
            finished = time.perf_counter()
        finally:
            engine.dispose()
    finally:
        drop_database(admin_dsn, database)
    kinds = kinds_of(suite)
    loaded_kinds = [kinds[suite_id] for suite_id in to_suite.values()]
    return SuiteRun(
        results=results,
        skipped=skipped,
        clients=loaded_kinds.count('client'),
        documents=loaded_kinds.count('document'),
        load_s=loaded - started,
        query_s=finished - loaded,
    )


def duration(seconds: float) -> str:
    """41 s, or 2 min 05 s."""
    minutes, rest = divmod(round(seconds), 60)
    return f'{minutes} min {rest:02d} s' if minutes else f'{rest} s'


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='python -m eval.run_testset', description='Run the test set against the service code.'
    )
    parser.add_argument('--no-concepts', action='store_true', help='without the concept map')
    parser.add_argument('--failures', action='store_true', help='list every failing query and why')
    parser.add_argument('suites', nargs='*', help='suite names, e.g. tools-mini-6 (default: all)')
    args = parser.parse_args()
    logging.basicConfig(format='%(levelname)s %(name)s: %(message)s')
    log.setLevel(logging.INFO)

    started = time.perf_counter()
    base = Settings(concepts_file='') if args.no_concepts else Settings()
    concepts = load_concepts(base.concepts_file)
    if concepts is None:
        config = 'concept map off (NEVIS_CONCEPTS_FILE empty)'
    else:
        config = f'concept map on ({base.concepts_file})'
    embedder = Embedder(base.model_dir, base.embed_threads)  # one model for all suites
    admin_dsn = make_conninfo(base.database_url.get_secret_value(), dbname='postgres')
    paths = [SUITES_DIR / f'{name}.json' for name in args.suites] or sorted(SUITES_DIR.glob('*.json'))

    board = Scoreboard()
    skipped: list[str] = []
    load_s = query_s = 0.0
    for path in paths:
        suite = json.loads(path.read_text(encoding='utf-8'))
        corpus = suite['corpus']
        log.info(
            '%s: loading %d clients and %d documents',
            suite['suite'],
            len(corpus['clients']),
            len(corpus['documents']),
        )
        run = run_suite(suite, admin_dsn, base, embedder, concepts)
        tally, failed = board.add_suite(suite, run.results)
        skipped += run.skipped
        load_s += run.load_s
        query_s += run.query_s
        log.info(
            '%s: %d clients and %d documents loaded, %d skipped; strict %d/%d; load %.1f s, queries %.1f s',
            suite['suite'],
            run.clients,
            run.documents,
            len(run.skipped),
            tally.passed,
            tally.total,
            run.load_s,
            run.query_s,
        )
        if args.failures:
            for query, why in failed:
                shown = query['q'][:SHOWN_Q_CHARS]
                log.info('  FAIL %s [%s] %r: %s', query['id'], query['level'], shown, '; '.join(why))

    print(render(board, config, skipped))
    print(
        f'\nRun time: {duration(time.perf_counter() - started)} (loading {duration(load_s)}, '
        f'queries {duration(query_s)}); model revision {MODEL_REVISION[:SHORT_REVISION_CHARS]}'
    )


if __name__ == '__main__':
    main()
