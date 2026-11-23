"""Document ingest: what is stored and embedded for an uploaded document.

The lead summary and the chunker are the code the search quality was measured with: change what they
return only together with a new measurement.
"""

import re

from app.config import CHUNK_WORDS, ELLIPSIS, SUMMARY_CHARS

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')  # the summary takes whole sentences


def lead_summary(content: str, limit: int = SUMMARY_CHARS) -> str:
    """The first sentences of the content, as many as fit into `limit` characters, whitespace collapsed.

    A longer first sentence is cut at its last space within `limit` characters (at `limit` if it has
    none), loses a comma, semicolon or colon before the cut, and ends with ELLIPSIS.
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

    Otherwise paragraphs (split on blank lines) are packed greedily up to max_words and joined by a blank
    line; no overlap.
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
