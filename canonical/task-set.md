# Canonical Task Set v0.2
## A comparative benchmark specification for modern data stacks

**Version:** 0.2 (draft)
**Date:** 2026-05-10
**Status:** Living document. v1.0 lands after Stack #1 ships end-to-end.

---

## What "modern analytics architecture expertise" means

The cleanest definition of the practice this benchmark is built to test, written tight enough to use in podcast bios, consulting copy, and the top of the GitHub README.

**One-line version.** Modern analytics architecture is the end-to-end data infrastructure that lets a Series A through mid-market company answer business questions, drive its operating systems, and run a small ML/AI practice — built on the cloud-native, open-source-first stacks that dominate the post-2020 hiring market.

**What that includes.** The full data lifecycle for the anchor buyer: ingestion (batch, CDC, first-party events, partner files), durable lake/warehouse/lakehouse storage, versioned transformation (SQL plus light Python), orchestration with reliability guarantees, BI exposure, reverse ETL, observability and data quality, catalog and lineage, and role-based access. ML/AI enablement scoped to a lone data scientist: feature pipelines built on top of the analytics stack, lightweight batch and online model serving, experiment tracking and model registry, LLM/RAG integration patterns, and a workable notebook-to-production path. The cross-cutting infrastructure that makes all of the above shippable: IaC, CI/CD, cost engineering, secrets management, environment isolation.

**What's adjacent but not the focus.** Real-time analytics below ~minute latency. Enterprise governance at federation scale. Domain-specific compliance regimes (HIPAA, FedRAMP, regulated trading). I have opinions on all three; they aren't where the test bench plays.

**What's explicitly out of scope.** ML platform engineering at production scale (custom training infrastructure, GPU clusters, multi-tenant model serving, full feature stores like Tecton at production parity). High-QPS real-time inference. Streaming-first architectures where the lake is downstream of Kafka rather than parallel to it. Database administration of source systems. Customer-facing embedded analytics at SaaS scale. Data mesh as a federation methodology.

Stacks evaluated by this test bench are evaluated against the in-scope and adjacent surfaces. The out-of-scope items aren't engineering judgments about what's important in the world — they're calibration choices about what this specific buyer profile actually needs and what a comparison with that buyer in mind can credibly say.

---

## What this document is

This is a written, defended specification of what a modern data stack actually has to do — defined as a set of comparable tasks that any candidate stack must implement to credibly serve a Series A-to-mid-market analytics organization. It is the foundation of a public, comparative test bench: each candidate stack is implemented against this task set, and every task × stack combination produces evidence — cost numbers, operational notes, ADRs.

The test bench is explicitly cross-cloud — AWS, GCP, and Azure are all represented in the indicative stack lineup (see CLAUDE.md for the current lineup). The task set itself is cloud-agnostic by construction: tasks describe capabilities (CDC ingestion, SCD-2 modeling, model output drift detection), and each candidate stack implements those capabilities on whatever cloud and tooling it natively prefers.

It is deliberately *not* a vendor-funded benchmark, an academic benchmark (TPC-DS), or a flowery "modern data stack overview." Vendor benchmarks are biased; TPC-DS targets a buyer who doesn't exist in our market; overviews are LLM-average. The gap this fills is operator-grade comparative truth, written by someone who has actually shipped each stack against the same specification.

## What this document is *not*

- Not a checklist of every conceivable data engineering task
- Not a prescription of which stack to choose — it's the test rubric, not the verdict
- Not an academic spec — it is calibrated to a specific buyer profile and explicit about what's out of scope
- Not stable yet — v0.2 is the second defensible draft, intended for public reaction and iteration

## The anchor buyer profile

Every task in this document is calibrated to a representative buyer. Stacks are not evaluated in the abstract — they are evaluated *for this profile*.

