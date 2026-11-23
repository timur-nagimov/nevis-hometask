"""The embedding model, run with onnxruntime: passages and search queries become unit vectors.

The model directory holds MODEL_FILE with its weights and TOKENIZER_FILE; nothing is downloaded at run time.
"""

import os
import threading
from pathlib import Path
from typing import TypedDict

import numpy as np
import numpy.typing as npt

from app.config import (
    DEFAULT_MODEL_DIR,
    EMBED_BATCH,
    EMBED_INTER_OP_THREADS,
    MAX_TOKENS,
    MODEL_FILE,
    MODEL_REPO,
    MODEL_REVISION,
    QUERY_PREFIX,
    RUNS_PER_LANE,
    TOKENIZER_FILE,
    TOKENIZER_SETTINGS,
)
from app.config import EMBEDDING_DIM as DIM

# The model's constants are defined in app.config; listed here, they can also be imported from this module.
__all__ = [
    'DEFAULT_MODEL_DIR',
    'DIM',
    'MAX_TOKENS',
    'MODEL_REPO',
    'MODEL_REVISION',
    'TOKENIZER_SETTINGS',
    'Embedder',
    'EmbedderInfo',
    'Vector',
]

# onnxruntime sends usage data to Microsoft unless ORT_DISABLE_TELEMETRY is set before it starts, and the
# Hugging Face variables keep any hub code offline. Set on import, before Embedder imports onnxruntime.
os.environ.update(ORT_DISABLE_TELEMETRY='1', HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')

OUTPUT = 'sentence_embedding'  # the model's pooled output; it also returns the states of the tokens
PAD_TOKEN = '[PAD]'
LOG_ERRORS_ONLY = 3  # onnxruntime log severity: 0 verbose, 1 info, 2 warning, 3 error, 4 fatal
MIN_NORM = 1e-12  # floor of the norms, so a zero vector cannot turn into NaN

Vector = npt.NDArray[np.float32]


class EmbedderInfo(TypedDict):
    model: str
    revision: str
    tokenizer: dict[str, int | str]
    dim: int
    threads: int


class Embedder:
    """One onnxruntime session and one tokenizer, shared by all request threads.

    Two lanes, one for document batches and one for queries. A model call holds its lane, never a whole
    document, so uploads take turns batch by batch and a search does not wait for them. The session is
    thread-safe; the lanes keep the memory at about two concurrent calls.
    """

    def __init__(self, model_dir: str | Path, threads: int) -> None:
        import onnxruntime as ort  # here, after the variables above are set
        from tokenizers import Tokenizer

        path = Path(model_dir)
        options = ort.SessionOptions()
        options.log_severity_level = LOG_ERRORS_ONLY
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = EMBED_INTER_OP_THREADS
        self._session = ort.InferenceSession(
            str(path / MODEL_FILE), sess_options=options, providers=['CPUExecutionProvider']
        )
        self._input_names: set[str] = {i.name for i in self._session.get_inputs()}
        self._tokenizer = Tokenizer.from_file(str(path / TOKENIZER_FILE))
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)  # the shipped file stops at 128
        pad_id = self._tokenizer.token_to_id(PAD_TOKEN) or 0
        # to the longest text of each call; the shipped file pads every text to 128 tokens
        self._tokenizer.enable_padding(pad_id=pad_id, pad_token=PAD_TOKEN)
        self._threads = threads
        self._document_lane = threading.BoundedSemaphore(RUNS_PER_LANE)
        self._query_lane = threading.BoundedSemaphore(RUNS_PER_LANE)

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        """Passages, without a prefix: a unit vector per text, in input order, EMBED_BATCH texts per call."""
        vectors: list[Vector] = []
        for start in range(0, len(texts), EMBED_BATCH):
            vectors.extend(self._run(texts[start : start + EMBED_BATCH], self._document_lane))
        return vectors

    def embed_query(self, text: str) -> Vector:
        """A search query: QUERY_PREFIX + text, on the query lane."""
        return self._run([QUERY_PREFIX + text], self._query_lane)[0]

    def info(self) -> EmbedderInfo:
        """The model and the settings the vectors come from."""
        return EmbedderInfo(
            model=MODEL_REPO,
            revision=MODEL_REVISION,
            tokenizer=dict(TOKENIZER_SETTINGS),
            dim=DIM,
            threads=self._threads,
        )

    def _run(self, texts: list[str], lane: threading.BoundedSemaphore) -> list[Vector]:
        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        feed = {'input_ids': input_ids}
        if 'attention_mask' in self._input_names:
            feed['attention_mask'] = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        if 'token_type_ids' in self._input_names:
            feed['token_type_ids'] = np.zeros_like(input_ids)
        with lane:  # the model call only; tokenizing runs outside the lane
            outputs = self._session.run([OUTPUT], feed)
        matrix = np.asarray(outputs[0], dtype=np.float32)
        norms = np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), MIN_NORM)
        return list((matrix / norms).astype(np.float32))
