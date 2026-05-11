"""LLM-assisted extraction of normalized fields from each included posting.

Input:  $CAPTURE_DIR/filtered/<source>.jsonl  (postings with included=true)
Output: $CAPTURE_DIR/extracted/<source>.jsonl (input + `extracted` payload)

The extractor does two jobs in a single LLM call:

1. **Final filter judgment.** The methodology's harder filters — company
   stage/size, industry, edge-case role inclusion (MLE with data focus, Data
   Architect hands-on) — need to read the posting body. We do them here rather
   than in filter_postings.py because the same LLM call is already reading the
   body for field extraction; splitting it across two calls would double API
   cost. Decisions flow into `extracted.keep` (bool) and `extracted.exclude_reason`.
2. **Field extraction.** The methodology row schema, populated from the
   posting's raw text. Closed-list enums are passed in the system prompt;
   stack components map to the two-level taxonomy in common.COMPONENT_TAXONOMY.

Verbatim contract: `extracted.stack_mentions_raw` MUST be a verbatim copy of
the paragraph(s) from `raw_text` that name stack components. The LLM is
explicitly instructed not to paraphrase. Spot-check verifies.

Confidence: the LLM returns per-field confidence implicitly via an overall
`confidence: low|medium|high` field. Low-confidence rows are tagged for the
spot-check queue regardless of the random sample.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator

from common import (
    COMPANY_SIZE_BANDS,
    COMPANY_STAGE_SIGNALS,
    COMPONENT_TAXONOMY,
    GEOS,
    INDUSTRIES,
    ROLE_TITLES_NORMALIZED,
    SENIORITIES,
    SOURCES,
    capture_dir,
    extracted_dir,
    filtered_dir,
    read_jsonl,
    today_iso,
    write_jsonl,
)
import llm_client


# ---- Prompt construction ----

def _taxonomy_for_prompt() -> str:
    """Render COMPONENT_TAXONOMY as a deterministic ordered list for the prompt."""
    lines = []
    for category, instances in COMPONENT_TAXONOMY.items():
        instances_str = ", ".join(instances)
        lines.append(f"  - {category}: [{instances_str}]")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You extract structured fields from data-team job postings.

You produce a single JSON object per posting. No prose, no markdown. Strict JSON.

# Task

For one job posting, you do two things in one response:

1. Decide whether the posting meets the methodology's inclusion criteria. The cheap
   mechanical pre-filter has already screened out obvious junk (no data-role keyword,
   junior, leadership, stale, non-target geo). Your job is the harder calls:
   - Industry must be one of: saas, fintech-software, ecommerce-platform, marketplace,
     healthtech-software, edtech, devtools, fintech-regulated (only if not compliance-
     dominated). Exclude defense, healthcare-provider operations, government, traditional
     finance trading systems, oil/gas.
   - Company size must be ~50–250 employees. Include 250–500 only if the posting clearly
     describes a small (1–5 person) data team. Exclude <50 (founder-as-data-team) and
     >500 (likely a dedicated platform team).
   - Role must be Data Engineer, Analytics Engineer, Data Platform Engineer, or
     conditionally: MLE with data pipeline / feature-engineering responsibilities
     (NOT pure ML inference), Data Architect with hands-on duties (NOT pure design
     oversight). Pure Data Scientist is excluded.
   - Geography must be US, Canada, UK, or EU (English-language) — including remote
     postings where the company is headquartered there.

   If the posting passes all criteria, set keep=true and exclude_reason="".
   If not, set keep=false and put a short tag in exclude_reason, one of:
   industry_excluded, company_too_small, company_too_large, role_not_in_scope,
   role_aspirational_stack_only, geography_excluded, data_team_role_unclear,
   insufficient_information.

   The `industry` field MUST be one of the closed-list values regardless of
   keep. For excluded industries (defense, automotive, energy/utilities, oil/gas,
   trading/asset-management, government, healthcare-provider operations,
   anything not in the include list) use industry="other" with keep=false and
   exclude_reason="industry_excluded". Never put filter sentinels (like
   "industry_excluded") in the industry field itself — the field is the
   classification, not the decision.

2. Extract the methodology row fields. Fill every field; use "unknown" where the
   closed-list enum allows it and the posting doesn't say. The stack components are
   the load-bearing extraction — see rules below.

# Schema

Return a single JSON object with these fields (all required):

{{
  "company_name": <string>,
  "company_size_band": one of [{", ".join(COMPANY_SIZE_BANDS)}],
  "company_stage_signal": one of [{", ".join(COMPANY_STAGE_SIGNALS)}],
  "industry": one of [{", ".join(INDUSTRIES)}],
  "role_title_raw": <string, verbatim from the posting>,
  "role_title_normalized": one of [{", ".join(ROLE_TITLES_NORMALIZED)}] OR null if keep=false,
  "seniority": one of [{", ".join(SENIORITIES)}] OR null if keep=false,
  "geo": one of [{", ".join(GEOS)}] OR null if keep=false,
  "stack_mentions_raw": <string, verbatim paragraph(s) naming stack components>,
  "stack_components_normalized": <array of {{"category": <string>, "instance": <string>}}>,
  "notes": <string, optional observations>,
  "keep": <boolean>,
  "exclude_reason": <string, empty if keep=true>,
  "confidence": one of ["low", "medium", "high"]
}}

# Stack component rules

Map every named tool to the closed taxonomy below. If a tool is mentioned that
isn't in the taxonomy, omit it from `stack_components_normalized` and add the raw
name to `notes` (we'll review the taxonomy in v0.2).

Taxonomy — category: [allowed instances]:
{_taxonomy_for_prompt()}

Edge cases:
- "We're migrating from X to Y": vote for Y, not X. Note the migration in `notes`.
- "Experience with X is a plus" or "nice to have": still counts as a mention.
  Tag in `notes`: "X aspirational".
- "Modern data stack" with no tools named: NO components, do not impute.
- A component category absent from the posting: simply do not list it. Do not add
  "none" entries.
- "Custom Python" for ingestion: instance = "custom_python" (it appears in both
  `ingestion_elt` and `transformation` — pick whichever role the posting describes).
- "Snowflake" alone implies cloud_platform="aws" only when the posting explicitly
  says so. Otherwise leave cloud_platform out — Snowflake runs on all three clouds.

# Verbatim contract

`stack_mentions_raw` MUST be the original posting paragraph(s) verbatim, character-
for-character. Do not paraphrase, summarize, or fix typos. If multiple paragraphs
mention stack components, concatenate them with a single blank line. This is a
methodology requirement, not a style preference.

# Confidence

- high: every required field is unambiguous in the posting.
- medium: at least one field required a judgment call (e.g., inferring industry
  from a one-line company description).
- low: company size, industry, or stack mentions were guessed from sparse context.
  Low rows get hand-reviewed; bias toward marking low rather than high.
"""


