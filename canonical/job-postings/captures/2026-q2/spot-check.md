# Spot-check sample — 2026-Q2 capture

Methodology v0.1.2 requires a ≥15% random sample to be human-reviewed before
analysis output is published. If sample agreement is below 95%, the extractor
prompt is corrected and the extract pass is re-run.

**Sample size:** 12 of 40 (30.0%)
**Seed:** 20260511 (deterministic; re-running this script with the same seed
produces the same sample)
**Includes all low-confidence rows:** yes (oversampled to 12)

## How to use

For each row below, read the source paragraph then check whether each LLM
classification is correct. Tick the boxes if so. If anything is wrong, leave
the box unchecked and write a note inline — that's the audit trail.

Tally at the bottom drives the agreement %.

---
## Row 1 of 12 — Yuzu Health (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=47979247
**Posting ID:** `0ce6edf84800`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Data Engineer |
| role_title_normalized | data_engineer |
| seniority | mid |
| geo | us |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> Primary need is for Fullstack/Product Engineers but we're also looking for a Data Engineer, a Backend Engineer and a Product Designer.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 2 of 12 — Enlace Health (`builtin`)

**Source URL:** https://builtin.com/job/data-engineer/8668563
**Posting ID:** `11d5c9f1c30a`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | unknown |
| company_stage_signal | unknown |
| role_title_raw | Data Engineer |
| role_title_normalized | data_engineer |
| seniority | mid |
| geo | us |

**Stack components extracted:** `cloud_platform=aws`, `open_table_format=iceberg`, `orchestration=step_functions`, `iac=terraform`, `iac=cdk`, `cicd=github_actions`

**`stack_mentions_raw`** (verbatim from source posting):

