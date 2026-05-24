# Job-posting analysis pipeline

Programmatic capture pipeline for the quarterly job-posting analysis. Specification lives at [`../methodology.md`](../methodology.md) v0.1.3; this directory is the implementation.

## What this pipeline does

For each quarterly run:

1. **Fetch** raw postings from the active sources (HN "Who is hiring" and BuiltIn at v0.1.3; Wellfound deferred — see methodology v0.1.3 for the rationale) into JSONL files under `../captures/YYYY-qN/raw/`.
2. **Filter** postings against the methodology's inclusion criteria (company stage/size, role, seniority, geography, industry, freshness). Excluded postings are kept on disk with `included: false` and an `exclude_reason` — auditability requires not deleting them.
3. **Extract** normalized fields from each included posting via an LLM. Verbatim source paragraphs are preserved in `stack_mentions_raw`; the pipeline is forbidden from being lossy on the source text.
4. **Load** rows into `../captures/YYYY-qN/postings.csv` idempotently on `posting_id`.
5. **Spot-check** a ≥15% random sample by hand. If model/human agreement is below 95%, the extractor prompt is corrected and the extract pass is re-run.

## Modules

```
pipeline/
  README.md                   this file
  requirements.txt            Python deps (requests, beautifulsoup4, litellm, python-dotenv)
  .env.example                env var template
  __init__.py
  fetch_hn.py                 HN Algolia API → raw/hn-<thread-id>.jsonl
  fetch_builtin.py            BuiltIn HTTP + BS4 → raw/builtin-<page>.jsonl
  # fetch_wellfound.py        deferred to methodology v0.2 — DataDome bot mitigation blocks the public path
  filter_postings.py          raw JSONLs + inclusion filters → filtered/<source>.jsonl
  llm_client.py               LiteLLM wrapper, provider via LLM_PROVIDER
  extract_fields.py           filtered JSONLs + llm_client → extracted/<source>.jsonl
  load_csv.py                 extracted JSONLs → captures/YYYY-qN/postings.csv (idempotent)
  spot_check.py               sample ≥15%, emit captures/YYYY-qN/spot-check.md
  aggregate.py                postings.csv → cloud-platform-breakdown.csv, frequency-by-category.csv, ...
```

JSONL shape across stages (one record per line):

```json
{
  "posting_id": "<sha1 of source_url + posting_date>",
  "source": "hn_whoishiring | builtin | wellfound",
  "source_url": "<permalink or hn-comment anchor>",
  "captured_date": "YYYY-MM-DD",
  "posting_date": "YYYY-MM-DD",
  "raw_text": "<full posting body verbatim>",
  "included": true,
  "exclude_reason": "",
  "extracted": { ... methodology row schema ... }
}
```

Stages append fields rather than rewriting records. `raw_text` is preserved through every stage; the extractor copies the relevant paragraph(s) into `extracted.stack_mentions_raw` verbatim.

## Running

```bash
cd canonical/job-postings/pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in LLM_PROVIDER + provider creds

# Per source. CAPTURE_DIR resolves to canonical/job-postings/captures/2026-q2/raw.
CAPTURE_DIR=../captures/2026-q2 python fetch_hn.py
CAPTURE_DIR=../captures/2026-q2 python fetch_builtin.py
# fetch_wellfound.py deferred to methodology v0.2 — Wellfound blocked by DataDome at v0.1.3

# Cross-source.
CAPTURE_DIR=../captures/2026-q2 python filter_postings.py
CAPTURE_DIR=../captures/2026-q2 python extract_fields.py
CAPTURE_DIR=../captures/2026-q2 python load_csv.py
CAPTURE_DIR=../captures/2026-q2 python spot_check.py
CAPTURE_DIR=../captures/2026-q2 python aggregate.py
```

Each script can be run standalone for a single source / single thread / single page during debugging; flags documented in each module's `--help`.

## Provider-agnostic LLM

`llm_client.py` is a thin wrapper over [LiteLLM](https://github.com/BerriAI/litellm). Pick a provider via env vars:

| `LLM_PROVIDER` | Required env vars | Notes |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | Direct API. Default model: `claude-sonnet-4-6`. |
| `bedrock` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Requires Anthropic model access in your AWS account (request via Bedrock console). Default model: `bedrock/anthropic.claude-sonnet-4-6`. |
| `openai` | `OPENAI_API_KEY` | Default model: `gpt-4.1`. |
| `vertex` | `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_AI_PROJECT`, `VERTEX_AI_LOCATION` | Anthropic-on-Vertex or Gemini. Default: `vertex_ai/claude-sonnet-4-6`. |

Any other LiteLLM-supported provider works — pass `LLM_MODEL` to override the model string. The extractor is single-purpose and short-context; any frontier-class chat model handles it.

## Reproducibility contract

Three rules the pipeline must honor (the methodology is explicit on all three):

1. **No lossy source text.** `raw_text` and `stack_mentions_raw` preserve the original paragraph verbatim. A stranger inspecting `postings.csv` must be able to reconstruct the LLM's input.
2. **Excluded postings stay on disk.** `filter_postings.py` records `included: false` rather than dropping. Filter logic is auditable from the JSONL files alone.
3. **Idempotent loads.** Re-running any stage against the same inputs produces the same outputs. `load_csv.py` keys on `posting_id`; replays update in place rather than appending duplicates.

## Cost envelope

Per-quarter run, with ~600 raw postings filtered to 150 extracted:

- Fetch passes: ~free (HN API, BuiltIn HTML; Wellfound deferred at v0.1.3).
- Extract pass: ~150 rows × ~2k tokens in / ~600 tokens out per call. On Anthropic Sonnet pricing roughly $1–2 per full quarter run. Bedrock and OpenAI are in the same envelope.
- Total: well under $5 per quarterly capture. Fits inside the project's under-$100/mo infrastructure target with rounding error.
