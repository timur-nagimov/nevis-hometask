"""Concept tags matched by the database: whole phrases, stemmed and without punctuation, the stop-word edge
rule, head entries, entry order; no tags without a concept map."""

import dataclasses
from pathlib import Path

import pytest
from psycopg.conninfo import make_conninfo

from app import db
from app.config import PACKAGED_CONCEPTS_FILE, SHORT_DOC_WORDS, Services, Settings
from app.ingest import Concepts, Tagging, tag_document

UTILITY = (
    'British Gas utility bill for March 2025. '
    'Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.'
)
SENTENCE = 'The adviser and the client discussed the portfolio allocation.'  # matches no phrase of the map
FILLER = ' '.join([SENTENCE] * SHORT_DOC_WORDS)  # a long document: far over SHORT_DOC_WORDS words
BILL = ['proof of address', 'customer due diligence']
EDGE = """
- concept: trust deeds
  triggers: [trust deeds]
  expands_to: [will trust, trust in, deed of trust]
"""
PUNCTUATED = """
- concept: proof of address
  triggers: [proof of address]
  expands_to: ['"utility bill"', '(council tax bill)']
"""


@pytest.fixture(scope='module')
def tagger(services: Services) -> Services:
    """The module's services with the shipped concept map, whatever the settings say."""
    return dataclasses.replace(services, concepts=Concepts.load(PACKAGED_CONCEPTS_FILE))


def test_a_short_bill_gets_both_concepts_as_head_entries(tagger: Services) -> None:
    tagging = tag_document(tagger, 'Utility bill', UTILITY)
    assert tagging.tags == BILL
    assert tagging.tags_text.startswith('proof of address, address proof, proof of residence, ')
    assert tagging.head_text == tagging.tags_text


def test_a_title_match_makes_a_long_document_head(tagger: Services) -> None:
    tagging = tag_document(tagger, 'Utility bill', FILLER)
    assert tagging.tags == BILL and tagging.head_text == tagging.tags_text


def test_a_short_document_is_head_when_the_phrase_is_only_in_the_text(tagger: Services) -> None:
    assert len(UTILITY.split()) <= SHORT_DOC_WORDS
    tagging = tag_document(tagger, 'Scan 0042', UTILITY)
    assert tagging.tags == BILL and tagging.head_text == tagging.tags_text


def test_a_long_document_mentioning_a_bill_in_passing_has_tags_but_no_head(tagger: Services) -> None:
    tagging = tag_document(tagger, 'Meeting notes', FILLER + ' The client will send a utility bill soon.')
    assert tagging.tags == BILL and tagging.head_text == ''


def test_matching_is_stemmed_and_ignores_punctuation(tagger: Services) -> None:
    assert tag_document(tagger, 'Forms', 'Two utility-bills attached.').tags == BILL


def test_a_phrase_starting_or_ending_with_a_stop_word_is_skipped(tagger: Services, tmp_path: Path) -> None:
    path = tmp_path / 'edge.yaml'
    path.write_text(EDGE, encoding='utf-8')
    custom = dataclasses.replace(tagger, concepts=Concepts.load(path))
    # 'will trust' and 'trust in' would shrink to 'trust' and match any trust: both are skipped
    assert tag_document(custom, 'Note', 'A discretionary trust was set up in 2019.').tags == []
    assert tag_document(custom, 'Note', 'The deed of trust is attached.').tags == ['trust deeds']


def test_a_phrase_matches_only_in_order_whatever_punctuation_surrounds_it(
    tagger: Services, tmp_path: Path
) -> None:
    path = tmp_path / 'punctuated.yaml'
    path.write_text(PUNCTUATED, encoding='utf-8')
    custom = dataclasses.replace(tagger, concepts=Concepts.load(path))
    assert tag_document(custom, 'Note', 'A copy of the utility bill.').tags == ['proof of address']
    assert tag_document(custom, 'Note', 'Council tax bill, March.').tags == ['proof of address']
    # both words, but not as the phrase
    assert tag_document(custom, 'Note', 'The bill from the utility company.').tags == []


def test_no_concept_map_means_no_tags(tagger: Services) -> None:
    disabled = dataclasses.replace(tagger, concepts=None)
    assert tag_document(disabled, 'Utility bill', UTILITY) == Tagging(tags=[], tags_text='', head_text='')


def test_each_matched_entry_comes_once_in_entry_order_with_where_it_matched(fresh_dsn: str) -> None:
    # Sorting is off for this session, so the database groups the matches by hashing: the entry order has to
    # come from the statement itself
    engine = db.open_engine(Settings(database_url=make_conninfo(fresh_dsn, options='-c enable_sort=off')))
    entries = [5, 3, 0, 4, 1, 3, 2, 5, 0]
    phrases = [
        'passport',  # 5: in the content
        'gas bill',  # 3: in the title, and again below
        'deed poll',  # 0: nowhere ...
        'tenancy agreement',  # 4: nowhere
        'bank statements',  # 1: in the content, stemmed
        'gas bill',
        'council tax',  # 2: in the title
        'payslip',
        'utility bill',  # 0: ... but this one is in the content
    ]
    title = 'Gas bill and council tax'
    content = 'Copies of a passport, a utility bill and two bank statement pages.'
    try:
        rows = db.match_concepts(engine, title, content, entries, phrases)
    finally:
        engine.dispose()

    assert rows == [(0, False, True), (1, False, True), (2, True, True), (3, True, True), (5, False, True)]
