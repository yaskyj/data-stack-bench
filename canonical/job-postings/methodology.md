# Job-posting analysis — methodology spec v0.1.3

**Version:** 0.1.3 (draft)
**Date:** 2026-05-11
**Status:** First capture (2026-Q2) executed against v0.1.2 of this spec; v0.1.3 incorporates the findings from that run. Future quarterly runs use v0.1.3. Sequencing: this analysis runs *before* ADR-001 (orchestrator), not in parallel — the lineup informs orchestrator constraints.

**v0.1.3 changes from v0.1.2 (post first-run revisions):**
- **HN per-thread keep rate is ~3-5 postings, not the ~25 the v0.1 source mix implicitly modeled.** Root cause: the modern "Ask HN: Who is hiring?" format is dominated by multi-role aggregator posts — HN comments that list several openings and link out to an ATS without embedding the JD body. Even when a role/industry/size combination passes the inclusion filters, the stack-mentions paragraph (the load-bearing extraction for this analysis) isn't in the comment text. The 2026-Q2 run had 4 HN threads in scope by the 60-day freshness window (only the most recent two threads fully in scope; the third partially, the fourth out); 1414 raw comments → 84 mechanical-filter passes → 7 LLM keeps. About one in 200 raw HN comments yields a usable row.
- **HN thread lifespan is ~14 days.** Threads stop accumulating top-level postings ~2 weeks after they open. With a 60-day freshness cutoff, at most 2 full threads + part of a third land inside the window. Pulling older threads doesn't help — their late-cycle comments are still older than 60 days. This means HN's contribution to any quarterly run is bounded above ~10-15 keeps regardless of effort.
- **BuiltIn yields ~10-15x HN per candidate processed.** 2026-Q2 run: 303 raw → 213 mechanical-pass → ~33 LLM keeps. The cause is structural: BuiltIn detail pages embed the full JD in a schema.org JobPosting JSON-LD block, so the stack paragraph is always present. BuiltIn deserves to be the workhorse source, not the third leg.
- **Source mix target rebalanced.** Old (v0.1.2): 50 HN / 50 BuiltIn / 50 Wellfound = 150 total. New (v0.1.3): 10 HN / 100 BuiltIn / 40 Wellfound = 150 total, with BuiltIn carrying the load. HN is kept in the mix because (a) HN postings sometimes name stack components that BuiltIn JDs don't (HN is engineer-written, BuiltIn is HR-written), and (b) the YC-startup skew is a useful counterweight to BuiltIn's mid-market skew. But its weight is much smaller.
- **Wellfound deferred to v0.2.** wellfound.com sits behind DataDome bot mitigation; every public URL returns 403 without a JS-executing browser. The methodology v0.1.2 fallback ("Claude in Chrome with a logged-in session") works but is fragile and time-consuming. For 2026-Q2 we accepted 40 keeps from HN+BuiltIn rather than spend additional effort on a third source whose marginal contribution to the headline aggregations is small at this sample size. v0.2 revisits: if N=150 isn't reached after Q3 BuiltIn runs more aggressively, invest in Wellfound automation or a paid aggregator (Coresignal/JSearch).
- **N=150 target softened to N=120-150.** First run yielded N=40, well below target. Future quarters with revised BuiltIn coverage (more pages, more role-search profiles) should hit N=120+. Tail-component confidence intervals are looser at N=40 than at N=150, but headline aggregations (cloud %, top warehouse/orchestrator/transformation) are tight enough at N=40 to make Stack #N selection decisions. Documented in the Q2 writeup; tighten in Q3.

