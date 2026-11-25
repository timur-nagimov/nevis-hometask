# Evaluation

`eval/run_testset.py` measures the shipped search code on 18 test suites: 1,887 queries whose correct answers were
written down before the code existed. It loads each suite and runs its queries through the service's own functions
(`app.db.insert_client`, `app.ingest.create_document`, `app.search.search` with the queries of `app/db.py`), so it
measures exactly what the API does, without the HTTP layer.

## Run it

Start the stack first (`docker compose up --build -d`, as in the [main README](../README.md)): the runner needs its
database, and `--no-deps` leaves the running containers alone.

```bash
docker compose --profile test run --rm --no-deps tests python -m eval.run_testset                 # shipped configuration
docker compose --profile test run --rm --no-deps tests python -m eval.run_testset --no-concepts   # without the concept map
```

One configuration takes about a minute to a minute and a half on an Apple M3 Pro (podman VM with 6 CPUs); the last
line of the output gives the run time. Every suite gets its own database (`nevis_ts_<suite>`), created, given the
schema with `app.db.create_schema` and dropped afterwards; the demo data is not touched. Records the API would
reject are skipped and logged, and a query the API would reject counts as an empty answer. Queries run with
`limit=50`; `type` is the query's `scope` (`clients` → `client`, `documents` → `document`, `all` → no type). Add
`--failures` to list every failing query with the reason, and suite names (`tools-mini-6`) to run only those
suites.

`--llm` enables the shipped Claude call at upload (needs `ANTHROPIC_API_KEY`; sends document titles and content to
Anthropic). It cannot be combined with `--no-concepts`. With Docker Compose, pass the key by variable name:

```bash
(set -a; . ./.env; set +a; docker compose --profile test run --rm --no-deps -e ANTHROPIC_API_KEY tests python -m eval.run_testset --llm)
```

podman-compose 1.4 cannot pass a variable by name, so run on the host with
`uv run --env-file .env python -m eval.run_testset --llm` and `NEVIS_DATABASE_URL` pointing at a database the host can reach.

The timing above and both committed result files are for Claude off.

The outputs on the shipped code are committed: [results/with-concepts.txt](results/with-concepts.txt) and
[results/no-concepts.txt](results/no-concepts.txt). The README's quality table quotes only these files. This prints
nothing when a new run gives the same numbers:

```bash
diff <(grep '^|' eval/results/with-concepts.txt) \
     <(docker compose --profile test run --rm --no-deps -T tests python -m eval.run_testset | grep '^|')
```

`docker compose --profile test run --rm --no-deps tests python -m eval.cosine_table` prints the README's
three-document cosine table ([results/cosines.md](results/cosines.md)).

## Rejected search variants

Six variants were measured independently on all 1,887 queries with the concept map enabled and Claude off.
Acceptance required strict pass counts over all queries and over the 621 required by the assignment to stay at
least at baseline; first-10 F1 could fall by at most 0.005. All six were rejected. Their patches are not part of
the repository.

| Variant | Strict pass, all | Strict pass, required | Precision@10 | Recall@10 | F1@10 | Relevant hit@10 | No-answer empty |
|---|---|---|---|---|---|---|---|
| Baseline | 1323/1887 (70 %) | 544/621 (88 %) | 0.80 | 0.74 | 0.766 | 0.86 | 0.67 (154/230) |
| Typo matches next to exact client matches | 1221/1887 (65 %) | 482/621 (78 %) | 0.75 | 0.74 | 0.744 | 0.86 | 0.67 (154/230) |
| Remove relative semantic cutoff | 1326/1887 (70 %) | 538/621 (87 %) | 0.78 | 0.75 | 0.763 | 0.87 | 0.67 (154/230) |
| Compare semantic-only candidates for the cutoff | 1308/1887 (69 %) | 538/621 (87 %) | 0.78 | 0.74 | 0.760 | 0.86 | 0.67 (154/230) |
| Title overlap and cosine ≥0.40 bypass the cutoff | 1319/1887 (70 %) | 541/621 (87 %) | 0.79 | 0.74 | 0.767 | 0.86 | 0.67 (154/230) |
| Title-only concept tags | 1326/1887 (70 %) | 545/621 (88 %) | 0.81 | 0.71 | 0.757 | 0.85 | 0.67 (155/230) |
| Title-only tags plus body-only lexical demotion | 1320/1887 (70 %) | 544/621 (88 %) | 0.82 | 0.70 | 0.756 | 0.85 | 0.67 (155/230) |

## Claude at upload

Measured on 2026-11-24 with `claude-haiku-5-5`:

- Live test against the real API (tests/live): 4 passed after the prompt was hardened; before that, 2 of the 3 prompt-injection cases failed (one summary quoted an embedded instruction, one followed a fake System line), and the prompt now tells the model to leave such text out of every field.
- Upload latency, 86 documents of testset/suites/existing-documents-86.json posted one after another (eval/post_latency.py), API process on an Apple M3 Pro: option off p50 32 ms, p95 153 ms, max 171 ms, summaries extractive 86; option on p50 2109 ms, p95 3645 ms, max 3968 ms, summaries llm 86, no fallback.
- Cost: 87 calls (86 uploads plus the start-up warm-up) used 148,635 input and 24,604 output tokens, about $0.027 in all, about $0.0003 per document at $0.10 / $0.50 per million tokens.
- Where it was measured: on this corporate network the Anthropic API resolves to IPv6 addresses only and the podman containers have IPv4 only, so the measurements with the option on ran the same code on the host (uv run) against the project database; in containers here every call falls back with connection_error. On a normal network the containers reach the API.

