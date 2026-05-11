"""Materialize the canonical postings.csv from the per-source extracted JSONLs.

Schema: methodology.md §Extraction schema. The CSV is the single source of
truth that aggregations and the spot-check tool both read.

Idempotent on `posting_id` — re-running this script replaces rows with the
same posting_id rather than appending duplicates. Safe to run mid-capture.

The CSV excludes rows where the extractor set keep=false. Those rows stay in
the JSONL files for audit; the CSV is the analysis-ready subset.

Usage:
    python load_csv.py                 # all sources, all extracted records
    python load_csv.py --include-excluded  # also write excluded rows (audit dump)
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from common import capture_dir, extracted_dir, read_jsonl


CSV_HEADER = [
    # methodology §Extraction schema
    "posting_id",
    "source",
    "source_url",
    "captured_date",
    "posting_date",
    "company_name",
    "company_size_band",
    "company_stage_signal",
    "industry",
    "role_title_raw",
    "role_title_normalized",
    "seniority",
    "geo",
    "stack_mentions_raw",
    "stack_components_normalized",  # JSON-encoded array of {category, instance}
    "notes",
    # Pipeline metadata (not in methodology schema but useful for audit).
    "confidence",
]


def _row(record: dict) -> dict[str, str] | None:
    """Project an extracted JSONL record to a CSV row dict, or None if excluded."""
    ext = record.get("extracted") or {}
    if not ext.get("keep"):
        return None
    return {
        "posting_id": record["posting_id"],
        "source": record["source"],
        "source_url": record["source_url"],
        "captured_date": record.get("captured_date", ""),
        "posting_date": record.get("posting_date", ""),
        "company_name": ext.get("company_name", ""),
        "company_size_band": ext.get("company_size_band", "unknown"),
        "company_stage_signal": ext.get("company_stage_signal", "unknown"),
        "industry": ext.get("industry", "other"),
        "role_title_raw": ext.get("role_title_raw", ""),
        "role_title_normalized": ext.get("role_title_normalized") or "",
        "seniority": ext.get("seniority") or "",
        "geo": ext.get("geo") or "",
        "stack_mentions_raw": ext.get("stack_mentions_raw", ""),
        "stack_components_normalized": json.dumps(
            ext.get("stack_components_normalized") or [],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "notes": ext.get("notes", ""),
        "confidence": ext.get("confidence", ""),
    }


def collect_rows(include_excluded: bool = False) -> list[dict[str, str]]:
    """Walk every extracted JSONL and produce keep=true rows (or all rows in audit mode)."""
    out: dict[str, dict[str, str]] = {}
    in_root = extracted_dir()
    for f in sorted(in_root.glob("*.jsonl")):
        for r in read_jsonl(f):
            ext = r.get("extracted") or {}
            keep = ext.get("keep")
            if not include_excluded and not keep:
                continue
            row = _row(r)
            if row is None and include_excluded:
                # Audit mode: emit a partial row so we can see what was excluded.
                row = {
                    "posting_id": r["posting_id"],
                    "source": r["source"],
                    "source_url": r["source_url"],
                    "captured_date": r.get("captured_date", ""),
                    "posting_date": r.get("posting_date", ""),
                    "company_name": ext.get("company_name", ""),
                    "company_size_band": ext.get("company_size_band", "unknown"),
                    "company_stage_signal": ext.get("company_stage_signal", "unknown"),
                    "industry": ext.get("industry", "other"),
                    "role_title_raw": ext.get("role_title_raw", ""),
                    "role_title_normalized": ext.get("role_title_normalized") or "",
                    "seniority": ext.get("seniority") or "",
                    "geo": ext.get("geo") or "",
                    "stack_mentions_raw": ext.get("stack_mentions_raw", ""),
                    "stack_components_normalized": json.dumps(
                        ext.get("stack_components_normalized") or [],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "notes": (ext.get("notes", "") + " [EXCLUDED: " +
                              (ext.get("exclude_reason") or "") + "]").strip(),
                    "confidence": ext.get("confidence", ""),
                }
            if row is None:
                continue
            # Idempotency: last write wins on posting_id.
            out[row["posting_id"]] = row
    return list(out.values())


def write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write the canonical postings.csv from extracted JSONLs.")
    p.add_argument("--include-excluded", action="store_true",
                   help="Audit dump: emit excluded rows too (writes postings-audit.csv).")
    args = p.parse_args(argv)

    rows = collect_rows(include_excluded=args.include_excluded)
    target_name = "postings-audit.csv" if args.include_excluded else "postings.csv"
    out_path = capture_dir() / target_name
    write_csv(rows, out_path)
    print(f"Wrote {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
