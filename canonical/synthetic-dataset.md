# Synthetic dataset spec + validation query suite v0.1

**Version:** 0.1 (draft)
**Date:** 2026-05-13
**Status:** Living document. Gates Stack #1 measurement. v1.0 lands after Stack #1 implements against this spec end-to-end and the queries-vs-tolerance contract is calibrated against actual cross-engine drift.

---

## What this document is

A defended specification of the canonical synthetic dataset and validation query suite that every candidate stack in `data-stack-bench` ships against. Two things are pinned here:

1. **A deterministic, seedable synthetic SaaS company** at three reference scales (S / M / L), shaped as the anchor buyer's actual data surface: an operational Postgres source-of-truth, two SaaS-source emulations (HubSpot- and Stripe-shaped REST payloads), a first-party event stream, a daily partner CSV drop, and an unstructured document corpus.
2. **A validation query suite** — 15 queries spanning revenue, retention, engagement, operations, and attribution — that every stack must answer to within a stated tolerance off the same generated dataset at the same scale.

Together they make the bench's two load-bearing claims verifiable by a stranger. Without them, "Stack A cost $X to run task 3.1" is unfalsifiable, and "Stack A and Stack B agree on the numbers" is a vibe rather than a measurement.

The implementation of the generator itself is Phase 1 work. This document specifies the contract the generator must satisfy. The generator emits raw landed data in the source-shapes below; each candidate stack ingests, transforms, and serves that data through its own idiomatic pipeline, then answers the validation queries.

## What this document is *not*

- Not the generator code. Phase 1 work. The spec is implementation-language-agnostic; reference implementation will likely be Python + Faker + a deterministic PRNG-seeded distributional layer, but that's not pinned here.
- Not a benchmark of the dataset itself (no TPC-style absolute scale claims). The point is comparative truth across stacks, calibrated to the anchor buyer's data shape — not "how many TPC-H queries per second."
- Not closed. Stack #1 implementation will surface generator-quality issues that send this back to v0.2 (e.g., distributions that look real until a stack's analyst-facing dashboard makes the artifice visible, or query results whose tolerance bands are wrong).

## Anchor buyer reminder

The dataset is shaped for the anchor buyer profile defined in `task-set.md` — a Series A through mid-market SaaS company, 50–250 employees, 1–3 data engineers + 1 data scientist, tens of GB to low TBs total, tens of millions of events per month with growth toward 10× over 18 months. Source mix: one operational Postgres, two SaaS sources (CRM-shaped + payments-shaped), first-party events, one partner CSV. Stakeholders span revenue, product, customer success, finance, exec. The dataset's scales and shape are calibrated to this profile; the queries are the questions this buyer actually asks.

## Determinism and reproducibility contract

The generator MUST satisfy these properties. Without them, the comparison is not falsifiable.

- **Single root seed.** A single integer seed parameterizes the entire dataset. Same seed → byte-identical output across runs, across machines, across operating systems.
- **Deterministic schedule.** The order of generated entities (account creation, user signup, event emission) is reproducible from the seed alone — no wall-clock dependence, no thread-scheduling dependence.
- **Scale-orthogonal seeds.** The same seed at S, M, and L produces datasets where the S dataset is a strict prefix of the M dataset is a strict prefix of the L dataset for the entities they share (i.e., the first 200 accounts in M are the same 200 accounts in S, with identical IDs and identical event histories within the S horizon). This lets a stack tested at S extend to M without regenerating, and lets the validation queries' expected-answer files for S remain valid when L is regenerated.
- **Simulated wall time.** The dataset spans 18 simulated months ending at a fixed simulated "now" (`2026-05-01T00:00:00Z` for v0.1). The generator output is anchored to simulated time, not real time, so a rerun two months later produces the same dataset.
- **Idempotent regeneration.** Re-running the generator with the same seed and scale produces no diff against the prior run.

## Data model

The synthetic SaaS company is a small B2B product (call it "Northwind SaaS" in writeups when a name is needed). Five source surfaces.