**v0.1.2 changes (kept for the record):**
- **LinkedIn → BuiltIn as the third source.** LinkedIn's API is gated behind a Talent Solutions partnership program and self-serve access doesn't exist. Aggregator services (Coresignal, Bright Data, JSearch on RapidAPI) sit in ToS gray and return normalized field sets that strip the "tools you'll use" paragraph this analysis depends on. BuiltIn (builtin.com) is a mid-market tech-focused job board with employee-size filtering, plain HTML, no auth wall, and substantially better mid-market coverage of the anchor buyer profile than LinkedIn would have provided. `linkedin` is reserved in the source enum for future use but not used in v0.1.
- **Manual capture → Python pipeline + LLM-assisted extraction.** v0.1's "don't build a parser; just read and tag" reasoning was written assuming a solo builder with no agent tools. With Cowork + Claude Code + Anthropic API available, a programmatic pipeline is faster, runs unattended quarterly, and is itself a portfolio artifact on-brand for the project. The pipeline preserves verbatim posting text in `stack_mentions_raw` (so the source-of-truth is not lossy), populates normalized fields via LLM extraction with confidence scores, and flags ambiguous cases for human spot-check. A ≥15% random sample is human-reviewed before any analysis output is generated; if sample agreement is below 95% the pipeline is corrected and the run repeats. The blog post framing for this run is "I built a small data pipeline to map the modern data stack hiring market" — better content than "I read 150 postings."

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

**BuiltIn (builtin.com) — primary, workhorse source (v0.1.3).** Tech-focused job board with strong coverage of 50–250-employee mid-market companies in NYC/SF/Chicago/LA/Austin. Plain HTML pages, employee-size and role-type filtering, no auth wall. Every detail page embeds the full JD in a schema.org JobPosting JSON-LD block, so the stack-mentions paragraph is always present — this is structurally why BuiltIn yields ~10-15× HN per candidate processed. Promoted to workhorse at v0.1.3 after first capture; replaces LinkedIn at v0.1.2 (see v0.1.2 changes above for the LinkedIn drop rationale).

**Wellfound (formerly AngelList Talent) — primary in principle, deferred to v0.2 in practice.** Startup-focused, often more authentic descriptions written by founders or hiring engineers, strong signal on Series A/B exactly inside the anchor buyer profile. **At v0.1.3, deferred:** wellfound.com sits behind DataDome bot mitigation; every public URL returns 403 without a JS-executing browser. The Claude in Chrome fallback works but is fragile and time-consuming. Skipped in the 2026-Q2 capture; revisit at v0.2 if N remains sample-size-limited after Q3.

**Hacker News "Who's Hiring" monthly threads — supplementary (v0.1.3).** Engineer-written job postings, very high content quality, low HR/recruiter padding, but skewed to YC/SV companies. Was "primary" at v0.1.2; demoted to supplementary at v0.1.3 because per-thread keep rate is structurally ~3-5 (multi-role aggregator format where comments link to an ATS without embedding the JD), and HN thread lifespan ~14 days means the 60-day freshness window can capture at most ~2.5 full threads per quarter. Ceiling ~10-15 keeps per quarter regardless of effort. Fetched via the public HN Algolia API.

**Indeed — excluded.** Volume is high but signal is poor. Heavy on agencies and reposts, and the descriptions skew toward role responsibilities rather than stack specifics. Excluded from v0.1 of this analysis. Revisit if the other three don't yield enough postings for the mid-market end of the buyer profile.

**LinkedIn — reserved, not used in v0.1.** API access is gated; aggregator services strip the fields this analysis depends on. Reconsidered at v0.2 if Coresignal or a similar source becomes affordable and a richer field set is available.

**Source mix target for the quarterly run (v0.1.3, post first-run revision):**
- BuiltIn: ~100 postings (workhorse — full JDs in JobPosting JSON-LD)
- Wellfound: ~40 postings (when accessible; deferred at v0.1)
- HN Who's Hiring: ~10 postings (per-thread keep rate is structurally low; ceiling ~15)

Total target: ~150 postings, same N as v0.1.2 but redistributed by observed yield. **v0.1.2's original 50/50/50 mix was wishful thinking** — see v0.1.3 changes block above for the data behind this rebalance.

Source weighting in the final analysis: each posting counts as one observation regardless of source. The narrative interpretation calls out where one source disagrees with another (e.g., "Snowflake is mentioned in 70% of BuiltIn postings but 40% of HN postings — likely a corporate-vs-startup divergence, not a measurement artifact").

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

