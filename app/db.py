from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import psycopg
from pgvector.sqlalchemy import Vector
from psycopg.conninfo import make_conninfo
from sqlalchemy import (
    CheckConstraint,
    Computed,
    Connection,
    DateTime,
    Engine,
    ForeignKey,
    Index,
    Integer,
    Text,
    all_,
    and_,
    case,
    cast,
    create_engine,
    exists,
    false,
    func,
    insert,
    inspect,
    literal,
    select,
    text,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, aggregate_order_by
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolExhausted
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import (
    CLIENT_TYPO_SIMILARITY,
    DESCRIPTION_WEIGHT,
    EMAIL_WEIGHT,
    EXACT_SCORE_MIN,
    FUZZY_SCORE_MAX,
    MIN_FUZZY_CHARS,
    NAME_WEIGHT,
)

# libpq options of every pooled connection
CONNECTION_OPTIONS: dict[str, str | int] = {
    'connect_timeout': 3,  # seconds to open a connection
    # The server cancels a statement after 5 s (QueryCanceled). The trigram threshold of the client typo
    # search is set here, so the search does not depend on the server's default.
    'options': f'-c statement_timeout=5000 -c pg_trgm.word_similarity_threshold={CLIENT_TYPO_SIMILARITY}',
    'keepalives': 1,  # TCP keepalives notice a server or a network that went away
    'keepalives_idle': 30,
    'keepalives_interval': 10,
    'keepalives_count': 3,
}

Reason = Literal['unreachable', 'busy', 'timeout']


class DatabaseUnavailable(Exception):
    def __init__(self, reason: Reason) -> None:
        super().__init__(reason)
        self.reason: Reason = reason


class Base(DeclarativeBase):
    pass


class ClientRow(Base):
    __tablename__ = 'clients'
    __table_args__ = (
        Index(
            'clients_search_text_trgm_idx',
            'search_text',
            postgresql_using='gin',
            postgresql_ops={'search_text': 'gin_trgm_ops'},
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('uuidv7()'))
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default='')
    social_links: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # case- and accent-insensitive text the client search matches against
    search_text: Mapped[str | None] = mapped_column(
        Text,
        Computed(
            "public.search_normalize(first_name || ' ' || last_name || ' ' || email || ' ' || description)",
            persisted=True,
        ),
    )


class DocumentRow(Base):
    __tablename__ = 'documents'
    __table_args__ = (Index('documents_client_id_idx', 'client_id'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('uuidv7()'))
    client_id: Mapped[UUID] = mapped_column(ForeignKey('clients.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default='{}')  # names of the matched concepts
    tags_text: Mapped[str] = mapped_column(Text, server_default='')  # each matched concept with its phrasings
    summary: Mapped[str] = mapped_column(Text)
    summary_method: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fts_text: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', public.strip_punct(title || ' ' || content))", persisted=True),
    )
    fts: Mapped[str | None] = mapped_column(  # tags first
        TSVECTOR,
        Computed(
            "to_tsvector('english', public.strip_punct(tags_text || ' ' || title || ' ' || content))",
            persisted=True,
        ),
    )


class DocumentChunkRow(Base):
    __tablename__ = 'document_chunks'

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True
    )
    chunk_no: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )  # -1: the tags chunk
    embedding: Mapped[Any] = mapped_column(Vector(768))


class AppMetaRow(Base):
    """What the stored vectors and tags were built with. At most one row: `id` can only be 1."""

    __tablename__ = 'app_meta'
    __table_args__ = (CheckConstraint('id = 1', name='app_meta_id_check'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, server_default=text('1'))
    model_revision: Mapped[str] = mapped_column(Text)  # Hugging Face revision of the embedding model
    tokenizer_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB
    )  # truncation and padding of the embedder
    concepts_sha256: Mapped[str | None] = mapped_column(Text)  # of the concept map; NULL when tagging is off


# What the tables need before they can be created: the extensions, and the two text functions that their
# generated columns and the searches use. SQLAlchemy has no construct for SQL functions, so this is plain DDL.
# psycopg receives these statements with an empty parameter list: a literal % must be written %%.
_EXTENSIONS_AND_FUNCTIONS = (
    'CREATE EXTENSION IF NOT EXISTS vector',
    'CREATE EXTENSION IF NOT EXISTS pg_trgm',
    'CREATE EXTENSION IF NOT EXISTS unaccent',
    # case- and accent-insensitive form used for client search (schema-qualified body: dump/restore safe)
    """CREATE FUNCTION public.search_normalize(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  RETURN casefold(
    public.unaccent('public.unaccent'::regdictionary, normalize($1, NFKC)) COLLATE "pg_unicode_fast"
  )""",
    # punctuation -> spaces, identically for documents and queries, independent of the database locale
    """CREATE FUNCTION public.strip_punct(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  RETURN regexp_replace($1 COLLATE "pg_unicode_fast", '[^[:alnum:]]+', ' ', 'g')""",
)


def create_schema(database_url: str) -> bool:
    """Create the extensions, functions and tables if the database has none yet.

    Returns True when it created them, False when they were there already. One transaction: a failure leaves
    nothing behind. There are no migrations: after a change to the models, start from an empty database.
    """
    engine = create_engine(
        'postgresql+psycopg://',
        creator=lambda: psycopg.connect(database_url, connect_timeout=3),
        poolclass=NullPool,
        hide_parameters=True,
    )
    try:
        with engine.begin() as conn:
            if inspect(conn).has_table('clients', schema='public'):
                return False
            for statement in _EXTENSIONS_AND_FUNCTIONS:
                conn.exec_driver_sql(statement)
            Base.metadata.create_all(conn, checkfirst=False)  # a table name taken already is an error
        return True
    finally:
        engine.dispose()


def open_engine(database_url: str) -> Engine:
    """The connection pool of the service."""
    conninfo = make_conninfo(database_url, **CONNECTION_OPTIONS)
    return create_engine(
        'postgresql+psycopg://',
        creator=lambda: psycopg.connect(conninfo),
        pool_size=8,
        max_overflow=0,  # at most 8 connections
        pool_timeout=5,  # wait at most 5 s for a free connection, then 503 busy
        pool_pre_ping=True,  # test a connection before handing it out: replaces those a restart dropped
        hide_parameters=True,  # error texts must not carry names, e-mails or search terms into the log
    )


@contextmanager
def _connection(engine: Engine) -> Iterator[Connection]:
    """One transaction on a pooled connection: committed when the block ends, rolled back if it raises."""
    try:
        with engine.begin() as conn:
            yield conn
    except PoolExhausted as exc:  # every connection is in use
        raise DatabaseUnavailable('busy') from exc
    except OperationalError as exc:
        if isinstance(exc.orig, psycopg.errors.QueryCanceled):  # statement_timeout expired
            raise DatabaseUnavailable('timeout') from exc
        raise DatabaseUnavailable('unreachable') from exc  # connection refused, lost or reset


_CLIENT_COLUMNS = (
    ClientRow.id,
    ClientRow.first_name,
    ClientRow.last_name,
    ClientRow.email,
    ClientRow.description,
    ClientRow.social_links,
)


def insert_client(
    engine: Engine,
    *,
    first_name: str,
    last_name: str,
    email: str,
    description: str,
    social_links: list[str],
) -> dict[str, Any]:
    """Insert one client and return it as the API shows it. Committed before it returns."""
    statement = (
        insert(ClientRow)
        .values(
            first_name=first_name,
            last_name=last_name,
            email=email,
            description=description,
            social_links=social_links,
        )
        .returning(*_CLIENT_COLUMNS)
    )
    with _connection(engine) as conn:
        return dict(conn.execute(statement).mappings().one())


def get_client(engine: Engine, client_id: UUID) -> dict[str, Any] | None:
    """The client with this id as the API shows it, or None."""
    with _connection(engine) as conn:
        row = conn.execute(select(*_CLIENT_COLUMNS).where(ClientRow.id == client_id)).mappings().first()
    return None if row is None else dict(row)


def search_clients(engine: Engine, q: str, limit: int) -> list[dict[str, Any]]:
    """Clients for a prepared query, best first, at most `limit`.

    Rows: id, match_type ('exact' or 'fuzzy'), score (unrounded), first_name, last_name, email, description,
    social_links. `exact`: every word of the normalised query occurs in the client's search_text, even inside
    a longer word; score EXACT_SCORE_MIN to 1. `fuzzy`, only when nothing is exact and the query has at least
    MIN_FUZZY_CHARS letters and digits: a typo match by trigram word similarity; score 0 to FUZZY_SCORE_MAX.
    """
    # The words of the query: normalised like search_text, split on spaces, commas and semicolons
    tok = (
        func.regexp_split_to_table(func.public.search_normalize(cast(q, Text)), r'[\s,;]+')
        .table_valued('tok')
        .render_derived()
    )
    # `%word%` with the LIKE wildcards % and _ (and the escape character \) escaped
    pattern = (
        literal('%')
        + func.replace(func.replace(func.replace(tok.c.tok, '\\', '\\\\'), '%', '\\%'), '_', '\\_')
        + literal('%')
    )
    query = (
        select(
            func.string_agg(tok.c.tok.distinct(), literal(' ')).label('norm'),
            func.array_agg(pattern.distinct(), type_=ARRAY(Text)).label('pats'),
            # the longest word's pattern: an extra LIKE that lets PostgreSQL use the trigram index
            func.array_agg(
                aggregate_order_by(pattern, func.length(tok.c.tok).desc(), tok.c.tok), type_=ARRAY(Text)
            )[1].label('longest'),
        )
        .select_from(tok)
        .where(tok.c.tok != '')
        .cte('q')
    )
    exact = (
        select(*_CLIENT_COLUMNS, true().label('exact'))
        .join_from(
            query,
            ClientRow,
            and_(ClientRow.search_text.like(query.c.longest), ClientRow.search_text.like(all_(query.c.pats))),
        )
        .cte('hits')
    )
    letters_and_digits = func.length(func.regexp_replace(query.c.norm, '[^[:alnum:]]', '', 'g'))
    typos = (
        select(*_CLIENT_COLUMNS, false().label('exact'))
        # `<%`: word similarity at least pg_trgm.word_similarity_threshold (CLIENT_TYPO_SIMILARITY)
        .join_from(query, ClientRow, query.c.norm.op('<%')(ClientRow.search_text))
        .where(letters_and_digits >= MIN_FUZZY_CHARS, ~exists(select(1).select_from(exact)))
        .cte('near')
    )
    found = union_all(select(exact), select(typos)).subquery('c')
    best = func.greatest(
        NAME_WEIGHT
        * func.word_similarity(
            query.c.norm, func.public.search_normalize(found.c.first_name + ' ' + found.c.last_name)
        ),
        EMAIL_WEIGHT * func.word_similarity(query.c.norm, func.public.search_normalize(found.c.email)),
        DESCRIPTION_WEIGHT
        * func.word_similarity(query.c.norm, func.public.search_normalize(found.c.description)),
    )
    score = case(
        (found.c.exact, EXACT_SCORE_MIN + (1 - EXACT_SCORE_MIN) * best), else_=FUZZY_SCORE_MAX * best
    ).label('score')
    statement = (
        select(
            found.c.id,
            case((found.c.exact, 'exact'), else_='fuzzy').label('match_type'),
            score,
            found.c.first_name,
            found.c.last_name,
            found.c.email,
            found.c.description,
            found.c.social_links,
        )
        .select_from(found.join(query, true()))
        .order_by(score.desc(), found.c.last_name, found.c.first_name, found.c.id)
        .limit(limit)
    )
    with _connection(engine) as conn:
        return [dict(row) for row in conn.execute(statement).mappings()]