**Claude-on quality:** Claude raises recall in the first 10 and barely moves strict pass, while losing four
`required` queries. Both runs used the same runner and host, with the concept map on:

| Metric | Claude on | Claude off |
|---|---|---|
| Strict pass | 1,324/1,887 | 1,323/1,887 |
| First 10, all suites: precision / recall / F1 | 0.80 / 0.79 / 0.794 | 0.80 / 0.74 / 0.766 |
| hit@10 | 0.87 | 0.86 |
| No-answer clean | 154/230 | 154/230 |
| `required` pass | 540/621 | 544/621 |
| `existing-documents-86` F1, dev / test | 0.683 / 0.600 | 0.646 / 0.595 |

Enrichment succeeded for 1,780 of 1,781 documents, with one timeout fallback. The run took 69 minutes and used
3,171,885 input and 490,868 output tokens: about $0.56 total, $0.00032 per document, excluding warm-up.

These four passing live tests do not establish general resistance to prompt injection. The upload measurements
establish latency, cost and coverage for those 86 documents; they do not establish improved search quality.

## The test set

[testset/](../testset/) holds the suites (`testset/suites/*.json`). Its [README](../testset/README.md) is in Russian;
this section summarises it.

- **Written blind** (6 suites, `codex-*` and `claude-*`): Codex (GPT-6) and Claude Opus 5.5 got the same brief, and
  each wrote a corpus, queries and answers without seeing the design or each other's work.
- **Open datasets** (8 suites, `ds-*`): Enron e-mails, FiQA, synthetic finance documents, the UK sanctions list,
  RVL-CDIP scans and name-matching sets. The answers come mechanically from the datasets' labels and, for questions
  about a document's purpose, from official UK lists (GOV.UK), with a quote.
- **Research** (4 suites, `existing-*` and `tools-mini-6`): the sets the design was measured on.
  `existing-documents-86` has a `dev` half (used to choose the thresholds) and a `test` half;
  `existing-clients-fixture-42` and `tools-mini-6` were written by the design's authors, so they are not independent.

Every query has a level: `required` (follows from the assignment's text), `expected` (a reasonable reviewer would
expect it) or `nice` (desirable; a miss is not a defect).

## What the tables mean

**Strict pass.** Results outside the query's scope are dropped first. A query passes only if every condition that
applies holds:

1. `empty`: the list is empty;
2. `relevant`: all listed results are present (with `within_top`, for typos and questions, at least one of them in the
   first k; when there are more than 50 relevant results, 50 suffice);
3. `others: wrong`, the default: nothing besides `relevant` and `acceptable`;
4. `must_not`: none of these;
5. `first`: the first result is one of these;
6. `top_set`: the first places hold exactly these;
7. `before`: for each pair both are present and the first ranks higher;
8. `min_results`: at least this many results.

One wrong result, even in last place, fails the query. In 532 queries of eight suites (`others: ignore`, for example
FiQA and Enron) extra results are not penalised.

**First 10.** Micro-averaged over (query, result) pairs in the first 10 results: a relevant result is a true
positive; an `acceptable` one is ignored; any other result is a false positive (for queries with `others: wrong`, and
every result of a query without an answer); a missed relevant result is a false negative (at most 10 per query).
`hit@10` is the share of answerable queries with a relevant result in the first 10; "no-answer clean" is the share of
the 230 queries without an answer that return nothing.

## Expected numbers

The reference implementation of the design (the same SQL, model and rules, without HTTP) scored this during design:

| | With the concept map | Without |
|---|---|---|
| Strict pass, all 1,887 | 1,325 (70 %) | 1,330 (70 %) |
| written blind, 400 | 255 | 259 |
| open datasets, 951 | 640 | 642 |
| research, independent, 391 | 298 | 298 |
| research, by the design's authors, 145 | 132 | 131 |
| required, 621 | 546 | 549 |
| First 10: precision / recall / F1 | 0.80 / 0.74 / 0.766 | 0.82 / 0.69 / 0.747 |
| hit@10 | 0.86 | 0.84 |
| no-answer clean (230) | 0.67 | 0.68 |

With Claude off, the shipped code scores 2 fewer strict passes in each configuration (1,323 and 1,328), and 2 fewer
in the rows "research, independent" and "required". The reference run loaded one client whose description exceeds the API's
2,000-character limit; without that client, queries B01 and B02 of `existing-clients-skeptic-44` (required,
research) always fail. Every other number above is the same in `results/`.

## Caveats

- The corpora are synthetic, except Enron, FiQA (forum posts), the sanctions list and RVL-CDIP; real documents need
  new thresholds.
- Two suites were written by the design's authors, and the thresholds were chosen on the `dev` half of a third suite;
  "written blind" and "open datasets" are the rows from outside the research.
- `codex-mixed` expects 200 and `[]` for an empty `q`, while the API answers 422: h23 and h24 of
  `tests/integration/test_http_cases.py` are expected failures (55 of the 57 HTTP checks pass).
- For future tuning, split the set by whole suites, not by query: otherwise spellings of one query land in both
  halves.
- Adding phrases from failed queries to the concept map would fit the map to this test set; new phrases come from
  official lists only.
