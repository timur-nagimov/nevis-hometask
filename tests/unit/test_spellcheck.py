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
def test_a_phrase_itself_a_distant_query_and_punctuation_are_not_corrected(
    concepts: Concepts, q: str
) -> None:
    assert concepts.alt(q) == (None, None)


def test_the_vocabulary_is_concept_names_and_triggers_of_min_spell_chars_or_more(tmp_path: Path) -> None:
    short = 'x' * (MIN_SPELL_CHARS - 1)
    path = tmp_path / 'concepts.yaml'
    path.write_text(
        f'- concept: proof of address\n  triggers: [address proof, {short}]\n  expands_to: [utility bill]\n',
        encoding='utf-8',
    )
    concepts = Concepts.load(path)

    assert concepts.alt('proof of adress')[0] == 'proof of address'  # the concept name
    assert concepts.alt('adress proof')[0] == 'address proof'  # a trigger
    assert concepts.alt('utilty bill') == (None, None)  # an expands_to phrase is not in it
    assert concepts.alt(short + 'x') == (None, None)  # similar enough, but the trigger is too short