### Operational Postgres source-of-truth

Backs the application. Mutates over time. Source for CDC (task 1.2). Tables:

| Table | Purpose | Key columns |
|---|---|---|
| `accounts` | B2B customer accounts (organizations) | `account_id` (uuid), `name`, `plan_id`, `mrr_cents`, `signup_date`, `country`, `status` (`active`, `paused`, `churned`), `created_at`, `updated_at` |
| `users` | Individual users belonging to accounts | `user_id` (uuid), `account_id`, `email` (PII), `name` (PII), `role` (`owner`, `admin`, `member`), `created_at`, `last_login_at`, `status`, `country`, `timezone` |
| `plans` | Pricing plan catalog | `plan_id`, `name` (`free`, `starter`, `growth`, `scale`, `enterprise`), `price_cents`, `billing_interval` (`monthly`, `annual`), `features_json`, `effective_from`, `effective_to` |
| `subscriptions` | Account subscriptions to plans (current state) | `subscription_id`, `account_id`, `plan_id`, `started_at`, `canceled_at`, `status`, `mrr_cents` |
| `subscription_events` | State-transition log for SCD-2 testing | `event_id`, `subscription_id`, `event_type` (`created`, `upgraded`, `downgraded`, `canceled`, `reactivated`), `occurred_at`, `from_plan_id`, `to_plan_id`, `mrr_delta_cents` |
| `invoices` | Billing artifacts | `invoice_id`, `account_id`, `subscription_id`, `amount_cents`, `currency`, `status`, `issued_at`, `paid_at`, `due_at` |
| `payments` | Payment attempts and outcomes | `payment_id`, `invoice_id`, `amount_cents`, `status` (`succeeded`, `failed`, `refunded`), `processed_at`, `method` (`card`, `ach`, `wire`) |
| `support_tickets` | Customer support cases | `ticket_id`, `account_id`, `user_id`, `opened_at`, `first_response_at`, `closed_at`, `priority` (`low`, `med`, `high`, `urgent`), `category`, `status`, `resolution_minutes` |
| `feature_flags` | Per-account entitlements (entitlement audit trail) | `flag_id`, `account_id`, `flag_name`, `enabled`, `set_at`, `set_by_user_id` |

