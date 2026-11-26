# Optional: Claude enrichment at upload

Off by default. Set `NEVIS_LLM_ENABLED=true` and `ANTHROPIC_API_KEY` in `.env`, then recreate the API container.
With the concept map enabled, Claude (`claude-haiku-5-5`) returns a summary (up to 600 characters), up to five
concepts, a document type and up to ten search phrases. Searches never call Claude. A timeout (10 s), API error,
refusal, invalid answer or third concurrent call falls back to extractive summarisation and the concept map.

Measured 2026-11-24: 86 sequential uploads of `testset/suites/existing-documents-86.json`
using `eval/post_latency.py`, API on an Apple M3 Pro:

| Option | POST p50 | p95 | max | Summaries |
|---|---|---|---|---|
| off | 32 ms | 153 ms | 171 ms | extractive 86 |
| on | 2109 ms | 3645 ms | 3968 ms | llm 86, no fallback |

87 calls (86 uploads plus the start-up warm-up) used 148,635 input and 24,604 output tokens: about $0.027 total,
about $0.0003 per document at $0.10 / $0.50 per million tokens. Enabled measurements ran the same code on the host
(uv run) against the project database: on this corporate network Anthropic resolves to IPv6 addresses only,
while podman containers have IPv4 only and every call falls back with `connection_error`.
On a normal network the containers reach the API.
[Evaluation details](../eval/README.md#claude-at-upload) include the 4 passing live tests and the earlier injection
failures.

**Data flow.** Opt-in: each uploaded title and content (up to 50,000 characters) go to Anthropic.
PostgreSQL stores the document, summary, tags, search phrases and vectors. Logs contain outcome, model, token counts,
timing and request ID, never document text or Claude's answer. Set `NEVIS_LLM_ENABLED=false` and recreate the API
to stop calls; stored enrichment remains. Any deployed copy should hold synthetic data only; hosting request logs
may record search terms. [Data-flow details](DESIGN.md#11-privacy-and-data-flow).
