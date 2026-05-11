"""Derive the four methodology-required aggregation CSVs from postings.csv.

Outputs in $CAPTURE_DIR:
  cloud-platform-breakdown.csv  — % of postings mentioning each cloud
  frequency-by-category.csv     — % of postings mentioning each (category, instance)
  cooccurrence-top-10.csv       — top-10 multi-component tuples
  stage-breakout.csv            — frequency tables re-run on Series A/B vs. mid-market subsets

These are simple aggregations; the heavy lifting is in postings.csv. Keeping
the script tiny on purpose — a stranger should be able to read it once and
trace every number in the quarterly blog post back to specific CSV rows.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from common import COMPONENT_TAXONOMY, capture_dir


def _load_postings(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                r["_components"] = json.loads(r.get("stack_components_normalized") or "[]")
            except json.JSONDecodeError:
                r["_components"] = []
            rows.append(r)
    return rows


def _writer(path: Path, fieldnames: list[str]):
    f = path.open("w", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    return f, w


# ---- 1. Cloud platform breakdown ----

def write_cloud_platform_breakdown(rows: list[dict], out_path: Path) -> None:
    """% of postings mentioning each cloud (aws, gcp, azure, multicloud, none)."""
    n = len(rows)
    counts: Counter[str] = Counter()
    for r in rows:
        clouds_in_post = {c["instance"] for c in r["_components"]
                          if c["category"] == "cloud_platform"}
        if not clouds_in_post:
            counts["none_stated"] += 1
        else:
            for c in clouds_in_post:
                counts[c] += 1
    f, w = _writer(out_path, ["cloud", "n_postings", "pct_of_total"])
    with f:
        for cloud, k in counts.most_common():
            w.writerow({
                "cloud": cloud,
                "n_postings": k,
                "pct_of_total": f"{(k / n * 100):.1f}" if n else "0.0",
            })


# ---- 2. Frequency by category ----

def write_frequency_by_category(rows: list[dict], out_path: Path) -> None:
    """For each (category, instance), the count and % of postings mentioning it.

    A posting mentioning the same instance twice (rare; LLM dedups) counts once.
    """
    n = len(rows)
    by_cat: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        seen: set[tuple[str, str]] = set()
        for c in r["_components"]:
            key = (c["category"], c["instance"])
            if key in seen:
                continue
            seen.add(key)
            by_cat[c["category"]][c["instance"]] += 1
    f, w = _writer(out_path, ["category", "instance", "n_postings", "pct_of_total"])
    with f:
        for category in COMPONENT_TAXONOMY:  # stable category order from the taxonomy
            counts = by_cat.get(category) or Counter()
            for inst, k in counts.most_common():
                w.writerow({
                    "category": category,
                    "instance": inst,
                    "n_postings": k,
                    "pct_of_total": f"{(k / n * 100):.1f}" if n else "0.0",
                })


# ---- 3. Co-occurrence top-10 ----

def write_cooccurrence_top10(rows: list[dict], out_path: Path) -> None:
    """Common multi-component tuples per the methodology.

    Tuples emitted:
      - (warehouse, transformation, orchestration)
      - (catalog_governance, observability_dq)
      - (vector_db, llm_provider)
      - (cloud_platform, warehouse, orchestration)
    """
    tuples_to_count: dict[str, tuple[str, ...]] = {
        "warehouse-transformation-orchestration": ("warehouse", "transformation", "orchestration"),
        "catalog-observability": ("catalog_governance", "observability_dq"),
        "vectordb-llm": ("vector_db", "llm_provider"),
        "cloud-warehouse-orchestration": ("cloud_platform", "warehouse", "orchestration"),
    }
    counters: dict[str, Counter[tuple[str, ...]]] = {k: Counter() for k in tuples_to_count}

    for r in rows:
        # Build dict[category] -> set(instance) for this posting.
        per_cat: dict[str, set[str]] = defaultdict(set)
        for c in r["_components"]:
            per_cat[c["category"]].add(c["instance"])
        for tname, cats in tuples_to_count.items():
            # Cartesian product of instances across the required categories.
            sets = [per_cat.get(cat) or set() for cat in cats]
            if not all(sets):
                continue
            for combo in _cartesian(sets):
                counters[tname][combo] += 1

    f, w = _writer(out_path, ["tuple_kind", "components", "n_postings"])
    with f:
        for tname, counter in counters.items():
            for combo, k in counter.most_common(10):
                w.writerow({
                    "tuple_kind": tname,
                    "components": "|".join(combo),
                    "n_postings": k,
                })


def _cartesian(sets: list[set[str]]) -> list[tuple[str, ...]]:
    """Cartesian product of instance sets. Sorted for determinism."""
    if not sets:
        return []
    out: list[tuple[str, ...]] = [()]
    for s in sets:
        out = [prev + (i,) for prev in out for i in sorted(s)]
    return out


# ---- 4. Stage breakout ----

def write_stage_breakout(rows: list[dict], out_path: Path) -> None:
    """Frequency tables re-run on Series A/B vs. mid-market subsets.

    Bands:
      series_a_b: company_stage_signal in {series-a, series-b}
                  OR company_size_band == 50-100
      mid_market: company_stage_signal in {series-c, mid-market}
                  OR company_size_band in {100-250, 250-500-conditional}
    Postings can satisfy both (e.g., Series B at 100-250) — they appear in
    both subset rows.
    """
    def _is_series_ab(r: dict) -> bool:
        return (r["company_stage_signal"] in ("series-a", "series-b")
                or r["company_size_band"] == "50-100")

    def _is_mid_market(r: dict) -> bool:
        return (r["company_stage_signal"] in ("series-c", "mid-market")
                or r["company_size_band"] in ("100-250", "250-500-conditional"))

    subsets = {
        "all": rows,
        "series_a_b": [r for r in rows if _is_series_ab(r)],
        "mid_market": [r for r in rows if _is_mid_market(r)],
    }

    f, w = _writer(out_path,
                   ["subset", "n_in_subset", "category", "instance", "n_postings", "pct_of_subset"])
    with f:
        for subset_name, subset_rows in subsets.items():
            n = len(subset_rows)
            by_cat: dict[str, Counter[str]] = defaultdict(Counter)
            for r in subset_rows:
                seen: set[tuple[str, str]] = set()
                for c in r["_components"]:
                    key = (c["category"], c["instance"])
                    if key in seen:
                        continue
                    seen.add(key)
                    by_cat[c["category"]][c["instance"]] += 1
            for category in COMPONENT_TAXONOMY:
                counts = by_cat.get(category) or Counter()
                for inst, k in counts.most_common():
                    w.writerow({
                        "subset": subset_name,
                        "n_in_subset": n,
                        "category": category,
                        "instance": inst,
                        "n_postings": k,
                        "pct_of_subset": f"{(k / n * 100):.1f}" if n else "0.0",
                    })


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Derive aggregation CSVs from postings.csv")
    args = p.parse_args(argv)
    capture = capture_dir()
    src = capture / "postings.csv"
    if not src.exists():
        print(f"No postings.csv at {src}. Run load_csv.py first.")
        return 1
    rows = _load_postings(src)
    print(f"Loaded {len(rows)} rows from {src.name}")
    write_cloud_platform_breakdown(rows, capture / "cloud-platform-breakdown.csv")
    print(f"  -> cloud-platform-breakdown.csv")
    write_frequency_by_category(rows, capture / "frequency-by-category.csv")
    print(f"  -> frequency-by-category.csv")
    write_cooccurrence_top10(rows, capture / "cooccurrence-top-10.csv")
    print(f"  -> cooccurrence-top-10.csv")
    write_stage_breakout(rows, capture / "stage-breakout.csv")
    print(f"  -> stage-breakout.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
