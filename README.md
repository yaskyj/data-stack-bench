# data-stack-bench

**A public, comparative test bench for modern data stacks.**

Real, runnable implementations of the same canonical task set across multiple data stack choices, with every architectural decision documented as an ADR and every cost claim reproducible from a synthetic dataset.

This is built in public, sequentially. The first stack ships ahead of the others. The repo is intentionally visible while incomplete.

---

## What this is

A specification + a set of implementations + a body of writeups, structured as one comparative artifact:

- A **canonical task set** ([`canonical/task-set.md`](canonical/task-set.md)) — a written, defended specification of what a modern data stack actually has to do for a Series A through mid-market analytics organization. Nine functional categories (ingestion, storage, transformation, orchestration, serving, observability, governance, ops, ML/AI), two cross-cutting concerns (cost and security), an explicit anchor buyer profile, explicit out-of-scope.
- **Multiple stack implementations** of the same task set, built sequentially. Each stack is production-grade IaC (Terraform), version-controlled, tested, and supports full teardown plus clean re-spinup so the project's total infrastructure burn stays under $100/mo most months.
- **A canonical synthetic dataset + validation query suite** (forthcoming) that lets a stranger reproduce the test bench on a laptop and verify cost and correctness claims.
- **Comparative writeups + ADRs** documenting the tradeoffs each implementation made. The mirror copies of these posts live in [`posts/`](posts/); ADRs live in [`adrs/`](adrs/) and per-stack subdirectories.
- **Quarterly job-posting analysis** ([`canonical/job-postings/methodology.md`](canonical/job-postings/methodology.md)) — N=150 postings filtered to the buyer profile, used to keep stack selection grounded in real hiring demand rather than vendor narratives or my priors.

## Who this is for

The anchor buyer profile is detailed in the task set; in short:

- 50–250 employees, Series A through mid-market.
- Small data team: 1–3 data engineers / analytics engineers plus 1 data scientist. No dedicated platform team or separate ML team.
- Tens of GB to low TBs of data, growing toward 10× over 18 months.
- A handful of production models, 0–2 LLM/RAG features, batch or single-digit-QPS inference.
- A Head of Data, VP of Engineering, or CTO trying to decide between stacks (selection) or escape one (replatform) on a 60-day-ish timeline.

If you are running a single founder's analytics out of a notebook, or running a Fortune 500 with a dedicated platform team, this test bench is calibrated to a different buyer than you. That is by design.

## Stack lineup (indicative)

The first stack is locked in shape. Stacks #2 onward are subject to rearrangement based on the first job-posting analysis run.

| # | Stack | Cloud | Status |
|---|---|---|---|
| 1 | AWS lake-first OSS — S3 + Athena + Postgres + dbt-core + OpenMetadata | AWS | In progress |
| 2 | Snowflake on AWS with managed orchestration | AWS | Planned |
| 3 | BigQuery + GCP-native | GCP | Planned |
| 4 | Databricks lakehouse | AWS or Azure (TBD) | Planned |
| 5 | Microsoft Fabric + Power BI | Azure | Planned |

The test bench is explicitly cross-cloud. An AWS-only "comparative" test bench is a tour, not a comparison.

## Principles

- **Comparative, not opinionated.** This project does not tell you which stack is right; it makes the choice legible. Individual ADRs are sharp and call specific tradeoffs, but the project identity is the methodology, not a personal stack.
- **Cross-cloud by design.** Buyers choosing between Snowflake-on-AWS, BigQuery, and Fabric+Power BI are the audience.
- **Reproducible by a stranger.** Synthetic data + validation queries mean cost claims aren't anecdotal and cross-stack disagreements surface as numerical drift, not vibes.
- **Cost-disciplined.** Every stack supports full teardown and clean re-spinup, validated by CI. Total project burn target: under $100/mo most months.
- **No vendor affiliation.** Not a vendor pitch. Not an industry analyst report. Not a course funnel.

## Repo layout

```
canonical/             specification (cloud-agnostic)
  task-set.md          the canonical task set
  job-postings/        the quarterly analysis methodology and captures
stacks/                implementations
  stack-01-athena/     AWS lake-first OSS anchor
adrs/                  cross-cutting decision records (per-stack ADRs live under stacks/)
posts/                 mirror copies of the comparative writeups
```

## Status

- Canonical task set v0.2 — drafted, public for reaction.
- Job-posting analysis methodology v0.1.3 — first capture complete. Pipeline at `canonical/job-postings/pipeline/`; outputs at `canonical/job-postings/captures/2026-q2/` (N=40, two of three sources — HN + BuiltIn; Wellfound deferred to v0.2). Headline reads: cloud platform AWS 40% / GCP 12.5% / Azure 10%; warehouse leaders Snowflake 42.5%, BigQuery 25%, Redshift 20%, Databricks 15%; top three-tuple `snowflake | dbt_core | airflow` at 22.5%. Spot-check signed off pending; analysis writeup is the next public artifact.
- Stack #1 implementation — not yet started. Orchestrator decision (ADR-001) follows the first job-posting analysis run.
- Synthetic dataset spec — not yet drafted.

The contract with the audience: meaningful repo activity at least weekly, a long-form ADR or comparative post every 2–3 weeks, no LLM-average filler.

## Contributing / feedback

This is not currently accepting code contributions — the value of the artifact depends on the implementations being mine, end-to-end. Issues and discussions for the canonical task set, the job-posting methodology, and the comparative writeups are welcome and will materially shape the work. If you are a buyer in the profile above and want to talk about an engagement, the contact path will land in this README before Stack #1 is presentable.

## License

Apache-2.0. See [LICENSE](LICENSE).
