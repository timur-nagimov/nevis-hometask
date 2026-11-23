"""Settings (NEVIS_* environment variables), the constants of the search rules, the Services bundle."""

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
    """Read from the environment when instantiated: the lifespan does that at start-up, never at import."""

    model_config = SettingsConfigDict(env_prefix="NEVIS_")

    database_url: str
    model_dir: str = "/opt/models/leaf-ir"
    # spec 13.2 B4: min(4, cpus) by default; set it to 1 in a deployment
    embed_threads: int = Field(default_factory=lambda: min(4, os.process_cpu_count() or 1), ge=1)
    concepts_file: str = str(Path(__file__).parent / "data" / "concepts.yaml")  # "" disables concept tagging
    max_content_chars: int = Field(default=50_000, ge=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


# Document search (spec section 2). `cos` is the cosine similarity of the query and a document's best chunk.
T_STRONG = 0.40  # a semantic hit needs cos >= T_STRONG ...
DELTA = 0.08  # ... and cos >= (best cos of the query) - DELTA
T_FALLBACK = 0.32  # when nothing is a hit: the nearest documents with cos >= T_FALLBACK ...
K_FALLBACK = 3  # ... at most this many
TAU_TITLE = 0.60  # word similarity of query and title from which a title is a typo match
MIN_FUZZY_CHARS = 5  # letters and digits a query needs before typo matching is tried
SPELL_CUTOFF = 0.90  # similarity from which a query is read as a misspelt concept phrase

# Ingest (spec sections 2, 6 and 7)
SHORT_DOC_WORDS = 200  # in a document up to this length a concept found anywhere counts like one in the title
CHUNK_WORDS = 200  # words per embedded chunk
SUMMARY_CHARS = 300  # length of the lead summary
EMBED_BATCH = 4  # texts per model call
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "  # queries only, never documents

# HTTP contract (spec section 3)
MAX_BODY_BYTES = 2 * 1024 * 1024  # larger request bodies are answered with 413
MAX_Q_CHARS = 200  # `q` after whitespace collapsing
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


@dataclass(frozen=True)
class Services:
    """What request handling needs, built once at start-up by app.main.build_services()."""

    settings: Settings
    pool: ConnectionPool[Connection[TupleRow]]
    embedder: object | None  # step 3: app.embedding.Embedder
    concepts: object | None  # step 3: app.ingest.Concepts; None also when concept tagging is disabled
