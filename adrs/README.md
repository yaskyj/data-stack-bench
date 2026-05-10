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

ADR drafting cannot be assistant-shipped. The draft can come from anywhere; the final must be read against the actual implementation, with the tradeoff judgment in the maintainer's voice.

## Index

- ADR-IAC-001 (forthcoming) — Terraform across all stacks. (Decision locked 2026-05-10; ADR text to be written.)
- ADR-001 (forthcoming) — Stack #1 orchestrator pick. Pending the first job-posting analysis run.
