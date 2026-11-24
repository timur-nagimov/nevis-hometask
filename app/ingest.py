"""Document ingest: what is stored and embedded for an uploaded document.

The lead summary, the chunker and the tagging rules are the code the search quality was measured with:
change what they return only together with a new measurement.
"""

import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit
from uuid import UUID

import yaml

from app import db
from app.config import (
    CHUNK_WORDS,
    ELLIPSIS,
    EXTRACTIVE,
    MIN_SPELL_CHARS,
    SHORT_DOC_WORDS,
    SPELL_CUTOFF,
    SUMMARY_CHARS,
    TAGS_CHUNK_NO,
    Services,
)
from app.schemas import Document, DocumentCreate

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')  # the summary takes whole sentences


def lead_summary(content: str, limit: int = SUMMARY_CHARS) -> str:
    """The first sentences of the content, as many as fit into `limit` characters, whitespace collapsed.

    A longer first sentence is cut at its last space within `limit` characters (at `limit` if it has none),
    loses a comma, semicolon or colon before the cut, and ends with ELLIPSIS.
    """
    text = ' '.join(content.split())
    out = ''
    for sentence in _SENTENCE_END.split(text):
        if not out:
            if len(sentence) > limit:
                return sentence[:limit].rsplit(' ', 1)[0].rstrip(',;:') + ELLIPSIS
            out = sentence
        elif len(out) + 1 + len(sentence) <= limit:
            out += ' ' + sentence
        else:
            break
    return out


_CLAUSE_END = re.compile(r'(?<=[.!?;:])\s+')  # where a long paragraph may be split


def _split_long(paragraph: str, max_words: int) -> list[str]:
    """A paragraph over max_words: split at sentence ends (also ';' and ':'), then at word boundaries."""
    if len(paragraph.split()) <= max_words:
        return [paragraph]
    out: list[str] = []
    current: list[str] = []
    n = 0
    for sentence in _CLAUSE_END.split(paragraph):
        words = len(sentence.split())
        if words > max_words:  # one huge sentence: hard word windows
            if current:
                out.append(' '.join(current))
                current, n = [], 0
            tokens = sentence.split()
            out.extend(' '.join(tokens[i : i + max_words]) for i in range(0, len(tokens), max_words))
            continue
        if n + words > max_words and current:
            out.append(' '.join(current))
            current, n = [], 0
        current.append(sentence)
        n += words
    if current:
        out.append(' '.join(current))
    return out


def _content_chunks(content: str, max_words: int = CHUNK_WORDS) -> list[str]:
    """Content of at most max_words words is one chunk, verbatim.

    Otherwise paragraphs (split on blank lines) are packed greedily up to max_words
    and joined by a blank line; no overlap.
    """
    if len(content.split()) <= max_words:
        return [content]
    units: list[str] = []
    for paragraph in re.split(r'\n\s*\n', content):
        stripped = paragraph.strip()
        if stripped:
            units.extend(_split_long(stripped, max_words))
    chunks: list[list[str]] = []
    current: list[str] = []
    n = 0
    for unit in units:
        words = len(unit.split())
        if n + words > max_words and current:
            chunks.append(current)
            current, n = [], 0
        current.append(unit)
        n += words
    if current:
        chunks.append(current)
    return ['\n\n'.join(chunk) for chunk in chunks]


def chunk_document(title: str, content: str) -> list[str]:
    """The texts to embed for the content, in chunk order (chunk_no 0, 1, ...): title + newline + chunk."""
    return [f'{title}\n{chunk}' for chunk in _content_chunks(content)]


class ConceptEntry(TypedDict):
    concept: str  # the tag shown in the API; also matched against the document
    triggers: list[str]  # how people ask for it; written into tags_text, never matched
    expands_to: list[str]  # the documents that are evidence of it; matched against the document
    sources: list[str]  # official lists stating the relation; not used for matching


