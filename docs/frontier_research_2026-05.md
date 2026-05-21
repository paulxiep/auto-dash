# Frontier Research Snapshot — May 2026

_Captured 2026-05-20. This is a point-in-time landscape audit. If work resumes substantially later than this, the products and papers cited will be out of date and should be refreshed._

## Purpose

This document is the source material behind two things:

- The two-axis roadmap in [development_plan.md](../development_plan.md) — specifically Axis B (AI Workflow Engineering), whose tier choices are justified by sections 3–7 below.
- The positioning claims in [vision.md](../vision.md) about which capabilities are crowded versus underbuilt.

Sections §1–§2 are background for a reader with no enterprise / business-intelligence / data-analysis experience. Sections §3–§7 are the landscape audit. §8 is the honest gap call.

A short glossary used throughout:

- **AI auto-intelligence** — informal umbrella term for AI features that turn raw data into answers or charts without a human writing the analysis.
- **AST** — abstract syntax tree; a structured representation of source code that programs can read and edit safely.
- **BI** — business intelligence; the practice (and the tools) of turning company data into dashboards and reports for decision-making.
- **CSV** — a spreadsheet-like data file, one row per record.
- **ETL** — extract / transform / load; the data-engineering pipelines that move data between systems.
- **Foreign key** — a column whose values match a key column in another file, allowing the two to be joined.
- **Grain** — what one row of a dataset describes. One row per customer vs one row per order vs one row per click — these are different grains and cannot be mixed naively.
- **Join cardinality** — for a join between two tables, how many rows in one side match each row in the other (one-to-one, one-to-many, many-to-many).
- **NL2SQL** — natural-language to SQL; AI that converts an English question into a SQL query.
- **Provenance / lineage** — the record of where a number came from: which file, which column, which transformation, which join.
- **SOTA** — state of the art.
- **VLM** — vision-language model; an AI that can look at an image and reason about it.

---

## §1 — Enterprise context primer (for a layperson)

### What "enterprise" means here

In this document, "enterprise" means large organisations — Fortune 1000 companies, big banks, retail chains, healthcare systems, telecoms, government agencies — where data analysis is *governed*. Governance means: every published number has to be reproducible, auditable, and traceable back to a source. The CFO can't accept "the AI said so" as the justification for a number on a quarterly report. So adoption of AI data tools in this setting has very different constraints than a developer running ChatGPT on a CSV at home.

### Roles in the data org

Large companies have a whole specialised data team. The roles that matter for this document:

- **Data engineer** — builds the pipelines that move data between databases and warehouses; owns reliability and freshness.
- **Data analyst** — translates business questions into queries and dashboards; usually a domain expert (finance analyst, marketing analyst).
- **Analytics engineer** — newer hybrid role; builds reusable data models and metric definitions (the things AI agents need to reference).
- **Data scientist** — builds predictive / ML models.
- **BI developer** — builds and maintains the dashboards in Tableau, Power BI, Looker.
- **Data steward** — owns data quality and policy for a specific domain ("the customer table"); enforces governance.
- **Chief Data Officer (CDO)** — executive in charge of overall data strategy, governance, and compliance.

### What BI is, and the dominant tools

**Business intelligence (BI)** is the practice of gathering historical data and presenting it as dashboards and reports for business decisions. The dominant BI tools as of 2026:

- **Tableau** (owned by Salesforce; ~375,000 organisations, ~30 million monthly active users)
- **Microsoft Power BI** (deeply tied to Microsoft 365 and the Fabric data platform; widely deployed in any Microsoft-shop enterprise)
- **Looker** (Google Cloud; popular with engineering-led data teams)
- **Qlik** (older but still entrenched in some industries)

A BI tool is where analysts and business users go to look at numbers. AI assistants in 2024–2026 are mostly being layered on top of these — not replacing them.

### Semantic / metric layer

A **semantic layer** (or **metric layer**) is a business-logic abstraction that sits between raw data and BI tools. It centralises the definition of important metrics — "revenue", "monthly active users", "customer churn", "gross margin" — so that every dashboard, notebook, and AI assistant references the *same* definition of "revenue" rather than each one re-inventing it.

This used to be optional. It became foundational in 2024–2026 because:

1. Every AI agent that queries data risks **hallucinating** if it interprets a schema without business context. "Revenue" might mean gross, net, or recognised — the AI shouldn't have to guess.
2. Enterprises run the same metric across many surfaces (BI tools, AI agents, notebooks, embedded reports) and need consistency.
3. Regulators auditing reported numbers want a single traceable definition.