- **Stage:** Series A or B SaaS, or comparably-sized mid-market company (~50–250 employees)
- **Data team:** 1–3 data engineers / analytics engineers **plus 1 data scientist**; no dedicated platform team and no separate ML team
- **Data scale:** tens of GB to low TBs total; tens of millions of events per month; growth trajectory toward 10× over 18 months
- **Sources:** 1 operational Postgres (or equivalent OLTP), 2–4 SaaS sources (CRM, payments, support, marketing), first-party event collection
- **Stakeholders:** 5–15 active consumers across revenue, product, customer success, finance, and exec
- **BI surface:** a few dozen dashboards growing to ~100; a handful of operational reverse-ETL flows
- **ML/AI surface:** 1–3 models in production (e.g., churn risk, lead scoring, support-routing) running on batch or low-QPS online inference; 0–2 LLM/RAG features in production (e.g., support-agent assist, internal knowledge search) consuming a hosted LLM API
- **Compliance:** SOC 2 Type II aspirational or in-progress; GDPR posture if customers in EU; PII handling under audit
- **Latency:** daily-to-hourly is the dominant requirement for analytics; minute-scale is rare and usually not actually needed when interrogated; ML inference is batch or single-digit QPS online

Stacks that target buyers materially smaller (a single founder doing analytics in a notebook) or materially larger (Fortune 500 with dedicated platform teams and dedicated ML platform teams) will perform poorly on this task set, and that is by design.

**On splitting the profile.** A 50-person Series A and a 250-person mid-market company genuinely differ in governance load, deploy cadence, and ML maturity. v0.2 keeps them under one profile; v0.3 reconsiders splitting after the job-posting analysis surfaces whether stack-component frequencies actually diverge across the band. Premature splitting dilutes the comparison without evidence.

## Structural overview

Nine functional categories. Two cross-cutting concerns. Each category contains specific tasks that get implemented and measured on each candidate stack.

**Functional categories:**

1. Ingestion
2. Storage & modeling
3. Transformation
4. Orchestration & reliability
5. Serving & activation
6. Observability & data quality
7. Governance — catalog, lineage, access
8. Operations — CI/CD & developer experience
9. ML & AI enablement

**Cross-cutting concerns** (tested *inside* every category, not given their own boxes):

- **Cost economics.** Every category has a cost answer at three workload sizes — what does this actually run at 10 GB, 100 GB, 1 TB (and for ML/AI: at small/medium/large model and corpus sizes)?
- **Security & compliance posture.** Every category has an answer to "what does an auditor need to see?" — encryption, access logging, retention, PII handling, audit trail.

## On the placement of ML/AI work

ML/AI work intersects with several existing categories. The placement rule for v0.2:

- **Feature engineering as transformation logic** lives in Transformation (3.7). The question there is whether the transformation layer expresses feature pipelines well.
- **Model output and feature distribution monitoring** live in Observability (6.7). The question there is whether the observability stack handles model artifacts the same as data artifacts.
- **Everything distinctly ML-shaped** — experiment tracking, model registry, batch and online inference operations, vector DB / retrieval / LLM eval, notebook-to-production workflow, LLM cost economics — lives in Category 9.

This split keeps the 9th category narrow and disciplined while ensuring stacks get tested on whether they support ML work in the places ML work actually intersects analytics infrastructure. A stack whose transformation layer can't express feature pipelines should fail on 3.7, not get a pass because the failure was hidden in a separate ML category.

## Explicit out-of-scope for v0.2

These are real exclusions, not oversights. Adding them dilutes the comparison and inflates the buyer profile beyond Series A-to-mid-market.

- **Streaming as a first-class category.** Treated as a sub-surface under Ingestion. Most buyers in this profile believe they need streaming and actually need micro-batch. A streaming-only test bench is a different project.
- **Real-time analytics serving** (Pinot, Druid, ClickHouse for sub-second BI). Niche for the target buyer.
- **Data products / data mesh** as an organizing methodology. Orthogonal axis — methodology, not capability.
- **Data sharing / clean rooms.** Later, niche.
- **Multi-tenant SaaS data infrastructure.** Different buyer, different problem.
- **Full ML platform engineering.** Production-scale feature stores (Tecton/Feast at full online+offline parity), custom training infrastructure on dedicated GPU clusters, multi-model A/B serving infrastructure, fine-tuning beyond LoRA-scale experiments. Different buyer, different team shape.
- **High-QPS online inference** (>100 QPS sustained, sub-100ms p99). Different buyer; usually a customer-facing product surface, not an internal data team's responsibility.
- **Custom LLM training or large-scale fine-tuning.** Out — the anchor buyer consumes hosted LLM APIs; LoRA-scale adapters are the upper bound.

