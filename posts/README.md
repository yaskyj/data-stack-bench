# Posts — comparative writeups

This directory holds the canonical Markdown source for the project's long-form public writeups. The blog (Substack or self-hosted, TBD) is a redistribution of these — the source of truth lives here and gets edited in PRs alongside the implementations they describe.

## Why mirror in the repo

- A reader who clones the repo gets the writeups in context with the code they describe.
- Posts can reference specific commits and link directly to ADRs and implementation files in the repo.
- The blog platform can change without losing the canonical text.
- ADR-style discipline (decisions are append-only, not edit-in-place) extends naturally to long-form posts when they live in source control.

## Filename convention

`YYYY-MM-DD-short-slug.md` — date is publication date.

Each post starts with frontmatter:

```yaml
---
title: "..."
date: 2026-MM-DD
status: draft | published
canonical_url: https://...   # the public blog URL once it exists
related_adrs: [ADR-NNN, ADR-NNN]
related_stacks: [stack-01-athena]
---
```

## Post types

- **Methodology posts** — explain a piece of the test bench (the canonical task set, the job-posting methodology, the cost discipline pattern). These are evergreen.
- **Quarterly posts** — the job-posting analysis quarterly readout.
- **ADR-companion posts** — a long-form writeup that turns an ADR into a public artifact. The ADR is the operator-grade record; the post is the public-facing argument with the implementation context filled in.
- **Stack writeups** — per-task or per-category writeups comparing how each stack handled the canonical task set.

## Index

- (Empty — first post lands with the first job-posting analysis run.)
