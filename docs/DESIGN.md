# Design

## 1. Constraints I set

Both examples work right after `docker compose up`, offline, with no key. One process, one database. Code readable in
half an hour. Nothing enters the search unless it was measured first.

## 2. Decisions

| Area | Chosen | Instead | Why |
|---|---|---|---|
| Storage | PostgreSQL 18 with pgvector, pg_trgm, unaccent | Elasticsearch, Meilisearch, a vector database | substrings, full text, typos and vectors in one store; a document and its vectors commit in one transaction and are searchable at once; Elasticsearch needs a second service, a refresh before a document is visible, and 0.9-1.5 GB of memory (design-time) |
| Client search | every query word a substring of normalised name + e-mail + description; a trigram typo tier when nothing matches | full-text search; embeddings | an e-mail is one full-text token, so `neviswealth` cannot match; 131 of 134 requirement-level cases (design-time) |
| Document search | one SQL statement: literal, typo and semantic legs, two-stage result rule | rank fusion (RRF), cross-encoders, LLM re-ranking | no measured gain, or seconds per query (design-time) |
| Domain knowledge | concept map applied at upload, 30 entries | synonyms at query time; an LLM on every search | the same map at query time: F1 0.628 / 0.525 against 0.646 / 0.595, dev / test (design-time); an LLM per search adds latency and fails without a key |
| Embeddings | `MongoDB/mdbr-leaf-ir` (Apache-2.0, 768 dimensions, 92 MB) through onnxruntime, in the image | `bge-small`; cloud embeddings | nDCG@10 0.606 against 0.473 for `bge-small` (design-time); works offline |
| Summary | first sentences up to 300 characters, marked `extractive` | LexRank; local LLMs | invents nothing and needs no key; LexRank was not significantly better |
| HTTP | FastAPI, synchronous handlers, one worker | Litestar; async handlers | the most exact OpenAPI for a list that mixes clients and documents (Litestar lost the discriminator); onnxruntime and psycopg release the GIL |
| SQL access | SQLAlchemy 2.1 Core over psycopg 3, tables and queries in `app/db.py` | SQL files run through psycopg | one place for tables and queries; each measured statement, translated, returns the same rows as its SQL did on the test set |
| Schema | created from the models at the first start, on an empty database | numbered migrations (own runner or Alembic) | one schema version, so migration machinery would guard nothing; after a schema change, start from an empty database |
| Vector index | none: every search scans all fragments | HNSW | milliseconds at this scale; needed after about 10,000 fragments (design-time) |

Numbers marked design-time were measured while designing; they are not reproducible from this repository.

## 3. Client search

`search_clients` in `app/db.py` normalises query and record alike (NFKC, no accents, case folded) and returns the
clients whose name, e-mail and description together contain every query word as a substring: `exact`. Not full
text: an e-mail is one token. Only when nothing is `exact` and the query has at least 5 letters or digits does the
typo tier run: trigram word similarity from 0.6, `fuzzy`. Score: `0.5 + 0.5 × similarity` with the fields weighted
(name 1, e-mail 0.7, description 0.5); `fuzzy` gets `0.49 × similarity`. Known misses: matches inside words
(`Chester` finds Manchester), similar names, swapped letters (`Jhon`).

## 4. Document ingest

An upload (`create_document` in `app/ingest.py`) checks the fields (404 for an unknown client), tags the concepts
whose name or `expands_to` phrase occurs in title or text, keeps the first sentences up to 300 characters as the
summary, cuts the text into fragments of up to 200 words with the title in front, adds the tags as a fragment if they
matched in the title or in a document of up to 200 words, embeds in batches of four, and stores it all in one
transaction before the 201. Synchronous by choice: a document is searchable when the 201 returns. Worst case about
2 s for 50,000 characters (design-time: about 40 ms per 200-word fragment on 2 CPUs); at most four uploads run at
once, the others wait without holding a thread.

## 5. Document search

`_search_documents_statement` in `app/db.py` builds one statement with three legs: literal (every query word in the
title, text or tags), typo (only when the literal leg found nothing) and semantic. Two stages: a literal or typo hit,
or a cosine of at least 0.40 within 0.08 of the best, is strong; only when nothing is strong do the three nearest
documents from 0.32 come back, scored below 0.2. On the 1,887 test queries, dropping the weak guesses would add 11
strict passes, but 29 answerable queries would lose every relevant result (design-time reference run).

Result rules compared (design-time, 86 documents, a 38-entry draft of the map):

| Result rule | P / R / F1 | Answered | Junk left empty |
|---|---|---|---|
| one threshold 0.40 / 0.08 | 0.70 / 0.58 / 0.636 | 0.74 | 0.88 |
| one threshold 0.32 / 0.08 | 0.54 / 0.69 / 0.606 | 0.88 | 0.75 |
| one threshold 0.32 / 0.06 | 0.58 / 0.68 / 0.623 | 0.87 | 0.75 |
| two-stage (shipped) | 0.65 / 0.65 / 0.651 | 0.85 | 0.75 |

