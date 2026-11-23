"""The connection pool (a SQLAlchemy engine) and the transaction rule every database function builds on,
and the three reasons of DatabaseUnavailable produced by real failures: statement timeout, busy pool, no
database."""

import time
import uuid
from collections.abc import Iterator

import numpy as np
import psycopg
import pytest
from pgvector.sqlalchemy import Vector
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import Engine, cast, func, select, text
from sqlalchemy.exc import DBAPIError

from app.db import DatabaseUnavailable, _connection, open_engine

UNREACHABLE = 'postgresql://nevis:nevis@127.0.0.1:1/nevis'  # nothing listens on port 1


@pytest.fixture
def engine(fresh_dsn: str) -> Iterator[Engine]:
    opened = open_engine(fresh_dsn)
    yield opened
    opened.dispose()


def count_clients(dsn: str, email: str) -> int:
    with psycopg.connect(dsn) as other:  # another session: it sees committed rows only
        row = other.execute('SELECT count(*) FROM clients WHERE email = %s', (email,)).fetchone()
    assert row is not None
    count: int = row[0]
    return count


def test_pooled_connections_carry_the_guardrails(engine: Engine) -> None:
    with _connection(engine) as conn:
        timeout = conn.execute(text('SHOW statement_timeout')).scalar()
        threshold = conn.execute(text('SHOW pg_trgm.word_similarity_threshold')).scalar()
        parameters = conn.connection.driver_connection.info.get_parameters()
        dims = conn.execute(select(func.vector_dims(cast(np.array([0.25, -1.0, 3.5]), Vector(3))))).scalar()

    assert timeout == '5s'
    assert threshold == '0.6'  # the typo tier of the client search: set here, not left to the server default
    assert parameters['connect_timeout'] == '3'
    assert parameters['keepalives_idle'] == '30'
    assert dims == 3  # numpy arrays are sent as `vector`
    assert (engine.pool.size(), engine.pool.timeout()) == (8, 5)


def test_connection_block_commits_when_it_ends_and_rolls_back_when_it_raises(
    engine: Engine, fresh_dsn: str
) -> None:
    email = f'{uuid.uuid4().hex}@example.com'
    insert = text("INSERT INTO clients (first_name, last_name, email) VALUES ('Ann', 'Lee', :email)")

    with _connection(engine) as conn:
        conn.execute(insert, {'email': email})
        assert count_clients(fresh_dsn, email) == 0  # not visible to others before the commit
    assert count_clients(fresh_dsn, email) == 1  # committed when the block ended

    with pytest.raises(RuntimeError, match='changed my mind'), _connection(engine) as conn:
        conn.execute(insert, {'email': email})
        raise RuntimeError('changed my mind')
    assert count_clients(fresh_dsn, email) == 1  # the second insert was rolled back


def test_pool_replaces_connections_the_server_dropped(engine: Engine, fresh_dsn: str) -> None:
    """A connection the server dropped is replaced, not handed out (pool_pre_ping)."""
    with _connection(engine) as conn:
        conn.execute(text('SELECT 1'))  # the pool keeps this connection for reuse
    with psycopg.connect(fresh_dsn, autocommit=True) as admin:
        admin.execute(
            'SELECT pg_terminate_backend(pid) FROM pg_stat_activity'
            ' WHERE datname = current_database() AND pid <> pg_backend_pid()'
        )

    with _connection(engine) as conn:
        assert conn.execute(text('SELECT 2')).scalar() == 2


def test_statement_over_the_timeout_is_unavailable_timeout(engine: Engine) -> None:
    with pytest.raises(DatabaseUnavailable) as error, _connection(engine) as conn:
        conn.execute(text('SET LOCAL statement_timeout = 200'))  # the pool's 5 s, shortened for the test
        conn.execute(text('SELECT pg_sleep(2)'))

    assert error.value.reason == 'timeout'
    cause = error.value.__cause__
    assert cause is not None
    assert isinstance(getattr(cause, 'orig', None), psycopg.errors.QueryCanceled)


def test_exhausted_pool_is_unavailable_busy(engine: Engine) -> None:
    held = [engine.connect() for _ in range(8)]  # every connection the pool may open
    try:
        began = time.monotonic()
        with pytest.raises(DatabaseUnavailable) as error, _connection(engine):
            pass
        waited = time.monotonic() - began
    finally:
        for conn in held:
            conn.close()

    assert error.value.reason == 'busy'
    assert 4.5 < waited < 10  # the pool's 5 s, not the library default of 30 s


@pytest.mark.usefixtures('admin_dsn')  # runs in compose only, like every integration test
def test_database_that_cannot_be_reached_is_unavailable_unreachable() -> None:
    dead = open_engine(UNREACHABLE)
    try:
        with pytest.raises(DatabaseUnavailable) as error, _connection(dead):
            pass
    finally:
        dead.dispose()

    assert error.value.reason == 'unreachable'


def test_the_first_request_after_an_outage_succeeds(engine: Engine, fresh_dsn: str, admin_dsn: str) -> None:
    name = sql.Identifier(conninfo_to_dict(fresh_dsn)['dbname'])
    with _connection(engine) as conn:
        conn.execute(text('SELECT 1'))  # the pool now holds one connection
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('ALTER DATABASE {} WITH ALLOW_CONNECTIONS false').format(name))
        admin.execute(
            sql.SQL('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = {}').format(
                sql.Literal(conninfo_to_dict(fresh_dsn)['dbname'])
            )
        )
    try:
        with pytest.raises(DatabaseUnavailable) as error, _connection(engine):
            pass
        assert error.value.reason == 'unreachable'
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('ALTER DATABASE {} WITH ALLOW_CONNECTIONS true').format(name))

    began = time.monotonic()
    with _connection(engine) as conn:
        assert conn.execute(text('SELECT 3')).scalar() == 3
    assert time.monotonic() - began < 2  # no back-off: the pool connects again at once


def test_errors_do_not_carry_the_query_parameters(engine: Engine) -> None:
    # An error the API does not expect becomes a 500, and its traceback goes to the server log: it must not
    # carry names, e-mail addresses or search terms.
    with pytest.raises(DBAPIError) as error, _connection(engine) as conn:
        conn.execute(text('SELECT 1 / 0 WHERE :email IS NOT NULL'), {'email': 'ann.lee@private.example'})

    assert 'ann.lee@private.example' not in str(error.value)
