"""The concept map: the shipped file, loading and checking a map, its phrases, sentences and head entries."""

import hashlib
import sys
from pathlib import Path

import pytest

from app.config import PACKAGED_CONCEPTS_FILE, SHORT_DOC_WORDS
from app.ingest import Concepts, load_concepts, tagging_from_matches

GOV = 'https://www.gov.uk/'
CHECKLIST = GOV + 'government/publications/proof-of-identity-checklist/proof-of-identity-checklist'
DBS = (
    GOV + 'government/publications/dbs-identity-checking-guidelines/'
    'id-checking-guidelines-for-standardenhanced-dbs-check-applications-from-22-april-2025'
)
JSA = GOV + 'jobseekers-allowance/your-jsa-interview'
JMLSG = 'https://www.jmlsg.org.uk/wp-content/uploads/2026/10/JMLSG-Guidance-Part-I_Oct-2026.pdf'
FAMILY_VISA = GOV + 'uk-family-visa/provide-information'
PLANTED = 'Zq9planted'  # file content that no error message may repeat

MINI = """
- concept: proof of address
  triggers: [proof of address, address proof]
  expands_to: [utility bill, council tax bill]
  sources: ["https://www.gov.uk/jobseekers-allowance/your-jsa-interview"]
- concept: customer due diligence
  triggers: [kyc]
  expands_to: [utility bill]
- concept: proof of address
  triggers: [residence proof]
  expands_to: [tenancy agreement]
"""


def words(n: int) -> str:
    return ' '.join(['word'] * n)


@pytest.fixture
def mini(tmp_path: Path) -> Concepts:
    path = tmp_path / 'concepts.yaml'
    path.write_text(MINI, encoding='utf-8')
    return Concepts.load(path)


def test_the_shipped_map_has_30_entries_and_four_official_sources() -> None:
    concepts = Concepts.load(PACKAGED_CONCEPTS_FILE)
    assert len(concepts.entries) == 30
    assert {e['concept']: e['sources'] for e in concepts.entries if e['sources']} == {
        'proof of identity': [CHECKLIST, DBS],
        'proof of address': [JSA, CHECKLIST],
        'customer due diligence': [JMLSG],
        'proof of income': [FAMILY_VISA],
    }


def test_the_hash_is_of_the_file_bytes(mini: Concepts) -> None:
    assert mini.sha256 == hashlib.sha256(MINI.encode()).hexdigest()


def test_phrases_are_the_concept_name_and_expands_to(mini: Concepts) -> None:
    assert mini.phrase_arrays() == (
        [0, 0, 0, 1, 1, 2, 2],
        [
            'proof of address',
            'utility bill',
            'council tax bill',
            'customer due diligence',
            'utility bill',
            'proof of address',
            'tenancy agreement',
        ],
    )


def test_a_sentence_is_the_concept_then_the_other_triggers(mini: Concepts) -> None:
    assert mini.sentence(0) == 'proof of address, address proof.'
    assert mini.sentence(1) == 'customer due diligence, kyc.'


def test_sources_are_optional(mini: Concepts) -> None:
    assert [entry['sources'] for entry in mini.entries] == [[JSA], [], []]


def test_tags_keep_file_order_without_duplicates(mini: Concepts) -> None:
    tagging = tagging_from_matches(mini, [(0, False, True), (1, False, True), (2, False, True)], 'short')
    assert tagging.tags == ['proof of address', 'customer due diligence']
    assert tagging.tags_text == (
        'proof of address, address proof. customer due diligence, kyc. proof of address, residence proof.'
    )


def test_head_entries_are_title_matches_or_any_match_in_a_short_document(mini: Concepts) -> None:
    long_content = words(SHORT_DOC_WORDS + 1)
    short = tagging_from_matches(mini, [(0, False, True)], words(SHORT_DOC_WORDS))
    titled = tagging_from_matches(mini, [(0, True, True), (1, False, True)], long_content)
    passing = tagging_from_matches(mini, [(1, False, True)], long_content)
    assert short.head_text == 'proof of address, address proof.'
    assert titled.head_text == 'proof of address, address proof.'
    assert titled.tags == ['proof of address', 'customer due diligence']
    # a match in passing is still a tag and searchable text, only not embedded
    assert (passing.tags, passing.tags_text) == (['customer due diligence'], 'customer due diligence, kyc.')
    assert passing.head_text == ''


