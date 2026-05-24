# Stack #1 — implementation plan

**Version:** v0.1
**Date:** 2026-05-17
**Status:** Living plan. Updates as slices ship and the exit criteria below either hold or get sharpened. v0.2 lands at the first scheduled review point (end of Slice 1).

---

## What this plan is

The sequencing doc for Stack #1 (AWS lake-first OSS — S3 + Athena + Postgres + dbt-core + Airflow on Fargate + OpenMetadata). Lists vertical slices in dependency order, names the canonical task-set tasks each slice closes, queues the ADRs that get drafted alongside, and pins the exit criterion for each slice.

The publication threshold for stem promotion (per CLAUDE.md: "ingestion + transformation + orchestration + one observability hook + a populated catalog producing validated numbers from the synthetic dataset") is marked explicitly at the slice where it lands.

This plan is the IDE-context bridge: opening this in Cursor (with the canonical specs and ADR-001) is meant to be the same as opening a project brief at the start of a build sprint. If a slice's scope creeps, this plan is the doc that gets edited first.

## What this plan is *not*

- Not a Gantt chart. Slice durations are rough; the cadence target is "Stack #1 in 4–5 weeks" (CLAUDE.md) and quality is the rate limiter, not calendar time.
- Not a substitute for the canonical task set. Tasks are referenced by number (e.g., 1.2, 4.7); their full text lives in `canonical/task-set.md`.
- Not a substitute for ADRs. Every load-bearing decision named below gets its own ADR drafted alongside the implementation slice that surfaces it. The slice ships an implementation; the ADR ships the argument.
- Not final on scope below the slice level. Each slice has an exit criterion; everything else inside the slice can be reordered as Justin works through the implementation.

## Vertical slice order

| # | Slice | Canonical tasks closed | New ADRs drafted alongside | Publication threshold |
|---|---|---|---|---|
| 1 | Foundation: Terraform, CI, synthetic data generator | (prerequisite for everything below) | ADR-002 (Terraform), ADR-003 (synthetic data generator) | — |
| 2 | Ingestion | 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 | ADR-004 (Airbyte vs Meltano vs custom Python) | — |
| 3 | Storage & modeling | 2.1, 2.2, 2.3, 2.4, 2.5, 2.6 | — (medallion conventions land in slice; ADR only if a real fork surfaces) | — |
| 4 | Transformation | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7 | — (dbt-core is locked; conventions emerge in code) | — |
| 5 | Orchestration | 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7 | ADR-001 flips Proposed → Accepted; ADR-005 (Airflow on Fargate flavor) | **Publication threshold met** when slices 1–5 + one slice-7 hook + slice-8 catalog reach validated S-scale numbers. |
| 6 | Serving & activation | 5.1, 5.2, 5.3, 5.4, 5.5, 5.6 | ADR-006 (BI tool — Metabase vs Lightdash) | — |
| 7 | Observability & data quality | 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7 | ADR-007 (Elementary vs re_data) | One hook (likely 6.1 source freshness or 6.2 volume anomaly) lands as part of the publication threshold; full slice closes later. |
| 8 | Governance — catalog, lineage, access | 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8 | ADR-008 (OpenMetadata vs alternatives — confirms the lock in stack-01 README) | A populated catalog (7.1) lands as part of the publication threshold; full slice closes later. |
| 9 | ML & AI enablement | 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7 | ADR-009 (experiment tracking + registry), ADR-010 (vector DB), possibly more | Out of the publication threshold for Stack #1; lands in the Stack-#1 second-pass after the first posts drop. |

Operations / CI/CD (canonical category 8) is cross-cutting and built incrementally inside each slice. It isn't its own slice; pieces land throughout.

The publication threshold marker matters because it gates when `posts/drafts/` stems get promoted to `posts/`. The build-first sequencing locked 2026-05-11 says: no posts until Stack #1 is substantially complete. That bar is met at the end of slice 5 plus the slice-7 and slice-8 hooks named above.

---

## Slice 1 — Foundation

**Status (2026-05-22): generator build plan written** at `canonical/synthetic-dataset-build-plan.md` (proposed tech choices, build order, test approach). No generator code committed yet — implementation happens in this slice, in the IDE. Pending in this slice: synthetic data generator implementation, Terraform backbone, AWS account scaffolding, VPC/networking, RDS, CI/CD skeleton.