# ---- JSONSchema (post-LLM validation) ----

EXTRACTED_SCHEMA = {
    "type": "object",
    "required": [
        "company_name", "company_size_band", "company_stage_signal", "industry",
        "role_title_raw", "stack_mentions_raw", "stack_components_normalized",
        "notes", "keep", "exclude_reason", "confidence",
    ],
    "properties": {
        "company_name": {"type": "string"},
        "company_size_band": {"enum": list(COMPANY_SIZE_BANDS)},
        "company_stage_signal": {"enum": list(COMPANY_STAGE_SIGNALS)},
        "industry": {"enum": list(INDUSTRIES)},
        "role_title_raw": {"type": "string"},
        "role_title_normalized": {"oneOf": [{"enum": list(ROLE_TITLES_NORMALIZED)}, {"type": "null"}]},
        "seniority": {"oneOf": [{"enum": list(SENIORITIES)}, {"type": "null"}]},
        "geo": {"oneOf": [{"enum": list(GEOS)}, {"type": "null"}]},
        "stack_mentions_raw": {"type": "string"},
        "stack_components_normalized": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["category", "instance"],
                "properties": {
                    "category": {"enum": list(COMPONENT_TAXONOMY.keys())},
                    "instance": {"type": "string"},
                },
            },
        },
        "notes": {"type": "string"},
        "keep": {"type": "boolean"},
        "exclude_reason": {"type": "string"},
        "confidence": {"enum": ["low", "medium", "high"]},
    },
}


