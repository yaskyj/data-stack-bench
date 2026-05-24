# Stack #2–5 lineup decision — Q2 2026

**Date:** 2026-05-11
**Status:** Locked. Internal decision document. The public counterpart lives at `posts/drafts/stem-01-lineup-confirmation.md` and ships per the build-first sequencing in CLAUDE.md.

**Source data:** `cloud-platform-breakdown.csv`, `frequency-by-category.csv`, `cooccurrence-top-10.csv`, `stage-breakout.csv` in this directory. N=40 across HN + BuiltIn; Wellfound deferred to methodology v0.2 (DataDome bot mitigation blocks the public path).

## Decision

The indicative lineup in CLAUDE.md — Stack #2 Snowflake-on-AWS, Stack #3 BigQuery on GCP, Stack #4 Databricks, Stack #5 Fabric + Power BI on Azure — survives the Q2 data unchanged. Stack #1 (AWS lake-first OSS) remains the anchor regardless of this analysis.

## Per-stack confirmations

**Stack #2 — Snowflake on AWS.** Snowflake is the #1 warehouse at 42.5% (17/40); dbt-core is #1 transformation at 42.5%; Airflow is #1 orchestrator at 40%. The triple `snowflake | dbt_core | airflow` is the single most common warehouse-transformation-orchestrator combination in the dataset at 22.5% (9/40). This is the "popular triple" anchor the lineup called for. Confirmed. *(Orchestrator subsequently locked to Airflow on 2026-05-12 via ADR-001, consistent with the triple above.)*

**Stack #3 — BigQuery on GCP.** BigQuery is #2 warehouse at 25% (10/40), well clear of the next instance. GCP's cloud-platform share is 12.5% — meaningful and asymmetric with AWS, which is what the cross-cloud differentiation dimension needs. Orchestrator pick is downstream of this lineup call and doesn't affect it. Confirmed. *(Orchestrator subsequently locked to Dagster on 2026-05-12 via ADR-001 to honor canonical tasks 4.7 and 6.7.)*

**Stack #4 — Databricks lakehouse.** Databricks at 15% (6/40). Lower raw frequency than Snowflake or BigQuery, but architecturally distinct from both Athena (lake-first) and Snowflake (warehouse-first), so the comparative value is high. Cloud host (AWS vs. Azure) deferred to closer to implementation; the data doesn't argue strongly either way. Confirmed.

**Stack #5 — Microsoft Fabric + Power BI on Azure.** Weakest single-cloud signal: Azure 10% overall, 16.7% in the mid-market subset. Power BI itself appears in only 5% overall / 11.1% mid-market. **Inclusion is partly a known-skew correction, not a frequency-pure call.** The methodology over-samples SaaS-tech via BuiltIn and HN, and structurally under-samples the broader Power-BI-heavy mid-market (financial services, manufacturing, healthcare-software outside the SaaS core). Independent signal — Power BI's seat-count market position and Fabric's analyst-report growth rate — argues for inclusion in a comparative test bench's lineup even when local frequency is low. Confirmed, with the caveat noted in the public writeup.

## Honorable mentions — considered, not added

**Redshift — 20% (8/40), #3 warehouse.** Not added. Two reasons: (a) AWS-resident, same cloud as Stack #1 and Stack #2, so adding Redshift would turn the AWS slice into a tour of AWS warehouses rather than a cross-cloud comparison; (b) Redshift mentions in 2026 postings correlate with legacy-stack maintenance and replatform-source rather than net-new selection, while the buyer profile is selection or net-new build. Revisit at v0.2 if the mention rate climbs and the buyer-context shifts.

**ClickHouse — 15% (6/40), 17.9% in Series A/B.** Not added. Tied with Databricks overall and slightly ahead of Databricks in the Series A/B subset, so worth engaging seriously rather than ignoring. Distinct buyer shape: real-time OLAP / event analytics for engineering-heavy product teams, not the daily-to-hourly BI-and-modeling shape the canonical task set is calibrated to. Acknowledged in the public writeup as a known omission with a stated reason; not a lineup addition.

## What this doesn't conclude

N=40 is well below the methodology's N=120–150 target. Headline aggregations (top warehouse, top transformation, top orchestrator, cloud platform) are tight enough to lock the lineup; tail-of-distribution components in the 5–15% range (where Databricks, ClickHouse, Power BI, and the full Azure slice live) carry wider error bars. The lineup call holds because each Stack #2–5 spec anchors on a primary signal clearly above noise, with secondary frequencies as supporting rather than load-bearing evidence. The Q3 capture (target N=120+ via revised BuiltIn coverage) refreshes this; the lineup is revisited if the warehouse or cloud-platform ranks shift materially.
