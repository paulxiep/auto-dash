# AutoDash + plotlint: Vision

## Executive summary

**The project ships AI-powered data tooling across two orthogonal dimensions:**

- **Axis A — Infra / Orchestration.** *How* the system runs. Local library → local pipeline → AWS Bedrock AgentCore → enterprise-hardened (Step Functions, Bedrock Guardrails, OpenTelemetry, CI eval harness).
- **Axis B — AI Workflow Engineering.** *What* the system is intelligent about. Deterministic chart auto-fix → LLM-driven chart repair → single-CSV agent maturity → multi-CSV agent with join inference, iterative replanning, provenance, and user-in-the-loop clarification.

Each axis advances independently. A merge request lands one (Axis A tier, Axis B stage) cell. Coherent products ship at every meaningful intersection — standalone plotlint with deterministic patcher (L1 × B1.1), local multi-CSV pipeline with join inference (L2 × B3.2), enterprise-hardened multi-CSV agent on AgentCore (L4 × B3.4). The project can be paused at any cell without leaving incoherent middle states.

The two products living inside this grid:

- **plotlint** — chart visual-compliance engine. Reads a rendered chart's geometry, detects defects, fixes them. Standalone library.
- **AutoDash** — end-to-end data → analysis pipeline. Takes one or more CSVs and a natural-language question; returns charts with full provenance back to the source files.

```
$ plotlint broken_chart.py
→ Renders chart, inspects geometry for visual defects
→ Applies deterministic mechanical fixes (overlap, cutoff, palette, legend)
→ Falls back to LLM for semantic defects (wrong chart type, axis range)
→ Converges; outputs fixed code + clean PNG + inspection JSON
```

```
$ autodash orders.csv customers.csv products.csv "Which regions grew Q4 revenue most?"
→ Profiles each file, infers grain and candidate keys
→ Proposes joins (orders↔customers on customer_id; orders↔products on product_id)
→ Validates joins (row counts, null rates, type integrity)
→ Plans analysis, generates pandas code, runs in sandbox
→ Generates charts, polished by plotlint
→ Emits report with provenance — every number traceable to file + column + transformation
→ Escalates clarifying questions if joins are ambiguous
```

---

## Why this matters

**Programmatic chart-quality measurement is unfilled territory.** Today's LLM chart-fixing either does nothing (you ask "fix the labels," paste the screenshot back into the chat) or invokes a vision-language model on every iteration (slow, expensive, non-deterministic). The frontier-research audit confirms there is no shipped open-source library that detects chart defects from rendered geometry and applies known mechanical fixes deterministically. plotlint is that library. See [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md) §7.

**Un-modelled multi-CSV question-answering is also unfilled.** Every shipping AI data tool either:

- requires a pre-defined schema or semantic model (Snowflake Cortex Analyst, Databricks AI/BI Genie, Vanna, Hex Magic, Looker + Gemini), or
- defers joins back to the user (ChatGPT Advanced Data Analysis, Julius AI, Cursor with data), or
- works only on a single file or dataframe (PandasAI, Microsoft LIDA).

An agent that accepts several un-modelled CSVs, infers joins, validates them, replans on failure, tracks provenance, and asks the user clarifying questions when joins are ambiguous is the AI-workflow-engineering target of Axis B. See [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md) §3 for the per-product landscape audit.

### The fixes-interact problem (plotlint's specific framing)

Chart visual problems are emergent and fixes cascade. Rotating axis labels changes effective figure height, which pushes the legend, which now overlaps the title. A linear "fix one thing" pass doesn't work. plotlint runs a convergence loop that re-inspects the entire chart after each fix, detects regressions, and rolls back when a fix made things worse. Measurement underwrites the loop: the inspector reads bounding boxes directly from matplotlib's artist tree (and equivalent internals in other renderers), giving exact, reproducible, sub-millisecond defect detection — for free, with no LLM call.

That measurement layer is independent of the patching strategy. Axis B1 ships both a deterministic patcher (no LLM, for mechanical defects) and an LLM patcher (for semantic defects), letting the fast path do most of the work.

---

## Two products, one engine

```
plotlint/       → zero imports from autodash. Pip-installable independently.
plotlint/core/  → foundation utilities (LLM client, sandbox, parsing, errors).
                  Imported by plotlint AND autodash.
autodash/       → may import from plotlint. Never the reverse.
```

plotlint is standalone — `pip install plotlint` and `plotlint script.py` works without ever installing AutoDash. AutoDash is the consumer: it generates chart code, then invokes the plotlint convergence loop per chart before emitting output.