**Scope.** Stand up the project's infrastructure baseline and the synthetic data generator. Nothing in this slice answers a canonical task on its own; everything below depends on this slice working.

**Components landing:**

- **Terraform backbone.** Remote state in an S3 bucket + DynamoDB lock table (bootstrapped manually once, then managed by Terraform). Root module + `modules/` directory for reusable components. Provider pinning, version constraints, `terraform fmt` and `tflint` in CI.
- **AWS account scaffolding.** IAM roles for the build user, for Airflow, for dbt, for Athena, for Glue. Per-environment AWS profiles or assumed-role pattern. KMS keys for at-rest encryption. CloudTrail enabled.
- **VPC + networking.** A small VPC with public + private subnets, NAT gateway if needed (cost note: NAT is $32/mo; eval whether VPC endpoints to S3/STS/SecretsManager remove the need). Security groups for RDS, Fargate, OpenMetadata.
- **RDS Postgres (small instance).** Shared between Stack #1's operational source-system simulator (the synthetic dataset's "operational Postgres source-of-truth" per `canonical/synthetic-dataset.md`) and the Airflow metadata DB. Schema-separated. ADR-005 documents the shared-DB tradeoff.
- **Synthetic data generator.** Implements the spec at `canonical/synthetic-dataset.md`. Lives at `canonical/synthetic-data/` (sibling to the spec). Python + Faker (or mimesis — call deferred to slice and documented in ADR-003) + deterministic PRNG. Generates the five source surfaces (operational Postgres mutations, HubSpot JSONL, Stripe JSONL, first-party events NDJSON, partner CSV) + the document corpus + held-out eval sets at S scale first; M/L scales validated at slice exit.
- **CI/CD skeleton.** GitHub Actions workflows: Terraform plan on PR, Terraform apply on merge to main behind a manual approval gate, Python lint/format/tests on PR, dbt slim CI scaffolding (filled in slice 4).
- **Pre-commit hooks.** `terraform fmt`, `tflint`, `ruff`, `mypy --strict` (or a softer initial bar — decided at slice-1-time).
- **Secrets management.** AWS Secrets Manager for runtime secrets; GitHub Encrypted Secrets for CI; `.env.example` committed.

**ADRs drafted alongside:**

- **ADR-002 — Terraform across all stacks.** The decision was locked 2026-05-10; the ADR text writes alongside the first non-trivial Terraform module. Alternatives section names CDK, Pulumi, OpenTofu, CloudFormation. Hiring-data anchor: Terraform 60–70%+ of buyer-profile postings vs CDK in single digits.
- **ADR-003 — synthetic data generator language and framework.** Python + which-library, the deterministic-seed contract enforcement, the spec's open questions (mimesis vs Faker, static-files vs mock HTTP server, PII-injection catalogue) resolved here. The implementation is real before this ADR finalizes.

**Files that land (illustrative; final layout decided at implementation):**

```
terraform/
  main.tf
  backend.tf
  variables.tf
  outputs.tf
  modules/
    vpc/
    rds/
    s3-data-lake/
    iam/
    secrets/
canonical/synthetic-data/
  __init__.py
  generator/
  cli.py
  pyproject.toml
  tests/
.github/workflows/
  terraform-plan.yml
  python-tests.yml
  pre-commit.yml
.pre-commit-config.yaml
.env.example
```

**Exit criterion.** Running `terraform apply` from a clean clone with appropriate AWS credentials stands up the foundation. Running the generator CLI emits S-scale output to a configured S3 bucket and an idempotent local directory; M scale runs without error in under 15 minutes on a laptop. Two regenerations with the same seed produce byte-identical MANIFEST hashes per the determinism contract in `canonical/synthetic-dataset.md`. `terraform destroy` returns the account to a clean state.

---

## Slice 2 — Ingestion

**Scope.** Land the synthetic data generator's output into the lake's raw zone via the ingestion patterns canonical category 1 specifies.

**Components landing:**