150 postings is the sweet spot in principle:
- Source-mix-weighted per the v0.1.3 targets (100 BuiltIn / 40 Wellfound / 10 HN). Earlier versions of this section assumed ~50 from each high-quality source; first-run reality forced the rebalance.
- Tight enough CIs on the top 20 components (a component mentioned in 30 postings ± 5 has a margin of error around ±5 percentage points at 95% confidence — useful).
- Enough sample to break out by company stage if patterns diverge: ~75 in the Series A/B end, ~75 in the mid-market end. Each subgroup is roughly the size of a 100-posting full sample with somewhat looser CIs — usable but not strong.
- A research effort that fits in roughly 8–12 hours of focused capture time per quarter, which keeps the cadence sustainable.

**First-run reality (2026-Q2):** N=40 actual, well below target. Causes: HN per-thread yield is ~3-5 (not 25); Wellfound deferred to v0.2 (DataDome blocked the public path). Headline aggregations (cloud %, top warehouse, top orchestrator) are still tight enough to make Stack #N selection decisions; tail-of-distribution components (5–15% range) carry wider error bars. Future quarters should hit 120-150 with revised BuiltIn coverage (more pages, more role-search profiles); revisit Wellfound automation if N stays below 120 after Q3.

## Extraction schema

Every posting that passes filters yields one row. Captured fields:

| Field | Type | Notes |
|---|---|---|
| `posting_id` | string | Hash of source URL + posting date |
| `source` | enum | `wellfound`, `hn_whoishiring`, `builtin` (`linkedin` reserved, not used in v0.1) |
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

- Extraction is LLM-assisted with verbatim source text preserved (v0.1.2 revision; see "Capture protocol" below). Earlier "don't build a parser, just read and tag" guidance was solo-builder reasoning and is superseded. The pipeline prompts an LLM extractor with the raw posting paragraph and the closed component taxonomy, returning a normalized array plus per-mapping confidence. Low-confidence rows route to the human spot-check queue.
- A component mentioned as "we're migrating away from X to Y" counts as **Y** (a vote for Y), not X. Capture in the `notes` field. The extractor prompt explicitly handles this case.
- A component mentioned as "experience with X is a plus" counts at half-weight (track separately in a `stack_components_aspirational` field if useful; for v0.1 just capture in notes).
- A component category absent from the posting is **not** an absence vote — postings are short and miss things. Co-occurrence and frequency analysis only count positive mentions.
- If a posting says "ELT pipeline" without naming the tool, that's a vote for "uses some ELT tool, instance unknown" — capture in notes; do not impute.

## Capture protocol (v0.1.2)

Capture is a Python pipeline in `canonical/job-postings/pipeline/`. Three fetchers plus a shared extractor and CSV writer.

**Fetchers (per source):**

- `fetch_hn.py` — pulls "Who is hiring" thread comments via the public HN Algolia API (`hn.algolia.com/api/v1/...`). Configurable thread list (default: most recent two monthly threads). Output: one JSONL per thread with `{posting_id, source_url, posting_date, raw_text}` per comment.
- `fetch_builtin.py` — scrapes BuiltIn search-result pages plus per-posting detail pages via HTTP + BeautifulSoup. Search filters baked into the URL: company size 50–250, role types in the include list, geo US + remote. Plain HTML; no auth required. Output: same JSONL schema.
- `fetch_wellfound.py` — *not yet implemented (deferred at v0.1.3).* Intended: Wellfound (formerly AngelList) public job listings via HTTP + BeautifulSoup where the listing is accessible without login; fall back to Claude in Chrome for sessions that require auth. **Probed 2026-05-11:** wellfound.com is gated by DataDome bot mitigation — every public URL returns 403 to non-JS clients. The Claude-in-Chrome fallback would be the path forward, but for the 2026-Q2 capture we accepted N=40 from HN+BuiltIn rather than invest the time. Revisit at v0.2.

**Filter pass.** `filter_postings.py` reads the raw JSONLs and applies the v0.1.2 inclusion filters (company stage/size, role title/function, seniority, geography, industry, posting freshness). Each posting gets `included: bool` and `exclude_reason: str` recorded. Exclusions are kept in the file (not deleted) so the filter pass is auditable.