Common semantic-layer products: **LookML** (Looker's native), **dbt Semantic Layer**, **Cube**, **AtScale**, **Power BI Semantic Models**. About 35% of mid-to-large data teams still don't have one as of mid-2026; for them, AI tools that depend on a semantic layer don't quite work.

### Data governance and lineage

**Data governance** is the bundle of policies, processes, and tools that define: who can access which data, how data is classified (PII, regulated, public), who owns what dataset, and how compliance regimes (GDPR in Europe, HIPAA in US healthcare, SOC 2, CCPA) are enforced.

**Lineage** tracks the origin and transformation history of a number — which upstream tables, columns, queries, and aggregations contributed to it. Lineage is critical for: troubleshooting bugs ("why did this number change?"), satisfying audit ("prove this number is correct"), and impact analysis ("if I change this column, what breaks?").

Enterprises insist on both because the cost of getting a number wrong — fined by a regulator, miscommunicated to investors, used to fire someone — is large.

### Shadow IT / shadow analytics

**Shadow IT** is technology that employees use without formal IT or security approval. Shadow analytics is the data equivalent: analysts using ChatGPT or personal notebooks on company data, outside governed channels.

Gartner estimates shadow IT accounts for 30–40% of enterprise IT spending. The 2025 ISACA survey on shadow AI says by 2027 75% of employees will engage in unauthorised technology creation. Motivations: official tools are slow, governance is frustrating, deadlines are tight. Risks: compliance violations, data leaks, official metrics that contradict shadow-derived ones.

---

## §2 — How enterprises are actually living with AI auto-intelligence tools

### §2.1 — Who's shipping

**Microsoft Copilot for Power BI / Microsoft Fabric.** Widespread adoption, often enabled by default in tenants that already have Microsoft Copilot. Copilot Capacity moved from the F64 tier to F2 tier in April 2025, dramatically lowering the cost of trial. "Chat with your data" full-screen interface announced at Build 2025. Pain points reported: cost surprises from heavy use, hallucination on complex multi-table queries.

**Snowflake Cortex Analyst.** Generally available since 2024. Named customer wins include Alberta Health Services, Advisor360°, Etam. Achieves ~92% SQL accuracy on star/snowflake schemas. Requires a pre-defined semantic model; doesn't work on raw, un-modelled tables.

**Databricks AI/BI Genie.** Reached 4,000+ customers during preview; now generally available. Notable wins: Walmart (90% reduction in time-to-value, $5.6M annual cost savings), HP Inc., Experian, Conagra, Premier Inc. (scaled to 20,000 users), Italgas (80% of employees on self-service BI). Requires the data team to curate a "knowledge store" of table relationships — i.e. doesn't infer joins autonomously.

**Tableau Pulse / Salesforce Einstein.** Tableau Pulse reached 3,000 customer organisations and 9,000 monthly active users at launch. Salesforce extended Pulse into Sales Cloud (surface AI insights inside CRM). Tableau Einstein launched as a broader AI analytics platform at Dreamforce 2024.

**ThoughtSpot Spotter / Sage AI.** Launched November 2024. By end of fiscal 2025, 52% of ThoughtSpot customers were actively using Spotter; 133% YoY usage growth. Multi-hop reasoning over complex schemas. Leader in 2025 Gartner Magic Quadrant for Analytics & BI.

**Looker Studio + Gemini / BigQuery Studio.** Google ships Gemini Deep Research integrations into Looker. Strong in GCP-native shops; less common outside.

**AWS QuickSight Q + Bedrock for data agents.** Amazon Q in QuickSight is GA. AWS pushes Bedrock agents (and AgentCore specifically) for multi-step data workflows. Strongest in AWS-committed enterprises.

**Mid-market: Sigma, Mode, Hex, Omni, Equals.** Hex captured 25% of BI spend among startups (up from 9% in 2023), overtaking Power BI and ThoughtSpot in that segment. Omni did 4× YoY revenue growth and raised a Series C at $1.5B valuation in April 2026. All ship NL-to-SQL and agentic workflow features.

**Standalone / shadow: ChatGPT Advanced Data Analysis, Julius AI, Cursor / Claude Code for data.** Used heavily by individual analysts. Officially, "no enterprise deployment"; in practice, pervasive shadow usage.

### §2.2 — Adoption modes

Three modes run in parallel in most enterprises:

- **Pilot / proof-of-concept** — one team or business unit, 3–12 months. Success criteria typically vague ("improve productivity").
- **Governed rollout** — broader release with access policy, model evaluation, data classification rules. 6–12 more months. Where most projects stall.
- **Shadow IT** — analysts use unsanctioned tools on the side, regardless of pilot or rollout status.

Who gets access first matters: analyst-first deployments are most common in regulated industries (analysts gatekeep for business users); executive-first deployments create governance headaches; business-user-first deployments without a semantic layer produce confusion and distrust.

### §2.3 — Pain points (the candid picture)

What enterprises actually complain about (sourced from blog posts, analyst reports, conference talks, Gartner / Forrester research):

1. **Hallucination and trust.** Reputational risk from AI-generated numbers being wrong is the top enterprise concern. Only 39% of organisations report high data-quality confidence in their BI insights.

2. **Semantic-layer maintenance burden.** Every time a metric definition changes ("revenue now excludes refunds"), every tool referencing it must update. Mistakes cascade.

3. **Security and compliance.** PII in prompts; prompt-injection attacks; model drift; EU AI Act enforcement (phasing in through 2026) with fines up to €35M or 7% of global turnover.

4. **Cost surprises.** Heavy Copilot / Cortex / Genie use produces unpredictable cloud bills. Unlike traditional BI, usage is hard to forecast.

5. **Change management.** Analysts fear replacement. Successful enterprises reposition them as "metric custodians" or "decision coaches" rather than query writers.

6. **Pilot-to-production gap.** 45% of self-service BI implementations in companies under 500 employees fail within 18 months — overwhelmingly from lack of governance, not lack of capability.

### §2.4 — Governance models in practice

- **Model evaluation gates** — a central team reviews model outputs for bias and hallucination before surfacing to end users.
- **Prompt-injection defence** — restrict queries to approved tables; enforce row-level security and semantic-layer constraints.
- **PII handling** — redact sensitive fields before sending to the LLM; some enterprises block analysis of PII-heavy tables outright.
- **Audit trails** — log every query (who, when, what tools, what sources). Replay capability is a requirement in regulated industries.
- **Accountability** — clearly define who owns it when an AI-generated number turns out wrong.

### §2.5 — The ROI conversation

What enterprises *do* measure: time-to-insight reduction (e.g. "2 days → 15 minutes"), analyst hours saved, dashboard refresh latency, query cost.

What they *don't* really measure (yet): decision quality (are decisions better, faster, more profitable?), hallucination rates (though they're starting to), opportunity cost of shadow IT.

