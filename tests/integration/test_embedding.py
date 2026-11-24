"""The embedder: vector shape and norm, batches, the query prefix, the token limit, the two lanes, threads;
the self-check the image build runs.

Needs the model, not the database. On the host, with the model downloaded to .cache/models/leaf-ir:
    NEVIS_MODEL_DIR=.cache/models/leaf-ir uv run pytest tests/integration/test_embedding.py
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import numpy.typing as npt
import pytest
from tokenizers import Tokenizer

from app.config import EMBED_BATCH, EMBED_INTER_OP_THREADS, QUERY_PREFIX, TOKENIZER_FILE
from app.embedding import (
    DEFAULT_MODEL_DIR,
    DIM,
    MAX_TOKENS,
    Embedder,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = os.environ.get('NEVIS_MODEL_DIR', DEFAULT_MODEL_DIR)
THREADS = 2


@pytest.fixture(scope='module')
def embedder() -> Embedder:
    return Embedder(MODEL_DIR, threads=THREADS)


@pytest.fixture(scope='module')
def raw_tokenizer() -> Tokenizer:
    """The model's tokenizer without cut and padding, to count the tokens of a whole text."""
    tokenizer = Tokenizer.from_file(str(Path(MODEL_DIR) / TOKENIZER_FILE))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def test_vectors_have_768_dimensions_and_unit_norm(embedder: Embedder) -> None:
    vectors = [embedder.embed_query('address proof'), *embedder.embed_documents(['Utility bill', 'Passport'])]
    for vector in vectors:
        assert vector.shape == (DIM,) and vector.dtype == np.float32
        assert abs(float(np.linalg.norm(vector)) - 1.0) < 1e-5


def test_vectors_are_scaled_to_unit_length_and_a_zero_vector_stays_zero(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the pinned model already returns unit vectors, so the model's output is replaced
    output = np.zeros((2, DIM), dtype=np.float32)
    output[1, :2] = (3.0, 4.0)  # length 5
    monkeypatch.setattr(embedder, '_session', SimpleNamespace(run=lambda outputs, feed: [output]))

    zero, scaled = embedder.embed_documents(['Utility bill', 'Passport'])

    assert np.array_equal(zero, np.zeros(DIM))  # not NaN
    assert np.allclose(scaled[:2], (0.6, 0.8)) and not scaled[2:].any()


def test_batches_keep_the_input_order(embedder: Embedder) -> None:
    texts = [f'Document {i} about a pension transfer.' for i in range(EMBED_BATCH + 2)]  # two calls, one full
    together = embedder.embed_documents(texts)
    alone = [embedder.embed_documents([text])[0] for text in texts]
    for a, b in zip(together, alone, strict=True):
        assert float(np.max(np.abs(a - b))) < 1e-5


def test_the_query_prefix_changes_the_vector(embedder: Embedder) -> None:
    query = embedder.embed_query('address proof')
    plain = embedder.embed_documents(['address proof'])[0]
    prefixed = embedder.embed_documents([QUERY_PREFIX + 'address proof'])[0]
    assert float(np.max(np.abs(query - prefixed))) < 1e-5  # the query lane adds exactly the prefix
    assert float(query @ plain) < 0.99


def test_texts_are_cut_at_the_512th_token(embedder: Embedder, raw_tokenizer: Tokenizer) -> None:
    # MAX_TOKENS includes [CLS] and [SEP]; 'word' is one token
    room_for_one = 'word ' * (MAX_TOKENS - 3)  # the first token of a tail is the last one read
    no_room = 'word ' * (MAX_TOKENS - 2)  # the tails start right after the cut
    counts = [len(raw_tokenizer.encode(filler).ids) for filler in (room_for_one, no_room)]
    assert counts == [MAX_TOKENS - 1, MAX_TOKENS]
    tails = ['Utility bill.', 'Passport.']  # they differ from their first token on

    a, b = embedder.embed_documents([room_for_one + tail for tail in tails])
    c, d = embedder.embed_documents([no_room + tail for tail in tails])  # too long for the model if not cut

    assert float(np.max(np.abs(a - b))) > 1e-4  # with the shipped truncation at 128 they would be equal
    assert float(np.max(np.abs(c - d))) < 1e-6


class LaneLog:
    """Takes the place of a lane and notes in `log` when it is taken and released."""

    def __init__(self, name: str, log: list[str]) -> None:
        self._name = name
        self._log = log

    def __enter__(self) -> None:
        self._log.append(f'{self._name} taken')

    def __exit__(self, *exc_info: object) -> None:
        self._log.append(f'{self._name} released')


def test_a_lane_is_held_for_one_call_of_at_most_embed_batch_texts(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    log: list[str] = []
    session = embedder._session

    def run(outputs: list[str], feed: dict[str, npt.NDArray[np.int64]]) -> object:
        texts = len(feed['input_ids'])
        log.append(f'run {texts}')
        return session.run(outputs, feed)

    monkeypatch.setattr(embedder, '_session', SimpleNamespace(run=run))
    monkeypatch.setattr(embedder, '_document_lane', LaneLog('documents', log))
    monkeypatch.setattr(embedder, '_query_lane', LaneLog('queries', log))

    embedder.embed_documents([f'Page {i} of a bank statement.' for i in range(2 * EMBED_BATCH + 1)])
    embedder.embed_query('address proof')

    full = ['documents taken', f'run {EMBED_BATCH}', 'documents released']
    rest = ['documents taken', 'run 1', 'documents released']
    assert log == [*full, *full, *rest, 'queries taken', 'run 1', 'queries released']


def test_a_query_does_not_wait_for_a_document_batch(embedder: Embedder) -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        with embedder._document_lane:  # as if an upload's batch were running
            query = pool.submit(embedder.embed_query, 'address proof')
            assert query.result(timeout=30).shape == (DIM,)
            batch = pool.submit(embedder.embed_documents, ['Passport'])
            with pytest.raises(TimeoutError):  # another batch waits for the lane
                batch.result(timeout=0.5)
        assert batch.result(timeout=30)[0].shape == (DIM,)


def test_sixteen_threads_share_one_embedder(embedder: Embedder) -> None:
    texts = [f'Statement {i}: interest paid on the savings account.' for i in range(16)]
    expected_documents = embedder.embed_documents(texts)
    expected_queries = [embedder.embed_query(text) for text in texts]

    def work(i: int) -> None:
        for call in range(20):
            if (i + call) % 2:
                got, want = embedder.embed_query(texts[i]), expected_queries[i]
            else:
                got, want = embedder.embed_documents([texts[i]])[0], expected_documents[i]
            assert float(np.max(np.abs(got - want))) <= 1e-5, f'thread {i}, call {call}: another vector'

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(work, i) for i in range(16)]
    for future in futures:
        future.result()  # raises what its thread raised


def test_the_session_runs_on_the_given_threads(embedder: Embedder) -> None:
    options = embedder._session.get_session_options()
    assert (options.intra_op_num_threads, options.inter_op_num_threads) == (THREADS, EMBED_INTER_OP_THREADS)


def test_selfcheck_command_exits_0() -> None:
    command = [sys.executable, '-m', 'app.embedding', '--selfcheck', '--model-dir', MODEL_DIR]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('selfcheck ok: MongoDB/mdbr-leaf-ir@4262131 dim=768')