**Extraction pass.** `extract_fields.py` calls a provider-agnostic LLM client (`llm_client.py`, built on LiteLLM) per included posting. Provider is configured via `LLM_PROVIDER` env var; supported defaults include `anthropic` (direct API), `bedrock` (Anthropic models on AWS), `openai`, and `vertex` (Anthropic models on GCP). Any LiteLLM-supported provider works. The system prompt encodes the closed component taxonomy from the section above and instructs the model to return strict JSON conforming to the row schema. The raw posting paragraph is preserved verbatim in `stack_mentions_raw`. Low-confidence extractions (model returns `confidence: low` on any field) are tagged for the spot-check queue. This provider-agnostic design is deliberate: the project is cross-cloud, and the pipeline must be reproducible by anyone with credentials for any one of the supported providers — not just by holders of an Anthropic API key. The README documents per-provider setup including AWS Bedrock model-access gating.

**Spot-check.** A ≥15% random sample of extracted rows is human-reviewed. If sample agreement with the model output is <95%, the extractor prompt is corrected and the pass is re-run. Sample-check results are committed to `captures/2026-q2/spot-check.md` for audit.

**CSV writer.** `load_csv.py` appends rows to `captures/2026-q2/postings.csv`. Idempotent on `posting_id`.

**Pipeline-as-content.** The pipeline itself is a deliverable: a small, real data pipeline that ingests heterogeneous web sources, applies filtering, runs LLM-based extraction, validates against a human-labeled sample, and emits a comparative dataset. This is on-brand for the project — a working demonstration of the practice the test bench is built to compare. The accompanying blog post leans on this framing.

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

- Storage shape for the captured data: CSV in repo for v0.1.2. Revisit (SQLite, DuckDB file) if the analysis becomes complex or the row count grows past a few thousand.
- Handling of postings that explicitly say "we're hiring you to choose the stack" — a real signal for the consulting wedge but a noise source for component-frequency counts. v0.1.2: exclude from frequency counts but route to a separate list (`captures/2026-q2/stack-choosing-companies.md`) for outreach purposes.
- Wellfound integration: probed 2026-05-11, found DataDome bot mitigation blocks all public URLs. Path forward is Claude in Chrome with a logged-in session, deferred to v0.2 (see Sources section). Decision criteria for revisiting: if Q3 BuiltIn-heavy capture lands below N=120, invest the time on Wellfound automation; if N=120+, accept the two-source mix and leave Wellfound on the bench.

## Versioning

- **v0.1 (2026-05-10):** Initial methodology. 150 postings, three sources (Wellfound + HN + LinkedIn), manual capture, two-level component taxonomy, quarterly cadence.
- **v0.1.1 (2026-05-10, same day):** Cloud-platform breakdown promoted to a headline output. Cross-cloud co-occurrence (cloud × warehouse × orchestrator) added. "Stack #N selection" section reframed to inform the full indicative lineup (Stacks #2–#5), not just Stack #2.
- **v0.1.2 (2026-05-11):** LinkedIn replaced by BuiltIn as the third source (LinkedIn API gated, aggregators strip needed fields, BuiltIn is plainer and has better mid-market coverage). Manual capture replaced by a Python pipeline with LLM-assisted extraction + ≥15% human spot-check, verbatim raw text preserved. Pipeline itself reframed as on-brand content for the project.
- **v0.1.3 (2026-05-11, same day, post first capture):** Source mix rebalanced after observed per-source yields: HN per-thread keep rate is ~3-5 (multi-role aggregator format, low signal density), BuiltIn is ~10-15x richer per candidate (JD in JSON-LD), Wellfound deferred to v0.2 (DataDome bot mitigation makes the public-listing path infeasible without browser automation). New target mix: 100 BuiltIn / 40 Wellfound / 10 HN. Target N softened to 120-150 in recognition of first-run reality. First capture (2026-Q2) landed N=40 with two sources.
- **v0.2 (target: after Q3 capture):** Decisions deferred: (a) whether to invest in Claude in Chrome automation for Wellfound or a paid aggregator (Coresignal/JSearch); (b) component taxonomy additions from observed un-mapped tools (e.g., LangGraph, QLoRA — currently captured in `notes`); (c) spot-check threshold tuning if the v0.1.2 ≥15% / 95% bar is wrong; (d) whether to expand the role-keyword filter to capture borderline DPE-flavored postings the v0.1 regex misses.