### §2.6 — Build vs buy

Enterprises buy from Cortex / Copilot / Genie when their data stack is standard. They build their own AI data agent when: (a) the semantic layer is unusual and vendor solutions don't integrate, (b) compliance (HIPAA, FINRA) requires on-prem or VPC-only deployment, (c) their stack is heavily customised. Most enterprises buy.

### §2.7 — Implications for this project

For any open-source multi-CSV agent that wants enterprise credibility (i.e. anyone other than a solo analyst would deploy it), these become non-optional:

1. **Provenance tracking.** Every number traces back to file + column + transformation + join.
2. **Audit trail.** Every analysis is logged (who, when, files, queries, model). Replayable.
3. **Governance hook.** Don't allow queries against files the user can't access. RBAC flows through the agent.
4. **Semantic-layer integration.** If a metric definition exists, reference it instead of inferring.
5. **On-prem / VPC deployment option.** SaaS-only is a non-starter for regulated workloads.
6. **Sanity checks / output observability.** Flag suspicious numbers (row count dropped after join, unexpected nulls, values outside historical range).
7. **Explainability.** State the agent's assumptions (e.g. "I joined `orders` to `customers` on `customer_id`; 5,000 matching rows of 5,100").
8. **Cost predictability.** Clear per-query / per-file / per-month pricing semantics.

These shape Axis B3.4 (Enterprise hardening of the multi-CSV agent) in [development_plan.md](../development_plan.md).

---

## §3 — Multi-CSV agentic question-to-charts: products in the wild

For each product, the central question: **does it do un-modelled multi-CSV join inference?**

