"""Concepts.alt: a query that misspells a concept name or trigger is read as that phrase."""

from pathlib import Path

import pytest

from app.config import MIN_SPELL_CHARS, PACKAGED_CONCEPTS_FILE
from app.ingest import Concepts


@pytest.fixture(scope='module')
def concepts() -> Concepts:
    return Concepts.load(PACKAGED_CONCEPTS_FILE)


@pytest.mark.parametrize(
    'q',
    [
        'adress proof',
        'Adress-Proof',  # case and punctuation do not count
    ],
)
def test_a_misspelt_concept_phrase_is_corrected(concepts: Concepts, q: str) -> None:
    alt, alt_sim = concepts.alt(q)

    assert alt == 'address proof'
    assert alt_sim == pytest.approx(0.96)  # the similarity of the normalised query and the phrase


@pytest.mark.parametrize(
    'q',
    [
        'address proof',  # a trigger itself
        'proof of name',  # 0.857 to "proof of income": below SPELL_CUTOFF
        '????',  # nothing is left after normalising
    ],
)
def test_a_query_that_misspells_no_concept_phrase_is_not_corrected(concepts: Concepts, q: str) -> None:
    assert concepts.alt(q) == (None, None)


def test_the_vocabulary_is_concept_names_and_triggers_of_min_spell_chars_or_more(tmp_path: Path) -> None:
    short = 'x' * (MIN_SPELL_CHARS - 1)
    path = tmp_path / 'concepts.yaml'
    path.write_text(
        f'- concept: proof of address\n  triggers: [address proof, {short}]\n  expands_to: [utility bill]\n',
        encoding='utf-8',
    )

    # neither the expands_to phrase nor the trigger that is too short
    assert Concepts.load(path).candidates == ['address proof', 'proof of address']
