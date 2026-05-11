"""Produce a markdown spot-check sample for the human reviewer.

Methodology v0.1.2 requires ≥15% random sample human-reviewed before any
analysis output is published. This script:

1. Selects a deterministic random sample of postings (default 15%, min 6) from
   postings.csv, biased to include all `confidence: low` rows.
2. For each sampled row, renders a markdown block showing the source paragraph
   (verbatim from `stack_mentions_raw`) and the LLM-extracted classification.
3. Writes the result to $CAPTURE_DIR/spot-check.md with check boxes the
   reviewer can tick.

The sample includes a small auto-review pass: for each row, a string-membership
heuristic flags fields where the extracted instance string is not visibly
present in the source paragraph. Heuristic disagreements are NOT corrections —
they're prompts for the reviewer to look carefully.

Usage:
    python spot_check.py                    # 15% sample
    python spot_check.py --pct 25 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from common import capture_dir


# Tokens we expect to literally appear in the source text for each instance.
# Used by the auto-review to flag possible misclassifications. Missing tokens
# below means "skip the check for this instance".
INSTANCE_TOKEN_HINTS: dict[str, tuple[str, ...]] = {
    "aws": ("aws", "amazon web services"),
    "gcp": ("gcp", "google cloud"),
    "azure": ("azure",),
    "snowflake": ("snowflake",),
    "bigquery": ("bigquery", "big query"),
    "redshift": ("redshift",),
    "databricks": ("databricks",),
    "athena": ("athena",),
    "duckdb": ("duckdb",),
    "clickhouse": ("clickhouse",),
    "postgres_as_warehouse": ("postgres",),
    "iceberg": ("iceberg",),
    "delta": ("delta lake", "delta table", "deltalake"),
    "hudi": ("hudi",),
    "dbt_core": ("dbt",),
    "dbt_cloud": ("dbt cloud", "dbt-cloud"),
    "sqlmesh": ("sqlmesh", "sqlMesh"),
    "dataform": ("dataform",),
    "airflow": ("airflow",),
    "mwaa": ("mwaa",),
    "dagster": ("dagster",),
    "prefect": ("prefect",),
    "temporal": ("temporal",),
    "fivetran": ("fivetran",),
    "airbyte_oss": ("airbyte",),
    "airbyte_cloud": ("airbyte",),
    "meltano": ("meltano",),
    "looker": ("looker",),
    "tableau": ("tableau",),
    "powerbi": ("power bi", "powerbi"),
    "metabase": ("metabase",),
    "mode": ("mode analytics", "mode bi"),
    "sigma": ("sigma",),
    "hex": ("hex",),
    "openmetadata": ("openmetadata",),
    "datahub": ("datahub",),
    "atlan": ("atlan",),
    "unity_catalog": ("unity catalog",),
    "monte_carlo": ("monte carlo",),
    "great_expectations": ("great expectations",),
    "terraform": ("terraform",),
    "cdk": ("cdk", "cloud development kit"),
    "pulumi": ("pulumi",),
    "kafka": ("kafka",),
    "msk": ("msk",),
    "kinesis": ("kinesis",),
    "pubsub": ("pub/sub", "pubsub"),
    "mlflow": ("mlflow",),
    "weights_and_biases": ("weights & biases", "weights and biases", "wandb"),
    "sagemaker": ("sagemaker",),
    "vertex_ai": ("vertex",),
    "pgvector": ("pgvector",),
    "pinecone": ("pinecone",),
    "weaviate": ("weaviate",),
    "qdrant": ("qdrant",),
    "openai": ("openai",),
    "anthropic": ("anthropic",),
    "bedrock": ("bedrock",),
    "langchain": ("langchain",),
    "llamaindex": ("llamaindex",),
    "github_actions": ("github actions",),
    "hightouch": ("hightouch",),
    "census": ("census",),
}


def auto_flags(stack_mentions: str, components: list[dict]) -> list[str]:
    """String-membership heuristic: flag instances not visibly present in source."""
    text = (stack_mentions or "").lower()
    flags = []
    for c in components:
        inst = c.get("instance")
        hints = INSTANCE_TOKEN_HINTS.get(inst)
        if not hints:
            continue
        if not any(h in text for h in hints):
            flags.append(f"{c.get('category')}.{inst} not visibly in source paragraph")
    return flags


def render_row(r: dict, idx: int, total: int) -> str:
    try:
        comps = json.loads(r.get("stack_components_normalized") or "[]")
    except json.JSONDecodeError:
        comps = []
    flags = auto_flags(r.get("stack_mentions_raw", ""), comps)
    flag_block = ""
    if flags:
        flag_block = "\n**Auto-review flags (reviewer please verify):**\n" + \
                     "\n".join(f"- {x}" for x in flags) + "\n"

    comps_str = ", ".join(f"`{c['category']}={c['instance']}`" for c in comps) or "_(none)_"

    return f"""## Row {idx} of {total} — {r['company_name']} (`{r['source']}`)