| Product | Multi-file? | Auto join inference from raw CSVs? | Notes |
|---|---|---|---|
| **ChatGPT Advanced Data Analysis** | Up to 20 file uploads | No. User must specify joins. Shallow cross-file planning. | Free-form Python; ~50MB per file. Most popular shadow tool. |
| **Julius AI** | Multiple datasets | No documented join inference; relies on user-specified relationships. | ~2M users, 10M+ daily visualisations. |
| **Hex Magic** | Yes, multi-cell SQL+Python+chart | Auto-complete joins on common patterns, but only over pre-loaded database tables with metadata. Not from raw CSVs. | Uses fine-tuned models on existing Hex projects. |
| **Snowflake Cortex Analyst** | Yes, multi-table | Joins on **pre-defined** star and snowflake schemas only. 92% accuracy on those. No raw-CSV discovery. | Requires Snowflake; requires semantic model. |
| **Databricks AI/BI Genie** | Yes, with file upload | Requires curated "knowledge store" of join relationships. No autonomous discovery. | Notable wins: Walmart, HP, Experian. |
| **Microsoft Copilot (Power BI, Excel)** | Multi-workbook (emerging Q4 2025) | Cross-file join inference described as "upcoming" in Microsoft Learn. Not production-grade for raw files. | Strongest within a single workbook. |
| **Vanna** | Multiple databases | SQL generation over **pre-defined** DDL schemas. Not CSV-based. | RAG-based. 97% JOIN accuracy on curated SQL. |
| **PandasAI** | SmartDatalake (multi-DF) | Documented unresolved problems with join discovery when column names differ. | Single-DataFrame focus historically. |
| **Defog SQLCoder** | Multi-table SQL | Joins on **pre-defined** SQL schemas. 97% JOIN accuracy. No CSV discovery. | Fine-tuned model. |
| **Microsoft LIDA** | Single-table visualisation | No multi-table reasoning. | Self-evaluation module is LLM-based reasoning about the spec, not measurement. |
| **OpenInterpreter** | General code execution | No specialised join discovery. ACL 2024 finding: open-source models struggle with diverse multi-step data reasoning. | Not specialised for data. |
| **TaskWeaver (Microsoft)** | Plugin architecture | Requires plugin authors to define join logic. No built-in discovery. | Stateful orchestration framework. |
| **MetaGPT DataInterpreter** | Hierarchical task planning | No documented multi-file join inference. Focus is ML/math task success. | Strong on ML benchmarks. |
| **AutoGen** | Multi-agent framework | No built-in. Schema understanding called out as a major unresolved challenge in community discussions. | General-purpose. |
| **Cursor / Claude Code** | Multi-file codebases | Generic code assistance; user codes joins explicitly. Not a data-discovery product. | Heavy shadow usage by analysts. |
| **Briefer, Mode, Equals, Outerbase, Sigma** | Various | All assume pre-defined database schemas or user-specified joins. No autonomous discovery from raw CSVs. | Mid-market analytics. |

### The gap

**No shipping product in mid-2026 does un-modelled multi-CSV join inference as a core, validated capability.** Products fall into three failure modes:

