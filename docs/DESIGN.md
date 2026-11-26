# Design

## 1. Constraints I set

Both examples work right after `docker compose up`, offline, with no key. One process, one database. Code readable in
half an hour. Nothing enters the search unless it was measured first.

## 2. Decisions

| Area | Chosen | Instead | Why |
|---|---|---|---|
| Storage | PostgreSQL 18, pgvector, pg_trgm, unaccent | Elasticsearch, Meilisearch, vector databases | atomic document/vector writes; immediate search; Elasticsearch needs another service, refreshes and 0.9-1.5 GB (design-time) |
| Client search | normalised substrings, then trigrams | full-text search; embeddings | full-text e-mail tokens miss `neviswealth`; 131/134 required queries (design-time) |
| Document search | one SQL statement: literal, typo and semantic legs, two-stage result rule | rank fusion (RRF), cross-encoders, LLM re-ranking | no measured gain, or seconds per query (design-time) |
| Domain knowledge | 30-entry map; optional Claude enrichment at upload | query-time synonyms or LLM | query-time map F1 0.628 / 0.525 against 0.646 / 0.595, dev / test (design-time); searches remain local |
| Embeddings | `MongoDB/mdbr-leaf-ir` (Apache-2.0, 768 dimensions, 92 MB) through onnxruntime, in the image | `bge-small`; cloud embeddings | nDCG@10 0.606 against 0.473 for `bge-small` (design-time); works offline |
| Summary | `extractive`, up to 300 characters, plus '…' when cut; opt-in Claude `llm`, up to 600 | LexRank; local LLMs | offline fallback; LexRank was not significantly better; Claude measured in [evaluation](../eval/README.md#claude-at-upload) |
| HTTP | FastAPI, synchronous handlers, one worker | Litestar; async handlers | correct mixed-result OpenAPI discriminator; onnxruntime and psycopg release the GIL |
| SQL access | SQLAlchemy 2.1 Core, psycopg 3, `app/db.py` | SQL files | tables and queries together; translated queries return identical test-set rows |
| Schema | models create an empty database | numbered migrations | one version; schema changes require an empty database |
| Vector index | none: every search scans all fragments | HNSW | milliseconds at this scale; needed after about 10,000 fragments (design-time) |

Numbers marked design-time were measured while designing; they are not reproducible from this repository.

## 3. Client search

`search_clients` in `app/db.py` normalises query and record (NFKC, no accents, case folded): `exact` means every
query word is a substring across name, e-mail and description. With no `exact` and at least 5 query letters/digits,
`fuzzy` uses trigram word similarity from 0.6. Score: `0.5 + 0.5 × similarity` with the fields weighted
(name 1, e-mail 0.7, description 0.5);
`fuzzy` gets `0.49 × similarity`. Known errors: matches inside words (`Chester` finds Manchester), similar names,
swapped letters (`Jhon`).

## 4. Document ingest

An upload (the route in `app/main.py`, then `create_document` in `app/ingest.py`):

1. checks the fields (404 for an unknown client);
2. optionally calls Claude, merging its concepts with phrase-matched tags and adding its document type and phrases;
3. uses Claude's summary (up to 600 characters), or the first sentences (up to 300, plus '…' when cut)
   when disabled or unsuccessful;
4. cuts the text into fragments of up to 200 words with the title in front;
5. embeds tags matched in the title or documents up to 200 words, plus Claude concepts/phrases;
6. embeds in batches of four and stores it all in one transaction before the 201.

Synchronous: searchable at 201. Without Claude, about 2 s for 50,000 characters
(design-time: about 40 ms per 200-word fragment on 2 CPUs); at most four uploads run at once, the others wait without
holding a thread.

## 5. Document search

`_search_documents_statement` in `app/db.py` builds one statement: literal (every query word in title, text or tags),
typo (only without literal hits) and semantic. Two stages: literal/typo hits or cosine ≥0.40 within 0.08 of the best
are strong; without strong hits, return the three nearest documents from 0.32, scored below 0.2.
Scores: literal `0.5 + 0.5 × cosine`, typo `0.49 × similarity`,
semantic `0.5 × cosine`. On the 1,887 test queries, dropping the weak guesses would add 11 strict passes, but 29
answerable queries would lose every relevant result (design-time reference run).

Result rules compared (design-time, 86 documents, a 38-entry draft of the map):

| Result rule | P / R / F1 | Answered | Junk left empty |
|---|---|---|---|
| one threshold 0.40 / 0.08 | 0.70 / 0.58 / 0.636 | 0.74 | 0.88 |
| one threshold 0.32 / 0.08 | 0.54 / 0.69 / 0.606 | 0.88 | 0.75 |
| one threshold 0.32 / 0.06 | 0.58 / 0.68 / 0.623 | 0.87 | 0.75 |
| two-stage (shipped) | 0.65 / 0.65 / 0.651 | 0.85 | 0.75 |

## 6. The concept map

`app/data/concepts.yaml` models documents accepted as evidence (utility bill → proof of address), unknown to
embeddings ([cosine table](SEARCH.md#why-there-is-a-concept-map)). Entries have `concept` (tag),
`triggers` (query phrasings, searched with tags), `expands_to` (accepted documents) and optional `sources`.
Concepts and `expands_to` match stemmed phrases, skipping
those starting or ending with stop words. Only matches in titles or documents up to 200 words enter the embedded tags
fragment; long letters mentioning a bill once get tagged but rank below bills for `address proof`.
An LLM drafted 120 entries from general UK wealth-management knowledge, cut to 30 by keeping these relations and
dropping single documents, topics and identifiers. Four entries name official lists:

- proof of address: [GOV.UK JSA interview](https://www.gov.uk/jobseekers-allowance/your-jsa-interview);
  [Bona Vacantia checklist](https://www.gov.uk/government/publications/proof-of-identity-checklist/proof-of-identity-checklist)
- proof of identity: [Bona Vacantia checklist](https://www.gov.uk/government/publications/proof-of-identity-checklist/proof-of-identity-checklist);
  [DBS ID checking guidelines](https://www.gov.uk/government/publications/dbs-identity-checking-guidelines/id-checking-guidelines-for-standardenhanced-dbs-check-applications-from-22-april-2025)
- customer due diligence: [JMLSG Guidance Part I, 5.3.75-5.3.76](https://www.jmlsg.org.uk/wp-content/uploads/2026/10/JMLSG-Guidance-Part-I_Oct-2026.pdf)
- proof of income: [GOV.UK family visas, proof of finances](https://www.gov.uk/uk-family-visa/provide-information)

The other 26 entries are curated; no official lists were found.

A closed list misses phrasings ("Council Tax demand notice") and tags letters asking for evidence as evidence.
Optional Claude enrichment adds phrases and document-type labels; matched tags remain, so false positives can persist.

## 7. Evaluation

`eval/run_testset.py` scores the service's own code on the 1,887 queries of `testset/`, with and without the concept
map ([eval/README.md](../eval/README.md)). Elasticsearch and Meilisearch in their best measured configurations, with
the same concept map but without vectors, passed 1,191 and 1,206 of the 1,887 queries; the reference implementation
of this design passed 1,325 (design-time), and this code passes 1,323 with Claude off.
Claude raises first-10 recall (0.74→0.79), barely changes strict pass (1,324), and loses four required queries
(544→540); see [evaluation results](../eval/README.md#claude-at-upload).

## 8. Operations

Image stages `deps`, `model`, `app`, `test`, `runtime`; the model is pinned by revision and sha256, and the build runs
`python -m app.embedding --selfcheck`. The schema is created in one transaction on an empty database; later starts
leave it alone. Pool timeouts: connect 3 s, statement 5 s; a 503 says unreachable, busy or timeout. One inference lock
per batch of at most four texts, separate lanes for documents and queries, an async `/health`. `app_meta` warns when
the model, the tokenizer settings or the concept map changed. Logs: one start-up line with the active modes, one
access line per request without the query string, never document text.

## 9. Considered and not built

- Dropping the weak guesses: section 5.
- A concept hit only when every query word comes from one concept: about zero effect (design-time).
- Concept hits above scattered literal hits: letters that ask for a document carry the same tag.
- Client substrings only in e-mails: the test authors disagree on matches inside words.
- No client typo tier: strict pass −116 (design-time).
- No concept spell-check: `adress proof` would find nothing.
- 200 and `[]` for an empty `q`: the test authors disagree.
- Phrases from failed tests added to the map: fitting the test set.
- An LLM on every search: latency, and no search without it.
- Typo matches next to exact client matches: all-query strict pass 1,323 → 1,221.
- Removing the semantic cutoff, comparing semantic-only candidates, or bypassing it for title overlap: best all-query
  strict pass 1,323 → 1,326 (removal), but required pass 544 → 538.
- Title-only concept tags: first-10 F1 0.766 → 0.757.
- Title-only tags plus body-only lexical demotion: first-10 F1 0.766 → 0.756.

## 10. Growth path

- **Vectors.** Past about 10,000 fragments: HNSW top-k for semantics, exact cosine for literal/typo candidates.
  Comparing each document's best fragment with the global best requires rewriting the semantic leg.
- **Full text.** A GIN index on `fts_text` and `fts` once the literal leg stops being a fast scan.
- **Concept tags in a side table** (`document_concepts(document_id, concept)`) and a re-tag command, avoiding
  document rewrites when the map changes.
- **Clients.** Cap the candidates of very common substrings after about 10,000 clients (design-time: 22-123 ms
  instead of 0.35-1.9 s).
- **Quality.** Re-tune thresholds on real queries, splitting by whole suites.
- **Product.** Access control per adviser, removal of personal data before any LLM call, asynchronous ingest for large
  uploads.

## 11. Privacy and data flow

Ids are UUID v7: the first 48 bits reveal creation time in milliseconds to anyone seeing the id. Use random v4 ids,
or opaque public ids, if that matters. Access logs contain paths without query strings; neither search terms nor
document text is logged. A document's own text decides its tags: a document that says "utility bill" is tagged as
proof of address, with or without an LLM.

**Claude at upload.** Opt-in, off by default: with `NEVIS_LLM_ENABLED=true`, `ANTHROPIC_API_KEY` and the concept
map enabled, validated uploads' titles and content (up to 50,000 characters) go to Anthropic.
One call per upload, no retries, at most two concurrent calls; start-up also sends a synthetic warm-up document.
Searches never call Claude. Delimited document text is untrusted; the prompt excludes embedded instructions from
every output field. Claude sees no other documents or client records; the key authenticates the request, never
enters the prompt. Answers allow five of 30 concepts, a 600-character summary, a document type and ten 60-character
phrases. PostgreSQL stores original text, summary/method, merged tags, type/phrases in `tags_text`, and vectors.
Logs record outcome/fallback reason, model, token counts, timing and request ID, never document text, titles,
names, e-mails, query values or Claude's answers. Set `NEVIS_LLM_ENABLED=false` and restart/recreate the API to stop
calls; stored enrichment remains. Any deployed copy should contain synthetic data only; hosting request logs may
capture search terms. Four live tests passed after hardening; this is not a general injection-resistance guarantee.
