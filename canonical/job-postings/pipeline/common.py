"""Shared helpers across the pipeline modules.

Keep this module tiny. Anything that grows past a couple of helpers should move
to its own module — common.py is for things genuinely shared across stages
(paths, posting-id hashing, JSONL I/O, the captured row schema).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator


# ---- Paths ----

PIPELINE_DIR = Path(__file__).resolve().parent
# Default: ../captures/<current-quarter>. Overridable via env CAPTURE_DIR for tests / replays.
DEFAULT_CAPTURE_DIR = PIPELINE_DIR.parent / "captures" / "2026-q2"


def capture_dir() -> Path:
    """Resolve the active capture directory. Honors $CAPTURE_DIR; falls back to 2026-q2."""
    raw = os.environ.get("CAPTURE_DIR")
    if raw:
        return Path(raw).resolve()
    return DEFAULT_CAPTURE_DIR.resolve()


def raw_dir() -> Path:
    p = capture_dir() / "raw"
    p.mkdir(parents=True, exist_ok=True)
    return p


def filtered_dir() -> Path:
    p = capture_dir() / "filtered"
    p.mkdir(parents=True, exist_ok=True)
    return p


def extracted_dir() -> Path:
    p = capture_dir() / "extracted"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---- Posting IDs ----

def posting_id(source_url: str, posting_date: str | None = None) -> str:
    """Stable hash for deduping postings across re-runs.

    Inputs: canonical source URL + ISO date (if known). 12 hex chars is plenty
    given expected row counts under a few thousand per quarter.
    """
    h = hashlib.sha1()
    h.update(source_url.encode("utf-8"))
    if posting_date:
        h.update(b"\x00")
        h.update(posting_date.encode("utf-8"))
    return h.hexdigest()[:12]


# ---- JSONL I/O ----

def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True))
            f.write("\n")
            n += 1
    return n


def append_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True))
            f.write("\n")
            n += 1
    return n


# ---- Row schema (methodology §Extraction schema) ----

# Enum domains. Kept in code so the LLM extractor prompt and the spot-check
# scripts both pull from one source. Update here if the methodology taxonomy
# grows.

SOURCES = ("hn_whoishiring", "builtin", "wellfound")  # `linkedin` reserved, not used at v0.1.2.

COMPANY_SIZE_BANDS = ("50-100", "100-250", "250-500-conditional", "unknown")

COMPANY_STAGE_SIGNALS = (
    "series-a", "series-b", "series-c", "bootstrapped", "mid-market", "unknown",
)

INDUSTRIES = (
    "saas", "fintech-software", "ecommerce-platform", "marketplace",
    "healthtech-software", "edtech", "devtools", "fintech-regulated", "other",
)

ROLE_TITLES_NORMALIZED = (
    "data_engineer",
    "analytics_engineer",
    "data_platform_engineer",
    "mle_with_data_focus",
    "data_architect_handson",
)

SENIORITIES = ("mid", "senior", "staff")

GEOS = ("us", "canada", "uk", "eu", "remote_us_hq", "remote_eu_hq")

# Component taxonomy: category -> tuple of instances.
COMPONENT_TAXONOMY: dict[str, tuple[str, ...]] = {
    "cloud_platform": ("aws", "gcp", "azure", "multicloud"),
    "warehouse": (
        "snowflake", "bigquery", "redshift", "databricks", "athena", "duckdb",
        "postgres_as_warehouse", "clickhouse", "motherduck",
    ),
    "open_table_format": ("iceberg", "delta", "hudi", "parquet_only"),
    "transformation": (
        "dbt_core", "dbt_cloud", "sqlmesh", "dataform", "dagster_assets_python",
        "custom_python",
    ),
    "orchestration": (
        "airflow", "mwaa", "dagster", "prefect", "temporal",
        "dbt_cloud_scheduler", "step_functions", "cron_or_homegrown",
    ),
    "ingestion_elt": (
        "fivetran", "airbyte_oss", "airbyte_cloud", "meltano", "stitch", "hevo",
        "custom_python", "singer_taps",
    ),
    "cdc": ("debezium", "dms", "fivetran_cdc", "airbyte_cdc", "kafka_connect"),
    "streaming": ("kafka", "msk", "kinesis", "pubsub", "confluent_cloud", "redpanda", "none"),
    "bi": (
        "looker", "tableau", "powerbi", "metabase", "lightdash", "mode", "sigma",
        "hex", "preset_superset", "omni",
    ),
    "reverse_etl": ("hightouch", "census", "polytomic", "custom"),
    "semantic_layer": ("dbt_semantic_layer", "cube", "metricflow", "looker_lookml", "none"),
    "catalog_governance": (
        "openmetadata", "datahub", "atlan", "collibra", "unity_catalog",
        "dbt_docs_only", "none",
    ),
    "observability_dq": (
        "dbt_tests", "elementary", "re_data", "monte_carlo", "bigeye", "soda",
        "great_expectations", "acceldata", "none",
    ),
    "iac": ("terraform", "cdk", "pulumi", "cloudformation", "none_explicit"),
    "cicd": ("github_actions", "gitlab_ci", "circleci", "jenkins", "dbt_cloud_ci"),
    "experiment_tracking": ("mlflow", "weights_and_biases", "neptune", "dvc", "none"),
    "model_serving": (
        "sagemaker", "vertex_ai", "modal", "bentoml", "seldon", "kserve",
        "custom_fastapi", "cloud_run",
    ),
    "vector_db": (
        "pgvector", "pinecone", "weaviate", "qdrant", "chroma", "opensearch", "elasticsearch",
    ),
    "llm_provider": (
        "openai", "anthropic", "bedrock", "azure_openai", "vertex_genai",
        "together", "groq", "cohere",
    ),
    "rag_framework": ("langchain", "llamaindex", "haystack", "none_explicit"),
    "ml_eval": (
        "ragas", "deepeval", "langsmith", "arize", "evidently", "whylabs", "custom",
    ),
}


@dataclass(frozen=True)
class Posting:
    """Convenience accessor for partially-filled posting dicts.

    Stages mutate dicts directly (cheaper, clearer in JSONL), but this dataclass
    is handy for type-checked reads in spot-checks and aggregations.
    """
    posting_id: str
    source: str
    source_url: str
    captured_date: str
    posting_date: str | None
    raw_text: str
    included: bool | None = None
    exclude_reason: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Posting":
        return cls(
            posting_id=d["posting_id"],
            source=d["source"],
            source_url=d["source_url"],
            captured_date=d["captured_date"],
            posting_date=d.get("posting_date"),
            raw_text=d["raw_text"],
            included=d.get("included"),
            exclude_reason=d.get("exclude_reason", ""),
        )


def today_iso() -> str:
    return date.today().isoformat()
