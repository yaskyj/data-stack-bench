# Job-posting analysis — methodology spec v0.1

**Version:** 0.1 (draft)
**Date:** 2026-05-10 (v0.1.1 — cloud-platform breakdown elevated to headline output, lineup-wide framing added)
**Status:** Spec only. The analysis itself runs after this is reviewed and locked. Sequencing update: this analysis now runs *before* ADR-001 (orchestrator), not in parallel — the lineup informs orchestrator constraints.

---

## Why this exists

Stack #2 (and #3, #4) for the comparative test bench should be chosen by what data teams in the anchor buyer profile actually use, not by my priors or vendor-funded "state of the modern data stack" reports.

The strong prior at v0.1 of `../task-set.md` was that Stack #2 would be Snowflake-based with a fully-managed orchestrator. Maybe — but the prior is doing too much work. The whole point of the comparative test bench is comparative truth grounded in the buyer's reality. The selection of which stacks to test should follow the same rule.

The analysis itself is also content: "I read 150 data engineering job postings filtered to Series A through mid-market companies and here's what teams are actually building" is a strong public post and a refresh-quarterly artifact.

## What this analysis is

A frequency-and-co-occurrence analysis of stack components mentioned in real job postings filtered to the anchor buyer profile, run quarterly, producing:

- A ranked list of stack components by mention frequency, broken out by component type (warehouse, transformation, orchestrator, etc.)
- A co-occurrence matrix showing which components cluster together in postings (e.g., "Snowflake + dbt + Airflow" frequency vs. "Snowflake + dbt + Dagster").
- A short narrative interpretation: what this implies for which Stack #N to build next, and what shifted since the prior quarter's run.

## What this analysis is not

- Not a survey of practitioners. Job postings overrepresent what hiring managers think they need, not what teams use day-to-day. That's a feature for this purpose: hiring-manager belief is what this project's content reaches and what consulting buyers ask about.
- Not a market-share analysis. We're counting *mentions in postings filtered to the buyer profile*, not vendor revenue or seat count.
- Not predictive of where the market is going. It's a snapshot of what currently-hiring teams want a hire to know. Trends emerge from quarterly refresh, not from any single snapshot.
- Not exhaustive. 150 postings is enough for tight signal on the top ~20 components and rough signal on the next 20; below that, the noise floor swallows the data.

## Sources and weighting

Four candidate sources, three included:

**Wellfound (formerly AngelList Talent) — primary.** Startup-focused, often more authentic descriptions written by founders or hiring engineers, strong signal on Series A/B exactly inside the anchor buyer profile. Weight: high.

**Hacker News "Who's Hiring" monthly threads — primary.** Engineer-written job postings, very high content quality, low HR/recruiter padding, but skewed to YC/SV companies. Strong signal precisely because the descriptions name specific tools. Weight: high.

**LinkedIn — secondary, for breadth.** Highest volume but lowest content quality (HR-written, padded with boilerplate). Best used for company-size filtering and for reaching mid-market postings that don't appear on Wellfound or HN. Weight: medium. Use with stronger normalization filtering.

**Indeed — excluded.** Volume is high but signal is poor. Heavy on agencies and reposts, and the descriptions skew toward role responsibilities rather than stack specifics. Excluded from v0.1 of this analysis. Revisit if the other three don't yield enough postings for the mid-market end of the buyer profile.

**Source mix target for the quarterly run:**
- Wellfound: ~50 postings
- HN Who's Hiring: ~50 postings (typically pulled from the most recent two threads)
- LinkedIn: ~50 postings

Source weighting in the final analysis: each posting counts as one observation regardless of source. The narrative interpretation calls out where one source disagrees with another (e.g., "Snowflake is mentioned in 70% of LinkedIn postings but 40% of HN postings — likely a corporate-vs-startup divergence, not a measurement artifact").

## Inclusion filters

Apply in order. A posting that fails any filter is excluded.

**Company stage / size.**
- Include: 50–250 employees. Include 250–500 if the posting clearly describes the data team as small (1–5 people), since at that company size the data function is sometimes still in the buyer-profile shape.
- Exclude: <50 (founder-as-data-team profile) and >500 (likely has dedicated platform team).
- Where employee count isn't explicit: use LinkedIn company-size band, Wellfound funding-stage signal (Series A/B presumed 50–150, Series C presumed 100–300), or a one-sentence judgment from the company description.

