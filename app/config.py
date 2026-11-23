import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='NEVIS_')

    database_url: str
    model_dir: str = '/opt/models/leaf-ir'

    embed_threads: int = Field(default_factory=lambda: min(4, os.process_cpu_count() or 1), ge=1)
    concepts_file: str = str(Path(__file__).parent / 'data' / 'concepts.yaml')  # "" disables concept tagging
    max_content_chars: int = Field(default=50_000, ge=1)
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'


# Document search
T_STRONG = 0.40  # a semantic hit needs cos >= T_STRONG ...
DELTA = 0.08  # ... and cos >= (best cos of the query) - DELTA
T_FALLBACK = 0.32  # when nothing is a hit: the nearest documents with cos >= T_FALLBACK ...
K_FALLBACK = 3  # ... at most this many
TAU_TITLE = 0.60  # word similarity of query and title from which a title is a typo match
MIN_FUZZY_CHARS = 5  # letters and digits a query needs before typo matching is tried
SPELL_CUTOFF = 0.90  # similarity from which a query is read as a misspelt concept phrase

# Ingest
SHORT_DOC_WORDS = 200  # in a document up to this length a concept found anywhere counts like one in the title
CHUNK_WORDS = 200  # words per embedded chunk
SUMMARY_CHARS = 300  # length of the lead summary
EMBED_BATCH = 4  # texts per model call
QUERY_PREFIX = 'Represent this sentence for searching relevant passages: '  # queries only, never documents

# HTTP contract
MAX_BODY_BYTES = 2 * 1024 * 1024  # larger request bodies are answered with 413
MAX_Q_CHARS = 200  # `q` after whitespace collapsing
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


@dataclass(frozen=True)
class Services:
    settings: Settings
    pool: ConnectionPool[Connection[TupleRow]]
    embedder: object | None
    concepts: object | None
