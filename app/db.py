from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import numpy as np
import numpy.typing as npt
import psycopg
from pgvector.sqlalchemy import Vector
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy import (
    CheckConstraint,
    Computed,
    Connection,
    DateTime,
    Engine,
    ForeignKey,
    Index,
    Integer,
    Select,
    Text,
    all_,
    and_,
    bindparam,
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
    EMBEDDING_DIM,
    EXACT_SCORE_MIN,
    FTS_CONFIG,
    FUZZY_SCORE_MAX,
    MIN_FUZZY_CHARS,
    NAME_WEIGHT,
    Settings,
)

# libpq options of every connection; the timeouts come from Settings (connection_info)
CONNECTION_OPTIONS: dict[str, str | int] = {
    'keepalives': 1,  # an idle connection to a server that went away is dropped within about 40 s
    'keepalives_idle': 30,
    'keepalives_interval': 10,
    'keepalives_count': 3,
    'tcp_user_timeout': 10_000,  # ms: a request the server stops acknowledging fails after 10 s (Linux)
    'fallback_application_name': 'nevis-search',  # names the sessions in pg_stat_activity
}

Reason = Literal['unreachable', 'busy', 'timeout']


class DatabaseUnavailable(Exception):
    def __init__(self, reason: Reason, cause: str = '') -> None:
        super().__init__(reason)
        self.reason: Reason = reason
        self.cause = cause  # what the driver or the pool reported, for the log


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
        Computed(f"to_tsvector('{FTS_CONFIG}', public.strip_punct(title || ' ' || content))", persisted=True),
    )
    fts: Mapped[str | None] = mapped_column(  # tags first
        TSVECTOR,
        Computed(
            f"to_tsvector('{FTS_CONFIG}', public.strip_punct(tags_text || ' ' || title || ' ' || content))",
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
    )  # TAGS_CHUNK_NO: the tags chunk
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIM))


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


def create_schema(settings: Settings) -> bool:
    """Create the extensions, functions and tables if the database has none yet.

    Returns True when it created them, False when they were there already. One transaction: a failure leaves
    nothing behind. There are no migrations: after a change to the models, start from an empty database.
    """
    info = connection_info(settings)
    engine = create_engine(
        'postgresql+psycopg://',
        creator=lambda: psycopg.connect(info),
        poolclass=NullPool,
        hide_parameters=True,
    )
    try:
        with engine.begin() as conn:
            if inspect(conn).has_table(ClientRow.__tablename__, schema='public'):
                return False
            for statement in _EXTENSIONS_AND_FUNCTIONS:
                conn.exec_driver_sql(statement)
            Base.metadata.create_all(conn, checkfirst=False)  # a table name taken already is an error
        return True
    finally:
        engine.dispose()


def connection_info(settings: Settings) -> str:
    """libpq parameters of every connection, at start-up and in the pool: the URL's own, then the options
    above and the timeouts. `options` from the URL are kept; the flags added after them win."""
    url = settings.database_url.get_secret_value()
    flags = (
        f'-c statement_timeout={settings.db_statement_timeout_ms} '
        # the trigram threshold of the client typo search, so the search does not depend on the server default
        f'-c pg_trgm.word_similarity_threshold={CLIENT_TYPO_SIMILARITY}'
    )
    given = conninfo_to_dict(url).get('options')
    return make_conninfo(
        url,
        **CONNECTION_OPTIONS,
        connect_timeout=settings.db_connect_timeout_seconds,
        options=f'{given} {flags}' if given else flags,
    )


def open_engine(settings: Settings) -> Engine:
    """The connection pool of the service."""
    info = connection_info(settings)
    return create_engine(
        'postgresql+psycopg://',
        creator=lambda: psycopg.connect(info),
        pool_size=settings.db_pool_size,
        max_overflow=0,  # never more than db_pool_size connections
        pool_timeout=settings.db_pool_timeout_seconds,  # then 503 busy
        pool_pre_ping=True,  # test a connection before handing it out: replaces those a restart dropped
        # bound values stay out of error texts; PostgreSQL's DETAIL can still quote row values
        hide_parameters=True,
    )


@contextmanager
def _connection(engine: Engine) -> Iterator[Connection]:
    """One transaction on a pooled connection: committed when the block ends, rolled back if it raises."""
    try:
        with engine.begin() as conn:
            yield conn
    except PoolExhausted as exc:  # every connection is in use
        raise DatabaseUnavailable('busy', _cause(exc)) from exc
    except OperationalError as exc:
        if isinstance(exc.orig, psycopg.errors.QueryCanceled):  # statement_timeout expired
            raise DatabaseUnavailable('timeout', _cause(exc)) from exc
        raise DatabaseUnavailable('unreachable', _cause(exc)) from exc  # connection refused, lost or reset


def _cause(exc: Exception) -> str:
    """Error class, SQLSTATE and the first line of the message, for the log: no DETAIL, no parameters."""
    error = getattr(exc, 'orig', None) or exc  # the driver's error inside SQLAlchemy's wrapper
    parts = (type(error).__name__, getattr(error, 'sqlstate', None), str(error).partition('\n')[0])
    return ' '.join(part for part in parts if part)


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


