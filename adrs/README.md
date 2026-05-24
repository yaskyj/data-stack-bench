# Architecture Decision Records

This directory holds **cross-cutting** ADRs — decisions that apply across multiple stacks or to the project as a whole. Stack-specific ADRs live under each stack's directory (e.g., `stacks/stack-01-athena/adrs/`).

## Format

Each ADR is one Markdown file named `ADR-NNN-short-name.md`, where `NNN` is a zero-padded sequence number unique within this directory.

Sections, in order:

- **Status.** One of: Proposed, Accepted, Superseded by ADR-NNN, Deprecated.
- **Date.** ISO date when status was last changed.
- **Context.** What forced this decision. The buyer constraints, the cost target, the cross-stack tension, the hiring landscape — whatever made this a real fork rather than a lookup. Should read like an honest narrative, not a pro/con table.
- **Decision.** What was chosen, in plain language.
- **Alternatives considered.** The other forks that were on the table and why they lost. A real list, not a strawman.
- **Consequences.** What this decision makes easier and harder downstream. Both intended and accepted-cost.
- **Open questions.** Anything this ADR explicitly punts.

ADRs are append-only. If a decision changes, write a new ADR that supersedes the old one and update the old one's status. Do not edit-in-place.

## Voice

Sharp, opinionated, calls specific tradeoffs by name. The project identity is a fair comparative tester, but individual ADRs are where the comparative work is shown — they earn the comparative credibility by being honest about what was hard.

Each ADR must be grounded in the actual implementation. The hard constraints are: the implementation is real before the ADR is finalized, the tradeoff named is the actual tradeoff the implementation surfaced (not a generic one), and the final voice and decision-judgment are the maintainer's. AI-assisted drafting is fair game — the project is build-in-public; the value of the artifact lives in operator-grade judgment, not in keystrokes.

## Index

- ADR-003 (forthcoming) — Synthetic data generator: determinism model + library choices. Proposed decisions are drafted in `canonical/synthetic-dataset-build-plan.md`; the ADR is written against the real implementation when the generator is built in Stack #1.
- ADR-002 (forthcoming) — Terraform across all stacks. (Decision locked 2026-05-10; ADR text to be written.)
- [ADR-001-orchestrator-strategy.md](ADR-001-orchestrator-strategy.md) — Status: Proposed (2026-05-12). Orchestrator strategy: Airflow at Stack #1 + Stack #2 (self-hosted on Fargate); Dagster at Stack #3; Databricks Workflows at Stack #4; Fabric Data Factory at Stack #5. Resolves the orchestrator family question as per-stack-with-intent rather than lock-one-across-the-lineup. Flips to Accepted after Stack #1's orchestration slice validates the call.