**Role title / function.**
- Include: Data Engineer, Senior Data Engineer, Analytics Engineer, Senior Analytics Engineer, Data Platform Engineer, Senior Data Platform Engineer, Staff Data Engineer (in companies <250).
- Conditionally include: Data Architect (only if the description shows hands-on responsibilities, not pure design oversight). Machine Learning Engineer (only if the description includes data pipeline / feature engineering responsibilities — pure ML inference roles excluded). Data Scientist (excluded — different role; their tooling preferences don't tell us about stack composition).
- Exclude: Director / Head / VP roles (their stack mentions are abstracted), Principal-only roles in 250+ companies, BI Developer / Tableau Specialist (too narrow), data analyst / BI analyst (consumer of stack, not builder).

**Seniority.**
- Include: mid-level through senior. Use 3+ years required experience as a rough cutoff.
- Exclude: junior / new grad postings — they often list aspirational stack names rather than what the team actually uses.

**Geography.**
- Include: US, Canada, UK, EU (English-language postings only). Remote postings count if the company is headquartered in one of those regions.
- Exclude: APAC and LATAM for v0.1, not because the data is uninteresting but because stack patterns there sometimes diverge for reasons (cloud vendor availability, data residency law) the buyer profile doesn't cover. Revisit at v0.3.

**Industry.**
- Include: SaaS, fintech-software (lending platforms, neobanks, BNPL), e-commerce platforms, marketplaces, healthtech-software (the software side, not provider-care), edtech, devtools.
- Conditionally include: regulated fintech (banks, brokerages) only if the description doesn't lean heavily on regulatory specifics; otherwise the stack choices are dominated by compliance constraints orthogonal to the buyer profile.
- Exclude: defense, healthcare-provider operations, government, traditional finance trading systems, oil/gas — different compliance regimes, different stack patterns.

**Posting freshness.**
- Include: posted within the last 60 days at time of capture.

## Target N: 150 postings

**Rationale.**

100 postings is enough for tight confidence intervals on the top of the list (Snowflake, dbt, Airflow as components mentioned in 50%+ of postings) but noisy on the tail (Dagster vs. Prefect, OpenMetadata vs. DataHub, where each shows up in 5–15% of postings).

200 postings gives marginally tighter CIs on the tail but the marginal cost in research time vs. the marginal information gain isn't worth it — and at 200 the analysis bleeds into "this isn't a side project anymore."

150 postings is the sweet spot:
- ~50 from each high-quality source × the mix above.
- Tight enough CIs on the top 20 components (a component mentioned in 30 postings ± 5 has a margin of error around ±5 percentage points at 95% confidence — useful).
- Enough sample to break out by company stage if patterns diverge: ~75 in the Series A/B end, ~75 in the mid-market end. Each subgroup is roughly the size of a 100-posting full sample with somewhat looser CIs — usable but not strong.
- A research effort that fits in roughly 8–12 hours of focused capture time per quarter, which keeps the cadence sustainable.

If after the first run, signal is too noisy at the tail (the 5–15% range), bump to 200 next quarter. Don't pre-decide that — let the v0.1 run inform it.

## Extraction schema

Every posting that passes filters yields one row. Captured fields:

| Field | Type | Notes |
|---|---|---|
| `posting_id` | string | Hash of source URL + posting date |
| `source` | enum | `wellfound`, `hn_whoishiring`, `linkedin` |
| `source_url` | string | Permalink where possible; HN comment anchor for HN |
| `captured_date` | date | When the posting was extracted |
| `posting_date` | date | When the posting was published, if discoverable |
| `company_name` | string | |
| `company_size_band` | enum | `50-100`, `100-250`, `250-500-conditional` |
| `company_stage_signal` | enum | `series-a`, `series-b`, `series-c`, `bootstrapped`, `mid-market`, `unknown` |
| `industry` | enum | Controlled vocabulary from the include list |
| `role_title_raw` | string | Verbatim from posting |
| `role_title_normalized` | enum | `data_engineer`, `analytics_engineer`, `data_platform_engineer`, `mle_with_data_focus`, `data_architect_handson` |
| `seniority` | enum | `mid`, `senior`, `staff` |
| `geo` | enum | `us`, `canada`, `uk`, `eu`, `remote_us_hq`, `remote_eu_hq` |
| `stack_mentions_raw` | text | Verbatim copy of the "tools you'll use" or equivalent paragraph(s) |
| `stack_components_normalized` | array of strings | Normalized component names (see taxonomy below) |
| `notes` | text | Free-text observations (e.g., "team is hiring its first data engineer," "explicitly mentions migrating off Redshift") |

## Component taxonomy and normalization

This is the hard part. Job postings name tools inconsistently. "We use Airbyte for ELT" and "We use Fivetran" both map to "managed ELT," but they should also be tracked individually. The taxonomy is two-level: **component category** (the role) and **component instance** (the specific tool).

**Component categories (closed list):**

1. Cloud platform — `aws`, `gcp`, `azure`, `multicloud`
2. Warehouse / lakehouse / lake — `snowflake`, `bigquery`, `redshift`, `databricks`, `athena`, `duckdb`, `postgres_as_warehouse`, `clickhouse`, `motherduck`
3. Open table format — `iceberg`, `delta`, `hudi`, `parquet_only`
4. Transformation — `dbt_core`, `dbt_cloud`, `sqlmesh`, `dataform`, `dagster_assets_python`, `custom_python`
5. Orchestration — `airflow`, `mwaa`, `dagster`, `prefect`, `temporal`, `dbt_cloud_scheduler`, `step_functions`, `cron_or_homegrown`
6. Ingestion / ELT — `fivetran`, `airbyte_oss`, `airbyte_cloud`, `meltano`, `stitch`, `hevo`, `custom_python`, `singer_taps`
7. CDC — `debezium`, `dms`, `fivetran_cdc`, `airbyte_cdc`, `kafka_connect`
8. Streaming / event broker — `kafka`, `msk`, `kinesis`, `pubsub`, `confluent_cloud`, `redpanda`, `none`
9. BI — `looker`, `tableau`, `powerbi`, `metabase`, `lightdash`, `mode`, `sigma`, `hex`, `preset_superset`, `omni`
10. Reverse ETL — `hightouch`, `census`, `polytomic`, `custom`
11. Semantic layer — `dbt_semantic_layer`, `cube`, `metricflow`, `looker_lookml`, `none`
12. Catalog / governance — `openmetadata`, `datahub`, `atlan`, `collibra`, `unity_catalog`, `dbt_docs_only`, `none`
13. Observability / data quality — `dbt_tests`, `elementary`, `re_data`, `monte_carlo`, `bigeye`, `soda`, `great_expectations`, `acceldata`, `none`
14. IaC — `terraform`, `cdk`, `pulumi`, `cloudformation`, `none_explicit`
15. CI/CD — `github_actions`, `gitlab_ci`, `circleci`, `jenkins`, `dbt_cloud_ci`
16. Experiment tracking / model registry — `mlflow`, `weights_and_biases`, `neptune`, `dvc`, `none`
17. Model serving — `sagemaker`, `vertex_ai`, `modal`, `bentoml`, `seldon`, `kserve`, `custom_fastapi`, `cloud_run`
18. Vector DB — `pgvector`, `pinecone`, `weaviate`, `qdrant`, `chroma`, `opensearch`, `elasticsearch`
19. LLM provider — `openai`, `anthropic`, `bedrock`, `azure_openai`, `vertex_genai`, `together`, `groq`, `cohere`
20. RAG framework — `langchain`, `llamaindex`, `haystack`, `none_explicit`
21. ML eval — `ragas`, `deepeval`, `langsmith`, `arize`, `evidently`, `whylabs`, `custom`

A posting that lists "Snowflake, dbt, Airflow, Looker" yields four normalized component instances across four categories. A posting that says "modern data stack" without naming components yields none — vague language is excluded by definition.

**Normalization rules.**

- Plain-text matching is fuzzy and the posting paragraph is short. Manual extraction is faster and more accurate than automating it for N=150. Don't build a parser; just read and tag. Quarterly cadence makes this acceptable.
- A component mentioned as "we're migrating away from X to Y" counts as **Y** (a vote for Y), not X. Capture in the `notes` field.
- A component mentioned as "experience with X is a plus" counts at half-weight (track separately in a `stack_components_aspirational` field if useful; for v0.1 just capture in notes).
- A component category absent from the posting is **not** an absence vote — postings are short and miss things. Co-occurrence and frequency analysis only count positive mentions.
- If a posting says "ELT pipeline" without naming the tool, that's a vote for "uses some ELT tool, instance unknown" — capture in notes; do not impute.

## Analysis outputs

For each quarterly run:

1. **Cloud-platform breakdown.** Percentage of postings that mention each major cloud (AWS, GCP, Azure, multicloud, none-stated). Reported as a headline finding, not buried in the general frequency table — the cross-cloud distribution is one of the most consequential things the analysis tells us, because it informs which clouds the test bench's stack lineup needs to cover.
2. **Frequency table by category.** For each component category, the percentage of postings that mention each instance. Sorted descending, with confidence intervals.
3. **Co-occurrence top-10.** The ten most common (warehouse, transformation, orchestrator) triples. The 10 most common (catalog, observability) pairs. The 10 most common (vector DB, LLM provider) pairs. Additionally: the 10 most common (cloud, warehouse, orchestrator) triples — because cloud × warehouse co-occurrence is what determines whether "Snowflake on AWS" and "Snowflake on Azure" should be treated as one or two test-bench targets.
4. **Stage breakout.** Frequency tables re-run on the Series A/B subset (~75 postings) and the mid-market subset (~75 postings). Differences highlighted, including whether cloud-platform distribution diverges across the band (a real possibility — mid-market skews Azure/Fabric more than Series A/B does).
5. **Quarter-over-quarter delta.** From the second run onward: which components gained or lost frequency vs. the prior quarter, in percentage-point terms.
6. **Stack #N recommendation + lineup confirmation.** A two-paragraph narrative interpretation: what this run implies for the test bench's stack lineup as a whole — which stacks to add, swap, or defer — and what was surprising vs. expected. The first run specifically confirms (or rearranges) the indicative lineup locked in CLAUDE.md: Stack #2 Snowflake-on-AWS, Stack #3 BigQuery, Stack #4 Databricks, Stack #5 Fabric+Power BI on Azure.

The first four outputs are tabular and live in the repo as CSVs. The fifth and sixth are narrative — they go in the corresponding quarterly blog post.

## Refresh cadence

Quarterly. Aligned to the calendar quarter so the post lands on a predictable cadence ("Q3 2026 modern data stack: what's in the postings"). If the first run reveals more noise than expected, consider biannual instead — but quarterly is the preferred default because:

- Stack adoption shifts slowly enough that quarterly captures real movement.
- The post itself is content the project needs anyway.
- The quarterly research effort is a forcing function for staying close to the market the project serves.

## How this feeds Stack #N selection

The first run informs the *entire* indicative lineup (Stacks #2–#5), not just Stack #2 selection — locked in CLAUDE.md as Snowflake-on-AWS, BigQuery, Databricks, Fabric+Power BI on Azure, but explicitly subject to rearrangement based on this analysis. The criteria for "this stack should be in the lineup":

- The (cloud, warehouse, transformation, orchestrator) tuple shows up with material frequency in the buyer-profile postings — meaningfully above the noise floor.
- The tuple is materially different from the other stacks already in the lineup (otherwise the comparison is uninteresting). The cross-cloud axis is one of the differentiation dimensions: a lineup of five Snowflake-on-AWS variants is not comparative.
- The lineup as a whole spans the major-cloud distribution the analysis surfaces. If 30%+ of postings are Azure, an Azure stack belongs in the lineup; if Azure is 5%, it may not.
- At least one component in each stack is something I have a real opinion on the tradeoffs for, so that the resulting comparative writeups carry argued perspective, not just measurement.

Subsequent quarterly runs revisit the lineup: a component that appears in 5% of postings in Q3 and 15% in Q4 is a candidate to add or swap; a stack already in the lineup whose components dropped sharply is a candidate to deprioritize.

## What this methodology is *not yet*

- Does not yet specify the exact capture protocol (browser-based copy/paste vs. semi-automated scraping). Manual capture is the v0.1 default; automation is a v0.2 question only if N grows past 200.
- Does not yet have a defined storage shape for the captured data (CSV in repo vs. SQLite vs. DuckDB file). Default to CSV in repo for v0.1; revisit if the analysis becomes complex.
- Does not yet specify how to handle postings that explicitly say "we're hiring you to choose the stack" — a real signal for the consulting wedge but a noise source for component-frequency counts. v0.1: exclude from frequency counts but capture as a separate list ("companies actively choosing their stack right now") for outreach purposes.

## Versioning

- **v0.1 (2026-05-10):** Initial methodology. 150 postings, three sources, two-level component taxonomy, quarterly cadence.
- **v0.1.1 (2026-05-10, same day):** Cloud-platform breakdown promoted to a headline output. Cross-cloud co-occurrence (cloud × warehouse × orchestrator) added. "Stack #N selection" section reframed to inform the full indicative lineup (Stacks #2–#5), not just Stack #2.
- **v0.2 (target: after first analysis run):** Refinements based on what was actually noisy vs. clean in the first capture. Likely revisions: source mix, component taxonomy additions, automation decision.