def client_exists(engine: Engine, client_id: UUID) -> bool:
    with _connection(engine) as conn:
        return bool(conn.execute(select(exists().where(ClientRow.id == client_id))).scalar())


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


_DOCUMENT_COLUMNS = (
    DocumentRow.id,
    DocumentRow.client_id,
    DocumentRow.title,
    DocumentRow.content,
    DocumentRow.created_at,
    DocumentRow.tags,
    DocumentRow.summary,
    DocumentRow.summary_method,
)


def insert_document(
    engine: Engine,
    *,
    client_id: UUID,
    title: str,
    content: str,
    tags: list[str],
    tags_text: str,
    summary: str,
    summary_method: str,
    chunks: list[tuple[int, npt.NDArray[np.float32]]],
) -> dict[str, Any]:
    """Insert the document and its chunk vectors (chunk_no, vector) in one transaction and return the
    document's row. Committed before it returns, so a 201 is never sent before the document can be read."""
    document = (
        insert(DocumentRow)
        .values(
            client_id=client_id,
            title=title,
            content=content,
            tags=tags,
            tags_text=tags_text,
            summary=summary,
            summary_method=summary_method,
        )
        .returning(*_DOCUMENT_COLUMNS)
    )
    with _connection(engine) as conn:
        row = dict(conn.execute(document).mappings().one())
        conn.execute(
            insert(DocumentChunkRow),
            [
                {'document_id': row['id'], 'chunk_no': chunk_no, 'embedding': vector}
                for chunk_no, vector in chunks
            ],
        )
    return row


def get_document(engine: Engine, client_id: UUID, document_id: UUID) -> dict[str, Any] | None:
    """The document's row if it exists and belongs to this client; None otherwise."""
    statement = select(*_DOCUMENT_COLUMNS).where(
        DocumentRow.id == document_id, DocumentRow.client_id == client_id
    )
    with _connection(engine) as conn:
        row = conn.execute(statement).mappings().first()
    return None if row is None else dict(row)


def _match_concepts_statement() -> Select[int, bool, bool]:
    """The statement of match_concepts, with the bound parameters title, content, entries and phrases."""
    title = cast(bindparam('title'), Text)
    content = cast(bindparam('content'), Text)
    # MATERIALIZED: the two search vectors are built once, not once per phrase
    texts = (
        select(
            func.to_tsvector(FTS_CONFIG, func.public.strip_punct(title)).label('tv_title'),
            func.to_tsvector(FTS_CONFIG, func.public.strip_punct(title + ' ' + content)).label('tv_all'),
        )
        .cte('t')
        .prefix_with('MATERIALIZED')
    )
    pairs = (
        func.unnest(bindparam('entries', type_=ARRAY(Integer)), bindparam('phrases', type_=ARRAY(Text)))
        .table_valued('entry', 'phrase')
        .render_derived(name='u')
    )
    stripped = (
        select(func.btrim(func.public.strip_punct(pairs.c.phrase)).label('stripped'))
        .correlate(pairs)
        .lateral('s')
    )
    parsed = (
        select(
            func.phraseto_tsquery(FTS_CONFIG, stripped.c.stripped).label('pq'),
            func.regexp_split_to_array(stripped.c.stripped, r'\s+', type_=ARRAY(Text)).label('w'),
        )
        .correlate(stripped)
        .lateral('x')
    )
    words = parsed.c.w
    phrases = (
        select(pairs.c.entry, parsed.c.pq)
        .select_from(pairs.join(stripped, true()).join(parsed, true()))
        .where(
            func.numnode(parsed.c.pq) > 0,
            # A phrase whose first or last word is a stop word is skipped: its query would silently lose
            # that word ('trust in' would match any trust). Stop words inside a phrase are kept.
            func.numnode(func.plainto_tsquery(FTS_CONFIG, words[1])) > 0,
            func.numnode(func.plainto_tsquery(FTS_CONFIG, words[func.cardinality(words)])) > 0,
        )
        .cte('ph')
    )
    in_title = func.bool_or(texts.c.tv_title.bool_op('@@')(phrases.c.pq))
    anywhere = func.bool_or(texts.c.tv_all.bool_op('@@')(phrases.c.pq))
    return (
        select(phrases.c.entry, in_title.label('in_title'), anywhere.label('anywhere'))
        .select_from(phrases.join(texts, true()))
        .group_by(phrases.c.entry)
        .having(anywhere)
        .order_by(phrases.c.entry)
    )


_MATCH_CONCEPTS = _match_concepts_statement()


def match_concepts(
    engine: Engine, title: str, content: str, entries: list[int], phrases: list[str]
) -> list[tuple[int, bool, bool]]:
    """The concept entries with a phrase that occurs in the document, each once and in entry order: (entry
    number, matched in the title, matched in title + content). One round trip.

    `entries` and `phrases` are parallel: entries[i] owns phrases[i]. Phrases match as whole phrases, stemmed
    and without punctuation (text search configuration FTS_CONFIG).
    """
    params = {'title': title, 'content': content, 'entries': entries, 'phrases': phrases}
    with _connection(engine) as conn:
        rows = conn.execute(_MATCH_CONCEPTS, params).all()
    return [(int(entry), bool(in_title), bool(anywhere)) for entry, in_title, anywhere in rows]