- **Postgres → lake (CDC) — canonical 1.2.** Either AWS DMS (managed; simpler ops) or Debezium running as a Fargate task (more authentic to the test bench's "OSS where defensible" framing). Lands change events into `s3://.../raw/cdc/event_date=YYYY-MM-DD/`. ADR-004 names the call.
- **HubSpot REST ingestion — canonical 1.1.** Pulls the generator's HubSpot-shaped JSONL fixtures. Validates the ingestion path against paginated REST. Airbyte OSS connector if available, else custom Python in an Airflow task. Lands into `s3://.../raw/hubspot/<resource>/event_date=...`.
- **Stripe REST ingestion — canonical 1.1.** Same shape, Stripe-flavored.
- **First-party events ingestion — canonical 1.3.** Reads the generator's NDJSON output, applies bot/duplicate filtering, lands into `s3://.../raw/events/event_date=.../`. Late-arrival handling deferred to slice 3 (medallion structure handles the "land then reconcile" pattern).
- **Partner CSV ingestion — canonical 1.4.** S3 EventBridge → Lambda or Airflow file sensor → validation → land into raw zone or quarantine zone. Bad files surface to an operator-friendly error channel.
- **Document corpus ingestion — canonical 1.6.** Land the generator's document corpus into `s3://.../raw/docs/` with metadata captured for downstream chunking and embedding (slice 9). Refresh-on-source-change pattern documented.
- **Vendor-outage recovery scenario — canonical 1.5.** Simulate a 6-hour outage by pausing the SaaS ingestion DAGs and verifying replay-from-cursor works without duplication when they resume.

**ADRs drafted alongside:**

- **ADR-004 — Ingestion: Airbyte OSS vs Meltano vs custom Python.** Per-source rationale. Probably ends as a mix (Airbyte for the SaaS sources where its connector library is strong; custom Python for the file-drop and the events stream). Hiring-data anchor: Airbyte and Fivetran dominate managed/OSS; Meltano is a long-tail mention in 2026-Q2.

**Exit criterion.** All five source surfaces from `canonical/synthetic-dataset.md` land in the raw zone for an S-scale dataset, with the partition conventions named below. The vendor-outage scenario (1.5) replays correctly. Quarantine for malformed partner CSVs writes to a designated bad-files prefix with the operator surface (CloudWatch log group or SNS topic) configured.

---

## Slice 3 — Storage & modeling

**Scope.** Land the medallion layering on top of the raw zone, partition convention, and the storage-tier policy.

**Components landing:**

- **Bronze / silver / gold layering — canonical 2.1.** Layer responsibilities documented in `stacks/stack-01-athena/README.md` (or a sibling `MODELING.md`). Bronze = raw landed format preserved; Silver = cleaned/conformed/Parquet/partitioned; Gold = business-grade marts.
- **Partition convention — canonical 2.2.** Date-first for high-volume events; tenant-second for multi-tenant readiness even though the synthetic data is single-tenant. Validated by measuring query-pruning savings on a representative Athena query.
- **Glue catalog tables.** Bronze and Silver tables registered as external tables in Glue. Athena queries them.
- **Schema evolution — canonical 2.3.** Column add, column rename with backfill, type narrowing. Iceberg or Hive-style — call gets made here and documented (likely Iceberg for the schema-evolution and time-travel benefits, but the implementation cost and Athena Iceberg engine version need verification at slice-3-time).
- **SCD Type 2 — canonical 2.4.** Implemented on `accounts` or `users` from the synthetic dataset, including the retroactive correction case the generator deliberately seeds (the plans-table mid-year price-correction).
- **Late-arriving facts — canonical 2.5.** 30-day-late event correctness.
- **Storage tiering — canonical 2.6.** S3 lifecycle policies move cold partitions to Glacier / IA after a defensible window. Measured cost savings documented.

**ADRs drafted alongside.** Iceberg vs Parquet-only-tables is the one that could surface a real ADR; number allocated at draft time. If the call falls cleanly toward Iceberg without genuine fork, an ADR isn't required and the choice gets documented in the modeling README.

**Exit criterion.** All canonical category-2 tasks pass against the S-scale dataset. Athena queries against Silver and Gold tables run within the cost-test rough bands named in `canonical/task-set.md` section 2.

---

## Slice 4 — Transformation

**Scope.** Stand up the dbt-core project, model the medallion layers, write the tests, ship the docs.

**Components landing:**

- **dbt project structure.** `dbt/` directory under `stacks/stack-01-athena/`. Profiles via environment variables. `dbt_project.yml`, packages.yml, profiles.yml template.
- **Sources, staging, marts.** Sources declared with freshness; staging models clean and conform; marts implement the Gold-tier business logic.
- **Incremental fact model — canonical 3.1.** Events fact table, incremental on `event_date`, with merge logic for late-arriving events.
- **Full-refresh dimension model — canonical 3.2.** A small dim (e.g., `dim_plans`) rebuilt every run; idempotent.
- **Snapshot — canonical 3.3.** dbt snapshot on HubSpot deals (or accounts) for point-in-time correctness.
- **Tests on Gold tier — canonical 3.4.** Source freshness, uniqueness, not-null, accepted-values, custom relationship tests. Every Gold model has the full suite.
- **Macros / abstraction reuse — canonical 3.5.** At least one reusable pattern (audit columns, currency conversion).
- **Docs — canonical 3.6.** Column-level YAML docs on every Gold model; `dbt docs generate` ships to an S3-hosted static site.
- **Feature engineering as transformation — canonical 3.7.** A `user_features` model with 30-day rolling activity, recency, monetary aggregates. Point-in-time correctness mechanism: `valid_from` / `valid_to` columns + window functions that filter on `<= as_of_date`. Demonstrates leakage protection without leaving SQL.

**ADRs drafted alongside.** None expected — dbt-core is locked, conventions emerge in code. If a real fork surfaces (e.g., dbt-Python vs Athena Python UDFs for the feature pipeline), draft an ADR at the time; number allocated at draft time.

**Exit criterion.** All canonical category-3 tasks pass. The validation query suite from `canonical/synthetic-dataset.md` (Q1–Q15) runs against the Gold models on the S-scale dataset and matches the reference implementation within tolerance. dbt docs site is live.

---

## Slice 5 — Orchestration

**Scope.** Wire the ingestion, transformation, and downstream slices together into Airflow DAGs on Fargate. This is where ADR-001's hypotheses about Fargate-Airflow cost, scheduler stability, and DAG ergonomics get tested in practice.

**Components landing:**

- **Airflow on Fargate — ADR-001 implementation.** Scheduler + webserver as long-running Fargate services behind an ALB. Workers as on-demand Fargate tasks (Celery executor or KubernetesExecutor-on-Fargate — call decided at slice time and documented in ADR-005). Metadata DB on the shared RDS Postgres from slice 1.
- **Cross-domain DAG — canonical 4.1.** End-to-end: ingestion → dbt build → publish to BI. Single DAG or coordinated DAGs with cross-DAG dependencies; ergonomics call documented.
- **Retry policy — canonical 4.2.** Exponential backoff, dead-letter handling.
- **Backfill — canonical 4.3.** 90 days of a partitioned model after a fix, parametrized.
- **Partial recovery — canonical 4.4.** Mid-DAG failure leaves clean state; rerun re-executes only failed + downstream.
- **SLA / freshness alerts — canonical 4.5.** "Fact table fresh by 9am ET." Alerts fire on miss, don't fire on success.
- **Runbook — canonical 4.6.** One-page on-call doc.
- **Heterogeneous-asset DAG — canonical 4.7.** SQL transformation → Python feature step → model training → batch inference. **The expected-awkward slice in Airflow's idiom** — ADR-001's hypothesis. Implementation surfaces are the operator notes that flip ADR-001 to Accepted.

**ADRs drafted alongside:**

- **ADR-001 flips Proposed → Accepted.** Consequences section updated with operator notes; "Hypotheses to validate" section becomes "Validated findings" with the real cost number, scheduler-stability observations, and 4.7 ergonomics writeup.
- **ADR-005 — Airflow on Fargate, flavor and operational shape.** Executor choice, image build, secrets injection, log surface, scaling pattern. Includes the shared-DB-with-source-simulator tradeoff (raised in ADR-001) and how it landed in practice.

**Exit criterion.** All canonical category-4 tasks pass. The full DAG runs against the S-scale dataset, ingests → transforms → produces Gold layer → triggers downstream notifications. Backfill of 30 days completes in a measurable time. ADR-001 flips to Accepted. **The publication threshold is now within one or two slice-hook commits of being met.**

---

## Slice 6 — Serving & activation

**Scope.** Make the Gold layer usable to humans (BI), machines (API), and operational systems (reverse ETL).

**Components landing:**

- **BI tool — canonical 5.1.** Metabase or Lightdash, against Athena. Three dashboards: revenue, product engagement, customer health. ADR-006 names the choice.
- **Semantic layer — canonical 5.2.** Lightdash's native semantic layer if Lightdash wins ADR-006; dbt Semantic Layer or Cube otherwise. MRR / WAU / NDR defined once.
- **Reverse ETL — canonical 5.3.** Customer-health-score sync to a stubbed HubSpot receiver (the synthetic HubSpot emulation accepts upserts). Hightouch, Census, or custom Python — likely custom for cost discipline at this stack; documented.
- **API exposure — canonical 5.4.** FastAPI service on Fargate returning a daily revenue rollup. Basic auth, rate limiting via API Gateway in front, OpenAPI spec.
- **Freshness contract — canonical 5.5.** Every served asset has a documented SLA visible in the dashboard chrome or the BI tool's data dictionary.
- **Self-service exploration — canonical 5.6.** Analyst-shaped dashboard layer that doesn't require touching raw tables.

**ADRs drafted alongside.** ADR-006 (BI tool).

**Exit criterion.** All canonical category-5 tasks pass. A new analyst (or Justin in analyst mode) can answer "what's the funnel for this campaign?" using the BI tool against the Gold layer alone.

---

## Slice 7 — Observability & data quality

**Scope.** Stand up the observability layer for data assets; one hook lands earlier to clear the publication threshold.

**Early hook (lands before publication threshold):** **canonical 6.1 — source freshness monitoring.** dbt source freshness checks fire on missed SLAs, route into a Slack channel or PagerDuty stub. This single hook clears the "one observability hook" piece of the publication threshold; the rest of category 6 lands here.

**Components landing (full slice):**

- **Volume anomaly — canonical 6.2.** Row-count anomalies via Elementary or re_data.
- **Schema drift — canonical 6.3.** Source column drop or retype detected before downstream breaks. The synthetic data generator's deliberately-seeded partner-CSV schema-drift (per `canonical/synthetic-dataset.md`) is the test fixture.
- **Value distribution — canonical 6.4.** Custom test flags a 50% MoM conversion-rate drop.
- **Alert routing tiers — canonical 6.5.** Page / ticket / silent-log. One of each demonstrated.
- **Incident postmortem template — canonical 6.6.** A real template the team would use.
- **Model output and input drift — canonical 6.7.** Deferred to alongside slice 9 (since it needs a deployed model to monitor). The infrastructure (alert routing into the same tier system) lands here; the model-specific checks land in slice 9.

**ADRs drafted alongside.** ADR-007 — Elementary vs re_data. Hiring-data note: Elementary leads in 2026-Q2 captures.

**Exit criterion.** All canonical category-6 tasks except 6.7 pass against the S-scale dataset and the deliberately-seeded bad-data scenarios.

---

## Slice 8 — Governance — catalog, lineage, access

**Scope.** Stand up OpenMetadata self-hosted; populate it via ingestion connectors against the lake, the dbt project, and the Airflow DAGs. One catalog hook lands earlier to clear the publication threshold.

**Early hook (lands before publication threshold):** **canonical 7.1 — catalog ingest.** OpenMetadata stood up, dbt models ingested, every Gold table appears with description, owner, last-updated, source-link. This single hook clears the "populated catalog" piece of the publication threshold.

**Components landing (full slice):**

- **OpenMetadata deployment.** Self-hosted on Fargate or EC2 (cost-vs-ergonomics call documented). Backed by RDS Postgres or a small dedicated DB (separated from Airflow metadata DB to avoid cross-system blast radius — call documented).
- **Column-level lineage — canonical 7.2.** Via dbt + OpenMetadata's dbt integration.
- **Business glossary — canonical 7.3.** Ten core terms — MRR, ARR, WAU, etc. — linked to canonical implementations.
- **PII tagging — canonical 7.4.** Source columns tagged; downstream models inherit via convention or dbt meta propagation.
- **Role-based access — canonical 7.5.** Three personas across IAM + dbt + Athena workgroup configs.
- **Access request flow — canonical 7.6.** Documented path under one business day.
- **Audit trail — canonical 7.7.** CloudTrail + Athena query log + dbt-Cloud-CI-or-equivalent stitched together.
- **Model lineage — canonical 7.8.** Lands alongside slice 9.

**ADRs drafted alongside.** ADR-008 — OpenMetadata self-hosted vs DataHub vs Atlan vs dbt-docs-only. The choice is locked at the stack-01 README; the ADR confirms it against the implementation experience.

**Exit criterion.** All canonical category-7 tasks except 7.8 pass against the S-scale stack.

---

## Slice 9 — ML & AI enablement

**Scope.** Stand up the lone-data-scientist productivity surface — experiment tracking, model registry, batch + lightweight online inference, LLM/RAG pipeline. **Out of the publication threshold for Stack #1** — the first posts drop before this slice ships.

**Components landing:**

- **Notebook-to-production handoff — canonical 9.1.**
- **Feature pipeline operations — canonical 9.2.** Point-in-time correctness for training-dataset assembly. Reuse pattern documented.
- **Experiment tracking + model registry — canonical 9.3.** MLflow self-hosted (test bench reference per assessment tool).
- **Batch inference — canonical 9.4.** Churn-risk classifier deployed as scheduled batch via Airflow Python task. Predictions land in Gold layer.
- **Lightweight online inference — canonical 9.5.** FastAPI on Fargate serving a single model. p50/p95 documented. **Capped at single-digit QPS sustained** per task-set 9.5 explicit cap.
- **LLM/RAG pipeline — canonical 9.6.** Chunk → embed → vector store → retrieve → call hosted LLM → return. Retrieval-quality eval against the synthetic dataset's held-out retrieval-eval set. Generation eval against the rubrics from `canonical/synthetic-dataset.md`.
- **LLM cost + latency observability — canonical 9.7.** Token usage, per-call cost broken down by template + consumer, latency tracked into the same observability surface as data pipelines.
- **Model output and input drift — canonical 6.7.** Lands here since it needs a deployed model.

**ADRs drafted alongside:**

- **ADR-009 — Experiment tracking + model registry: MLflow self-hosted vs W&B managed vs Vertex/SageMaker built-ins.**
- **ADR-010 — Vector DB: pgvector on Postgres vs Pinecone vs alternatives.** Cost-vs-throughput tradeoff at the anchor buyer's scale.
- Possibly a RAG-framework ADR (LangChain vs LlamaIndex vs raw orchestration) if the choice is a real fork; number allocated at draft time.

**Exit criterion.** All canonical category-9 tasks pass at S scale. Validation against the held-out retrieval and generation eval sets in `canonical/synthetic-dataset.md` produces measurable numbers.

---

## What this plan defers

- **M and L scale measurements per slice.** Each slice ships at S scale; M and L scale runs land in a sweep at the end of Stack #1, partly because cost discipline requires running L only when it's about to produce a real number worth keeping. CLAUDE.md's cost target ($50–150/mo most months, $200–300 during measurement windows) is the governing constraint.
- **Cross-stack comparison.** Comparison writeups (e.g., Stack #1 vs Stack #2 lake-first-vs-Snowflake at the AWS slice) land only when Stack #2 has shipped and run the same canonical task set. Stack #1's writeups are single-stack ADRs and operational notes until then.
- **Assessment tool cost-claim locks.** The assessment tool v0.1's TBD-pending-Stack-#N markers don't all lock with Stack #1. Lake-first cost number locks here; the AWS-warehouse comparison locks at Stack #2; cross-cloud comparisons lock at Stack #3+.
- **Posts.** Drafts accrete in `posts/drafts/` (gitignored) during this plan. Promotion to `posts/` happens after the publication threshold is met (end of slice 5 + slice 7 hook + slice 8 hook). Stem-05 (Stack #1 progress series) is the natural first promotion candidate.

## Review points

- **End of slice 1.** Plan v0.2 published. The foundation reveals what's premature in this v0.1 (e.g., a slice that should have been split, an ADR that didn't need to exist, a piece that needs to land earlier).
- **End of slice 5 (publication threshold).** Plan v0.3. The post window opens. Stem promotion sequence decided.
- **End of Stack #1.** Plan retired as a sequencing doc. Becomes the reference for Stack #2's parallel plan.

## Working with this plan in an IDE

When opening this repo in Cursor (or another AI IDE) for Stack #1 implementation, the load-bearing context files are:

1. `CLAUDE.md` — strategic frame, working-style rules, project state. Read first.
2. `canonical/task-set.md` — what to build.
3. `canonical/synthetic-dataset.md` — what data to build against.
4. `canonical/assessment-tool.md` — why the choices.
5. `adrs/ADR-001-orchestrator-strategy.md` — Airflow at Fargate, rationale and hypotheses.
6. `stacks/stack-01-athena/README.md` — Stack #1 component lockfile.
7. **This file** — slice order and exit criteria.

ADRs that get drafted alongside slices live in `adrs/` (cross-cutting: 002, 003) or `stacks/stack-01-athena/adrs/` (stack-specific: 004 onward).
