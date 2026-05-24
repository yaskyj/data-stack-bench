# Stack #1 — AWS lake-first OSS

**Status:** Scoped. Implementation has not started. Unblocked: orchestrator call locked 2026-05-12 (Airflow); ADR-001 drafted at Proposed status ([`../../adrs/ADR-001-orchestrator-strategy.md`](../../adrs/ADR-001-orchestrator-strategy.md)) — sharpens with operator notes and flips to Accepted during implementation; synthetic dataset spec v0.1 drafted 2026-05-13 ([`../../canonical/synthetic-dataset.md`](../../canonical/synthetic-dataset.md)); assessment tool v0.1 drafted 2026-05-15 ([`../../canonical/assessment-tool.md`](../../canonical/assessment-tool.md)); implementation plan drafted 2026-05-17 ([`plan.md`](plan.md)).

**Where to start.** Read [`plan.md`](plan.md) — vertical-slice order, canonical tasks closed per slice, ADRs queued alongside each slice, exit criteria. The plan is the IDE-context bridge for opening this stack in Cursor.

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
| Orchestration | Airflow (self-hosted on Fargate) | Locked 2026-05-12; ADR-001 drafted at Proposed, sharpens during implementation |
| Ingestion | Airbyte or Meltano + custom Python | Pending |
| Catalog / lineage | OpenMetadata (self-hosted) | Locked |
| Observability | dbt tests + Elementary or re_data | Pending |
| BI | Metabase or Lightdash | Pending |
| CI/CD | GitHub Actions | Locked |

## Cost target

$50–150/mo at full operation, with disciplined spin-down between measurement windows. S3 is pennies; Athena is pennies-to-dollars per query; small RDS Postgres is $15–30/mo; OpenMetadata self-hosted is $15–30/mo if 24/7. Full teardown + clean re-spinup is a hard requirement and will be CI-validated.

## What this stack tests against the canonical task set

All nine functional categories. See [`../../canonical/task-set.md`](../../canonical/task-set.md) for the task definitions and [`../../canonical/synthetic-dataset.md`](../../canonical/synthetic-dataset.md) for the dataset shapes, reference scales (S/M/L), and validation query suite this stack must answer to within tolerance.

## Per-stack ADRs

Stack-specific ADRs live in `adrs/` under this directory once they are written. Cross-cutting ADRs (orchestrator pick, IaC choice, anything that applies to multiple stacks) live in [`../../adrs/`](../../adrs/).