# ---- Per-posting extraction ----

def _trim_for_user(record: dict, max_chars: int = 8000) -> str:
    """Build the user message body. Truncate egregiously long postings."""
    text = record.get("raw_text") or ""
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...truncated...]"
    return text


def _validate_component_instances(payload: dict) -> list[str]:
    """Return human-readable issues with `stack_components_normalized` entries.

    We don't reject the row — methodology lets unknown components fall to notes
    — but we do flag them for spot-check.
    """
    issues: list[str] = []
    for c in payload.get("stack_components_normalized", []):
        cat = c.get("category")
        inst = c.get("instance")
        valid_instances = COMPONENT_TAXONOMY.get(cat) or ()
        if inst not in valid_instances:
            issues.append(f"{cat}.{inst} not in taxonomy")
    return issues


def extract_one(record: dict) -> dict:
    """Run extraction on one filtered posting; return the input + `extracted` payload."""
    user_msg = _trim_for_user(record)
    try:
        payload = llm_client.extract(
            system=SYSTEM_PROMPT,
            user=user_msg,
            schema=EXTRACTED_SCHEMA,
            temperature=0.0,
            max_tokens=2000,
        )
    except llm_client.LLMError as e:
        # Don't lose the record — annotate the failure and let the row pass to
        # the spot-check queue. Final CSV will exclude these unless they're
        # repaired manually.
        record["extracted"] = {
            "company_name": "",
            "company_size_band": "unknown",
            "company_stage_signal": "unknown",
            "industry": "other",
            "role_title_raw": "",
            "role_title_normalized": None,
            "seniority": None,
            "geo": None,
            "stack_mentions_raw": "",
            "stack_components_normalized": [],
            "notes": f"EXTRACTION_FAILED: {e}",
            "keep": False,
            "exclude_reason": "extraction_failed",
            "confidence": "low",
        }
        record["extraction_error"] = str(e)
        return record

    # Soft validation: unknown taxonomy instances downgrade confidence.
    issues = _validate_component_instances(payload)
    if issues and payload.get("confidence") == "high":
        payload["confidence"] = "medium"
        payload["notes"] = (payload.get("notes") or "") + \
            f"\n[validator] taxonomy issues: {'; '.join(issues)}"

    record["extracted"] = payload
    return record


# ---- File-level driver ----

def _index_existing(out_path: Path, retry_failed: bool = False) -> dict[str, dict]:
    """Return posting_id -> record dict from a previous extracted file, if any.

    Used for resumability: if extract_fields.py is interrupted mid-run, the
    next invocation picks up where it left off rather than re-extracting rows.
    A record is considered "already extracted" if it has an `extracted` payload.

    If `retry_failed` is True, records whose extraction failed (exclude_reason
    == "extraction_failed") are not indexed — they'll be re-extracted.
    """
    if not out_path.exists():
        return {}
    out: dict[str, dict] = {}
    for r in read_jsonl(out_path):
        ext = r.get("extracted")
        if not ext:
            continue
        if retry_failed and ext.get("exclude_reason") == "extraction_failed":
            continue
        out[r["posting_id"]] = r
    return out


