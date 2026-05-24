# ADR-001: Orchestrator strategy — per-stack with intent

**Status:** Proposed

**Date:** 2026-05-12

## Context

`data-stack-bench` ships five real, runnable implementations of the same canonical task set across AWS, GCP, and Azure. Orchestration is foundational: it's the layer that runs the pipelines, owns retries and scheduling, exposes lineage hooks, and interacts heavily with both the transformation layer (dbt) and the catalog/observability layer. An orchestrator pick is not a swap-in component — it's a posture about how pipelines are structured (task DAG vs. asset graph), how state is materialized (operator-level vs. data-asset-level), and how the operational surface looks (managed metadata DB and webserver vs. native to the data platform).

The default move for a single-team data project is to standardize on one orchestrator across the organization. The 2026-Q2 hiring data agrees with that default: Airflow shows up in 40% of buyer-profile postings (#1), Dagster in 20% (#2), and `snowflake | dbt_core | airflow` is the most common three-tuple at 22.5%. A "standardize on Airflow" call would be conservative and frequency-validated.

For this project, that's the wrong call. The asset is a *comparative* test bench. Locking one orchestrator across five stacks would make each comparison about "the same orchestrator running against different warehouses," which is not the comparison a buyer actually faces. A buyer choosing between Databricks and Fabric is not choosing "Airflow on Databricks vs. Airflow on Fabric" — they're choosing how the whole platform behaves end-to-end, including the native orchestrator that ships with the platform. A comparison that strips out the native orchestrator misrepresents what the buyer's actual decision looks like.

Constraints in play:

- **Cross-cloud breadth.** Stacks span AWS, GCP, and Azure plus the cloud-agnostic Databricks. Some orchestrators are first-party on one cloud (MWAA on AWS, Cloud Composer on GCP, ADF on Azure) and second-party elsewhere; the lineup needs to be fair to the native-platform pitch where one exists.
- **Cost discipline.** <$100/mo most months, $200–300 during measurement windows. Every stack must support full teardown and clean re-spinup. Orchestrator choices that carry a fixed baseline cost regardless of utilization fight this constraint structurally.
- **Native-platform integrity.** Stack #4 (Databricks) and Stack #5 (Fabric + Power BI on Azure) are sold as self-contained platforms. Honoring their native orchestrators at least once in the lineup is what makes the comparison fair to the platform pitch.
- **Canonical task set shape.** Two tasks in the canonical set — 4.7 (heterogeneous-asset DAG mixing dbt models, Python ML batches, and notebook artifacts) and 6.7 (model-output drift detection wired into the orchestration graph) — have architectural implications for orchestrator choice. Dagster's asset model treats lineage and observation hooks as first-class structure; Airflow's task-DAG idiom treats them as operator-level concerns that have to be assembled. The asset-graph payoff is structural, not preference.
- **Hiring frequency.** 2026-Q2: Airflow 40%, Dagster 20%. Both have material market presence; the test bench should run both at least once.

The orchestrator question landed on a meta-fork: lock one family across the lineup vs. pick per-stack with intent. This ADR resolves the meta-fork.

## Decision

Orchestrator is chosen **per stack with intent**, not locked across the lineup.

| # | Stack | Orchestrator | Lock status |
|---|---|---|---|
| 1 | AWS lake-first OSS | Airflow (self-hosted on AWS Fargate) | Family locked; flavor locked |
| 2 | Snowflake on AWS | Airflow (self-hosted on AWS Fargate) | Family locked; flavor locked |
| 3 | BigQuery on GCP | Dagster (Cloud Hybrid likely; flavor decided at Stack #3-time) | Family locked; flavor open |
| 4 | Databricks lakehouse | Databricks Workflows (native to the platform) | Family locked; surface decided at Stack #4-time |
| 5 | Fabric + Power BI on Azure | Fabric Data Factory (native to the platform) | Family locked; surface decided at Stack #5-time |

The intent behind each pick:

**Airflow at Stack #1 + Stack #2.** Conservative anchor. Stack #1 is the pragmatic-anchor stack, not the unique-angle stack; pairing it with the most frequently-recognized orchestrator keeps operator burden low at the moment the project most needs to ship. Stack #1 + Stack #2 on the same orchestrator isolates the warehouse-and-storage axis cleanly in their head-to-head comparison: Athena lake-first vs. Snowflake warehouse-first, with orchestrator held constant. That's the comparison the path-1 buyer actually runs in their head when evaluating "stay lake-first or migrate to Snowflake."

**Dagster at Stack #3.** Asset-graph payoff. Canonical tasks 4.7 and 6.7 are structurally awkward in Airflow's task-DAG idiom — partition-aware lineage and model-output observation hooks live at the operator level and have to be assembled by hand — and structurally clean in Dagster's asset model, where each data asset and each materialization is a first-class structure with built-in lineage and observation. Stack #3 is also the first cloud-boundary crossing (GCP) — the orchestrator change moves with the cloud change, which keeps the variable-isolation story consistent (one stack-step changes multiple things, with documented rationale, rather than every stack changing one thing). BigQuery's per-byte-scanned cost model also lands cleanly on Dagster's assets-as-materialized-queries pattern: each asset materialization is annotated with the bytes scanned, which feeds the cost-observability story without manual instrumentation.

**Databricks Workflows at Stack #4.** Native-platform integrity. Databricks Workflows ships inside the Databricks platform with native cluster-management, lineage, and Unity Catalog integration. Running Airflow against Databricks would be the strawman version of the Databricks pitch — it strips out half of what the platform sells. The comparative test bench is fair to each stack's actual value proposition, which means honoring the native orchestrator when the platform has one.

**Fabric Data Factory at Stack #5.** Same logic. Fabric is sold as a unified workload that includes its own pipelines surface (Fabric Data Factory, derived from Azure Data Factory but integrated into the Fabric capacity-and-workspace model). A Fabric stack with Airflow bolted on misrepresents the pitch. ADF-standalone is the alternative but it's a separate Azure service from Fabric, so it would land as "ADF + Fabric" rather than canonical Fabric — interesting as a variant later, but the canonical Stack #5 implementation uses native Fabric pipelines.

The meta-decision behind these picks: **per-stack-with-intent, not lock-one-family**. Each pick is defensible from its own context (cost discipline, native-platform integrity, asset-graph payoff, hiring frequency); the lineup as a whole is defensible from the comparative-tester POV.

## Alternatives considered

**Lock Airflow across all five stacks.** The hiring-frequency-validated default. Rejected. It would force Airflow onto Databricks and Fabric — misrepresenting how those platforms get sold — and it would strip Dagster's asset-graph payoff out of the project entirely, leaving canonical tasks 4.7 and 6.7 in the orchestrator family they're known to be awkward in. The cost is a "comparison" that's actually a tour of warehouses with one orchestrator out front.

**Lock Dagster across all five stacks.** Inverse. Rejected harder. Lower hiring frequency (20% vs. 40%) means readers expecting the most-common orchestrator wouldn't see it run; same native-platform problem at Stacks #4 and #5; and Airflow's task-DAG idiom is genuinely closer to how the buyer-profile postings describe their pipelines (cron-shaped, scheduled, task-oriented), which means missing that mode would weaken the comparison.

**Pick per-stack ad hoc, no intent.** Rejected. The "with intent" framing is what makes this defensible. Without it, the lineup reads as "the maintainer picked whatever was easiest each time," which is a credibility problem for a project whose POV is fair comparative testing. Per-stack-with-intent commits the project to specific rationale for each pick and lets the comparison call out which variable each stack-step moves.

**Stack #1 specifically — MWAA (AWS Managed Airflow).** Rejected on shape, not just price. MWAA's baseline is ~$400+/mo regardless of utilization — there's no scale-to-zero. The smallest environment runs whether a DAG triggered today or not. That's incompatible with the project's spin-down-between-measurement-windows discipline. The cost number alone would disqualify it; the lack of scale-to-zero is the structural reason. MWAA's value prop — AWS managing scheduler + webserver + metadata DB + autoscaling workers, plus first-party IAM/VPC/Secrets Manager integration — is real for an enterprise that values not babysitting Airflow infrastructure. The buyer this test bench profiles is cost-disciplined and explicitly values teardown ergonomics; MWAA is the wrong shape, not just the wrong price.

**Stack #1 specifically — Astronomer (managed Airflow, multi-cloud).** Defensible production option. Commercial pricing is opaque and the minimum tier is well above the project's cost target. Real for path-1 buyers; not in the test bench's cost envelope. Mentioned as a sidebar in the writeup, not implemented.

**Stack #1 specifically — self-hosted Airflow on EC2.** Cheaper at the floor than Fargate but adds AMI patching and instance-lifecycle ops burden. Conflicts with the "stranger can teardown + re-spinup" requirement and with the cost-discipline-as-content thread. Rejected.

**Stack #1 specifically — self-hosted Airflow on EKS.** Powerful but adds EKS ops burden that's overkill for the buyer profile (50–250 employees, small data team). The buyer this test bench profiles does not run Kubernetes for orchestration if they can avoid it. Rejected.

**Stack #3 specifically — Cloud Composer (GCP managed Airflow).** The GCP-native managed Airflow. Same cost-shape problem as MWAA: minimum environment runs above the cost target regardless of utilization. Also misses the asset-graph payoff, which is the entire reason Stack #3 leaves the Airflow family.

## Consequences

**Intended.**

The lineup-level comparison reads as "here's what the buyer's stack choice actually looks like in practice," not "here's the same orchestrator against five warehouses." Stack #4 and Stack #5 are fair to their native-platform pitches. Stack #3 runs Dagster against the orchestrator-shape its asset model is built for.

The Stack #1 ↔ Stack #2 head-to-head isolates the warehouse-and-storage axis cleanly: same orchestrator, same cloud, different warehouse. That's the comparison the path-1 buyer evaluating "stay lake-first or migrate to Snowflake" runs in their head.

The project signals — through its structural choices, not just its stated POV — that it's a comparative tester, not an opinionated builder. Per-stack-with-intent is the structural commitment to fairness across the lineup.

**Accepted costs.**

Each orchestrator pick has to be defended at the time its stack ships. Not a one-shot decision; the ADR commits the project to per-stack judgment.

The lineup-level comparison can't isolate the orchestrator variable cleanly across every pairwise comparison. Mitigation: Stack #1 ↔ Stack #2 holds orchestrator constant (clean warehouse-axis comparison); Stack #3's orchestrator change is paired with the cloud-boundary crossing so the moving variables are documented together; Stacks #4 and #5 are honoring native orchestrators by design, so the comparison there is platform-vs-platform, not orchestrator-vs-orchestrator.

Operating multiple orchestrators carries real cognitive overhead for a solo build. Mitigation: Stack #1 + Stack #2 share Airflow (one orchestrator family covers two stacks); Dagster, Databricks Workflows, and Fabric Data Factory each appear once. Total orchestrator families to operate: four.

For path-1 buyers: if a prospect asks "have you run Dagster on Snowflake?", the honest answer is "Dagster runs on BigQuery in this project; the Dagster-Snowflake combination is documented but not implemented." That's an accepted gap. The project doesn't try to be comprehensive across the Cartesian product of orchestrator × warehouse; it tries to be honest about which combinations it has run.

**Hypotheses to validate when Stack #1 ships.** Proposed-status hypotheses, not claims of operator tenure. The Accepted-status revision of this ADR — and the corresponding writeup — pulls in actual operator notes once Stack #1's orchestration slice runs against the canonical task set.

- Self-hosted Airflow on Fargate (scheduler + webserver as Fargate services, workers as Fargate tasks, metadata DB on a small RDS Postgres) is expected to land at ~$30–50/mo for a 24/7 small environment, lower with disciplined spin-down.
- Scheduler-on-Fargate is expected to be stable for the test bench's load profile (single dev, occasional measurement runs, not high-concurrency production). Known weak point: scheduler restarts are slower on Fargate than on EC2 because container provisioning is the floor; for the test bench's usage pattern this is acceptable.
- The shared-metadata-DB pattern (small RDS Postgres serving both Airflow metadata and any Stack #1 source-system simulation, separated by schema or by instance depending on the cost-vs-isolation tradeoff that surfaces during implementation) is a deliberate cost-disciplined choice. The risk is operational coupling — if the shared DB has an incident, both Airflow and the source-system simulator are affected. To be called out explicitly in the Stack #1 writeup if it bites.
- DAG ergonomics for canonical tasks in categories 1–3 (ingestion, storage, transformation) are expected to fit Airflow's task-DAG idiom cleanly. Tasks 4.7 and 6.7 are expected to feel awkward and are part of why Stack #3 picks Dagster — the awkwardness is part of the comparative content, not a bug.

## Open questions

- **Stack #3 Dagster flavor.** Cloud Hybrid (free tier suitable for the test bench's row counts; saves operating Dagit, scheduler, daemon) vs. self-hosted Dagster on GCP. Lean: Cloud Hybrid. Confirmed at Stack #3-time.
- **Stack #5 Fabric Data Factory implementation surface.** Fabric Data Factory has overlapping surfaces inside Fabric (pipelines, Dataflows Gen2, notebook orchestration). The canonical Stack #5 implementation should use the surface that maps most cleanly to the canonical task set; decided at Stack #5-time.
- **dbt invocation pattern across stacks.** Stack #1 + Stack #2 will invoke dbt via Cosmos (or BashOperator as fallback) inside Airflow. Stack #3 will invoke dbt via dagster-dbt. Cross-stack comparisons on the transformation layer will note this as documented variance rather than a confounder, and the writeup needs to be explicit about it.
- **Whether tasks 4.7 and 6.7 are awkward enough in Airflow's idiom at Stack #1 to support the architectural argument for Dagster at Stack #3.** If Airflow handles them more cleanly than expected, the asset-graph payoff is sharpened rather than contradicted — the argument shifts to "Dagster does this with less plumbing," not "Airflow can't do this." Validated when Stack #1's task 4.7 ships.
