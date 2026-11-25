# Nevis Search API

A REST service that stores wealth-management clients and their documents and searches both through one endpoint.
FastAPI and PostgreSQL 18 (pgvector, pg_trgm, unaccent); a local embedding model is baked into the image, so after
the first build everything runs offline and without any API key. An optional Claude call at upload is described
under "How LLMs were used".

## Run it

You need Docker with Compose v2 (or Podman with a compose provider), bash, curl and python3.

```bash
docker compose up --build -d                              # build and start PostgreSQL and the API
scripts/demo.sh                                           # create John Doe and five documents, run both examples
docker compose --profile test run --rm --no-deps tests    # unit and integration tests, on the running database
```

- **First build.** Downloads: images from docker.io and ghcr.io, packages from PyPI, the embedding model (92 MB,
  pinned revision and sha256) from huggingface.co. Measured: 46 s on fresh GitHub Actions x86_64; later starts take
  seconds. For a model mirror: `docker compose build --build-arg HF_ENDPOINT=<mirror URL>`.
- **Port.** The API answers on http://127.0.0.1:8000 only. For another port:
  `docker compose down && API_PORT=8001 docker compose up -d` and `API_PORT=8001 scripts/demo.sh`, or set `API_PORT`
  in `.env` (see `.env.example`) and export it for the scripts. The database publishes no port.
- **API description.** http://127.0.0.1:8000/docs requires cdn.jsdelivr.net;
  [docs/openapi.json](docs/openapi.json) works offline.
- **Reset.** `docker compose down -v` stops everything and deletes the database volume. `scripts/demo.sh` creates
  nothing on a second run.
- **Tests.** Rebuild after code changes: `docker compose --profile test build`. Host unit tests:
  `uv sync && uv run pytest tests/unit` (Linux or Apple Silicon; no onnxruntime wheels for Intel macOS).
- **Evaluation.** `docker compose --profile test run --rm --no-deps tests python -m eval.run_testset` scores this
  code on the 1,887-query test set in under a minute and a half; see [eval/README.md](eval/README.md).

## The two examples from the assignment

Captured with `scripts/demo.sh` on an empty database (full output: [docs/demo-transcript.txt](docs/demo-transcript.txt));
ids and timestamps differ on every machine.

**`NevisWealth` → the client with the e-mail john.doe@neviswealth.com.** `exact`: every query word is part of the
client's name, e-mail or description.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=NevisWealth' | python3 -m json.tool --no-ensure-ascii
[
    {
        "type": "client",
        "score": 0.85,
        "match_type": "exact",
        "id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@neviswealth.com",
        "description": "Founder of a logistics company; prefers ESG funds.",
        "social_links": [
            "https://www.linkedin.com/in/johndoe"
        ]
    }
]
```
<!-- transcript:end -->

**`address proof` → the utility bills.** `concept`: the query's words are in the tags the documents got at upload
(`proof of address`), not in their text. "Scan 0042" mentions "utility bill" only once, inside a 123-word text.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=address%20proof' | python3 -m json.tool --no-ensure-ascii
[
    {
        "type": "document",
        "score": 0.7531,
        "match_type": "concept",
        "id": "01a20d78-a241-7823-9839-67457e69335f",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Electricity bill",
        "content": "Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10.",
        "created_at": "2026-11-24T12:12:19.393278Z",
        "tags": [
            "proof of address"
        ],
        "summary": {
            "text": "Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10.",
            "method": "extractive"
        }
    },
    {
        "type": "document",
        "score": 0.7396,
        "match_type": "concept",
        "id": "01a20d78-a17e-7410-82f7-0e000102bcc2",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Scan 0042",
        "content": "Scan: utility bill (electricity), 2 pages.\n\nNORTHMOOR ENERGY\nMr Tobias Hallworth\n14 Larkspur Close, Harrogate HG2 7QD\nCustomer number 8830 5512 07. Bill date 14 March 2025.\n\nYour electricity bill for 11 December 2024 to 10 March 2025 (90 days).\nMeter 21E4470913: previous reading 41,208, latest reading 42,371 (smart meter). Electricity used: 1,163 kWh.\nUnit charges 1,163 kWh at 24.86p: £289.12\nStanding charge 90 days at 60.97p: £54.87\nVAT at 5%: £17.20\nTotal charges this period: £361.19\nPayments received, thank you (3 direct debits of £95.47): £286.41\nBalance carried forward: £74.78 debit\n\nYour monthly direct debit stays at £95.47 and is collected on the 3rd of each month. Tariff: Fixed Saver 18, ends 30 September 2025. Estimated annual cost on this tariff: £1,210.",
        "created_at": "2026-11-24T12:12:19.198030Z",
        "tags": [
            "proof of address",
            "customer due diligence"
        ],
        "summary": {
            "text": "Scan: utility bill (electricity), 2 pages. NORTHMOOR ENERGY Mr Tobias Hallworth 14 Larkspur Close, Harrogate HG2 7QD Customer number 8830 5512 07. Bill date 14 March 2025. Your electricity bill for 11 December 2024 to 10 March 2025 (90 days).",
            "method": "extractive"
        }
    },
    {
        "type": "document",
        "score": 0.7382,
        "match_type": "concept",
        "id": "01a20d78-9ec5-7c74-acdd-4ab3baa2a17e",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Utility bill",
        "content": "British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.",
        "created_at": "2026-11-24T12:12:18.501407Z",
        "tags": [
            "proof of address",
            "customer due diligence"
        ],
        "summary": {
            "text": "British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.",
            "method": "extractive"
        }
    }
]
```
<!-- transcript:end -->

