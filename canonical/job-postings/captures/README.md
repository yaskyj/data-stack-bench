# Job-posting analysis captures

This directory holds the outputs of each quarterly job-posting analysis run. The methodology that produces these files lives at [`../methodology.md`](../methodology.md).

## Layout

One subdirectory per quarterly run, named `YYYY-qN/`:

```
captures/
  README.md
  2026-q2/                             first capture (May–June 2026)
    postings.csv                       row-per-posting captures per the methodology schema
    cloud-platform-breakdown.csv       headline output: % of postings per cloud
    frequency-by-category.csv          % of postings mentioning each component, per category
    cooccurrence-top-10.csv            top 10 (warehouse, transformation, orchestrator) triples + others
    stage-breakout.csv                 frequency tables re-run on Series A/B vs. mid-market subsets
    spot-check.md                      human-reviewed sample log (≥15% of rows)
    lineup-decision.md                 internal decision doc — locks Stack #2-5 against this capture
    raw/                               JSONL dumps from the fetchers (one file per source)
  2026-q3/                             second capture (from qoq-delta.csv onward)
    ...
```

Two narrative artifacts come out of each run:

- A short **internal lineup decision doc** (`lineup-decision.md` inside the quarterly directory) that locks the call against the data — which stacks the lineup confirms, which it rearranges, what the surprising signals were. This is project-internal and lives next to the capture data.
- A **public writeup** of the same run in [`../../../posts/`](../../../posts/) as a dated post. The public writeup is timed against the project's overall publication threshold, not the run itself — see the build-first sequencing note in the internal brief.

## File format conventions

- All capture files are CSV with a header row, UTF-8, RFC-4180-quoted.
- Date fields use ISO-8601 (`YYYY-MM-DD`).
- Boolean fields use lowercase `true` / `false`.
- Missing-but-known-absent values use empty cells; missing-and-unknown values use `unknown` (the methodology calls out the distinction).
- `postings.csv` follows the extraction schema defined in `../methodology.md` exactly. The other CSVs are aggregations derived from `postings.csv`.

## Reproducibility

Each quarterly directory should contain enough information that a stranger can re-derive the aggregations from `postings.csv` alone. If a derivation script is used, commit it next to the CSVs (e.g., `2026-q3/aggregate.py`). Numbers in the corresponding quarterly post in `posts/` must be traceable back to specific rows in these files.

## Cadence

Quarterly. First capture: **2026-Q2**, complete (N=40, HN + BuiltIn — Wellfound deferred to v0.2). Internal lineup decision doc landed 2026-05-11. Spot-check sign-off pending. Public writeup follows per the build-first sequencing in the internal brief.