# the keys of ConceptEntry: the only ones an entry in the file may have
_ENTRY_KEYS = tuple(ConceptEntry.__annotations__)


class Concepts:
    """The concept map, loaded once at start-up: its entries in file order and the phrases they match."""

    def __init__(self, entries: list[ConceptEntry], sha256: str) -> None:
        self.entries = entries
        self.sha256 = sha256  # of the file's bytes; stored in app_meta
        self._entry_numbers: list[int] = []
        self._phrases: list[str] = []
        self.known: set[str] = set()  # every concept name and trigger, normalised: never corrected
        for number, entry in enumerate(entries):
            for phrase in [entry['concept'], *entry['expands_to']]:
                self._entry_numbers.append(number)
                self._phrases.append(phrase)
            for name in [entry['concept'], *entry['triggers']]:
                self.known.add(self.norm(name))
        self.known.discard('')  # left by a trigger of punctuation only
        # what a query can be corrected to
        self.candidates = sorted(name for name in self.known if len(name) >= MIN_SPELL_CHARS)

    @classmethod
    def load(cls, path: str | Path) -> Concepts:
        """Read and check a concept file. Errors name the file and the entry, never the file's text."""
        data = Path(path).read_bytes()
        raw = _parse_yaml(path, data)
        if not isinstance(raw, list) or not raw:
            raise ValueError(f'{path}: expected a non-empty list of concept entries')
        entries = [_entry(path, number, item) for number, item in enumerate(raw)]
        return cls(entries, hashlib.sha256(data).hexdigest())

    @staticmethod
    def norm(s: str) -> str:
        """Casefolded; every run of characters other than letters and digits made one space; trimmed."""
        return ' '.join(re.sub(r'[\W_]+', ' ', s.casefold()).split())

    def alt(self, q: str) -> tuple[str | None, float | None]:
        """The concept name or trigger that `q` misspells, and their similarity; (None, None) if none.

        That is the candidate closest to the normalised query, from a similarity of SPELL_CUTOFF on. A query
        that is a concept name or trigger itself is not corrected.
        """
        normalised = self.norm(q)
        if not normalised or normalised in self.known:
            return None, None
        best = difflib.get_close_matches(normalised, self.candidates, n=1, cutoff=SPELL_CUTOFF)
        if not best:
            return None, None
        return best[0], difflib.SequenceMatcher(None, normalised, best[0]).ratio()

    def phrase_arrays(self) -> tuple[list[int], list[str]]:
        """Parallel arrays for the concept match: the entry number of every phrase, and the phrase.

        An entry's phrases are its concept name and its expands_to phrases, not its triggers.
        """
        return self._entry_numbers, self._phrases

    def sentence(self, number: int) -> str:
        """`concept, trigger, trigger, ... .` (a trigger equal to the concept name is not repeated)."""
        entry = self.entries[number]
        triggers = [trigger for trigger in entry['triggers'] if trigger != entry['concept']]
        return ', '.join([entry['concept'], *triggers]) + '.'


def _parse_yaml(path: str | Path, data: bytes) -> object:
    try:
        return yaml.safe_load(data)
    except Exception as exc:  # also plain errors, e.g. for a value its explicit tag does not fit (!!int x)
        mark = exc.problem_mark if isinstance(exc, yaml.MarkedYAMLError) else None
        where = f' (line {mark.line + 1}, column {mark.column + 1})' if mark is not None else ''
    # PyYAML's messages may quote the file: raised here, not in `except`, so they are not chained
    raise ValueError(f'{path}: not a valid YAML file{where}')