def test_an_empty_setting_disables_the_map() -> None:
    assert load_concepts('') is None


@pytest.mark.parametrize(
    ('text', 'message'),
    [
        ("- concept: x\n  triggers: []\n  expands_to: []\n  sources: ['http://example.com']\n", 'https'),
        ("- concept: x\n  triggers: []\n  expands_to: []\n  sources: ['https:///no-host']\n", 'https'),
        ('- concept: x\n  triggers: []\n  expand_to: [y]\n', 'unknown keys'),
        ("- concept: ' '\n  triggers: []\n  expands_to: []\n", 'concept'),
        ("- concept: x\n  triggers: ['  ']\n  expands_to: []\n", 'triggers'),
        ('- concept: x\n  triggers: []\n', 'expands_to'),
        ('- concept: x\n  triggers: []\n  expands_to: [1040]\n', 'expands_to'),  # YAML reads 1040 as a number
        ("- concept: x\n  triggers: []\n  expands_to: [ok, ' ']\n", 'expands_to'),
        ("- concept: x\n  triggers: []\n  expands_to: []\n  sources: [' ']\n", "'sources' must be"),
        ('- just a phrase\n', 'not a mapping'),
        ('{}', 'non-empty list'),
        ('[]', 'non-empty list'),
        ('', 'non-empty list'),
        (
            '- concept: x\n  triggers: [a]\n  expands_to: b: c\n',
            r'not a valid YAML file \(line 3, column 16\)',
        ),
        # PyYAML gives no position for these: a value its tag does not fit, and nesting too deep to read
        ('- concept: !!int x\n  triggers: []\n  expands_to: []\n', 'not a valid YAML file$'),
        ('[' * sys.getrecursionlimit() + ']' * sys.getrecursionlimit(), 'not a valid YAML file$'),
    ],
    # explicit ids: the default ids are the YAML texts, and the first one would match `-k sources`
    ids=[
        'http-url',
        'url-without-host',
        'unknown-key',
        'blank-concept',
        'blank-trigger',
        'no-expands-to',
        'number-phrase',
        'blank-expands-to',
        'blank-source',
        'not-a-mapping',
        'not-a-list',
        'empty-list',
        'empty-file',
        'not-yaml',
        'tag-value-mismatch',
        'too-deep',
    ],
)
def test_invalid_files_are_rejected(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / 'bad.yaml'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        Concepts.load(path)


@pytest.mark.parametrize(
    'text',
    [
        f'- concept: x\n  triggers: [{PLANTED}\n',
        PLANTED,
        f'- concept: x\n  triggers: []\n  expands_to: []\n  {PLANTED}: y\n',
        f"- concept: x\n  triggers: []\n  expands_to: []\n  sources: ['http://{PLANTED}.example']\n",
        f"- concept: x\n  triggers: []\n  expands_to: []\n  sources: ['https://[{PLANTED}]/']\n",
        # a value its explicit tag does not fit: PyYAML raises a plain exception
        f'- concept: !!int {PLANTED}\n',
    ],
    ids=[
        'unclosed-list',
        'not-a-list',
        'unknown-key',
        'http-url',
        'bracketed-host',
        'int-tag',
    ],
)
def test_errors_name_the_file_and_quote_nothing_from_it(tmp_path: Path, text: str) -> None:
    """A wrong NEVIS_CONCEPTS_FILE may point at a file with secrets: the error must not show them."""
    path = tmp_path / 'bad.yaml'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError) as error:
        Concepts.load(path)
    assert str(error.value).startswith(f'{path}: ')
    assert PLANTED not in str(error.value)
    assert error.value.__context__ is None  # PyYAML's and urllib's own messages quote the file
