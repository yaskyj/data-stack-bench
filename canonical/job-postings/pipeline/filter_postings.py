"""Apply the v0.1.2 inclusion filters to raw fetched postings.

This is the cheap mechanical pre-filter pass. Its job is to drop postings that
obviously can't pass the methodology's filters: missing data-role keyword,
junior, leadership, explicit non-target geo, stale. Postings that survive are
handed to extract_fields.py, which does the harder filter judgments (company
stage/size, industry, conditional MLE/data-architect inclusion) as part of LLM
extraction.

Split rationale: paying an LLM to read 600+ HN postings just to discover that
80% don't mention "data" is wasteful (~$3 of API spend per quarter to do work
regex handles in 80ms). Splitting the filter into a cheap mechanical pass +
an LLM-aware extract pass keeps the per-quarter cost under $2 without sacrificing
filter precision — the LLM still adjudicates every edge case that matters.

Usage:
    python filter_postings.py                          # filter every raw/*.jsonl
    python filter_postings.py --source hn_whoishiring  # one source

Output:
    $CAPTURE_DIR/filtered/<source>.jsonl  (one record per raw, with `included`
                                           and `exclude_reason` populated;
                                           excluded rows kept on disk for audit)
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from common import (
    SOURCES,
    capture_dir,
    filtered_dir,
    raw_dir,
    read_jsonl,
    today_iso,
    write_jsonl,
)


# ---- Filter rules ----

# Methodology §Role title / function. Postings without at least one of these
# tokens are excluded — vague language ("we hire engineers") is not a positive
# vote.
ROLE_INCLUDE_RE = re.compile(
    r"\b(data engineer|data engineering|analytics engineer|data platform|"
    r"data infrastructure|data architect|machine learning engineer|"
    r"\bml engineer|mle\b|data eng\b)",
    re.I,
)

# Leadership-level exclusion. Methodology: Director/Head/VP roles are abstracted
# stack mentions and don't reflect the day-to-day tools the team uses.
LEADERSHIP_RE = re.compile(
    r"\b(director|head of (?:data|engineering|platform|analytics)|"
    r"vp\s|vice president|chief data officer|cdo\b|cto\b|chief)\b",
    re.I,
)

# Junior-level exclusion. Methodology: junior postings list aspirational stacks
# rather than what the team actually uses.
JUNIOR_RE = re.compile(
    r"\b(intern(?:ship)?|junior|entry[- ]level|new grad|graduate program|"
    r"early career|associate engineer)\b",
    re.I,
)

# Explicit non-target geographies that, if mentioned in the role's location
# line, are immediate excludes. Methodology: include US, Canada, UK, EU.
# Other locations sometimes appear alongside US/EU offices on the same posting
# (e.g., "Remote (US, Canada, Argentina)") — for those the LLM extract pass
# adjudicates whether the role is fillable from a target geo. The mechanical
# filter only triggers when the listed location is unambiguously not-US/EU.
NON_TARGET_GEO_TOKENS = (
    "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "chennai", "pune",
    "brazil", "são paulo", "sao paulo", "rio de janeiro",
    "mexico city", "mexico ", "ciudad de méxico", "monterrey",
    "argentina", "buenos aires",
    "singapore",
    "japan", "tokyo", "osaka",
    "korea", "seoul",
    "china", "beijing", "shanghai", "shenzhen", "hong kong",
    "thailand", "bangkok",
    "malaysia", "kuala lumpur",
    "vietnam", "ho chi minh", "hanoi",
    "indonesia", "jakarta",
    "taiwan", "taipei",
    "philippines", "manila",
    "australia", "sydney", "melbourne",
    "new zealand", "auckland",
    "uae", "dubai", "abu dhabi",
    "saudi", "riyadh",
    "israel", "tel aviv",
    "south africa", "cape town",
    "egypt", "cairo",
    "nigeria", "lagos",
)

# Tokens that are POSITIVE for target geo, used to override a non-target token
# that appears in a multi-region "Remote" line (e.g., "Remote (US, India)").
TARGET_GEO_TOKENS = (
    "united states", " usa", " us ", "u.s.", "u.s.a", "us-only", "us only",
    "canada", "toronto", "montreal", "vancouver", "ottawa",
    "uk", "united kingdom", "london", "manchester", "edinburgh", "bristol",
    "ireland", "dublin",
    "germany", "berlin", "munich", "hamburg",
    "france", "paris",
    "spain", "madrid", "barcelona",
    "italy", "rome", "milan",
    "netherlands", "amsterdam",
    "sweden", "stockholm",
    "denmark", "copenhagen",
    "finland", "helsinki",
    "norway", "oslo",
    "poland", "warsaw",
    "portugal", "lisbon",
    " eu ", " eu/", " eea ",
    "remote",  # last-resort signal — "Remote" alone is ambiguous but very common
)


@dataclass(frozen=True)
class FilterDecision:
    included: bool
    reason: str  # short tag, empty if included


def _first_line(text: str) -> str:
    # HN postings: first line is typically "Company | Role | Location". BuiltIn
    # and Wellfound: first line is the canonicalized title. In both cases the
    # first line is where leadership/junior keywords appear most reliably.
    return (text or "").split("\n", 1)[0].strip()


def _has_token(text: str, tokens: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(tok in t for tok in tokens)


def _stale(posting_date: str, captured_date: str, max_age_days: int = 60) -> bool:
    if not posting_date:
        return False  # unknown date — let it through; LLM extract has final say
    try:
        pd = date.fromisoformat(posting_date)
        cd = date.fromisoformat(captured_date) if captured_date else date.today()
    except ValueError:
        return False
    return (cd - pd) > timedelta(days=max_age_days)


def decide(record: dict) -> FilterDecision:
    text = record.get("raw_text") or ""
    first = _first_line(text)

    # Order: cheap filters first, role-keyword check last (most expensive regex).

    if _stale(record.get("posting_date", ""), record.get("captured_date", "")):
        return FilterDecision(False, "stale_>60_days")

    if LEADERSHIP_RE.search(first):
        return FilterDecision(False, "leadership_role")

    if JUNIOR_RE.search(text):
        # Junior keyword anywhere in the body. The methodology rules junior out
        # because postings list aspirational stacks. Even if the role title is
        # "Senior", a junior co-listing makes the posting noisy.
        return FilterDecision(False, "junior_or_intern")

    # Non-target geography on the location line. Only triggers when no target
    # token is present — multi-region "Remote (US, India)" listings pass.
    first_lower = first.lower()
    if _has_token(first_lower, NON_TARGET_GEO_TOKENS) and not _has_token(
        first_lower, TARGET_GEO_TOKENS
    ):
        return FilterDecision(False, "non_target_geo")

    if not ROLE_INCLUDE_RE.search(text):
        return FilterDecision(False, "no_data_role_keyword")

    return FilterDecision(True, "")


# ---- File-level driver ----

def filter_file(in_path: Path, out_path: Path) -> tuple[int, int]:
    """Filter one raw JSONL file → one filtered JSONL file.

    Returns (kept, total).
    """
    records = list(read_jsonl(in_path))
    kept = 0
    out: list[dict] = []
    for r in records:
        d = decide(r)
        r["included"] = d.included
        r["exclude_reason"] = d.reason
        out.append(r)
        if d.included:
            kept += 1
    write_jsonl(out_path, out)
    return kept, len(records)


def _source_of(filename: str) -> str:
    # Conventional prefixes: hn-*, builtin-*, wellfound-*
    head = filename.split("-", 1)[0]
    if head == "hn":
        return "hn_whoishiring"
    if head in ("builtin", "wellfound"):
        return head
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Filter raw postings against v0.1.2 inclusion criteria.")
    p.add_argument("--source", choices=list(SOURCES) + ["all"], default="all")
    args = p.parse_args(argv)

    raw = raw_dir()
    out_root = filtered_dir()

    files = sorted(p for p in raw.glob("*.jsonl") if p.is_file())
    if not files:
        print(f"No raw files in {raw}. Run a fetcher first.")
        return 1

    by_source: dict[str, list[Path]] = {}
    for f in files:
        s = _source_of(f.name)
        if s == "unknown":
            continue
        if args.source != "all" and s != args.source:
            continue
        by_source.setdefault(s, []).append(f)

    if not by_source:
        print(f"No raw files matching source={args.source}")
        return 1

    overall_kept = overall_total = 0
    for src, fs in by_source.items():
        all_records: list[dict] = []
        kept_src = 0
        for f in fs:
            records = list(read_jsonl(f))
            for r in records:
                d = decide(r)
                r["included"] = d.included
                r["exclude_reason"] = d.reason
                all_records.append(r)
                if d.included:
                    kept_src += 1
        # Per source: one consolidated filtered file. Easier downstream.
        out_path = out_root / f"{src}.jsonl"
        write_jsonl(out_path, all_records)
        total_src = len(all_records)
        overall_kept += kept_src
        overall_total += total_src

        # Per-reason breakdown for visibility.
        reasons: dict[str, int] = {}
        for r in all_records:
            if not r["included"]:
                reasons[r["exclude_reason"]] = reasons.get(r["exclude_reason"], 0) + 1
        print(f"{src}: {kept_src}/{total_src} kept ({kept_src/total_src*100:.1f}%) -> {out_path.name}")
        for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"  excluded ({reason}): {n}")

    print(f"\nTotal: {overall_kept}/{overall_total} kept across {len(by_source)} sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