| Component | Belongs to | Standalone? |
|---|---|---|
| Data loading + profiling | autodash | yes |
| Analysis planning | autodash | no (needs profile) |
| Data exploration in sandbox | autodash | no |
| Chart planning + code generation | autodash | no |
| Renderer (matplotlib + future Plotly) | plotlint | yes |
| Inspector (bbox extraction + defect checks) | plotlint | yes |
| Patcher (deterministic + LLM tracks) | plotlint | yes |
| Convergence loop | plotlint | yes |
| Multi-file profiling + join inference (B3) | autodash | n/a (extends profiling) |
| Provenance tracking (B2.2+) | autodash | yes (orthogonal concern) |

See [architecture.md](architecture.md) for normative package boundaries, dependency rules, and protocols.

---

## Axis A — Infra / Orchestration

How the system is deployed and operated. Progression from a local library to a fully-hardened AWS-native deployment.

| Tier | Headline | Stop here if |
|---|---|---|
| **L1** | Local library (plotlint installable; CLI runnable) | The goal is a publishable open-source artifact |
| **L2** | Local end-to-end pipeline (sequential orchestration on a laptop) | The goal is a demo runnable on one machine |
| **L3** | Cloud-native on AWS Bedrock AgentCore | The goal is cloud deployment |
| **L4** | Enterprise hardening — Step Functions, Bedrock Guardrails, OpenTelemetry → CloudWatch, CI eval harness | The goal is enterprise-credible deployment |

### Cloud deployment (target shape)

```
                 ┌─────────────────────────────────────────────┐
                 │  AWS Step Functions (durable workflow)       │
                 │  ingest → validate → AGENT → render →        │
                 │  guardrails → emit → audit                   │
                 └───────────────────┬─────────────────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │  Bedrock AgentCore         │  ← agent reasoning
                       │  (tools: load, explore,    │
                       │   chart, inspect, join,    │
                       │   validate, replan)        │
                       └─────┬──────────────┬───────┘
                             │              │
                  ┌──────────▼───┐     ┌────▼────────┐
                  │  plotlint    │     │  sandbox    │
                  │  (chart      │     │  (pandas    │
                  │   compliance)│     │   + mpl)    │
                  └──────────────┘     └─────────────┘

  Bedrock Guardrails wraps inputs/outputs (PII, prompt injection, content)
  OpenTelemetry → CloudWatch traces every agent decision + tool call + LLM cost
  Foundation model: Claude via Bedrock — routed through caravan
```

### Local deployment (development + offline)

```
                 ┌────────────────────────────────────┐
                 │  Plain Python orchestrator         │
                 │  (or minimal ReAct loop)            │
                 └──────────────────┬──────────────────┘
                                    │
                       ┌────────────▼────────────┐
                       │  Same tool implementations │
                       │  (plotlint, sandbox)       │
                       └────────────────────────────┘

  Foundation model: Ollama (Llama 3.x, Qwen) — routed through caravan
```

### Honest abstraction scoping

Cloud and local modes share **tool implementations and the LLM-call layer**, not orchestration. Pretending otherwise would create a leaky abstraction that fails the moment a non-trivial AWS-specific feature gets used.

| Layer | Cloud | Local | Caravan-abstracted? |
|---|---|---|---|
| LLM provider call | Bedrock Claude | Ollama | **Yes** — clean seam (messages in → response out) |
| Agent orchestration | Bedrock AgentCore | Plain Python / minimal ReAct loop | No — feature surfaces too different |
| Workflow orchestration | Step Functions | Plain Python | No — abstraction would be too thin |
| Tool implementations (plotlint, sandbox) | shared | shared | n/a |

Concretely: the LLM patcher (B1.2), all data-exploration LLM calls, chart-code generation, validation LLM-as-judge, and join LLM ranking flow through caravan and can be retargeted between Bedrock and Ollama via a single YAML edit. AgentCore and Step Functions are cloud-only — the local path is a separate code path, not a caravan-swapped equivalent.

Full per-tier exit criteria, files, and verification commands live in [development_plan.md](development_plan.md) under "Axis A — Infra / Orchestration".

---

## Axis B — AI Workflow Engineering

The dimension the original single-axis roadmap conflated with infra. Pulled out here because the AI capabilities the system has are independent of where it runs.

| Phase | Headline | Stop here if |
|---|---|---|
| **B1** | Chart patcher (deterministic + LLM fallback) | The goal is plotlint as a complete visual-compliance library |
| **B2** | Single-CSV agent maturity (orchestrator-worker, scratchpad, validation critic, provenance) | The goal is one "real" AI agent demo |
| **B3** | Multi-CSV agent (multi-file → join inference → iterative replanning → enterprise-grade provenance) | The goal is the underbuilt frontier-research target |

