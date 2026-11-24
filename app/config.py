import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import psycopg
from psycopg.conninfo import conninfo_to_dict
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine

if TYPE_CHECKING:  # for the type checker only: app.embedding and app.ingest import this module
    from app.embedding import Embedder
    from app.ingest import Concepts

PACKAGED_CONCEPTS_FILE = str(Path(__file__).parent / 'data' / 'concepts.yaml')  # the shipped concept map
DEFAULT_MODEL_DIR = '/opt/models/leaf-ir'  # where the image keeps the embedding model
DEFAULT_MAX_CONTENT_CHARS = 50_000  # document content limit when NEVIS_MAX_CONTENT_CHARS is not set


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='NEVIS_', hide_input_in_errors=True
    )  # errors never print values

    database_url: SecretStr = Field(min_length=1)  # repr and model_dump print **********
    db_pool_size: int = Field(default=8, ge=1)  # connections; SQLAlchemy reads 0 as no limit
    db_pool_timeout_seconds: float = Field(default=5.0, gt=0)  # wait for a free connection, then 503 busy
    db_connect_timeout_seconds: int = Field(default=3, ge=2)  # libpq counts less than 2 as 2
    db_statement_timeout_ms: int = Field(default=5000, ge=1)  # then 503 timeout; 0 would mean no limit
    model_dir: str = DEFAULT_MODEL_DIR

    embed_threads: int = Field(default_factory=lambda: min(4, os.process_cpu_count() or 1), ge=1)
    concepts_file: str = PACKAGED_CONCEPTS_FILE  # "" disables concept tagging
    max_content_chars: int = Field(default=DEFAULT_MAX_CONTENT_CHARS, ge=1)
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'
    host: str = '127.0.0.1'  # the container image sets 0.0.0.0
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator('database_url')
    @classmethod
    def _readable_by_libpq(cls, value: SecretStr) -> SecretStr:
        """libpq's own errors quote the part they cannot read, and that part may be the password."""
        try:
            parts = conninfo_to_dict(value.get_secret_value())
            # an unencoded @ or / in the password leaves an @ in the host or the database name
            readable = not any('@' in str(parts.get(key) or '') for key in ('host', 'dbname'))
        except psycopg.ProgrammingError:
            readable = False
        if not readable:  # raised here, not in `except`, so libpq's message is not chained to it
            raise ValueError(
                'not a valid PostgreSQL URL: percent-encode @ : / % and spaces in user and password'
            )
        return value


# Document search
DocumentMatchType = Literal['lexical', 'concept', 'fuzzy', 'semantic']  # `match_type` of a document hit
T_STRONG = 0.40  # a semantic hit needs cos >= T_STRONG ...
DELTA = 0.08  # ... and cos >= (best cos of the query) - DELTA
T_FALLBACK = 0.32  # when nothing is a hit: the nearest documents with cos >= T_FALLBACK ...
K_FALLBACK = 3  # ... at most this many
TAU_TITLE = 0.60  # word similarity of query and title from which a title is a typo match
MIN_FUZZY_CHARS = 5  # letters and digits a query needs before typo matching is tried
SPELL_CUTOFF = 0.90  # similarity from which a query is read as a misspelt concept phrase
MIN_SPELL_CHARS = 6  # characters a concept name or trigger needs, normalised, to be offered as a correction
FTS_CONFIG = 'english'  # text search configuration of the documents' tsvector columns and of queries on them
MIN_WORD_CHARS = 2  # shorter pieces of a query are not words: `a`, or the 1s of `1=1`
# A query of stop words only (`will`) finds the titles that contain its words as typed (UNSTEMMED_FTS_CONFIG)
# when its words have at least MIN_STOP_WORDS_CHARS letters and digits together: `of` finds nothing.
UNSTEMMED_FTS_CONFIG = 'simple'
MIN_STOP_WORDS_CHARS = 4

# Client search: a client is `exact` when every query word occurs in it; otherwise, for queries of at least
# MIN_FUZZY_CHARS letters and digits, a typo match from this word similarity on. The weights say how much a
# match in each field counts for the score.
CLIENT_TYPO_SIMILARITY = 0.6
NAME_WEIGHT = 1.0
EMAIL_WEIGHT = 0.7
DESCRIPTION_WEIGHT = 0.5
# The score scale of clients and documents: matches of the query's words score from EXACT_SCORE_MIN to 1,
# typo matches from 0 to FUZZY_SCORE_MAX, documents close in meaning from 0 to EXACT_SCORE_MIN. So every
# match of the query's words ranks above every typo or meaning match, and a caller can read a score of at
# least EXACT_SCORE_MIN as "the query words were found".
EXACT_SCORE_MIN = 0.5
FUZZY_SCORE_MAX = 0.49