> Design and operate ingestion and normalization pipelines across the Bronze and Silver layers of a multi-tenant healthcare lakehouse.
> 
> Develop secure batch and streaming ingestion processes supporting schema drift, replay, and PHI-compliant storage.
> 
> Build scalable Spark-based transformation pipelines and reusable ingestion frameworks aligned to data mesh principles.
> 
> Optimize storage, partitioning, and schema evolution strategies using open table formats.
> 
> Deploy and manage platform infrastructure, CI/CD workflows, and observability using Infrastructure as Code and cloud-native tooling.
> 
> Utilize cloud-native monitoring tooling; CloudWatch familiarity is a plus.
> 
> Experience working in AWS-native or equivalent cloud data ecosystems.
> 
> Familiarity with open table formats (e.g., Apache Iceberg); required depth at Senior level.
> 
> Experience with Infrastructure as Code (Terraform, AWS CDK).
> 
> Experience implementing CI/CD pipelines (GitHub Actions, AWS CodePipeline).
> 
> Familiarity with orchestration frameworks such as AWS Step Functions.
> 
> Familiarity with cloud monitoring/observability patterns; CloudWatch preferred.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 3 of 12 — Caribou (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=47604056
**Posting ID:** `1b4f340ec5ce`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | 50-100 |
| company_stage_signal | unknown |
| role_title_raw | Senior Analytics Engineer |
| role_title_normalized | analytics_engineer |
| seniority | senior |
| geo | canada |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> _(empty)_

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 4 of 12 — Caribou (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=47977568
**Posting ID:** `1b74cd1b37b1`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | 50-100 |
| company_stage_signal | unknown |
| role_title_raw | Senior Analytics Engineer |
| role_title_normalized | analytics_engineer |
| seniority | senior |
| geo | canada |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> We are building on our core product such as deploying AI-powered agentic systems that work alongside agency coordinators to handle routine coordination, outreach, and administrative workflows to improve agency operations.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 5 of 12 — RWA.xyz (`builtin`)

**Source URL:** https://builtin.com/job/software-engineer-data-platform/9154056
**Posting ID:** `2f68a864b8f7`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | fintech-software |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Software Engineer (Data Platform) |
| role_title_normalized | data_platform_engineer |
| seniority | mid |
| geo | us |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> 3+ years of experience engineering data systems with technologies like Spark, Beam, or Flink
> 
> Strong experience in relational database schema design
> 
> Experience with cloud infrastructure DevOps

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 6 of 12 — Granica (`builtin`)

**Source URL:** https://builtin.com/job/senior-software-engineer-foundational-data-systems-ai/7633322
**Posting ID:** `888faaede70f`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | devtools |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Senior Software Engineer – Foundational Data Systems for AI |
| role_title_normalized | data_platform_engineer |
| seniority | senior |
| geo | us |

**Stack components extracted:** `open_table_format=iceberg`, `open_table_format=delta`, `open_table_format=hudi`, `open_table_format=parquet_only`

**`stack_mentions_raw`** (verbatim from source posting):

> Production experience with Spark , Flink , or custom distributed engines on cloud object storage.
> 
> Familiarity with Iceberg , Delta Lake , or Hudi .
> 
> Experience with columnar formats such as Parquet or ORC and low-level encoding strategies.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 7 of 12 — Thirdfort (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=47610840
**Posting ID:** `8a70c15f6040`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | fintech-regulated |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Analytics Engineer (Fixed Term Contract) |
| role_title_normalized | analytics_engineer |
| seniority | mid |
| geo | uk |

**Stack components extracted:** `orchestration=temporal`

**`stack_mentions_raw`** (verbatim from source posting):

> We've spent the last year rebuilding our product from the ground up and are increasingly leaning into AI across the team/system, focusing on technologies that let product-minded engineers solve hard client problems fast and with confidence: Go, Temporal, NextJS and React Native.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 8 of 12 — Mithrl (`builtin`)

**Source URL:** https://builtin.com/job/data-engineer-knowledge-graphs/8083840
**Posting ID:** `b504bf0cfc3b`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | unknown |
| company_stage_signal | series-a |
| role_title_raw | Data Engineer, Knowledge Graphs |
| role_title_normalized | data_engineer |
| seniority | senior |
| geo | us |

**Stack components extracted:** `ingestion_elt=custom_python`

**`stack_mentions_raw`** (verbatim from source posting):

> Build and maintain ETL pipelines for large public biological datasets and curated knowledge sources
> 
> Design, implement, and evolve schemas and storage models for graph structured biological data
> 
> Create efficient APIs and query surfaces that allow internal teams and AI systems to retrieve nodes, relationships, pathways, annotations, and graph analytics
> 
> Implement scalable storage and indexing strategies for high volume graph data
> 
> Support data warehousing, documentation, and API reliability
> 
> Experience with cloud infrastructure and modern data stack tools
> 
> Nice to Have
> 
> Experience with graph databases or graph query languages
> 
> Experience with data warehousing and analytical storage formats

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 9 of 12 — RWA.xyz (`builtin`)

**Source URL:** https://builtin.com/job/software-engineer-data-platform/7276456
**Posting ID:** `bcea5c73cbc9`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | fintech-software |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Software Engineer (Data Platform) |
| role_title_normalized | data_platform_engineer |
| seniority | mid |
| geo | us |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> 3+ years of experience engineering data systems with technologies like Spark, Beam, or Flink
> 
> Strong experience in relational database schema design
> 
> Experience with cloud infrastructure DevOps

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 10 of 12 — Hive (hive.co) (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=48052750
**Posting ID:** `be9811fcaae9`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | saas |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Senior Software Engineer, Data |
| role_title_normalized | data_platform_engineer |
| seniority | senior |
| geo | remote_us_hq |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> Senior Software Engineer, Data (7+ yrs) Design and own a cloud-native big data platform handling audience data for millions of attendees and billions of interactions a year. This is one of our newest pods- you'll be part of the founding team.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 11 of 12 — Mercor (`hn_whoishiring`)

**Source URL:** https://news.ycombinator.com/item?id=47978339
**Posting ID:** `cdb0ede5fb75`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | marketplace |
| company_size_band | 50-100 |
| company_stage_signal | series-a |
| role_title_raw | Data Engineer |
| role_title_normalized | data_engineer |
| seniority | mid |
| geo | us |

**Stack components extracted:** _(none)_

**`stack_mentions_raw`** (verbatim from source posting):

> Build the data infrastructure that powers Mercor's matching, evaluation, and business intelligence systems. You'll design and own pipelines, warehousing, and data models that inform both product and operations at scale.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---

## Row 12 of 12 — Inspiren (`builtin`)

**Source URL:** https://builtin.com/job/senior-data-platform-engineer/8030279
**Posting ID:** `ebdb42322dd7`
**Confidence:** low

| field | LLM extracted |
|---|---|
| industry | healthtech-software |
| company_size_band | unknown |
| company_stage_signal | unknown |
| role_title_raw | Senior Data Platform Engineer |
| role_title_normalized | data_platform_engineer |
| seniority | senior |
| geo | remote_us_hq |

**Stack components extracted:** `cloud_platform=aws`, `warehouse=databricks`, `streaming=kafka`, `streaming=kinesis`

**`stack_mentions_raw`** (verbatim from source posting):

> From our realtime monitoring platform to deeper longitudinal insights, data is at the heart of everything Inspiren does. We are seeking a highly skilled Senior Data Platform Engineer to own, maintain, and develop our data infrastructure built on Databricks and AWS to scale and accelerate our data capabilities across the company.
> 
> Define, drive, and implement the future live ingestion layer of data into our data platform (e.g. Kafka, Kinesis). 
> 
> Define and evolve standards for storage, compute, data management, provenance, and orchestration. 
> 
> Cloud Providers: Demonstrated hands-on experience with Databricks. AWS experience is a plus but not required. 
> 
> Data Warehousing: Expertise in modern data warehouse and lakehouse architectures.

**Reviewer sign-off**

- [ ] Industry classification is correct
- [ ] Company size band is correct
- [ ] Role classification is correct
- [ ] Stack components match what the source paragraph names (no hallucinated tools, no missed tools in the taxonomy)
- [ ] `stack_mentions_raw` is verbatim from the source

---
## Tally

- Total rows reviewed: ___ / 12
- Rows with all fields correct: ___ / 12
- Agreement: ___ % (target ≥95%)
- Reviewer: ___
- Date: ___