Each phase decomposes into MR-shippable sub-stages:

- **B1.1** — Deterministic mechanical-defect patcher (no LLM)
- **B1.2** — LLM patcher fallback for semantic defects
- **B2.1** — Orchestrator-worker + scratchpad refactor
- **B2.2** — Validation critic + provenance tracking
- **B3.1** — Multi-file profiling + question routing (no joins)
- **B3.2** — Join inference (single-pass)
- **B3.3** — Iterative replanning + user clarification escalation
- **B3.4** — Enterprise hardening of the multi-CSV agent (audit trail, sanity bounds, semantic-layer hook)

Full per-stage scope, files, and exit criteria live in [development_plan.md](development_plan.md) under "Axis B — AI Workflow Engineering". The landscape and methodology choices underlying these phases are sourced from [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md).

---

## Enterprise context

For a reader without a corporate-data background: "enterprise" here means large organisations — banks, retailers, healthcare systems, government agencies — where data analysis is *governed*. Every published number has to be reproducible, auditable, and traceable back to a source. They use tools called BI ("business intelligence") platforms (Tableau, Power BI, Looker) and increasingly want AI assistants on top of them.

Microsoft, Snowflake, Databricks, Salesforce/Tableau, ThoughtSpot, AWS, and a long tail of mid-market players (Hex, Mode, Sigma, Omni) all shipped AI auto-intelligence products in 2024–2026. Adoption is real but uneven. Microsoft Copilot for Power BI is default-on in many tenants. Databricks AI/BI Genie has named wins at Walmart and HP. Snowflake Cortex Analyst hits 92% accuracy — but only on star/snowflake schemas that someone modelled in advance.

The recurring pain points enterprises report (sourced from blog posts, customer case studies, Gartner / Forrester research): **hallucination + trust**, **the maintenance burden of keeping metric definitions consistent across tools**, **security + compliance** (PII in prompts, prompt-injection attacks, EU AI Act enforcement through 2026), **cost surprises** from unpredictable LLM usage, **change-management resistance** from analysts who fear replacement, and the **pilot-to-production gap** — about 45% of self-service BI implementations fail within 18 months, overwhelmingly from lack of governance, not lack of capability.

The implication for this project: for the multi-CSV agent in Axis B3 to be more than a demo, it has to **track provenance from day one, surface its assumptions, expose an audit log, and have a clear escalation protocol when it isn't sure**. Those aren't enterprise-sales features — they are the basic forcing functions any agent operating on data anyone cares about will need. They land formally in B3.4 (enterprise hardening of the multi-CSV agent).

See [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md) §1 for the layperson primer on enterprise data roles, BI tools, semantic layers, and governance terminology; §2 for the full adoption picture; §2.7 for the non-negotiables list that shapes B3.4.

---

## Where this sits in the world

Plain-English summary of the frontier-research conclusions per Axis B phase. Citations in [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md).

- **plotlint (Axis B1).** No shipped equivalent. The closest adjacent prior art is `vislint_mpl` (research code, detection only), Chartability (an accessibility checklist designed for humans to use), matplotlib's built-in `tight_layout` / `constrained_layout` (handles spacing only, not element-level overlap or palette safety), and recent VLM-based chart-critique research papers from 2024–2026 (skip mechanical fixes entirely and go straight to LLM). The hybrid "deterministic mechanical fixes + LLM semantic fallback" library does not exist yet. Genuine gap.

- **Single-CSV question-to-charts (B2).** Heavily crowded — ChatGPT Advanced Data Analysis, Julius AI, Hex Magic, PandasAI, plus most enterprise BI vendors with AI assistants. B2's value is engineering the existing pipeline as a *real agent* (orchestrator-worker dispatch, shared scratchpad, validation critic, provenance tracking) rather than chat-with-data, which makes B2 mostly a stepping stone to B3 rather than a standalone differentiator.

- **Multi-CSV with autonomous join inference + replanning + provenance + clarification (B3).** Genuinely underbuilt. Schema-bound NL2SQL tools (Cortex Analyst, Vanna, Defog) handle joins on *pre-modelled* schemas. ChatGPT ADA accepts multiple file uploads but its cross-file planning is shallow and defers joins to the user. PandasAI is single-DataFrame focused. Hex Magic and Snowflake Cortex Analyst both depend on a pre-existing semantic model. The autonomous, un-modelled-CSV agentic case is the frontier.

- **Infra (Axis A).** Well-served. Bedrock AgentCore, Bedrock Guardrails, Step Functions, OpenTelemetry are standard AWS-stack composition. The differentiator on Axis A is not "we wrote an agent runtime" — it is "this is what we built *on* the standard AWS stack." Value comes from Axis B running on top of it.

