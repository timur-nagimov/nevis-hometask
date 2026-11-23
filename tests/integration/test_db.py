"""The pool and the transaction rule every SQL function builds on (spec section 4), and the three reasons
of DatabaseUnavailable (13.2 B5) produced by real failures: statement timeout, busy pool, no database."""

import time
import uuid
from collections.abc import Iterator

import numpy as np
import psycopg
import pytest

from app.db import DatabaseUnavailable, Pool, _connection, open_pool

UNREACHABLE = "postgresql://nevis:nevis@127.0.0.1:1/nevis"  # nothing listens on port 1


@pytest.fixture
def pool(fresh_dsn: str) -> Iterator[Pool]:
    opened = open_pool(fresh_dsn)
    yield opened
    opened.close()


def count_clients(dsn: str, email: str) -> int:
    with psycopg.connect(dsn) as other:  # another session: it sees committed rows only
        row = other.execute("SELECT count(*) FROM clients WHERE email = %s", (email,)).fetchone()
    assert row is not None
    count: int = row[0]
    return count


def test_pooled_connections_carry_the_guardrails(pool: Pool) -> None:
    with _connection(pool) as conn:
        timeout = conn.execute("SHOW statement_timeout").fetchone()
        parameters = conn.info.get_parameters()
        dims = conn.execute(
            "SELECT vector_dims(%s)", (np.array([0.25, -1.0, 3.5], dtype=np.float32),)
        ).fetchone()

    assert timeout == ("5s",)
    assert parameters["connect_timeout"] == "3"
    assert parameters["keepalives_idle"] == "30"
    assert dims == (3,)  # register_vector ran: a numpy array is sent as a `vector`


def test_connection_block_commits_when_it_ends_and_rolls_back_when_it_raises(
    pool: Pool, fresh_dsn: str
) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    insert = "INSERT INTO clients (first_name, last_name, email) VALUES ('Ann', 'Lee', %s)"

    with _connection(pool) as conn:
        conn.execute(insert, (email,))
        assert count_clients(fresh_dsn, email) == 0  # not visible to others before the commit
    assert count_clients(fresh_dsn, email) == 1  # committed when the block ended

    with pytest.raises(RuntimeError, match="changed my mind"), _connection(pool) as conn:
        conn.execute(insert, (email,))
        raise RuntimeError("changed my mind")
    assert count_clients(fresh_dsn, email) == 1  # the second insert was rolled back


def test_pool_replaces_connections_the_server_dropped(pool: Pool, fresh_dsn: str) -> None:
    """After a database restart the next request must not fail (check=ConnectionPool.check_connection)."""
    with _connection(pool) as conn:
        conn.execute("SELECT 1")  # the pool keeps this connection for reuse
    with psycopg.connect(fresh_dsn, autocommit=True) as admin:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
            " WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )

    with _connection(pool) as conn:
        assert conn.execute("SELECT 2").fetchone() == (2,)


def test_statement_over_the_timeout_is_unavailable_timeout(pool: Pool) -> None:
    with pytest.raises(DatabaseUnavailable) as error, _connection(pool) as conn:
        conn.execute("SET LOCAL statement_timeout = 200")  # the pool's 5 s, shortened for the test
        conn.execute("SELECT pg_sleep(2)")

    assert error.value.reason == "timeout"
    assert isinstance(error.value.__cause__, psycopg.errors.QueryCanceled)


def test_exhausted_pool_is_unavailable_busy(pool: Pool) -> None:
    held = [pool.getconn() for _ in range(8)]  # every connection the pool may open (max_size=8)
    try:
        began = time.monotonic()
        with pytest.raises(DatabaseUnavailable) as error, _connection(pool):
            pass
        waited = time.monotonic() - began
    finally:
        for conn in held:
            pool.putconn(conn)

    assert error.value.reason == "busy"
    assert 4.5 < waited < 10  # the pool's 5 s, not the library default of 30 s


@pytest.mark.usefixtures("admin_dsn")  # runs in compose only, like every integration test
def test_database_that_cannot_be_reached_is_unavailable_unreachable() -> None:
    dead = open_pool(UNREACHABLE)
    try:
        with pytest.raises(DatabaseUnavailable) as error, _connection(dead):
            pass
    finally:
        dead.close()

    assert error.value.reason == "unreachable"
