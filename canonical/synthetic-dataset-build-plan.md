# Synthetic dataset generator — build plan

**Version:** v0.1 (plan only — no generator code exists yet)
**Date:** 2026-05-22
**Status:** Plan. Implementation happens in the IDE as part of Stack #1 Slice 1, after the dev foundation is in place. This document is the spec-for-the-build, to be approved before any code is written.

---

## What this is

The implementation plan for the generator that satisfies the contract in [`synthetic-dataset.md`](synthetic-dataset.md). The spec says *what* the data must be (five source surfaces, three scales, a determinism contract, a 15-query validation suite). This plan says *how* the generator gets built — the proposed tech choices, the build order, the test approach, and the prerequisites that come first.

The generator is a **cross-stack `canonical/` asset**: all five stacks consume its output. It is not Stack-#1-specific code, but it's sequenced inside Stack #1 Slice 1 because Stack #1 is the first consumer.

## What this is *not*

- Not code. Every tech choice below is a **proposal to confirm**, not a locked decision.
- Not a second spec. Data shapes, scales, and the validation suite live in `synthetic-dataset.md` and are not restated here except where the build needs to reference them.

## Prerequisites (must exist before any generator code is written)

This is the part that was missing when the build got ahead of itself. None of the below is in place yet:

1. **IDE chosen and set up** (Cursor vs. Antigravity — separate decision; see the prompt prepared for that session).
2. **Python environment + dependency management** — a decision on `uv` vs. `pip`+`venv` vs. Poetry, and a pinned `pyproject.toml`. Recommendation: `uv` for speed and reproducible lockfiles, but this is a confirm-before-coding fork.
3. **Test runner + CI** — `pytest` wired into GitHub Actions so the determinism tests run on every push (the cost-discipline / reproducibility story depends on this).
4. **A clean committed git baseline** — the repo currently has several sessions of uncommitted work in the working tree. That should be committed (or intentionally staged) before new code lands on top of it, so a generator commit is reviewable in isolation.

## Proposed tech decisions (confirm before coding)

Each is a fork with a recommendation and the reasoning. These are the calls that, once approved, get recorded in an ADR written *against the real implementation* (ADR-003, forthcoming).

**1. Language: Python.** Locked by the spec's lean. Not a real fork.

**2. Entity attributes — Faker (pinned) vs. mimesis vs. pure stdlib.**
Recommendation: **Faker, pinned to an exact version.** It's the library a reader of a public build-in-public artifact expects, and the realism breadth (companies, names, emails, locales) is strong out of the box. The cost: Faker's provider data can shift between releases, which would break the byte-identical-across-machines contract — so the exact version pin *is* part of the determinism contract and gets recorded in `MANIFEST.json`. mimesis is faster but less recognizable; pure-stdlib avoids the version coupling but needs embedded word lists and yields lower realism. Confirm.

**3. Distributional / behavioral RNG — stdlib `random` vs. NumPy.**
Recommendation: **stdlib `random.Random`.** Mersenne Twister output is stable across CPython 3.x for a fixed seed, which satisfies the cross-machine requirement with zero added dependencies. The needed distributions (Pareto users-per-account, growth-weighted signups, per-month churn hazard) are all expressible with stdlib primitives. NumPy is faster for vectorized draws but the generation pattern is per-entity scalar draws, and a smaller dependency surface makes the determinism argument easier. Confirm; revisit only if a surface needs heavy vectorized sampling.