def _strings(path: str | Path, number: int, key: str, value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError(f"{path}: entry {number}: '{key}' must be a list of non-empty strings")
    return value


def _is_https_url(text: str) -> bool:
    try:
        parts = urlsplit(text)
    except ValueError:  # e.g. a bracketed host that is no IP address; the message would quote it
        return False
    return parts.scheme == 'https' and bool(parts.hostname)


def _entry(path: str | Path, number: int, item: object) -> ConceptEntry:
    if not isinstance(item, dict):
        raise ValueError(f'{path}: entry {number} is not a mapping')
    if any(key not in _ENTRY_KEYS for key in item):
        raise ValueError(f'{path}: entry {number}: unknown keys; an entry has only {", ".join(_ENTRY_KEYS)}')
    concept = item.get('concept')
    if not isinstance(concept, str) or not concept.strip():
        raise ValueError(f"{path}: entry {number}: 'concept' must be a non-empty string")
    sources = _strings(path, number, 'sources', item.get('sources', []))
    for index, url in enumerate(sources):
        if not _is_https_url(url):
            raise ValueError(f'{path}: entry {number}: source {index} is not an https URL')
    return ConceptEntry(
        concept=concept,
        triggers=_strings(path, number, 'triggers', item.get('triggers')),
        expands_to=_strings(path, number, 'expands_to', item.get('expands_to')),
        sources=sources,
    )


def load_concepts(path: str) -> Concepts | None:
    """The map named by NEVIS_CONCEPTS_FILE; None when the setting is empty (no tags at all)."""
    return Concepts.load(path) if path else None


@dataclass(frozen=True)
class Tagging:
    tags: list[str]  # concept names of all matched entries, file order, no duplicates (in the API)
    tags_text: str  # one sentence per matched entry (searched through documents.fts)
    head_text: str  # sentences of the head entries only; '' means no tags chunk (TAGS_CHUNK_NO)


def tagging_from_matches(concepts: Concepts, matches: list[tuple[int, bool, bool]], content: str) -> Tagging:
    """Tags from the matched entries, in entry order: (entry number, in the title, in title or content).

    Head entries: matched in the title, or matched anywhere when the content has at most SHORT_DOC_WORDS
    words. Only head entries are embedded (the tags chunk, TAGS_CHUNK_NO): otherwise a long letter that
    mentions a bill in passing would look like proof of address.
    """
    short = len(content.split()) <= SHORT_DOC_WORDS
    matched = [entry for entry, _, _ in matches]
    head = [entry for entry, in_title, anywhere in matches if in_title or (anywhere and short)]
    return Tagging(
        tags=list(dict.fromkeys(concepts.entries[number]['concept'] for number in matched)),
        tags_text=' '.join(concepts.sentence(number) for number in matched),
        head_text=' '.join(concepts.sentence(number) for number in head),
    )


def tag_document(services: Services, title: str, content: str) -> Tagging:
    """The concept tags of a document, matched by the database in one round trip; none without a map."""
    if services.concepts is None:
        return Tagging(tags=[], tags_text='', head_text='')
    entries, phrases = services.concepts.phrase_arrays()
    matches = db.match_concepts(services.engine, title, content, entries, phrases)
    return tagging_from_matches(services.concepts, matches, content)


def create_document(services: Services, client_id: UUID, payload: DocumentCreate) -> Document:
    """Tag, summarise, chunk, embed and store one document.
    The caller has validated the payload and checked that the client exists."""
    tagging = tag_document(services, payload.title, payload.content)
    summary = lead_summary(payload.content)
    texts = chunk_document(payload.title, payload.content)
    chunk_numbers = list(range(len(texts)))
    if tagging.head_text:  # the tags are embedded only when there are head entries
        texts.append(f'{payload.title}\n{tagging.head_text}')
        chunk_numbers.append(TAGS_CHUNK_NO)
    vectors = services.embedder.embed_documents(texts)
    row = db.insert_document(
        services.engine,
        client_id=client_id,
        title=payload.title,
        content=payload.content,
        tags=tagging.tags,
        tags_text=tagging.tags_text,
        summary=summary,
        summary_method=EXTRACTIVE,
        chunks=list(zip(chunk_numbers, vectors, strict=True)),
    )
    return Document.from_row(row)