---

## 1. Ingestion

**Capability statement.** Land data from heterogeneous sources into the lake or warehouse with documented frequencies, schema-evolution handling, and replay semantics.

**Tasks.**

- **1.1 Batch SaaS API pull.** Pull from a paginated REST source (HubSpot or Stripe). Handle rate limits, incremental sync via cursor or timestamp, and a full historical backfill from cold start.
- **1.2 CDC from operational Postgres.** Capture change events from a transactional Postgres using logical replication or equivalent. Demonstrate at-least-once delivery, schema-drift handling, and replay from a known LSN.
- **1.3 First-party event ingestion.** Collect events (Snowplow-style or simple webhook collector) into the lake with bot/duplicate filtering and a defined late-arriving-events policy.
- **1.4 File-drop / S3 landing.** Handle a partner dropping a daily flat file (CSV or Parquet) on SFTP or S3. Detect, validate, ingest, and quarantine bad files with an operator-friendly error surface.
- **1.5 Recovery from vendor outage.** Simulate a 6-hour SaaS API outage and reload missing windows without duplication or data loss.
- **1.6 Unstructured document ingestion (for RAG).** Land a corpus of unstructured documents (PDFs, HTML, Markdown — partner docs or internal knowledge) into object storage with metadata captured for downstream chunking and embedding. Document the refresh-on-source-change pattern.

**Primary axes of variation across stacks.** Airbyte (OSS or Cloud) vs. Meltano vs. Fivetran vs. custom Python (or Singer taps). Managed vs. self-hosted. Connector library breadth and quality vs. blast radius of a custom connector going wrong.

**Cost test.** Monthly fully-loaded cost (compute + connector pricing + engineer time) at three scales: 50K rows/day, 5M rows/day, 50M rows/day across each candidate.

**Security test.** Where credentials live, how they rotate, what audit trail exists for "who pulled what data when."

**Out of scope for v0.2.** Streaming-first ingestion architectures (Kafka/Kinesis as the primary store), CDC at multi-TB OLTP scale, change-data feeds from non-relational sources.

---

## 2. Storage & modeling

**Capability statement.** Durable, queryable storage tiered for cost and access pattern, with a modeling pattern that gives a defensible answer to "what does production look like and how do you reason about it?"

**Tasks.**