---

## Guiding principles

> **"Declarative, Modular, SoC"**

| Principle | Meaning | Example |
|---|---|---|
| **Declarative** | Describe *what*, not *how*. Config over code. Data-driven behaviour. | Defect checks declare severity thresholds; join validators declare expected cardinality bounds. Behaviour is data, not hardcoded if-else chains. |
| **Modular** | Components are self-contained, swappable, independently testable. | plotlint works standalone or inside AutoDash. Swap matplotlib for Plotly without touching defect detection. Join inference is one module; replanner is another. |
| **SoC** (Separation of Concerns) | Each module has ONE job. No god objects. Clear boundaries. | Inspector detects. Patcher fixes. Convergence loop orchestrates. Critic validates. Replanner recovers. Provenance tracker logs. No component does two things. |

### Additional principles

| Principle | Meaning | Example |
|---|---|---|
| **Measure, Don't Guess** | Prefer programmatic measurement over LLM inference. Use the LLM only where judgment is required. | Inspector reads pixel-precise bounding boxes; LLM patcher invoked only for semantic defects. Join validator counts rows; LLM-as-judge invoked only for tie-breaking. |
| **Risk-First Validation** | Highest-risk assumptions get validated earliest. | Bounding-box extraction reliability was validated in MVP.7 ("the critical test") before building the patcher. Join inference accuracy should be validated on a curated multi-CSV fixture set before scaling. |
| **Incremental Value** | Each merge improves user-facing capability. No half-cells. | An MR is shippable if it advances one (Axis A, Axis B) cell to a coherent state. |
| **Honest Abstraction** | Abstract only where seam surfaces converge. Don't paper over feature differences. | caravan abstracts the LLM-call layer; AgentCore and Step Functions are cloud-only by design. |
| **Two axes, independent merges** | No MR straddles both axes. An MR either advances infra (Axis A) or AI capability (Axis B). | This is what makes the (A, B) grid composable. Mixing axes in one MR creates entangled changes that are hard to revert independently. |

---

## Modular design

Every component communicates via well-defined interfaces. plotlint works standalone or inside the AutoDash pipeline. Chart and dashboard specifications are renderer-agnostic.

### Components by axis

| Component | Axis | Built? | Notes |
|---|---|---|---|
| Data loader + profiler | — | yes (MVP.2) | Foundation. Used by both axes. |
| Analysis planner | — | yes (MVP.3) | |
| Data explorer (sandbox + retry) | — | yes (MVP.4) | |
| Chart planner + code generator | — | yes (MVP.5) | |
| Renderer (matplotlib) | — | yes (MVP.6) | Extended for Plotly post-MVP. |
| Inspector + bbox extractor + checks | — | yes (MVP.7) | The thesis validation. |
| `plotlint.patcher_deterministic` | B1.1 | no | Mechanical fixes; no LLM. |
| `plotlint.patcher_llm` | B1.2 | no | Semantic-defect fallback. |
| `plotlint.loop` (full convergence wiring) | B1 | partial | Inspect+render nodes exist; patcher wiring pending. |
| `autodash.orchestrator` | B2.1 | no | Orchestrator-worker dispatch. |
| `autodash.scratchpad` | B2.1 | no | Shared memory across pipeline steps. |
| `autodash.critic` | B2.2 | no | Per-step validation pass. |
| `autodash.provenance` | B2.2 | no | Number → source lineage tracking. |
| `autodash.multi_file` | B3.1 | no | Multi-file profiling + question routing. |
| `autodash.join_inference` | B3.2 | no | Name + type + value-set overlap; LLM tiebreaker. |
| `autodash.join_validation` | B3.2 | no | Row count, nulls, type, sample spot-check. |
| `autodash.replanner` | B3.3 | no | Reflexion-style memory; bounded retry. |
| `autodash.clarification` | B3.3 | no | Confidence-thresholded escalation to user. |
| `autodash.audit` | B3.4 | no | Exportable audit trail. |
| `autodash.semantic_layer` | B3.4 | no | Hook for external metric definitions. |

The Axis B components do not exist yet; they are what the Axis B development plan creates.

---

See [development_plan.md](development_plan.md) for the per-tier and per-stage roadmap with exit criteria and the merge-request grid.
See [docs/executive_summary.md](docs/executive_summary.md) for a portfolio-level overview, [docs/technical_summary.md](docs/technical_summary.md) for the engineer-level walkthrough, and [docs/frontier_research_2026-05.md](docs/frontier_research_2026-05.md) for the landscape audit underlying Axis B.
See [architecture.md](architecture.md) for normative module/package boundaries (still authoritative for already-built components; will need extension for Axis B modules in a later round).