## 6. The concept map

`app/data/concepts.yaml` models one relation: documents like X are accepted as Y (a utility bill as proof of
address), which embeddings do not know (the README's cosine table). An entry has a `concept` (the tag), `triggers`
(how people ask for it), `expands_to` (the documents that satisfy it) and optional `sources`. The concept and its
`expands_to` phrases match as stemmed phrases; a phrase whose first or last word is a stop word is skipped. Only a
match in the title, or in a document of up to 200 words, enters the embedded tags fragment, so a long letter that
mentions a bill once does not look like proof of address. An LLM drafted 120 entries from general UK
wealth-management knowledge; a rule cut them to 30 (keep needs whose evidence is named differently; drop single
documents, topics and identifiers). Four entries name official lists:

- proof of address: [GOV.UK JSA interview](https://www.gov.uk/jobseekers-allowance/your-jsa-interview);
  [Bona Vacantia checklist](https://www.gov.uk/government/publications/proof-of-identity-checklist/proof-of-identity-checklist)
- proof of identity: [Bona Vacantia checklist](https://www.gov.uk/government/publications/proof-of-identity-checklist/proof-of-identity-checklist);
  [DBS ID checking guidelines](https://www.gov.uk/government/publications/dbs-identity-checking-guidelines/id-checking-guidelines-for-standardenhanced-dbs-check-applications-from-22-april-2025)
- customer due diligence: [JMLSG Guidance Part I, 5.3.75-5.3.76](https://www.jmlsg.org.uk/wp-content/uploads/2026/10/JMLSG-Guidance-Part-I_Oct-2026.pdf)
- proof of income: [GOV.UK family visas, proof of finances](https://www.gov.uk/uk-family-visa/provide-information)

The other 26 entries are curated; no official list was found for them.

A closed list misses the phrasings it lacks ("Council Tax demand notice"), and a letter asking for proof of address
gets the bill's tag. Tags from an LLM at upload could add the missing phrasings and a document-type label.

## 7. Evaluation

`eval/run_testset.py` scores the service's own code on the 1,887 queries of `testset/`, with and without the concept
map ([eval/README.md](../eval/README.md)). Elasticsearch and Meilisearch in their best measured configurations, with
the same concept map but without vectors, passed 1,191 and 1,206 of the 1,887 queries; the reference implementation
of this design passed 1,325 (design-time reference run), and this code passes 1,323.

## 8. Operations

Image stages `deps`, `model`, `app`, `test`, `runtime`; the model is pinned by revision and sha256, and the build runs
`python -m app.embedding --selfcheck`. The schema is created in one transaction on an empty database; later starts
leave it alone. Pool timeouts: connect 3 s, statement 5 s; a 503 says unreachable, busy or timeout. One inference lock
per batch of at most four texts, separate lanes for documents and queries, an async `/health`. `app_meta` warns when
the model, the tokenizer settings or the concept map changed. Logs: one start-up line with the active modes, one
access line per request without the query string, never document text.

## 9. Considered and not built

- Dropping the weak guesses: section 5.
- A concept hit only inside one concept: about zero effect (design-time).
- Concept hits above scattered literal hits: letters that ask for a document carry the same tag.
- Client substrings only in e-mails: the test authors disagree on matches inside words.
- No client typo tier: strict pass −116 (design-time).
- No concept spell-check: `adress proof` would find nothing.
- 200 and `[]` for an empty `q`: the test authors disagree.
- Phrases from failed tests added to the map: fitting the test set.
- An LLM on every search: latency, and no search without it.
- RRF and cross-encoders: no measured gain, or seconds per query.

## 10. Growth path

- **Vectors.** Past about 10,000 fragments: an HNSW index for the top-k fragments of the semantic leg, plus the exact
  cosine for the documents the literal and typo legs return. The leg compares each document's best fragment with the
  global best, and an index returns only the top k, so the leg is rewritten, not just indexed.
- **Full text.** A GIN index on `fts_text` and `fts` once the literal leg stops being a fast scan.
- **Concept tags in a side table** (`document_concepts(document_id, concept)`) instead of the `tags_text` sentence,
  plus a re-tag command, so that a change of the map re-tags documents without rewriting them.
- **Clients.** Cap the candidates of very common substrings after about 10,000 clients (design-time: 22-123 ms
  instead of 0.35-1.9 s).
- **Quality.** Tags from an LLM at upload for phrasings the map lacks; thresholds re-tuned on real queries, with the
  test set split by whole suites.
- **Product.** Access control per adviser, removal of personal data before any LLM call, asynchronous ingest for large
  uploads.

## 11. Privacy and data flow

Ids are UUID v7: the first 48 bits are the creation time in milliseconds, so anyone who sees an id learns when the
record was created. Use random v4 ids, or opaque public ids, if that matters. The access log records the path without
the query string, so search terms are not logged, and document text is never logged. A document's own text decides
its tags: a document that says "utility bill" is tagged as proof of address, with or without an LLM.