Mutation behavior: accounts churn, upgrade, downgrade, and reactivate over simulated time; the `subscription_events` table preserves the full state-transition history (the test bench's SCD-2 source). The `plans` table itself has retroactive corrections (a plan price changed mid-year and a one-row correction was made the next day) — to exercise task 2.4's retroactive-correction-with-history requirement. PII columns are explicitly tagged: `users.email`, `users.name` are PII; `users.country`, `users.timezone` are quasi-identifiers.

The generator emits the operational Postgres as a SQL DDL file plus per-table INSERT/UPDATE/DELETE statements timestamped at simulated wall time. A separate derived artifact — a Debezium-shaped CDC stream in JSONL — is also emitted for stacks that exercise replay-from-LSN.

### HubSpot-shaped REST source emulation

Partial mirror of accounts and users, written by the sales team in HubSpot, drifting from the operational source in realistic ways (sales reps update contact info that doesn't sync back; companies created in HubSpot that never become accounts; companies missing in HubSpot that are accounts). This drift is *intentional* — reconciling it is an analytics-engineering task the buyer actually runs.

Resources:

- `contacts` — partial mirror of `users` plus prospects who never signed up
- `companies` — partial mirror of `accounts` plus prospects
- `deals` — sales pipeline objects, some that close into an `account`, some that don't
- `deal_pipelines` — pipeline-stage definitions
- `activities` — calls, emails, meetings logged against contacts and deals

Output shape: one JSONL file per resource type per simulated day, in HubSpot's documented API response envelope (results array + paging cursor). Generator simulates pagination (page size 100, multi-page responses for any day with >100 entities).

### Stripe-shaped REST source emulation

Partial mirror of subscriptions, invoices, and payments. Drifts in different ways: webhook delivery is not guaranteed in order; some payments hit Stripe before the corresponding invoice's webhook fires. Reconciling Stripe-side state against operational-Postgres state is the second of the two synthetic data-reconciliation tasks the buyer runs.

Resources:

- `customers` — mirrors `accounts`
- `subscriptions` — mirrors `subscriptions`
- `invoices` — mirrors `invoices`
- `charges` — payment attempts (mirrors `payments`)
- `payment_methods` — cards and ACH on file

Output shape: JSONL per resource per simulated day, in Stripe's documented API response envelope (`data` array + `has_more` boolean + `starting_after` cursor).

### First-party event stream

Application-emitted events. Schema:

```
event_id        uuid v7        — sortable by emission time
user_id         uuid           — FK to users (sometimes null for pre-signup events)
account_id      uuid           — FK to accounts (sometimes null)
session_id      uuid           — groups events into sessions
occurred_at     timestamp tz   — client-side timestamp
received_at     timestamp tz   — server ingest timestamp
event_name      string         — controlled vocabulary (see taxonomy)
properties      json           — event-specific payload
context         json           — device, ip, user_agent, ip_country, app_version
```

Controlled event vocabulary (v0.1): `page_view`, `signup`, `signup_completed`, `login`, `logout`, `feature_used` (with `feature_name` in properties), `plan_upgraded`, `plan_downgraded`, `subscription_canceled`, `subscription_reactivated`, `invoice_paid`, `invoice_failed`, `support_chat_opened`, `support_chat_closed`, `dashboard_viewed`, `report_exported`, `api_request`, `integration_connected`, `integration_disconnected`.

Late-arrival profile: the difference `received_at - occurred_at` is drawn from a configured distribution where the median is ~5 minutes (network + ingestion latency), p99 ~30 days (mobile clients reconnecting after offline use). Drives task 2.5 (late-arriving facts) and task 1.3 (late-arriving events policy).

Bot/duplicate behavior: 1–3% of emitted events are duplicates (same `event_id`, slightly different `received_at`); a small fraction are bot-shaped (single `user_id` emitting 1000+ events/minute for a short window). Drives task 1.3's bot/duplicate filtering.

Output shape: NDJSON files, Hive-partitioned by `event_date=YYYY-MM-DD/`, one file per partition. The stack's storage layer is responsible for re-landing into Parquet (or its idiomatic format) — the generator emits the raw form a real first-party collector would land.

### Partner CSV drop

A daily marketing ad-spend file delivered by a third-party agency. Schema:

```
date           YYYY-MM-DD
campaign_id    string
channel        enum: google_ads, meta, linkedin, reddit
impressions    integer
clicks         integer
cost_cents     integer
conversions    integer
```

Output shape: one CSV with header per simulated day, named `ad_spend_YYYY-MM-DD.csv`. Generator deliberately seeds errors at a controlled rate (~2% of files): negative `cost_cents`, missing `campaign_id`, malformed date, encoding garble, schema drift (an extra column appearing mid-quarter). Drives task 1.4 (file-drop with bad-file quarantine) and task 6.3 (schema drift detection).

Some files are delivered late or re-delivered with corrected data (partner reissues yesterday's file at 10am with revised numbers). Drives task 2.5 from the file-drop side.

### Document corpus (tasks 1.6 + 9.6)

The unstructured-data surface. Three buckets, all conceptually owned by the SaaS company but managed in different places:

- **Product documentation** — Markdown files describing product features, integrations, and onboarding flows. ~100 / 500 / 2,000 docs at S / M / L. Files are updated over simulated time (some get a few revisions; some get retired and replaced).
- **Internal support knowledge base articles** — Markdown files. Written by the support team for support agents. ~50 / 250 / 1,000 articles. Reference the operational schema (account types, plan features) in a way that lets retrieval-augmented answers ground in current product state.
- **Resolved support ticket transcripts** — JSON files (one per ticket) with structured metadata (ticket_id linking back to `support_tickets`, account_id, opened_at, closed_at, category, priority) and an unstructured `transcript` field containing simulated customer-question / support-answer dialogue. ~200 / 1,000 / 5,000 transcripts.

Each document has metadata: `doc_id`, `source` (`product_docs`, `support_kb`, `support_tickets`), `title`, `path`, `created_at`, `last_modified_at`, `tags` (array), `language` (en for v0.1), `length_tokens` (approximate, deterministic from content), `pii_present` (boolean, deliberately true for some support-ticket transcripts to exercise task 9.6's PII handling).

The corpus mutates: documents are added, revised, and retired across simulated time. The generator emits a `manifest.jsonl` for each scale checkpoint and a `change_log.jsonl` of doc-level mutations between checkpoints. Drives task 1.6's refresh-on-source-change pattern.

**Held-out evaluation sets** (for task 9.6's retrieval + generation eval):

- **Retrieval ground truth.** ~50 / 200 / 500 (Q, source_doc_id, expected_passage_id) triples at S / M / L. Each Q is answerable from exactly one passage in exactly one source doc. The generator emits these to a separate `eval/retrieval/` directory and excludes them from the corpus delivered to the stack's RAG pipeline (i.e., they are held out, not just labeled). Calibrates recall@k metrics.
- **Generation eval.** ~30 / 100 / 200 open-ended Qs at S / M / L, each with a rubric (3–5 scoring dimensions, expected key facts). Used for LLM-as-judge calibration. Includes deliberately ambiguous Qs and Qs where the correct answer is "I don't know based on the available documents" — to test that the stack's RAG pipeline doesn't hallucinate on out-of-corpus questions.

Generation of the held-out sets is deterministic from the seed; the Qs are emitted alongside the corpus but in a separate directory the stack's pipeline is contractually forbidden from reading at ingest time.

## Reference scales

Anchored to the anchor buyer profile. Three scales because (a) S enables CI and laptop development, (b) M sits inside the anchor profile's "now," (c) L is the same buyer ~18 months later after 10× growth.

| Dimension | S | M | L |
|---|---|---|---|
| Accounts | 200 | 4,000 | 40,000 |
| Active users | 1,000 | 20,000 | 200,000 |
| Events / month (steady state) | 100,000 | 10,000,000 | 500,000,000 |
| Total events (18 mo history) | ~1.5M | ~150M | ~7.5B |
| Subscriptions (lifetime) | ~300 | ~6,000 | ~60,000 |
| Invoices (18 mo) | ~3,500 | ~70,000 | ~700,000 |
| Support tickets (18 mo) | ~600 | ~12,000 | ~120,000 |
| HubSpot contacts | ~1,500 | ~30,000 | ~300,000 |
| HubSpot companies | ~400 | ~8,000 | ~80,000 |
| Partner CSV files | 540 (18 mo × 30/mo) | 540 | 540 |
| Product docs | 100 | 500 | 2,000 |
| Support KB articles | 50 | 250 | 1,000 |
| Support ticket transcripts | 200 | 1,000 | 5,000 |
| Retrieval-eval Q&A pairs | 50 | 200 | 500 |
| Generation-eval Qs | 30 | 100 | 200 |
| Approximate total uncompressed bytes | ~500 MB | ~50 GB | ~2.5 TB |

S is the every-pipeline-runs scale — every stack's CI must run end-to-end at S. M is the headline scale for cost comparisons and the bench's default "this is what the buyer looks like." L is the stretch scale — every stack must successfully ingest, but only the cost-relevant tasks (storage, transformation, BI query cost) need full measurements at L. The bench's published cost numbers are reported as three points per task (S / M / L) so the slope of cost-vs-scale is visible, not just a single number.

## Output-format conventions

How the generator lays the data on disk:

- **Operational Postgres:** SQL DDL file (`postgres/schema.sql`) + per-table INSERT/UPDATE/DELETE files timestamped at simulated wall time (`postgres/mutations/YYYY-MM/...`). A loader script applies them in order against a live Postgres to reach any point-in-simulated-time state.
- **CDC stream:** derived from the mutation log. Debezium-shaped JSONL, one file per simulated day, in `cdc/event_date=YYYY-MM-DD/changes.jsonl`. Each line is a Debezium-shaped change event (op: `c`/`u`/`d`, before/after, source LSN).
- **HubSpot REST emulation:** `hubspot/<resource>/event_date=YYYY-MM-DD/page_NNNN.jsonl`. One file per page of API response.
- **Stripe REST emulation:** `stripe/<resource>/event_date=YYYY-MM-DD/page_NNNN.jsonl`. Same shape.
- **First-party events:** `events/event_date=YYYY-MM-DD/events.ndjson`. One NDJSON file per partition.
- **Partner CSV:** `partner/ad_spend_YYYY-MM-DD.csv`. One per simulated day.
- **Documents:** `docs/product/`, `docs/support_kb/`, `docs/support_tickets/` filesystem trees plus `docs/manifest.jsonl` and `docs/change_log.jsonl`.
- **Held-out eval sets:** `eval/retrieval/qa_pairs.jsonl`, `eval/generation/questions.jsonl` with `eval/generation/rubrics.jsonl`.

All paths are relative to a single root output directory. A `MANIFEST.json` at the root records the seed, scale, generator version, simulated time horizon, byte counts, and content hash of every emitted file. Two regenerations with the same seed/scale produce identical MANIFEST hashes.

## Distributional shape requirements

The dataset must be realistic enough that an analyst dashboard built against it isn't immediately obviously synthetic. The generator MUST produce these distributional properties; v0.1 leaves the exact distributions to implementation but pins the qualitative shapes:

- **Account size:** long-tailed (top ~5% of accounts contribute ~50% of MRR). Concretely: a Pareto-like distribution over `users_per_account`.
- **Plan mix:** majority on `starter` and `growth`; `free` is a trial cohort that converts at a stated rate; `scale` and `enterprise` are the long-tail revenue.
- **Churn:** monthly account churn rate ~3–5% (annualized ~30–45%, realistic for B2B SaaS in this profile), with cohort-aware shape — first-90-days churn is materially higher than steady-state churn.
- **Growth:** monthly net new accounts grows over simulated time, faster in the back half (the 10× over 18 months trajectory). Generator parameterized so M-scale total ≈ S-scale total × 20 and L ≈ M × 10 by L's terminal date.
- **Engagement:** event volume per user is long-tailed; a small power-user cohort accounts for a large fraction of events; many accounts have one user who logs in occasionally.
- **Seasonal shape:** mild weekly seasonality (weekday > weekend) and quarterly billing spike at month-end (invoice generation concentrates in last 3 days of each calendar month).
- **Geographic distribution:** ~60% US, ~20% EU, ~10% UK/Canada, ~10% other — drives GDPR scenarios in task 2.6 and PII-residency in task 7.

These are *requirements* on the generator, not parameters the bench user tunes. The dataset is what it is at a given seed/scale; only the seed and the scale are user-controlled.

## Validation query suite

Fifteen queries every candidate stack MUST implement and answer. Each query has a documented output schema, a defined tolerance class, and a reference expected-result file produced by the standalone reference implementation (Python + DuckDB, not via any candidate stack) at S scale; M and L expected results are computed at run time by the reference implementation and not checked into the repo (they'd be too large) but are reproducible from the seed.

| # | Query | Output shape | Tolerance class |
|---|---|---|---|
| Q1 | **MRR at month end** — sum of active subscription `mrr_cents` at each calendar month-end | (month_end_date, mrr_cents) per month | Numeric ±0.01% relative |
| Q2 | **ARR run rate** — Q1 × 12 | (month_end_date, arr_cents) | Numeric ±0.01% relative |
| Q3 | **New accounts per month** — count of accounts with `signup_date` in month | (month, new_accounts) | Exact |
| Q4 | **Churned accounts per month** — count of accounts whose status transitioned to `churned` in month | (month, churned_accounts) | Exact |
| Q5 | **Net dollar retention by signup-month cohort** — for each signup-month cohort, NDR at month N | (cohort_month, month_offset, ndr_ratio) | Numeric ±0.05% relative |
| Q6 | **Gross dollar retention by signup-month cohort** — same shape as Q5 but excluding expansion | (cohort_month, month_offset, gdr_ratio) | Numeric ±0.05% relative |
| Q7 | **WAU** — distinct user_id with ≥1 event in the trailing 7-day window, computed at each calendar week boundary | (week_end_date, wau) | Exact |
| Q8 | **DAU/WAU stickiness** — DAU divided by WAU at each week boundary | (week_end_date, stickiness_ratio) | Numeric ±0.01 absolute |
| Q9 | **Cohort retention curve** — % of accounts in each signup-month cohort still `active` at month N | (cohort_month, month_offset, retained_pct) | Numeric ±0.05% absolute |
| Q10 | **ARPU** — total MRR / count of active accounts, at each month-end | (month_end_date, arpu_cents) | Numeric ±0.01% relative |
| Q11 | **Days-to-first-value** — median days from `signup_completed` to first `feature_used`, by signup cohort | (cohort_month, median_days) | Numeric ±1 day absolute |
| Q12 | **Support SLA compliance** — % of tickets where `first_response_at - opened_at ≤ priority_sla` | (month, priority, sla_compliance_pct) | Numeric ±0.5% absolute |
| Q13 | **Top-of-funnel attribution** — count of signups whose first session_id is within 7 days of any partner-CSV-recorded click | (campaign_id, signups_attributed) | Exact |
| Q14 | **Plan mix at month end** — count of accounts by `plan_id` at each month-end | (month_end_date, plan_id, account_count) | Exact |
| Q15 | **Late-event share** — % of events with `received_at - occurred_at > 1 hour` per ingestion month | (ingestion_month, late_pct) | Numeric ±0.1% absolute |

Each query has a corresponding SQL file in the reference implementation directory (`canonical/validation/queries/QNN.sql`) written in portable ANSI SQL where possible, with documented dialect deviations per candidate stack. Each candidate stack's repo contains its own implementation of the same query against its own modeled Gold layer; the comparison is *result equivalence*, not query-text equivalence.

## Validation tolerance protocol

How "the same answer" is judged across stacks.

- **Exact-match queries (Q3, Q4, Q7, Q13, Q14):** every row in the candidate's output appears in the reference output and vice versa; column values match exactly. Implemented as a set-symmetric-difference check.
- **Numeric tolerance, relative (Q1, Q2, Q5, Q6, Q10):** all-dollar-aggregate queries. For each row, the candidate value is within ±X% relative to the reference value, with X stated per query. Computed on integer-cents wherever the candidate can preserve cents arithmetic; floats only used at the comparison step. The slack accommodates engine-specific summation order over very large aggregations (Snowflake's parallel sum vs. Athena/Trino's, vs. BigQuery's) — but it should never need to absorb genuine modeling drift.
- **Numeric tolerance, absolute (Q8, Q9, Q11, Q12, Q15):** ratios, percentages, medians. Stated per query.
- **Tolerance class is the contract, not the floor.** A stack that comes in tighter than tolerance is healthy. A stack that comes in at the tolerance boundary every time is a smell — investigate before treating it as passing.

A `validate.py` reference script in `canonical/validation/` runs the candidate's query outputs against the reference outputs and reports per-query pass / fail / drift-direction. CI gates Stack #N builds on this script returning all-green at S scale.

## Refresh and regeneration policy

- **Spec version bumps regenerate.** A v0.2 of this spec that changes data shapes (adds a column, changes a distribution) bumps the generator's `MANIFEST.json` and invalidates prior-version expected-results files. Stacks must re-validate against the new manifest. Spec versioning is conservative — bumps are deliberate, not casual.
- **Seed bumps do not regenerate by default.** The reference seed is `42` for v0.1. Stacks ship validation results against seed 42 at the three scales. Additional seeds are run as sensitivity analysis at Stack-#1-time; if cross-stack drift is seed-correlated, that's a finding.
- **Simulated "now" bumps with spec version.** v0.1's simulated now is `2026-05-01T00:00:00Z`. v0.2's now is bumped explicitly to keep the dataset feeling fresh in writeups; it's not auto-advanced.

## Open questions / not in v0.1

- **Faker / generator library choice.** Reference implementation language is unspecified. Lean: Python + `mimesis` (or `faker`) for entity attributes + a custom event-emission engine driven by a per-account behavioral state machine. Decision deferred to Phase 1 generator implementation, since "what library makes the seed-determinism contract easiest" is a build-time call. A recommended choice (Faker pinned + stdlib `random` + SHA-256 sub-seeds) is proposed in `canonical/synthetic-dataset-build-plan.md`, to be confirmed and recorded in ADR-003 when the generator is built.
- **SaaS source emulation: static files vs. mock HTTP server.** v0.1 specifies static JSONL files on disk. Stack #1 against static files validates the ingestion-from-flat-files path. A future v0.2 may add a small mock HTTP server (responding to GET requests with the same JSONL payloads, supporting pagination cursors) so stacks can also exercise the live-API-shaped ingestion path. Defer until a stack needs it.
- **Document corpus PII handling.** A subset of support ticket transcripts deliberately contain synthetic PII (names, emails, occasional partial credit-card numbers — explicitly fake, but realistic-shaped) to exercise tasks 7.4 and 9.6's PII paths. v0.1 lock: yes, plant PII deliberately, mark `pii_present=true` in metadata, validate that masking pipelines surface and handle it. Open: exact PII-injection rate and the synthetic-PII catalogue (do we use a documented set of synthetic placeholders, or generated ones?). Phase 1 call.
- **L-scale mandatory vs. stretch.** v0.1 requires every stack to ingest L; full validation-query-suite measurement at L is required for the cost-relevant tasks (storage, transformation, BI) but optional for L-impractical tasks (e.g., a full re-aggregation that would cost more than $50 to run). Per-task call documented in each candidate stack's writeup.
- **CDC replay shape.** v0.1 specifies a pre-baked CDC stream (JSONL files) derived from the operational mutation log. Stacks that prefer to consume CDC from a live Postgres source can run the Postgres mutation loader against their own Postgres and stream CDC live. v0.2 reconsiders whether the pre-baked stream is enough or whether a live-Postgres source is required for fairness.
- **Generation-eval rubric format.** v0.1 specifies a per-Q rubric with 3–5 scoring dimensions and a list of expected key facts; LLM-as-judge scores against the rubric. Open whether to also require a small human-labeled gold set (per the open question in `task-set.md` 9.6) to calibrate the LLM-judge before any RAG-comparison post claims are made. Decision before Stack #1 ships 9.6.
- **Multi-tenant simulation.** v0.1 generates a single tenant company. Multi-tenant simulation (multiple SaaS company datasets in the same warehouse, exercising row-level-security and tenant-scoped queries) is out for v0.1; revisit if Stack-#N implementation surfaces a real need.

## Versioning

- **v0.1 (2026-05-13):** Initial spec. Five source surfaces (operational Postgres, HubSpot REST, Stripe REST, first-party events, partner CSV) + document corpus. Three reference scales (S / M / L) anchored to the anchor buyer profile. 15-query validation suite with three tolerance classes (exact, relative-numeric, absolute-numeric). Determinism contract pinned. Reference seed `42`, simulated now `2026-05-01T00:00:00Z`.
- **v0.2 (target: after Stack #1 ships):** Updates from Stack #1 implementation findings. Likely changes: distributional-shape parameter tuning where the v0.1 shapes produced unrealistic analyst-dashboard artifacts; tolerance-class refinement based on actual cross-engine drift observed; PII-injection catalogue locked; CDC pre-baked-vs-live decision resolved.
- **v1.0 (target: after Stack #2 ships):** First two stacks have both validated against this spec; the comparison itself is the validation. Locks the spec for a year before v1.1.