def extract_file(in_path: Path, out_path: Path, *, limit: int | None = None,
                 sleep_s: float = 0.0, concurrency: int = 1,
                 resume: bool = True, retry_failed: bool = False) -> tuple[int, int, int]:
    """Extract one filtered JSONL → extracted JSONL.

    Returns (extracted_n, kept_n, low_conf_n).
    Skips records with `included=False` (they pass through unchanged so the
    extracted file stays a superset of the filtered file for audit).

    Resumability: if `resume=True` (default) and the output file already exists,
    records present there with an `extracted` payload are kept as-is. Re-runs
    after a partial extraction don't re-spend API budget.

    Concurrency: if `concurrency > 1`, included records are extracted in a
    thread pool. LLM calls are I/O-bound; concurrency=5–8 typically saturates
    the per-account Bedrock quota without throttling.
    """
    records = list(read_jsonl(in_path))
    existing = _index_existing(out_path, retry_failed=retry_failed) if resume else {}

    # Build the work plan: (idx, record). Preserve original order in `out`.
    work: list[tuple[int, dict]] = []
    out: list[dict | None] = [None] * len(records)
    extracted_n = 0
    for i, r in enumerate(records):
        if not r.get("included"):
            out[i] = r
            continue
        prior = existing.get(r["posting_id"])
        if prior is not None:
            out[i] = prior  # already done in a previous run
            continue
        if limit is not None and extracted_n >= limit:
            out[i] = r  # left for a future run
            continue
        work.append((i, r))
        extracted_n += 1

    kept_n = low_n = 0

    def _record_stats(result: dict) -> None:
        nonlocal kept_n, low_n
        if result["extracted"].get("keep"):
            kept_n += 1
        if result["extracted"].get("confidence") == "low":
            low_n += 1

    if concurrency <= 1:
        for i, r in work:
            result = extract_one(r)
            out[i] = result
            _record_stats(result)
            if sleep_s > 0:
                time.sleep(sleep_s)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(extract_one, r): i for i, r in work}
            for fut in as_completed(futures):
                i = futures[fut]
                result = fut.result()
                out[i] = result
                _record_stats(result)

    # Count rows that already had extracted (from previous run) toward kept/low.
    for r in existing.values():
        ext = r.get("extracted") or {}
        if ext.get("keep"):
            kept_n += 1
        if ext.get("confidence") == "low":
            low_n += 1

    final: list[dict] = [r for r in out if r is not None]
    write_jsonl(out_path, final)
    # extracted_n above counts only freshly-scheduled this call.
    return extracted_n, kept_n, low_n


# ---- CLI ----

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LLM-extract methodology fields from filtered postings.")
    p.add_argument("--source", choices=list(SOURCES) + ["all"], default="all")
    p.add_argument("--limit", type=int, default=None,
                   help="Cap extractions per source. Useful for dry runs.")
    p.add_argument("--sleep", type=float, default=0.0,
                   help="Seconds to sleep between LLM calls (provider-friendly rate limiting). "
                        "Ignored when --concurrency > 1.")
    p.add_argument("--concurrency", type=int, default=1,
                   help="Parallel LLM calls. Bedrock per-account quotas comfortably handle 5–8.")
    p.add_argument("--no-resume", action="store_true",
                   help="Re-extract every included record, even ones already present in the output.")
    p.add_argument("--retry-failed", action="store_true",
                   help="Re-extract rows previously marked extraction_failed (transient API errors).")
    args = p.parse_args(argv)

    in_root = filtered_dir()
    out_root = extracted_dir()
    files = sorted(p for p in in_root.glob("*.jsonl") if p.is_file())
    if not files:
        print(f"No filtered files in {in_root}. Run filter_postings.py first.")
        return 1

    sources = [f.stem for f in files]
    if args.source != "all":
        sources = [args.source]

    overall_extracted = overall_kept = overall_low = 0
    for src in sources:
        in_path = in_root / f"{src}.jsonl"
        if not in_path.exists():
            print(f"  skip {src}: no filtered file")
            continue
        out_path = out_root / f"{src}.jsonl"
        ex, kept, low = extract_file(
            in_path, out_path,
            limit=args.limit,
            sleep_s=args.sleep,
            concurrency=args.concurrency,
            resume=not args.no_resume,
            retry_failed=args.retry_failed,
        )
        print(f"{src}: extracted={ex}  kept={kept}  low_confidence={low}  -> {out_path.name}")
        overall_extracted += ex
        overall_kept += kept
        overall_low += low

    print(f"\nTotal: extracted={overall_extracted}  kept={overall_kept}  "
          f"low_confidence={overall_low}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