**A query with no answer gets an empty list.**

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=chocolate%20cake%20recipe' | python3 -m json.tool --no-ensure-ascii
[]
```
<!-- transcript:end -->

## Optional: Claude enrichment at upload

Off by default. Set `NEVIS_LLM_ENABLED=true` and `ANTHROPIC_API_KEY` in `.env`, then recreate the API container.
With the concept map enabled, Claude (`claude-haiku-5-5`) returns a summary (up to 600 characters), up to five
concepts, a document type and up to ten search phrases. Searches never call Claude. A timeout (10 s), API error,
refusal, invalid answer or third concurrent call falls back to extractive summarisation and the concept map.

Measured 2026-11-24: 86 sequential uploads using `eval/post_latency.py`, API on an Apple M3 Pro:

| Option | POST p50 | p95 | max | Summaries |
|---|---|---|---|---|
| off | 32 ms | 153 ms | 171 ms | extractive 86 |
| on | 2109 ms | 3645 ms | 3968 ms | llm 86, no fallback |

87 calls including warm-up used 148,635 input and 24,604 output tokens: about $0.027 total, about $0.0003 per
document at $0.10 / $0.50 per million tokens. Enabled measurements ran on the host: this corporate network resolves
Anthropic to IPv6 only, but its podman containers have IPv4 only and fall back with `connection_error`.
On a normal network the containers reach the API. [Evaluation details](eval/README.md#claude-at-upload) include
the 4 passing live tests and the earlier injection failures.

**Data flow.** Opt-in: each uploaded title and content (up to 50,000 characters) go to Anthropic.
PostgreSQL stores the document, summary, tags, search phrases and vectors. Logs contain outcome, model, token counts,
timing and request ID, never document text or Claude's answer. Set `NEVIS_LLM_ENABLED=false` and recreate the API
to stop calls; stored enrichment remains. Any deployed copy should hold synthetic data only; hosting request logs
may record search terms. [Data-flow details](docs/DESIGN.md#11-privacy-and-data-flow).

## How search decides

**Clients.** Query and record use Unicode NFKC, accent removal and case folding. `exact` requires every query word
in name, e-mail or description: `neviswealth`, `wealth`, `john.doe`, `Doe John` find John Doe. With no matches and
at least 5 letters/digits, trigrams handle typos (`NevisWelth`, `Jon Doe` → `fuzzy`).

**Documents.** Documents are cut into fragments of up to 200 words, each with a vector; a document's cosine is its
best fragment's. One SQL statement, four ways in:
1. *literal*: every query word (English stemming) is in the title, the text or the tags → `lexical`, or `concept`
   when the tags were needed;
2. *typo*, only if the literal way found nothing: the title resembles the query, or the query is a misspelt concept
   phrase (`adress proof`) → `fuzzy`;
3. *meaning*: the document's cosine is at least 0.40 and within 0.08 of the best document's → `semantic`;
4. *weak guess*, only if nothing above matched: up to three nearest documents with a cosine of at least 0.32 →
   `semantic`.

Both kinds are fetched with `limit` each, merged, sorted by score, type and id, and cut to `limit` (1-50, default 10).

| Score | Meaning | `match_type` |
|---|---|---|
| 0.5 and above | the query's words are in the record, or in the document's tags | `exact`, `lexical`, `concept` |
| 0.2 to 0.5 | a strong semantic match, or a typo | `semantic`, `fuzzy` |
| below 0.2 | a weak semantic guess, or a client typo found only in the description (at most 0.245) | `semantic`, `fuzzy` |

For confident results, drop `semantic` items below 0.2.

## Why there is a concept map

Embeddings alone do not know that a utility bill is accepted as proof of address. With the shipped model, three
short documents and no concept map, `address proof` ranks the bill last
(`docker compose --profile test run --rm --no-deps tests python -m eval.cosine_table`; each document is embedded as
title and text):

<!-- cosines:start -->
| Query | 1st | 2nd | 3rd |
|---|---|---|---|
| `address proof` | Passport 0.25 | Tax return 0.19 | Utility bill 0.14 |
| `proof of address` | Passport 0.29 | Tax return 0.22 | Utility bill 0.17 |
| `utility bill` | Utility bill 0.52 | Tax return 0.21 | Passport 0.15 |
<!-- cosines:end -->

`app/data/concepts.yaml` lists 30 concepts, query phrasings (`triggers`) and accepted documents (`expands_to`).
Concept names and `expands_to` phrases matched at upload become tags. Tags/triggers enter literal matching and,
for title matches or documents up to 200 words, an embedded fragment. Bills thus return as `concept` with
`proof of address` tags. Claude can add concepts and phrases when enabled.

An LLM drafted 120 entries from UK wealth-management knowledge, cut to 30 relations by dropping single documents,
topics and identifiers. Four cite official lists (GOV.UK, Bona Vacantia, DBS, JMLSG). Other relations include
`proof of income` → payslip and `photo ID` → passport.

## Measured quality

`eval/run_testset.py` runs the 1,887 queries of `testset/` (18 suites) against this code, once with the concept map
and once without, with Claude off. Both columns come from `eval/results/`.
Claude raises first-10 recall (0.74→0.79), barely changes strict pass (1,323→1,324), and loses four required queries
(544→540); see [evaluation results](eval/README.md#claude-at-upload).

<!-- quality:start -->
| | With the concept map (shipped) | Without the concept map |
|---|---|---|
| Strict pass, all 1,887 queries | 1323/1887 (70 %) | 1328/1887 (70 %) |
| … written by Codex and Claude without seeing the design (400) | 255/400 (64 %) | 259/400 (65 %) |
| … built from open datasets (951) | 640/951 (67 %) | 642/951 (68 %) |
| … required by the assignment's text (621) | 544/621 (88 %) | 547/621 (88 %) |
| First 10: precision | 0.80 | 0.82 |
| First 10: recall | 0.74 | 0.69 |
| First 10: F1 | 0.766 | 0.747 |
| Answerable queries with a relevant result in the first 10 | 0.86 | 0.84 |
| Queries without an answer that return nothing (230) | 0.67 (154/230) | 0.68 (156/230) |
| `NevisWealth`, strict, all its queries in the test set | 16/16 | 16/16 |
| `address proof`, strict, all its queries in the test set | 0/10 | 0/10 |
<!-- quality:end -->

Strict pass requires every expected result, no wrong results and correct ordering ([eval/README.md](eval/README.md)).
Thresholds were tuned on one suite's dev half; the design's authors wrote two suites. The map trades precision and
strict passes for recall, making `address proof` find bills. That query never passes strictly: bills are missed and
documents merely mentioning proof or address also return (see Limits).
[docs/DESIGN.md](docs/DESIGN.md) compares the strict pass with Elasticsearch and Meilisearch.

Under load: `/search` p95 21 ms and `/health` p95 5 ms while 16 parallel uploads send the 86 documents of the `existing-documents-86` suite (6 CPUs, `NEVIS_EMBED_THREADS=4`, podman on an Apple M3 Pro); idle `/search` p95 9 ms.

## API

| Operation | Success | Errors |
|---|---|---|
| `POST /clients` | 201, `Location`, the client | 400, 413, 415, 422 |
| `GET /clients/{id}` | 200, the client | 404 |
| `POST /clients/{id}/documents` | 201, `Location`, the document with `tags` and `summary` | 400, 404, 413, 415, 422 |
| `GET /clients/{id}/documents/{document_id}` | 200, the document | 404, also for another client's document |
| `GET /search?q=&type=&limit=` | 200, a list; `[]` when nothing matches | 400 (query string not UTF-8), 422 |
| `GET /health` | 200 `{"status": "ok"}`, without touching the database | none |

- Errors are `application/problem+json` (RFC 9457); a 422 adds `errors` (`loc`, `msg`, `type`) and never repeats the
  submitted value. Any call that uses the database may answer 500 without details, or 503 with `Retry-After: 5`
  (database unreachable, busy, or a query over 5 s). A body over 2 MiB gets 413, possibly as plain text.
- A search item is the client or document itself plus `type`, `score` and `match_type`, so `item["email"]` works.
  Documents carry `tags` (matched or Claude-added concepts) and `summary` (first sentences, up to
  300 characters, plus '…' when cut, `"method": "extractive"`; with Claude enabled, up to
  600 characters, `"method": "llm"`).
- Validation: names up to 100 characters, description 2,000, 20 social links, title 300, text 50,000, `q` 1-200 after
  collapsing whitespace. Control characters are rejected, except tab and newline in a description or a document's
  text (and carriage return in the text). Non-UUID path ids get 404. E-mails may repeat (spouses share
  addresses), so no 409.
- The 200-character cap on `q` bounds the substring patterns and the client typo tier; longer queries were not
  measured.
- Results carry whole documents, like the assignment's Document model: at most 50 documents of 50,000 characters,
  about 2.5 MB of Latin text and up to about 7.5 MB in other scripts; a few kilobytes on the demo data.
- Swagger UI offers both assignment queries as examples; `scripts/demo.sh` shows the create calls with curl.

## Limits

- **What a document is for** (`proof of income`, `photo ID`) is the weakest kind of query: the map is a closed list,
  so phrasings it lacks ("Council Tax demand notice") get no tag, and documents that merely mention the words, or carry
  a neighbouring tag, come back too.
- **`address proof`** with Claude off also returns "Proof of delivery … home address" and letters asking for proof
  of address. With Claude, still 0/10.
- **Client substrings inside words:** `Chester` finds Manchester, `Ng` finds England. Test authors disagree;
  whole-word matching for up to three letters is the first alternative to measure.
- **Similar names:** `Sergey Menshikov` finds Sergey Melikov; removing typo matching loses more typos and nicknames.
- **Typos inside a document's text** are not corrected, only in titles and concept phrases; swapped letters in a short
  name (`Jhon`) defeat trigrams.
- **Names in another script:** Cyrillic or Arabic spellings of Latin names are not found.
- **Queries without answers:** up to three weak guesses below 0.2 (`marriage certificate`); wrong semantic matches
  above 0.2 (`tenancy agreement`). Relative semantic cutoff can omit "Electricity bill" for `utility bill`.
- **Long and empty queries** get 422 (over 200 characters, or only spaces); one test suite expects 200 and `[]` for
  the empty one.

## What is not verified

- **Real data.** All corpora are synthetic or public; the thresholds were chosen on synthetic documents and should be
  re-tuned on real ones ([eval/README.md](eval/README.md)).
- **Scale.** There is no vector index and no candidate cap. Design-time measurements put document search above 0.1 s
  at about 10,000 fragments, and very common client substrings (`gmail`, `com`) at 0.35-1.9 s per query with 100,000
  clients.
- **Whole API process memory.** Unmeasured; the model alone took about 180 MB, peaking at 415 MB
  while loading (design-time).
- **Platforms.** Built and tested with podman on Apple Silicon (arm64) and with Docker on x86_64 in
  [GitHub Actions](https://github.com/timur-nagimov/nevis-hometask/actions/workflows/ci.yml); Docker Desktop on
  Windows was not tried.
- **No deployed instance.**

## How LLMs were used

**At run time**, without `NEVIS_LLM_ENABLED=true`, no LLM is called: vectors come from the local
`mdbr-leaf-ir` model (Apache-2.0) inside the image; nothing leaves the machine.
With `NEVIS_LLM_ENABLED=true` and an Anthropic key, Claude Haiku writes the summary and adds tags at upload; on 86
documents it took p50 2.1 s and p95 3.6 s, about $0.0003 per document. Document titles and text go to Anthropic.

**During development** I used AI agents throughout. Claude Code researched, designed and wrote most of the code
test-first; Codex wrote part of the Claude enrichment and the final review fixes (12 commits) and reviewed the code;
separate agents reviewed the design. Agents wrote 10 suites (Codex and Claude wrote 6 blind), built 8 from open
datasets and drafted the concept map. **Checked, not trusted:** scripts reproduce quality/cosine tables, enforced by
`tests/unit/test_docs.py`; "design-time" numbers predate the code. Transcripts are captured; image builds require a
model self-check. Implementation took about 39 hours of wall time (agents also worked overnight), after the initial
research and test set.

## Repository map

```
app/                     the service: main.py (routes, errors), search.py, ingest.py, embedding.py, db.py, config.py, schemas.py
app/db.py                the tables as SQLAlchemy models and every query in SQLAlchemy Core: client search, document search, concept matching
app/data/concepts.yaml   the concept map (30 entries)
scripts/                 demo.sh, check_demo.py, export_openapi.py, fetch_model.py (model download at build time)
eval/                    evaluation runner and metrics, committed results, cosine table
testset/                 18 test suites with recorded answers (summary in eval/README.md)
tests/                   unit tests (host) and integration tests (compose)
docs/                    DESIGN.md, openapi.json, demo-transcript.txt
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
```

Design decisions and reasons: [docs/DESIGN.md](docs/DESIGN.md). Licences of the parts: the embedding model
`MongoDB/mdbr-leaf-ir` is Apache-2.0; psycopg is LGPL-3.0 and used unmodified as a library; each suite built from an
open dataset (`ds-*`) names its source and licence in its `about` and `source` fields.