1. **Schema-bound** — assume a pre-modelled semantic layer (Cortex Analyst, Databricks Genie, Vanna, Defog).
2. **Code-execution-as-escape-hatch** — let the user write/specify joins explicitly (ChatGPT ADA, Cursor, Claude Code, Julius).
3. **Narrow-domain** — handle joins well only on star schemas or specific shapes (Cortex Analyst's 92% is on star schemas; falls off elsewhere).

The autonomous multi-CSV case — agent ingests several un-modelled files, infers joins, validates them, replans on failure, tracks provenance, and asks the user clarifying questions when ambiguous — is unfilled. This is the territory Axis B3 targets.

---

## §4 — Academic frontier on multi-CSV agentic data analysis

### Text-to-SQL benchmarks

- **Spider 2.0** (ICLR 2025 Oral) — enterprise-scale workflows (>3000 columns, multiple SQL dialects, real metadata). SOTA in mid-2026: o1-preview at 23.77%, o3-mini at 23.40% on Spider2-snow. **The frontier is genuinely hard for LLMs.**
- **BIRD** — 12,751 examples over 95 databases, real dirty data. Notable: leaderboard was found unreliable; re-evaluation produced 3–31% rank shifts and a corrected BIRD-clear version.
- **Dr.Spider, MultiSpider** — multilingual / multi-dialect variants. Less widely adopted.

### Schema linking

These methods all assume the schema *exists* and link an English question to known columns. None solve the harder problem of inferring whether two un-modelled CSVs *should* be joined.

- **RAT-SQL (2020)** — foundational; 65.6% Spider with BERT.
- **DAIL-SQL (2023)** — prompting + decoding constraints.
- **MAC-SQL, CHESS, RESDSQL** — 2023–2024 schema-linking improvements.

### Join discovery (the genuine frontier)

This is where 2024–2026 research has been most active.

- **Starmie (2024)** — contextualised column representations for union/join search. <0.6 precision on high-recall tasks.
- **Josie** — similarity-based join discovery for data lakes.
- **Snoopy (2025)** — semantic join discovery via proxy columns.
- **Freyja (2024)** — efficient join discovery in data lakes.
- **WarpGate (2024)** — semantic join discovery for cloud data warehouses.
- **OmniMatch (VLDB 2025)** — joinability discovery for data products.
- **HyperJoin (2025)** — LLM-augmented hypergraph link prediction. **21.4% improvement in Precision@15, 17.2% in Recall@15** over baselines. Most relevant to this project.
- **Magneto (VLDB 2025)** — hybrid small + large LLM for schema matching.

**Consensus**: join discovery is active research with no unified SOTA. LLMs are entering the toolkit (HyperJoin, Magneto) but at computational cost. Column-level semantic similarity, name overlap, and type overlap remain the key signals; LLMs add reasoning on top.

### Data-analysis agent benchmarks

- **DataInterpreter (MetaGPT, 2024)** — dynamic planning + tool integration; ML task score 0.86→0.95; MATH +26%; open-ended tasks +112%.
- **InfiAgent-DABench (2024)** — first benchmark for data-analysis agents.
- **DABstep (2025)** — multi-step reasoning for data agents.
- **AgentDS (2025)** — human-AI collaboration on domain-specific data science.

None of these specifically benchmark multi-CSV join inference; they evaluate overall task success.

### Agent design papers

- **ReAct (Yao et al., 2022)** — thought-action-observation cycle. The default pattern.
- **CodeAct (Wang et al., 2024)** — code as action, enabling multi-tool composition in a single step. Outperforms JSON/text-action baselines.
- **Reflexion (Shinn et al., 2023)** — linguistic feedback loops; agents learn from errors without retraining. Highly relevant to join validation.
- **Plan-and-Execute** — separate planning from execution.
- **Tree-of-Thoughts** — branch-and-evaluate for long-horizon decisions.
- **Anthropic Multi-Agent Research System (2024–2025)** — orchestrator-worker pattern. **90.2% improvement over single Claude Opus 4** on research tasks. Direct template for parallel join hypothesis testing.

### Model Context Protocol (MCP)

Anthropic's open standard for connecting AI to data sources. Launched November 2024; adopted by OpenAI (March 2025), Google, Microsoft, AWS. 1000+ community servers by February 2025. Relevant: a multi-CSV agent could expose schema discovery, join proposal, and validation as MCP servers, making them composable with other agents.

---

## §5 — Methodology toolbox for a multi-CSV agent

The patterns a multi-CSV agentic question-to-charts system should choose from. Each pattern: short description + when it applies.

### Planning patterns

- **ReAct (Thought-Action-Observation)** — decompose into reason → act → observe loops. Best for exploratory analysis where the agent discovers relationships incrementally.
- **Plan-and-Execute** — separate plan generation from execution. Useful when you want to show the user the plan before executing (transparency) or batch for cost.
- **CodeAct** — generate Python that performs joins, validation, and charting in a single executable block. Flexible and composable; harder to intercept each step.
- **Orchestrator-Worker (Anthropic pattern)** — lead agent plans; specialised subagents execute in parallel (one validates schemas, one proposes joins, one validates results). Best for parallelism on large datasets.

### Schema understanding

- **Profile-then-link** — lightweight profile of each CSV (sample 100–1000 rows, types, cardinality, nulls) → use as context for join proposals.
- **Semantic embeddings of columns** — embed column names and sample values; cosine-similarity find candidate join columns. Fast but produces false positives.
- **Sample-and-LLM-describe** — extract sample rows; LLM describes ("looks like a ZIP code", "likely a foreign key"). More semantic; slower.
- **Hybrid** — embeddings for speed, name overlap as tiebreaker, LLM only for ambiguous cases. HyperJoin / Magneto pattern.

### Join inference

- **Name overlap** — exact or fuzzy match column names. Simple, fast, misses semantic relationships.
- **Type overlap** — necessary but not sufficient.
- **Value-set overlap (semantic join discovery)** — check whether values are subsets of each other. High precision, requires sampling at least.
- **LLM-proposes-then-validates** — LLM proposes join keys; validate via cardinality, sample spot-checks, LLM-as-judge. Most flexible; cost trade-off.

### Validation loops

- **Row-count plausibility** — many-to-many causes row explosion; 1-to-many should match the "many" side.
- **Type checks** — post-join type consistency.
- **Sanity bounds** — domain-specific: date ranges overlap, ID distributions sensible.
- **LLM-as-judge** — "given these inputs and this join, does it look correct?" Catches semantic inconsistencies. Must combine with deterministic checks because LLMs hallucinate.
- **Deterministic post-conditions** — assertions ("every joined order should have a non-null customer name").
- **Executable verification** — generate test queries; "SELECT COUNT(*) WHERE customer_id IS NULL should return 0."

### Replanning and recovery

- **Reflexion** — on join failure, capture the failure as text in memory ("previous join on email_id produced 0 rows; try phone_number"). Next attempt has context.
- **Self-refine** — generate multiple candidate join hypotheses; pick highest-scoring; iterate.
- **Tree-of-Thoughts for join candidates** — explore multiple join paths in parallel; prune failing branches.
- **Scratchpad memory** — dynamic summary of findings ("Validated orders.customer_id → customers.id 1-to-many; rejected email-based join").

### User-in-the-loop escalation

- **Ambiguity detection** — multiple hypotheses with similar scores, or domain ambiguity.
- **Confidence-thresholded clarification** — if best score < threshold, escalate.
- **Probabilistic ranking** — show user top-3 with evidence rather than forcing one choice.

### Provenance tracking

- **Column-level lineage** — output columns → source file + column + transformations.
- **Query-level provenance** — log the join itself (which tables, keys, when, whether user-approved, validation outcome).
- **Cell-level provenance** — for each output cell, which input rows contributed. Computationally expensive; offer as optional deep-dive.

### Tool design

- **Granular tools** — `profile_dataset()`, `propose_join_keys()`, `validate_join()`. Easier to intercept; more LLM calls.
- **Coarse tools** — single `join_datasets()` that handles everything. Faster; harder to inspect.
- **Hybrid** — expose both. Use coarse for trivial cases, granular for discovery and validation. This is what CodeAct enables.

### Evaluation in 2026

- **Join validity** — schema correct, types correct, cardinality in expected range. Necessary but not sufficient.
- **LLM-as-judge** — separate model scores the join. Cheap, biased.
- **User acceptance** — analysts agree the join is correct. Gold standard; expensive.
- **Downstream task success** — if joined data is used to answer a question, does the answer look plausible? Indirect.
- **Error recovery** — given a deliberately wrong join proposal, does the agent detect and fix it?
- **No established benchmark yet** for un-modelled multi-CSV join discovery. InfiAgent-DABench / DABstep / AgentDS cover task-level outcomes only.

---

## §6 — Research-agent frontier and transfer to multi-CSV

"Research agents" — agents that take a research question, plan a search agenda, fan out across sub-questions, verify findings, and synthesise a cited report — matured rapidly in 2024–2026. Their patterns are highly transferable to multi-CSV data analysis.

### §6.1 — Products and reference implementations

- **OpenAI Deep Research** (Feb 2025) — autonomous multi-step research, dozens of websites synthesised into cited reports. Initially o3, now GPT-5.2 variant. Connects to any MCP server. Occasional hallucination and false confidence.
- **Anthropic Claude Research / multi-agent system** (Apr 2025; mobile May 2025) — lead agent plans, subagents explore in parallel. Accesses web + Google Workspace.
- **Perplexity Deep Research / Pro Search** (Oct 2025) — 95% accuracy claim via strict cross-verification. 3–5 sequential search passes.
- **Gemini Deep Research + Deep Research Max** — Max uses extended test-time compute. Integrated with Workspace; MCP server support.
- **Grok DeepSearch** — in development.
- **GPT Researcher (open source)** — outperformed Perplexity and OpenAI on Carnegie Mellon's DeepResearchGym. Any LLM, any search engine. 2000+ word reports with inline citations.
- **Stanford STORM** — perspective-guided multi-agent conversations + outline-driven RAG.
- **LangChain open_deep_research** — open-source harness for building deep research agents on LangGraph.
- **Browser Use** — leading agentic browsing framework (89.1% on WebVoyager benchmark, 78k GitHub stars).

### §6.2 — Architectural patterns common across research agents

- **Planner → Executor → Critic** — large model plans, smaller models execute, critic verifies.
- **Orchestrator-Worker** — lead orchestrator decomposes; specialised workers run in parallel.
- **Reflective / iterative search** — search → read → identify gaps → refine query → search again.
- **Citation tracking** — every claim linked to source URL or document.
- **Self-verification** — re-read sources to confirm; cross-check multiple sources for consistency.
- **Memory / scratchpad** — running notes shared across subagents; updates as research progresses.
- **Going deeper** — recognise when a sub-question deserves its own research thread.
- **Final synthesis** — scratchpad → structured outline → polished cited report.
- **Stop criteria** — all top-level questions answered, or confidence threshold met, or diminishing returns, or budget exhausted.

### §6.3 — Direct mapping to multi-CSV agent

| Research-agent pattern | Multi-CSV analogue | Direct? | Note |
|---|---|---|---|
| Citation tracking | Provenance tracking — file + column + transformation + join path | ✓ Direct | Must extend "source URL" → "(file_path, file_version, column, row_ids, transformation_id)". |
| Going deeper | Drilling into a join hypothesis when it looks promising | ✓ Direct | Spawn subagent to validate cardinality / nulls / sample spot-checks. |
| Orchestrator-worker | Parallel hypothesis testing on candidate joins | ✓ Direct | Lead proposes N joins; N workers test each; lead picks best. |
| Self-verification | Row-count / type / sanity validation of joins | ✓ Direct | Flag anomalies. |
| Memory / scratchpad | Schema understanding accumulated across files | ✓ Direct | `{tables: [...], keys: [...], temporal: [...], relationships: [...]}`. |
| Planner → Executor → Critic | Plan join strategy → execute → validate | ✓ Direct | Clear task decomposition. |
| Reflective search | Explore → validate → replan on failure | Partial | Data reads are more expensive than web fetches; bound iteration. |
| Final synthesis | Raw analysis output → cited report | ✓ Direct | Provenance footnotes per number. |
| Stop criteria | When to stop replanning and escalate to user | ✓ Direct | Explicit ambiguity protocol. |
| Planner splits task | Decompose multi-file question into per-file or per-join subgoals | ✓ Direct | "Show Q4 revenue by region" → identify tables → plan join sequence → aggregate → visualise. |

### §6.4 — Synthesis: which patterns to adopt for the multi-CSV agent

**Adopt:**
- **Orchestrator-worker** for parallel join hypothesis validation. Fast, interpretable.
- **Planner → Executor → Critic** pipeline. Cost-efficient; clean separation of concerns.
- **Reflective loop, bounded** (max 2–3 retries) — replan on join failure but stop.
- **Provenance from day one** — every number tagged.
- **Scratchpad** for schema state shared across pipeline steps.
- **Explicit stop criteria + clarification protocol** — surface to user rather than hallucinate.

**Skip:**
- **3000-word narrative synthesis** — overkill; CSV analysis produces table + chart + 1–2 paragraph takeaway.
- **Debate / deliberation arbiters** — expensive and slow; validation suffices.
- **Event-driven long-running agents** — CSV analysis is request-response.
- **Knowledge graphs** — overkill for CSVs; scratchpad sufficient.

**Final architecture sketch:**

```
user query
  ↓
orchestrator (mid-tier model)
  - parse question; identify candidate tables and keys; plan join + aggregation
  ↓
[parallel workers]
  - validate each candidate join (row count, nulls, type, semantic plausibility)
  - return feasibility score
  ↓
executor
  - run best-scoring join path + aggregation + filtering
  ↓
critic (lightweight)
  - flag row-count anomalies, null spikes, outliers; emit confidence
  ↓
report generator
  - format table + chart + narrative
  - embed provenance per number
  ↓
user (click any number → see lineage)
```

This is the design Axis B2 + B3 in [development_plan.md](../development_plan.md) progressively builds toward.

---

## §7 — Chart auto-fix landscape (background for Axis B1)

### Built-in layout managers

- **matplotlib `tight_layout()`** — post-hoc subplot spacing adjustment. Fragile on complex nested layouts.
- **matplotlib `constrained_layout`** — global constraint solver; better than `tight_layout` for nested subfigures.
- **matplotlib `rcParams["figure.autolayout"]`** — declarative toggle for auto-layout per render.
- **Plotly `automargin`** — dynamic margin expansion. Limited to margins, doesn't address element-level overlaps.
- **Vega-Lite / Altair** — declarative grammar avoids some defects by separating data encoding from rendering. No post-hoc detection or repair.

All of these address spacing but not: element overlap at granular detail, content visibility (legend on data), colour-blindness safety, semantic chart-type wrongness.

### Existing linters / checkers (detection, not repair)

- **vislint_mpl** (McNutt et al. 2018) — evaluates matplotlib figures against design rules (require-titles, require-axes, etc.). **The closest prior art to plotlint's detection premise. Does not repair.** Research code.
- **Chartability** — 50-heuristic accessibility checklist for visualisations. Audit framework for human review. Not a linter; not automated.
- **Draco v2** (CMU) — constraint-based visualisation recommender via Answer Set Programming. Operates on Vega-Lite specs, not rendered figures. Recommends; does not repair.

### Colour-blindness simulators (no repair)

- **Coblis**, **Color Oracle**, **CoBlind** — browser/desktop simulators showing how charts appear to colour-blind viewers. Detection by human inspection only.

### Palette libraries (specification, no auto-swap)

- **palettable** — ColorBrewer / Tableau / matplotlib palettes with direct matplotlib integration.
- **colorcet** — perceptually accurate 256-colour maps.

Both are *specification* libraries; neither detects nor swaps unsafe palettes automatically.

### Recent academic work (VLM-based chart critique and repair)

- **De-rendering, Reasoning, and Repairing Charts (2026, arXiv 2602.20291)** — first explicit VLM-based chart repair loop. De-renders → VLM reasons → proposes modifications. Evaluated on 1,000 charts; 10,452 design recommendations across 10 categories. **Uses visual reasoning, not geometric measurement.** Post-hoc; requires large model; no deterministic fallback.
- **ChartIR (2025, arXiv 2506.14837)** — iterative refinement for chart generation via structured difference instructions. Works on Qwen2-VL and GPT-4o. Shows that iteration helps but doesn't formalise convergence.
- **ChartLlama, ChartAssistant, ChartGalaxy, ChartGemma** — chart understanding and generation models. None include a repair module.
- **Label placement research** — bitmap-based label placement integrating into Vega-Lite; LLM-driven map labelling (2025). NP-hard in general; cartography literature is rich.

### The gap

**No shipped open-source library applies mechanical fixes to matplotlib charts deterministically.** Detectors exist (vislint_mpl) but don't repair. Repairers exist in 2026 research papers but skip mechanical fixes and go straight to LLM. The hybrid "deterministic mechanical track + LLM semantic fallback" is unfilled.

This is the territory Axis B1 targets.

### Mechanical fix catalogue for matplotlib (the recipes)

For Axis B1.1 — these recipes shipped in L1:

- **Horizontal axis label overlap** → `ax.set_xticklabels(..., rotation=45, ha='right')`, `ax.tick_params(axis='x', labelsize=8)`.
- **Title / label cut off** → `tight_layout(pad=1.2)` or `constrained_layout=True`; shrink font; enlarge `figure.figsize`.
- **Legend covering data** → `ax.legend(loc='upper left', bbox_to_anchor=(1, 1))` (outside axes); shrink legend font; reduce entries. _(Recipe not yet shipped — no LegendOcclusionCheck in L1.)_
- **Colour-blind unsafe palette** → swap to `colorcet.colorblind_safe` or `palettable.tableau.Tableau_10_Proper`. _(Recipe not yet shipped — no PaletteCheck in L1.)_
- **Raw axis numbers** → `matplotlib.ticker.FuncFormatter` or `matplotlib.ticker.EngFormatter`. _(Recipe not yet shipped — no FormattingCheck in L1.)_

Verification: re-render, re-measure overlap area and clipping count, keep fix if score improved, roll back if worse.

---

## §8 — Honest gap call

**Crowded** (well-served, not where to differentiate):

- Schema-bound NL2SQL — Snowflake Cortex Analyst, Vanna, Defog SQLCoder, ThoughtSpot Spotter.
- Single-CSV chat-with-your-data — ChatGPT Advanced Data Analysis, Julius AI, Hex Magic, PandasAI, plus most enterprise BI vendors.
- VLM-based chart critique — emerging research papers in 2024–2026; not yet shipped products.
- AI infra on AWS — Bedrock AgentCore, Bedrock Guardrails, Step Functions, OpenTelemetry → CloudWatch. Standard composition; no novel research required.

**Underbuilt** (where Axis B of this project lands):

- **Un-modelled multi-CSV join inference + replanning + provenance + clarification.** No shipping product does this autonomously from raw files. Recent academic work (HyperJoin, Magneto, Snoopy) is not yet production-tested. The autonomous, un-modelled-CSV agentic case is genuinely the frontier. This is **Axis B3**.
- **Deterministic chart auto-fix library.** Detectors and VLM-based repairers exist; the hybrid deterministic-mechanical + LLM-semantic patcher does not. L1 shipped the first version of this — see [docs/technical_summary.md](technical_summary.md). This is **Axis B1**.

The project's value proposition, accordingly: AI workflow engineering on the under-served axis, deployed on the well-served infra axis.