**4. Seed derivation — SHA-256 sub-seeds keyed by `(root_seed, *namespace, index)`.**
Recommendation: **adopt.** This is the mechanism behind scale-orthogonality (the spec's "S is a strict prefix of M is a strict prefix of L"): each entity's seed depends only on its index, never on the total count, so the first N entities at a larger scale are byte-identical to a smaller scale's full set. SHA-256 rather than Python's built-in `hash()` because `hash()` is salted per process (`PYTHONHASHSEED`) and not stable across runs. This is the load-bearing design decision; everything else hangs off it.

**5. Determinism caveats to bake in from the start.**
- Pin the Faker version; record it in `MANIFEST.json`.
- Use instance-level Faker seeding (`seed_instance`) per entity stream, not class-level.
- Keep draw order fixed within each entity (UUIDs and attribute draws consume RNG state in order).

## Determinism contract (restated from the spec) and how the build satisfies it

The two properties the generator must prove, both as automated tests:

1. **Idempotent regeneration** — same seed + scale → byte-identical output across runs and machines. Test by comparing `MANIFEST.json` file hashes across two independent runs.
2. **Scale-orthogonality** — S is a strict prefix of M is a strict prefix of L. Test by asserting the S accounts file is a byte-prefix of the M accounts file (and likewise for dependent entities like users).

CI gates every push on these tests passing at S scale.

## Proposed package layout

```
canonical/synthetic-data/
  pyproject.toml          pinned deps (faker==X.Y.Z), package metadata
  README.md               quickstart + determinism contract + status table
  .gitignore              ignore generated output (out/) and build noise
  synthdata/
    config.py             scales, root seed, simulated-now anchor, plan catalog, weights
    seeds.py              SHA-256 sub-seed derivation, deterministic UUID, weighted choice
    clock.py              simulated time window + growth-weighted signup draw
    manifest.py           content hashing + MANIFEST.json writer
    cli.py                python -m synthdata --scale S --seed 42 --out DIR
    surfaces/
      operational_postgres.py
      events.py
      hubspot.py
      stripe.py
      partner_csv.py
      documents.py
  tests/
    test_determinism.py
    test_distributions.py
```

## Output format (per spec)

- Operational Postgres: `schema.sql` + per-table CSV (RFC-4180, LF line endings, stable column order). Mutation log + Debezium-shaped CDC stream added with the CDC surface.
- SaaS REST surfaces: JSONL per resource per simulated day, in the documented API envelope shapes.
- Events: NDJSON, Hive-partitioned by `event_date`.
- Partner CSV: one file per simulated day, with seeded bad files.
- Documents: filesystem tree + `manifest.jsonl` + `change_log.jsonl`; held-out eval sets in a separate directory the RAG pipeline is forbidden to read at ingest.
- Root `MANIFEST.json`: seed, scale, generator version, simulated-now, library version pins, per-file SHA-256 + byte count.

## Build order (vertical accretion)

Each step ships against the determinism contract and gets a test before the next begins.

1. **Determinism core + operational-Postgres spine.** `config` / `seeds` / `clock` / `manifest` plus the five-table spine (`plans`, `accounts`, `users`, `subscriptions`, `subscription_events`) at S scale. Exit: determinism tests pass; distributional checks hit the spec's qualitative targets (long-tail MRR via per-seat billing over Pareto seats → ~50% from top 5%; cohort-aware churn; growth-weighted signups).
2. **First-party event stream.** Needed by the WAU, DAU/WAU stickiness, days-to-first-value, and late-event-share validation queries (Q7, Q8, Q11, Q15). Late-arrival profile + bot/duplicate behavior per spec.
3. **SaaS REST surfaces (HubSpot, Stripe).** With the intentional drift from the operational source the spec calls for (reconciliation is an analytics task the buyer runs).
4. **Partner CSV drop.** Daily ad-spend files with the seeded ~2% bad-file rate (negative costs, malformed dates, schema drift) for tasks 1.4 and 6.3.
5. **Document corpus + held-out eval sets.** Product docs, support KB, ticket transcripts, plus the retrieval and generation eval sets for task 9.6.
6. **Mutation log + Debezium CDC stream; plan price-versioning + task-2.4 retroactive-correction fixture; remaining operational tables** (`invoices`, `payments`, `support_tickets`, `feature_flags`).

## Test approach

- **Determinism tests** (gate CI): idempotent regeneration + scale-orthogonality, per the contract above.
- **Distributional-shape checks**: assert the qualitative shapes the spec pins (MRR concentration band, churn-rate band, signup growth skew, plan mix) so a regression in realism fails loudly.
- **Validation-query reference implementation**: the 15-query suite implemented once in portable SQL against DuckDB (independent of any candidate stack), producing the expected-answer files at S scale that every stack validates against. This is what makes cross-stack "they agree on the numbers" checkable.

## Known cost / perf note

A fresh Faker instance per entity is the expected bottleneck at M/L scale. Plan to reuse a seeded Faker instance (reseeding per entity) rather than constructing one per entity — but only after the determinism tests are green, so the contract isn't risked for a speed win that doesn't matter at the CI scale (S).

## Decisions to confirm before coding

1. Python dependency manager (recommend `uv`).
2. Faker pinned vs. mimesis vs. stdlib for entity attributes (recommend Faker pinned).
3. stdlib `random` vs. NumPy for distributions (recommend stdlib).
4. SHA-256 sub-seed derivation keyed by entity index (recommend adopt).
5. Per-seat MRR model vs. account-level flat pricing for revenue concentration (recommend per-seat over Pareto seats to hit the ~50%-from-top-5% target — but this changes plan-price semantics, so confirm).

## Where and when this gets built

In the IDE, as Stack #1 Slice 1, after the prerequisites above are in place. Not in Cowork. The ADR recording the approved decisions (ADR-003) is written against the real implementation once step 1 ships and its determinism tests pass.