# Ingest
SHORT_DOC_WORDS = 200  # in a document up to this length a concept found anywhere counts like one in the title
CHUNK_WORDS = 200  # words per embedded chunk
SUMMARY_CHARS = 300  # length of the lead summary
ELLIPSIS = '\u2026'  # ends a lead summary that had to cut its first sentence
SummaryMethod = Literal['extractive']  # how a document's summary was made: `summary.method` in the API
EXTRACTIVE: SummaryMethod = 'extractive'  # the lead summary, taken from the content as written
TAGS_CHUNK_NO = -1  # chunk_no of the embedded tags; the content chunks are numbered from 0
MAX_CONCURRENT_UPLOADS = 4  # documents processed at once; further uploads wait without holding a thread

# Embedding model, pinned to a Hugging Face commit so the files behind it cannot change.
# scripts/fetch_model.py downloads the same repository, revision and files;
# it cannot import this module, so a unit test compares them.
MODEL_REPO = 'MongoDB/mdbr-leaf-ir'
MODEL_REVISION = '4262131b32c3182bd06e67e92ae69d7bd66e0c5c'
MODEL_FILE = 'onnx/model.onnx'  # in the model directory; its weights sit beside it in model.onnx_data
TOKENIZER_FILE = 'tokenizer.json'
EMBEDDING_DIM = 768  # length of every embedding vector: the model's output and the column type
QUERY_PREFIX = 'Represent this sentence for searching relevant passages: '  # queries only, never documents
MAX_TOKENS = 512  # tokens read per text; the shipped tokenizer.json would stop at 128
# how the embedder cuts and pads texts: at MAX_TOKENS, and to the longest text of each call
TOKENIZER_SETTINGS: dict[str, int | str] = {'truncation': MAX_TOKENS, 'padding': 'batch_longest'}
EMBED_BATCH = 4  # texts per model call
RUNS_PER_LANE = 1  # model calls at once per lane; document batches and queries each have a lane of their own
EMBED_INTER_OP_THREADS = 1  # the model's nodes run one at a time, so a call uses NEVIS_EMBED_THREADS threads
SHORT_REVISION_CHARS = 7  # MODEL_REVISION is shown by its first characters, like a short git hash

# Model self-check (python -m app.embedding --selfcheck; the image build runs it). The cosine of this query
# and this passage, a short document as it is embedded (title, newline, content), was measured once with the
# pinned model; another model or other tokenizer settings give another value.
SELFCHECK_QUERY = 'address proof'
SELFCHECK_PASSAGE = (
    'Utility bill\nBritish Gas utility bill for March 2025. '
    'Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.'
)
GOLDEN_COSINE = 0.1403  # the measured value, to four decimals
GOLDEN_TOLERANCE = 1e-3  # allowed difference from GOLDEN_COSINE: numeric noise across CPUs and thread counts
NORM_TOLERANCE = 1e-4  # allowed difference of a self-check vector's length from 1
SELFCHECK_THREADS = 1  # two short texts need no more

# HTTP contract
MAX_BODY_BYTES = 2 * 1024 * 1024  # larger request bodies are answered with 413
MAX_Q_CHARS = 200  # `q` after whitespace collapsing
DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_NAME_CHARS = 100  # first_name and last_name, after trimming
MAX_EMAIL_CHARS = 254
MAX_DESCRIPTION_CHARS = 2000
MAX_SOCIAL_LINKS = 20
MAX_SOCIAL_LINK_CHARS = 2048  # each link, after trimming
MAX_TITLE_CHARS = 300  # document title, after trimming
SCORE_DECIMALS = 4  # scores in responses are rounded to this many decimals
RETRY_AFTER_SECONDS = 5  # Retry-After of every 503
MAX_ECHOED_ID_CHARS = 64  # an unknown id is quoted in the 404 detail up to this length

# /docs loads Swagger UI from this exact release, so the script it runs cannot change by itself
SWAGGER_UI = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.36.0'


@dataclass(frozen=True)
class Services:
    """What request handling needs, built once at start-up."""

    settings: Settings
    engine: Engine  # the connection pool
    embedder: Embedder
    concepts: Concepts | None  # None: NEVIS_CONCEPTS_FILE is empty, no tagging