**Source URL:** {r['source_url']}
**Posting ID:** `{r['posting_id']}`
**Confidence:** {r.get('confidence', '?')}

| field | LLM extracted |
|---|---|
| industry | {r['industry']} |
| company_size_band | {r['company_size_band']} |
| company_stage_signal | {r['company_stage_signal']} |
| role_title_raw | {r['role_title_raw']} |
| role_title_normalized | {r['role_title_normalized']} |
| seniority | {r['seniority']} |
| geo | {r['geo']} |

**Stack components extracted:** {comps_str}
{flag_block}
**`stack_mentions_raw`** (verbatim from source posting):

> {r['stack_mentions_raw'].replace(chr(10), chr(10) + '> ') or '_(empty)_'}

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Produce spot-check.md for the human reviewer.")
    p.add_argument("--pct", type=float, default=15.0, help="Sample percentage. Default 15.")
    p.add_argument("--min", type=int, default=6, help="Minimum sample size. Default 6.")
    p.add_argument("--seed", type=int, default=20260511, help="RNG seed for reproducibility.")
    args = p.parse_args(argv)

    capture = capture_dir()
    src = capture / "postings.csv"
    if not src.exists():
        print(f"No postings.csv at {src}. Run load_csv.py first.")
        return 1
    rows = list(csv.DictReader(src.open("r", encoding="utf-8")))
    n_total = len(rows)
    n_target = max(args.min, int(round(n_total * args.pct / 100)))

    rng = random.Random(args.seed)

    # Strata: include ALL low-confidence rows, then random-sample the rest until target.
    low = [r for r in rows if r.get("confidence") == "low"]
    rest = [r for r in rows if r.get("confidence") != "low"]
    rng.shuffle(rest)
    chosen = list(low)
    for r in rest:
        if len(chosen) >= n_target:
            break
        chosen.append(r)
    # Stable order in output by posting_id for diffing across reviews.
    chosen.sort(key=lambda r: r["posting_id"])

    pct = (len(chosen) / n_total * 100) if n_total else 0.0
    header = f"""# Spot-check sample — 2026-Q2 capture

Methodology v0.1.2 requires a ≥15% random sample to be human-reviewed before
analysis output is published. If sample agreement is below 95%, the extractor
prompt is corrected and the extract pass is re-run.

**Sample size:** {len(chosen)} of {n_total} ({pct:.1f}%)
**Seed:** {args.seed} (deterministic; re-running this script with the same seed
produces the same sample)
**Includes all low-confidence rows:** yes (oversampled to {len(low)})

## How to use

For each row below, read the source paragraph then check whether each LLM
classification is correct. Tick the boxes if so. If anything is wrong, leave
the box unchecked and write a note inline — that's the audit trail.

Tally at the bottom drives the agreement %.

---
"""
    blocks = [render_row(r, i + 1, len(chosen)) for i, r in enumerate(chosen)]
    footer = """## Tally

- Total rows reviewed: ___ / {n}
- Rows with all fields correct: ___ / {n}
- Agreement: ___ % (target ≥95%)
- Reviewer: ___
- Date: ___
""".format(n=len(chosen))

    out_path = capture / "spot-check.md"
    out_path.write_text(header + "\n".join(blocks) + footer, encoding="utf-8")
    print(f"Wrote {len(chosen)} sample rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
