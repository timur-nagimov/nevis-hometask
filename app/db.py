from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import numpy as np
import numpy.typing as npt
import psycopg
from pgvector.sqlalchemy import Vector
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy import (
    CTE,
    CheckConstraint,
    Computed,
    Connection,
    DateTime,
    Double,
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
    null,
    or_,
    select,
    text,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSQUERY, TSVECTOR, aggregate_order_by
from sqlalchemy.dialects.postgresql import insert as pg_insert  # with ON CONFLICT
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolExhausted
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import (
    CLIENT_TYPO_SIMILARITY,
    DELTA,
    DESCRIPTION_WEIGHT,
    EMAIL_WEIGHT,
    EMBEDDING_DIM,
    EXACT_SCORE_MIN,
    FTS_CONFIG,
    FUZZY_SCORE_MAX,
    K_FALLBACK,
    MIN_FUZZY_CHARS,
    MIN_STOP_WORDS_CHARS,
    MIN_WORD_CHARS,
    NAME_WEIGHT,
    T_FALLBACK,
    T_STRONG,
    TAU_TITLE,
    UNSTEMMED_FTS_CONFIG,
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
    statement = select(exists().where(ClientRow.id == client_id))
    with _connection(engine) as conn:
        return conn.execute(statement).scalar_one()


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
    statement = (
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
        row = dict(conn.execute(statement).mappings().one())
        chunk_rows = [
            {'document_id': row['id'], 'chunk_no': chunk_no, 'embedding': vector}
            for chunk_no, vector in chunks
        ]
        conn.execute(insert(DocumentChunkRow), chunk_rows)
    return row


def get_document(engine: Engine, client_id: UUID, document_id: UUID) -> dict[str, Any] | None:
    """The document's row if it exists and belongs to this client; None otherwise."""
    statement = select(*_DOCUMENT_COLUMNS).where(
        DocumentRow.id == document_id, DocumentRow.client_id == client_id
    )
    with _connection(engine) as conn:
        row = conn.execute(statement).mappings().first()
    return None if row is None else dict(row)


def _query_row() -> CTE:
    """One row about the query (`p`), from the bound parameters q, qvec, alt and alt_sim."""
    q = cast(bindparam('q'), Text)
    alt = cast(bindparam('alt'), Text)
    # The query's words: each whitespace piece without its punctuation, short tokens dropped
    pieces = (
        func.regexp_split_to_table(q, r'\s+').table_valued('raw', with_ordinality='n').render_derived('w')
    )
    tokens = (
        func.regexp_split_to_table(func.btrim(func.public.strip_punct(pieces.c.raw)), ' ')
        .table_valued('tok', with_ordinality='k')
        .render_derived()
        .lateral('t')
    )
    words = (
        select(
            pieces.c.n,
            func.string_agg(tokens.c.tok, aggregate_order_by(literal(' '), tokens.c.k)).label('word'),
        )
        .select_from(pieces.join(tokens, true()))
        .where(func.char_length(tokens.c.tok) >= MIN_WORD_CHARS)
        .group_by(pieces.c.n)
        .cte('tok')
        .prefix_with('MATERIALIZED')
    )
    # The full-text query: every word must occur (stemmed, stop words ignored); a word with a digit must occur
    # as the phrase of its tokens, so LV-7734-0921-KX is found whole and by 7734
    word_query = (
        select(
            case(
                (words.c.word.regexp_match('[0-9]'), func.phraseto_tsquery(FTS_CONFIG, words.c.word)),
                else_=func.plainto_tsquery(FTS_CONFIG, words.c.word),
            ).label('t')
        )
        .correlate(words)
        .lateral('x')
    )
    every_word = func.string_agg(cast(word_query.c.t, Text), aggregate_order_by(literal(' & '), words.c.n))
    tsq = (
        select(cast(func.coalesce(every_word, ''), TSQUERY))
        .select_from(words.join(word_query, true()))
        .where(func.numnode(word_query.c.t) > 0)
    )
    # The words as typed, stop words kept: for a query of stop words only, matched against titles
    as_typed = func.coalesce(func.string_agg(words.c.word, aggregate_order_by(literal(' '), words.c.n)), '')
    q_words = select(func.plainto_tsquery(UNSTEMMED_FTS_CONFIG, as_typed))
    q_word_chars = select(func.coalesce(func.sum(func.char_length(func.replace(words.c.word, ' ', ''))), 0))
    # The concept phrase that the query misspells, as a full-text query
    altq = case((alt.is_(None), null()), else_=func.plainto_tsquery(FTS_CONFIG, func.public.strip_punct(alt)))
    vector = Vector(EMBEDDING_DIM)  # the parameter's type sends the numpy array; the cast types the column
    return (
        select(
            q.label('q'),
            cast(bindparam('qvec', type_=vector), vector).label('qvec'),
            cast(bindparam('alt_sim'), Double).label('alt_sim'),
            tsq.scalar_subquery().label('tsq'),
            q_words.scalar_subquery().label('q_words'),
            q_word_chars.scalar_subquery().label('q_word_chars'),
            func.length(func.regexp_replace(q, '[^[:alnum:]]', '', 'g')).label('q_alnum_chars'),
            altq.label('altq'),
        )
        .cte('p')
        .prefix_with('MATERIALIZED')
    )


def _lexical_leg(query: CTE) -> CTE:
    """The documents with every query word in the title, the content or the tags (`lex`); `in_text`: in the
    title or the content alone. A query of stop words only can match titles, by its words as typed."""
    has_words = func.numnode(query.c.tsq) > 0
    title_words = func.to_tsvector(UNSTEMMED_FTS_CONFIG, func.public.strip_punct(DocumentRow.title))
    title_hit = (
        select(
            and_(
                func.numnode(query.c.tsq) == 0,
                func.numnode(query.c.q_words) > 0,
                query.c.q_word_chars >= MIN_STOP_WORDS_CHARS,
                title_words.bool_op('@@')(query.c.q_words),
            ).label('title_hit')
        )
        .correlate(DocumentRow, query)
        .lateral('h')
    )
    in_text = or_(and_(has_words, DocumentRow.fts_text.bool_op('@@')(query.c.tsq)), title_hit.c.title_hit)
    with_tags = or_(and_(has_words, DocumentRow.fts.bool_op('@@')(query.c.tsq)), title_hit.c.title_hit)
    return (
        select(DocumentRow.id.label('document_id'), in_text.label('in_text'))
        .join_from(DocumentRow, query, true())
        .join(title_hit, true())
        .where(with_tags)
        .cte('lex')
    )


def _typo_leg(query: CTE, lexical: CTE) -> CTE:
    """Only when the lexical leg found nothing: the documents whose title is similar to the query, or that
    contain the concept phrase the query misspells (`fuz`). `s`: the title's similarity or alt_sim, the
    greater when both apply."""
    title_similarity = (
        select(func.word_similarity(query.c.q, DocumentRow.title).label('ws'))
        .correlate(DocumentRow, query)
        .lateral('w')
    )
    near_title = (
        select(
            and_(query.c.q_alnum_chars >= MIN_FUZZY_CHARS, title_similarity.c.ws >= TAU_TITLE).label('ok'),
            title_similarity.c.ws,
        )
        .correlate(query, title_similarity)
        .lateral('tt')
    )
    has_alt = (
        select(
            and_(
                query.c.altq.is_not(None),
                func.numnode(query.c.altq) > 0,
                DocumentRow.fts.bool_op('@@')(query.c.altq),
            ).label('ok')
        )
        .correlate(DocumentRow, query)
        .lateral('aa')
    )
    similarity = func.greatest(
        case((near_title.c.ok, near_title.c.ws)), case((has_alt.c.ok, query.c.alt_sim))
    )
    # On the join, not in WHERE: PostgreSQL then tests it once and skips this leg when the lexical leg found
    # something. In WHERE it would become a filter of the candidates' outer join, tested after the leg ran.
    nothing_lexical = ~exists(select(1).select_from(lexical))
    return (
        select(DocumentRow.id.label('document_id'), similarity.label('s'))
        .join_from(DocumentRow, query, nothing_lexical)
        .join(title_similarity, true())
        .join(near_title, true())
        .join(has_alt, true())
        .where(or_(near_title.c.ok, has_alt.c.ok))
        .cte('fuz')
    )


def _search_documents_statement() -> Select[Any]:
    """The statement of search_documents, with the bound parameters q, qvec, alt, alt_sim and limit."""
    query = _query_row()
    # The best cosine of each document's chunks: an exact scan, no vector index
    semantic = (
        select(
            DocumentChunkRow.document_id,
            func.max(1 - DocumentChunkRow.embedding.cosine_distance(query.c.qvec)).label('cos'),
        )
        .join_from(DocumentChunkRow, query, true())
        .group_by(DocumentChunkRow.document_id)
        .cte('sem')
    )
    lexical = _lexical_leg(query)
    typos = _typo_leg(query, lexical)
    cos_rank = func.row_number().over(order_by=(semantic.c.cos.desc(), semantic.c.document_id))
    candidates = (
        select(
            semantic.c.document_id,
            semantic.c.cos,
            lexical.c.in_text,
            typos.c.s.label('fs'),
            lexical.c.document_id.is_not(None).label('lex_hit'),
            or_(lexical.c.document_id.is_not(None), typos.c.document_id.is_not(None)).label('literal'),
            func.max(semantic.c.cos).over().label('top_cos'),
            cos_rank.label('cos_rank'),
        )
        .outerjoin_from(semantic, lexical, lexical.c.document_id == semantic.c.document_id)
        .outerjoin(typos, typos.c.document_id == semantic.c.document_id)
        .cte('cand')
    )
    # Strong: a word or typo match, or a cosine of at least T_STRONG within DELTA of the best one. A query
    # without a searchable word gets no matches by meaning (sem_ok).
    has_words = func.numnode(query.c.tsq) > 0
    near_best = and_(
        has_words, candidates.c.cos >= T_STRONG, candidates.c.cos >= candidates.c.top_cos - DELTA
    )
    marked = (
        select(candidates, has_words.label('sem_ok'), or_(candidates.c.literal, near_best).label('strong'))
        .join_from(candidates, query, true())
        .cte('marked')
    )
    found = select(marked, func.bool_or(marked.c.strong).over().label('any_strong')).subquery('m')
    clamped_cos = func.least(func.greatest(found.c.cos, 0), 1)
    score = case(
        (found.c.lex_hit, EXACT_SCORE_MIN + (1 - EXACT_SCORE_MIN) * clamped_cos),
        (found.c.fs.is_not(None), FUZZY_SCORE_MAX * found.c.fs),
        else_=EXACT_SCORE_MIN * clamped_cos,
    ).label('score')
    match_type = case(
        (found.c.in_text, 'lexical'),
        (found.c.lex_hit, 'concept'),
        (found.c.fs.is_not(None), 'fuzzy'),
        else_='semantic',
    ).label('match_type')
    # Nothing strong: the K_FALLBACK nearest documents from a cosine of T_FALLBACK on
    fallback = and_(
        found.c.sem_ok, ~found.c.any_strong, found.c.cos >= T_FALLBACK, found.c.cos_rank <= K_FALLBACK
    )
    return (
        select(*_DOCUMENT_COLUMNS, score, match_type, found.c.cos)
        .join_from(found, DocumentRow, DocumentRow.id == found.c.document_id)
        .where(or_(found.c.strong, fallback))
        .order_by(score.desc(), DocumentRow.id)
        .limit(bindparam('limit'))
    )


_SEARCH_DOCUMENTS = _search_documents_statement()


def search_documents(
    engine: Engine,
    q: str,
    qvec: npt.NDArray[np.float32],
    alt: str | None,
    alt_sim: float | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Documents for a prepared query, best first, at most `limit`.

    `qvec` is the query's vector; `alt` is the concept phrase the query misspells and `alt_sim` its similarity
    to the query, or both are None. Rows: the document's columns, score (unrounded), match_type and cos (of
    the best chunk).
    - `lexical`: every query word is in the title or the content (stemmed, stop words ignored); a query of
      nothing but stop words (`will`) can match only titles, by its words as typed. `concept`: only with the
      concept tags. Score EXACT_SCORE_MIN to 1, higher with the cosine.
    - `fuzzy`, only when nothing is lexical or concept: the title is similar to the query, or the document
      contains `alt`. Score FUZZY_SCORE_MAX times the similarity.
    - `semantic`, never for a query without a searchable word: a cosine of at least T_STRONG and within DELTA
      of the best document's; when nothing else is found, the K_FALLBACK nearest documents from T_FALLBACK on.
      Score EXACT_SCORE_MIN times the cosine.
    """
    params = {'q': q, 'qvec': qvec, 'alt': alt, 'alt_sim': alt_sim, 'limit': limit}
    with _connection(engine) as conn:
        return [dict(row) for row in conn.execute(_SEARCH_DOCUMENTS, params).mappings()]


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


@dataclass(frozen=True)
class AppMeta:
    """What stored vectors and tags are built with: the row of app_meta."""

    model_revision: str
    tokenizer_settings: dict[str, Any]
    concepts_sha256: str | None  # None: concept tagging is off


def read_app_meta(engine: Engine) -> AppMeta:
    """The stored row, written by write_app_meta at the first start."""
    statement = select(AppMetaRow.model_revision, AppMetaRow.tokenizer_settings, AppMetaRow.concepts_sha256)
    with _connection(engine) as conn:
        row = conn.execute(statement).one()
    return AppMeta(*row)


def write_app_meta(engine: Engine, meta: AppMeta) -> None:
    """Store the running configuration when the table is empty; an existing row is kept."""
    statement = (
        pg_insert(AppMetaRow)
        .values(
            model_revision=meta.model_revision,
            tokenizer_settings=meta.tokenizer_settings,
            concepts_sha256=meta.concepts_sha256,
        )
        .on_conflict_do_nothing(index_elements=[AppMetaRow.id])
    )
    with _connection(engine) as conn:
        conn.execute(statement)
