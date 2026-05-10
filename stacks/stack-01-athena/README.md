# Stack #1 — AWS lake-first OSS

**Status:** Scoped. Implementation has not started. Orchestrator decision (ADR-001) is the immediate blocker.

## Shape

The pragmatic anchor stack — first to ship because it's the cheapest to keep running long-term and the most aligned with the project's <$100/mo cost discipline. **Not** the unique-angle stack; the credibility of the project comes from comparison across the lineup, not from this stack on its own.

| Component | Choice | Status |
|---|---|---|
| Cloud | AWS | Locked |
| IaC | Terraform | Locked (cross-stack standard) |
| Lake | S3 + Parquet | Locked |
| Transactional source | Postgres (RDS) | Locked |
| Lake-side query | Athena | Locked |
| Transformation | dbt-core | Locked |
| Orchestration | Airflow / Dagster / Prefect | Pending ADR-001 |
| Ingestion | Airbyte or Meltano + custom Python | Pending |
| Catalog / lineage | OpenMetadata (self-hosted) | Locked |
| Observability | dbt tests + Elementary or re_data | Pending |
| BI | Metabase or Lightdash | Pending |
| CI/CD | GitHub Actions | Locked |

## Cost target

$50–150/mo at full operation, with disciplined spin-down between measurement windows. S3 is pennies; Athena is pennies-to-dollars per query; small RDS Postgres is $15–30/mo; OpenMetadata self-hosted is $15–30/mo if 24/7. Full teardown + clean re-spinup is a hard requirement and will be CI-validated.

## What this stack tests against the canonical task set

All nine functional categories. See [`../../canonical/task-set.md`](../../canonical/task-set.md) for the task definitions.

## Per-stack ADRs

Stack-specific ADRs live in `adrs/` under this directory once they are written. Cross-cutting ADRs (orchestrator pick, IaC choice, anything that applies to multiple stacks) live in [`../../adrs/`](../../adrs/).