- **2.1 Medallion layering.** Implement raw landing → cleaned/conformed → curated business-grade layers (or the stack's idiomatic equivalent). Layer responsibilities are written down and enforced.
- **2.2 Partition convention.** Define and implement a partitioning strategy for high-volume event data (e.g. date + tenant_id). Demonstrate that query pruning measurably reduces cost.
- **2.3 Schema evolution.** Handle three changes against a live model: a column add, a column rename with backfill, and a type narrowing (string → int) — without breaking downstream consumers.
- **2.4 Slowly-changing dimension (Type 2).** Implement an SCD-2 on a customers table including a retroactive correction (the data was wrong yesterday; fix it today and preserve history correctly).
- **2.5 Late-arriving facts.** Handle a 30-day-late event correctly without recomputing the full universe.
- **2.6 Storage tiering.** Define a hot/warm/cold retention policy, implement it, and demonstrate measurable cost savings.

**Primary axes of variation across stacks.** Lake (S3 + Parquet + Athena) vs. warehouse (Snowflake / BigQuery / Redshift) vs. lakehouse (Iceberg or Delta) vs. Postgres-as-warehouse for low end. Open table formats vs. proprietary.

**Cost test.** Cost per TB-month stored. Cost per query at three workload sizes: an analyst ad-hoc exploration, a dashboard refresh, a full re-aggregation of a Gold table.

**Security test.** Encryption at rest. Column-level access controls for PII. Deletion-on-request (GDPR Article 17) — show the actual mechanism, not a policy doc.

**Out of scope for v0.2.** Real-time materialized views, multi-region replication, data sharing / clean rooms, time-travel beyond the stack's default retention.

---

## 3. Transformation

**Capability statement.** Versioned, tested, modular transformation logic that is reproducible from any commit and documented well enough that a new analyst can navigate it.

**Tasks.**

- **3.1 Incremental fact model.** Implement an event-fact table that incrementally appends and handles late-arriving events with merge logic.
- **3.2 Full-refresh dimension model.** A small dimension table that's rebuilt every run; demonstrate idempotency and correctness.
- **3.3 Snapshot.** Capture history of a mutable source (e.g., HubSpot deals) for trend analysis with point-in-time correctness.
- **3.4 Test coverage on Gold tier.** Every Gold-tier model has source-freshness, uniqueness, not-null, accepted-values, and at least one custom relationship test.
- **3.5 Macro / abstraction reuse.** Implement one reusable pattern (e.g., generated audit columns, standardized currency conversion) and use it in three or more models.
- **3.6 Documentation.** Every Gold-tier model has YAML docs with column-level descriptions; auto-generated docs site is published and discoverable.
- **3.7 Feature engineering as a transformation.** Implement a user-level feature table (e.g., 30-day rolling activity, recency, monetary aggregates) as a tested, documented model in the transformation graph. Demonstrate leakage protection (no future information bleeding into training-window features) using the stack's idiomatic mechanism. The question this task answers: can this stack's transformation layer express ML feature logic well, or does it punt to a separate Python/notebook layer?

**Primary axes of variation across stacks.** dbt-core vs. dbt Cloud vs. SQLMesh vs. Python-first (Dagster software-defined assets). Jinja-SQL vs. native SQL vs. DataFrames. Bundled scheduler vs. external orchestrator.

**Cost test.** Time-to-build a representative DAG of ~50 models at three data scales. Warehouse compute cost per full build.

**Security test.** PII column tagging propagated through models. Masking macros / dynamic data masking. Confirmation that secrets do not leak into compiled SQL or logs.

**Out of scope for v0.2.** Heavy Python transformations beyond what dbt-Python or Dagster idiomatically supports; cross-model differential privacy.

---

## 4. Orchestration & reliability

**Capability statement.** Schedule work, manage dependencies across domains, recover from failure without human babysitting.

**Tasks.**

- **4.1 Cross-domain DAG.** Ingestion → transformation → publish-to-BI flow with alerting on any failed task and clear failure attribution.
- **4.2 Retry policy.** Configure exponential backoff and dead-letter handling. Demonstrate it works when a downstream API throttles or a transient infra error occurs.
- **4.3 Backfill.** Backfill 90 days of a partitioned model after a logic fix, without manually running each partition.
- **4.4 Partial recovery.** A mid-DAG failure leaves the DAG in a state where a re-run only re-executes the failed and downstream tasks, not the whole pipeline.
- **4.5 SLA / freshness alert.** Define and enforce "this fact table must be fresh by 9am ET." Alerting fires correctly when missed; does not fire when not missed.
- **4.6 On-call runbook.** A one-page runbook for "the DAG failed, what do I do" that an analyst (not the engineer who built it) can follow.
- **4.7 Heterogeneous-asset DAG.** A single DAG that schedules a SQL transformation, a Python feature-engineering step, a model training run, and a batch-inference scoring step — with correct cross-asset dependency handling (training waits for fresh features, scoring waits for trained model). The question this task answers: does this stack's orchestrator handle ML assets as first-class citizens, or as foreign tasks bolted onto a SQL graph?

**Primary axes of variation across stacks.** Airflow on MWAA vs. Dagster vs. Prefect vs. Temporal. Bundled orchestration (dbt Cloud's scheduler, Dagster Cloud) vs. standalone. Task-graph model vs. asset-graph model. (Note: 4.7 in particular surfaces the task-graph vs. asset-graph distinction; this task should weigh heavily in the orchestrator tradeoff doc.)

**Cost test.** Managed-orchestration monthly cost. Compute cost of running the canonical DAG once per day for a month.

**Security test.** How secrets are passed to tasks. Task identity / IAM model. Audit log of what ran when, by what identity.

**Out of scope for v0.2.** Cross-team multi-tenant orchestration patterns, hand-rolled Airflow-on-Kubernetes deployments, complex event-driven orchestration beyond simple sensor patterns.

---

## 5. Serving & activation

**Capability statement.** Make data usable to humans (BI), machines (APIs), and operational systems (reverse ETL) — with documented freshness contracts.

**Tasks.**

- **5.1 BI exposure.** Connect a BI tool (Metabase, Lightdash, Looker, or Mode) to the Gold layer. Build three production-grade dashboards: revenue, product engagement, customer health.
- **5.2 Semantic layer / metric definitions.** Define MRR, weekly active users, and net retention once, in code, and surface them consistently across BI and downstream consumers (no metric drift).
- **5.3 Reverse ETL.** Sync a customer-health-score from the Gold layer back to a CRM (HubSpot or simulated). Handle upserts and removals.
- **5.4 API exposure.** A documented read API that returns a daily revenue rollup. Basic auth, rate limiting, schema validation, OpenAPI spec.
- **5.5 Freshness contract.** Every served asset has a documented freshness SLA visible to consumers — not just to the team.
- **5.6 Self-service exploration.** An analyst can answer "what's the funnel for this campaign" using only the Gold layer, without writing custom SQL against raw tables.

**Primary axes of variation across stacks.** Athena vs. Snowflake vs. Postgres as the BI back-end. Lightdash vs. Metabase vs. Looker (paid). Hightouch vs. Census vs. custom for reverse ETL. Native semantic layer vs. dbt Semantic Layer vs. Cube vs. none.

**Cost test.** Cost per dashboard refresh × refresh frequency. Reverse-ETL row-cost economics. API cost per million requests.

**Security test.** Row-level security (an analyst sees only their tenant's data, an exec sees an aggregated view). API auth mechanism. Audit of who ran which query.

**Out of scope for v0.2.** Customer-facing embedded analytics, real-time dashboards (sub-minute latency), customer-data-platform use cases (multi-source identity resolution).

---

## 6. Observability & data quality

**Capability statement.** Detect freshness, volume, schema, and value-distribution issues *before* a stakeholder does — for both data assets and ML/AI artifacts.

**Tasks.**

- **6.1 Source freshness monitoring.** Every source has a freshness check that fires if data hasn't arrived within its SLA window.
- **6.2 Volume anomaly detection.** Row-count anomalies on a daily fact table trigger an alert (Elementary, re_data, or hand-rolled).
- **6.3 Schema drift detection.** A source column being dropped or retyped is detected, and a ticket or alert fires *before* downstream models break.
- **6.4 Value-distribution test.** A custom test flags a 50% MoM drop in conversion rate as suspicious. Could be real, could be a bug — the alert routes to a human who decides.
- **6.5 Alert routing tiers.** Page (revenue-blocking), ticket (next-business-day), silent-log (informational). Demonstrate one of each routed correctly.
- **6.6 Incident postmortem.** Simulate a data quality incident, write the postmortem template the team would actually use.
- **6.7 Model output and input drift.** A deployed model has monitoring on its output distribution (e.g., predicted churn rates) and on its input feature distributions. Drift fires alerts that route into the same tier system as data-quality alerts. The question this task answers: does this stack's observability layer treat models as first-class monitored assets, or are models a separate observability surface (Evidently, Arize, etc.) that doesn't share alert routing with data?

**Primary axes of variation across stacks.** dbt tests + Elementary vs. dbt tests + re_data vs. Monte Carlo (paid) vs. Bigeye (paid) vs. Soda. PR-time tests vs. runtime monitoring vs. both. For 6.7 specifically: native data-observability tools' model-monitoring extensions vs. dedicated ML monitoring (Evidently, Arize, WhyLabs).

**Cost test.** Cost of running the full quality suite per day, including model-monitoring checks.

**Security test.** Alerts do not leak PII into Slack channels. Access to alert payloads is role-appropriate.

**Out of scope for v0.2.** ML-driven anomaly detection beyond simple threshold/baseline approaches, end-to-end trace propagation across the entire stack as a single observability surface.

---

## 7. Governance — catalog, lineage, access

**Capability statement.** Anyone in the company can discover what data exists, see how it was built, and access it appropriately for their role — without filing tickets per asset.

**Tasks.**

- **7.1 Catalog ingest.** Every Gold-tier table appears in the catalog with description, owner, last-updated timestamp, and link to source code.
- **7.2 Column-level lineage.** Trace a single column in a Gold table back through its dbt models to the originating source field.
- **7.3 Business glossary.** Ten core business terms defined and linked to their canonical implementation.
- **7.4 PII tagging.** Every column containing PII is tagged at the source; downstream models inherit the tag automatically or via convention.
- **7.5 Role-based access.** Three personas — analyst, engineer, exec viewer — each get the right level of access without manual ticket-by-ticket grants.
- **7.6 Access request flow.** A documented path for "I'm a new analyst, I need access to revenue data" that completes in under one business day end-to-end.
- **7.7 Audit trail.** Who-queried-what is queryable for the last 90 days.
- **7.8 Model lineage.** A deployed model is discoverable in the catalog with lineage back to its training data and its feature inputs. The question this task answers: does this stack's catalog treat models as cataloged assets, or are models invisible to it?

**Primary axes of variation across stacks.** OpenMetadata vs. DataHub vs. Atlan (paid) vs. Collibra (paid) vs. Unity Catalog (Databricks) vs. nothing (just dbt docs). IAM-native access vs. catalog-managed access patterns.

**Cost test.** Catalog hosting cost + maintenance hours per month.

**Security test.** Audit trail is itself audit-immutable. PII tags are *enforced*, not just declared.

**Out of scope for v0.2.** Data contracts as a formal protocol (mention as adjacent), column-level differential privacy, fine-grained policy engines (e.g., Immuta, Privacera).

---

## 8. Operations — CI/CD & developer experience

**Capability statement.** Ship safely, onboard new engineers fast, keep the on-call burden bounded.

**Tasks.**

- **8.1 PR-to-prod pipeline.** A pull request triggers tests, dbt compile/build against staging, plan-output for IaC changes, and merge gates on green.
- **8.2 Environment isolation.** Dev, staging, prod environments with clear data and credential separation. Dev runs on a laptop or in a personal cloud env using the synthetic data generator.
- **8.3 Secret management.** Zero secrets in repo. Rotation works without breaking running pipelines.
- **8.4 Time-to-first-commit.** A new engineer can clone the repo, run the stack locally against synthetic data, and merge a meaningful PR within two working days.
- **8.5 Cost guardrails in CI.** A CI check that fails the build if a query plan would cost more than a configured threshold to run in production.
- **8.6 Onboarding documentation.** A README that gets a stranger to a working stack in 60 minutes.
- **8.7 Rollback.** A documented and tested rollback for a failed transformation deploy — including a model-deployment rollback (revert to the previous registered model version).

**Primary axes of variation across stacks.** GitHub Actions + CDK vs. Terraform Cloud vs. dbt Cloud's bundled CI vs. Dagster Cloud's bundled deploy.

**Cost test.** CI minutes per PR. Infrastructure cost of staging env. Minutes-to-deploy from merge.

**Security test.** Secrets-in-CI handling. Branch protection. Deploy actor identity and audit trail.

**Out of scope for v0.2.** Multi-account AWS Organizations setups, fully ephemeral PR environments at full data scale.

---

## 9. ML & AI enablement

**Capability statement.** Make a lone data scientist productive on the stack — from notebook exploration to production batch and lightweight online inference, with experiment tracking, model registry, and the operational shape needed to run LLM/RAG integrations on hosted APIs. This is **enablement**, not a platform: no custom training infrastructure, no high-QPS serving, no production-scale feature store.

**Tasks.**

- **9.1 Notebook-to-production handoff.** A data scientist iterates in a notebook against the Gold layer; the work is promoted to a scheduled, version-controlled, tested pipeline without re-implementation by a data engineer. Document the path: where the notebook lives, how it gets promoted, what changes (if anything) at the boundary, who owns each artifact.
- **9.2 Feature pipeline operations.** Building on 3.7 (feature engineering as a transformation): demonstrate point-in-time correctness for assembling a training dataset from feature tables — i.e., a training row for user U at time T sees only feature values that were known at T, not values computed later. Document the reuse pattern: training-time and inference-time read from the same feature table without code duplication.
- **9.3 Experiment tracking + model registry.** Every model training run logs hyperparameters, training data version, metrics, and artifacts. Promoted models are registered with versioning and lineage to training data. Demonstrate a production model can be traced back to the exact training run, the exact feature snapshot, and the exact code revision.
- **9.4 Batch inference.** Deploy a trained model (e.g., a churn-risk classifier) as a scheduled batch job that scores a Gold table daily. Outputs land in the Gold layer (a `predictions` model) and are downstream-discoverable as any other Gold asset.
- **9.5 Lightweight online inference.** Serve a single model behind a low-traffic HTTP endpoint (single-digit QPS sustained, ~hundreds of QPS burst). Documented latency p50/p95, cost economics, and authentication. **Explicitly not a high-QPS production system.**
- **9.6 LLM/RAG pipeline.** Build a retrieval-augmented generation pipeline against the document corpus from 1.6: chunk → embed → store in a vector DB → retrieve → call hosted LLM → return. Includes a retrieval-quality test suite (e.g., on a held-out Q&A set, recall@k for the top-k retrieved chunks) and a generation-eval harness (e.g., LLM-as-judge or rubric-based scoring on a held-out evaluation set). Failure modes are tracked, not papered over.
- **9.7 LLM cost + latency observability.** Token usage, per-call cost (broken down by model, prompt template, and upstream consumer), and latency are tracked and surfaced in the same observability stack as data pipelines (6.x). A spike in spend or latency fires an alert routed through the same tier system.

**Primary axes of variation across stacks.**
- Experiment tracking + registry: MLflow (self-hosted) vs. Weights & Biases (managed) vs. DVC vs. nothing-but-Git.
- Online serving: SageMaker vs. Modal vs. BentoML vs. self-rolled FastAPI on Fargate/ECS vs. Cloud Run.
- Batch inference: dbt-Python or Dagster asset vs. Airflow PythonOperator vs. SageMaker batch transform.
- Vector DB: pgvector (Postgres) vs. Pinecone vs. Weaviate vs. Qdrant vs. OpenSearch.
- RAG framing: LangChain vs. LlamaIndex vs. raw orchestration with provider SDKs.
- LLM eval: Ragas vs. DeepEval vs. custom rubric + LLM-as-judge.

**Cost test.**
- Monthly fully-loaded cost of experiment-tracking infrastructure at three workload sizes (10, 100, 1000 training runs/month).
- Per-1K-tokens cost across the LLM provider used, broken down by prompt template and feature.
- Vector DB cost at three corpus sizes (10K, 100K, 1M chunks).
- Batch inference cost per run at three model sizes (small classifier, medium gradient-boosted model, light embedding model).
- Online inference cost per 100K requests.

**Security test.** PII in training data is masked or excluded, with auditable evidence (lineage from prediction back through features back to source columns shows no unmasked PII path). Vector DB access is role-bounded. LLM prompts and responses do not leak through application or LLM-provider logs in a way that violates the buyer's compliance posture. Provider-side data retention is configured (e.g., zero-retention mode where available). Models in the registry are immutable once promoted; rollback is via re-promotion, not edit-in-place.

**Out of scope for v0.2.** Production-scale feature stores (Tecton/Feast at full online+offline parity SLAs). Custom GPU training infrastructure. High-QPS online inference (>100 QPS sustained, sub-100ms p99). Multi-model A/B serving. Fine-tuning beyond LoRA-scale experiments. Custom LLM training. RLHF pipelines.

---

## How candidate stacks are evaluated against this task set

For each candidate stack, the comparative test bench produces:

- **Working code** for every task in this document, in a public, runnable repository
- **A synthetic data generator** that lets anyone reproduce the test bench end-to-end on a laptop (including a synthetic document corpus for 1.6 / 9.6)
- **Per-task ADRs** documenting the decision, the alternatives considered, and the tradeoff made
- **Cost numbers** at the three reference workload sizes for every cost-relevant task
- **Operational notes** capturing the friction discovered during implementation that the documentation does not warn you about
- **A production-readiness checklist** the buyer can hand to leadership

Each task × stack combination is content. Each ADR is a candidate blog post. Each cost comparison is a candidate podcast segment. The artifact and the distribution strategy are the same artifact, viewed from two angles.

## What this draft is *not yet*

- Synthetic data shapes, volumes, and the document corpus shape for 1.6 / 9.6 are specified in `synthetic-dataset.md` (v0.1 landed 2026-05-13). The generator implementation itself is Phase 1 work.
- It does not yet have explicit pass/fail criteria per task — those will emerge from Stack #1 implementation, where running the tasks reveals which acceptance bars actually matter.
- It does not yet include a worked example of a comparative writeup — the first one lands when Stack #1 finishes Category 1.
- It does not yet incorporate findings from the job-posting analysis. The methodology is specified separately (`job-postings/methodology.md`, sibling to this doc); when the analysis runs, results may shift category emphasis, surface missing tasks, or trigger a buyer-profile split.

## Open questions for v0.3 / v1.0

- **Buyer profile split.** Series A (50–100 employees) vs. mid-market (100–250) may need separate task-set tunings. v0.3 reconsiders this once the job-posting analysis surfaces whether stack-component frequencies actually diverge across the band.
- **Activation as its own category.** Reverse ETL (5.3) may deserve promotion from a sub-surface of Serving to its own category if real engagements show it carries more weight than expected.
- **Time-to-first-insight as a meta-task.** A cross-category measurement of how long it takes a new analyst to answer a real business question on a fresh deployment. Currently implied across 5.6, 7.6, 8.4, 8.6; possibly worth promoting.
- **9.6 RAG evaluation rigor.** LLM-as-judge has well-known biases; the test bench may need a small human-labeled gold set as the ground truth that the LLM-judge is calibrated against. Decide before Stack #1 ships 9.6.
- **Online-inference scope creep risk.** 9.5 explicitly caps at single-digit QPS sustained. If real engagements push this higher, decide whether to expand 9.5 or open a new "high-QPS serving" category in v2.0 — and whether that breaks the buyer profile.

## Versioning

- **v0.1 (2026-05-08):** Initial structure. 8 categories, 2 cross-cutting concerns, anchor buyer profile, explicit out-of-scope.
- **v0.2 (2026-05-10):** Adds Category 9 (ML & AI enablement) with seven tasks. Adds 3.7 (feature engineering as transformation), 4.7 (heterogeneous-asset DAG), 6.7 (model output/input drift), 7.8 (model lineage), 1.6 (unstructured document ingestion). Updates anchor buyer profile to include 1 data scientist and quantify ML/AI surface. Adds top-level definition of "modern analytics architecture expertise" for use in positioning copy. Adds explicit out-of-scope clarifications for ML platform engineering, high-QPS inference, and custom LLM training. Notes pending integration with the job-posting analysis (`job-postings/methodology.md`).
- **v1.0 (target: end of Stack #1 implementation):** Refined task definitions, pass/fail criteria, synthetic data spec, first complete worked example. Job-posting analysis findings folded in.
- **v2.0 (target: after Stack #2):** Cross-stack comparative findings folded back; category structure revisited based on what actually mattered in two implementations.
