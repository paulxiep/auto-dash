# AutoDash

An end-to-end pipeline: data tables + natural-language questions → polished, multi-chart dashboards. Its core engine, **plotlint**, closes the visual feedback loop through programmatic spatial analysis — extracting bounding boxes directly from the rendering engine and running geometric collision detection. As vision-language models have closed much of the bounding-box gap, plotlint is positioned as the **deterministic complement to VLM chart critics**: cost-, latency-, and reproducibility-superior for measurable defects, with VLM reserved for the semantic judgments that genuinely require it.

- [Project Vision](vision.md)
- [Architecture](architecture.md)

## Usage

```
$ autodash sales.csv "What drove Q4 revenue? How do regions compare?"
→ Loads & profiles data
→ Plans analysis, explores data, identifies insights
→ Generates charts, each polished by plotlint (visual compliance engine)
→ Outputs: dashboard.png
```

```
$ plotlint broken_chart.py
→ Renders chart, inspects for visual defects
→ Fixes: label overlap, legend occlusion, y-axis formatting
→ Converges in 3 iterations (score: 0.30 → 0.72 → 0.88 → 1.00)
→ Outputs: fixed code + convergence GIF
```

## Development Roadmap

- [Development Log](development_log.md)
- [Development Plan](development_plan.md)

### Built (paused 2026-02-09 after MVP.7 · 368 tests passing · commit `2d05046`)

| Milestone | Focus | Tests |
|---|---|---|
| **MVP.1** | Foundation + LangGraph scaffold (state schemas, graph skeletons, `plotlint/core/` utilities, all model types) | 69 |
| **MVP.2** | Data intelligence (loaders, profiling, semantic-type detection) | +46 |
| **MVP.3** | Analysis planning (LLM: profile + questions → validated `AnalysisStep`) | +35 |
| **MVP.4** | Data exploration (LLM pandas code → subprocess sandbox → `InsightResult`) | +33 |
| **MVP.5** | Chart planning + code generation (renderer-agnostic `ChartSpec` → matplotlib code) | +89 |
| **MVP.6** | Matplotlib renderer (Agg subprocess sandbox, pickled Figure + PNG) | +22 |
| **MVP.7** | Inspector foundation — bbox extraction + LabelOverlap + ElementCutoff. **THE CRITICAL TEST validates the plotlint thesis end-to-end.** | +74 |

### Forward (tiered — see [development_plan.md](development_plan.md))

| Tier | Scope | Duration |
|---|---|---|
| **L1** | Complete plotlint: Patcher (MVP.8) + Output (MVP.9). Standalone visual-compliance engine, LLM calls caravan-routed. | ~1 week |
| **L2** | Local pipeline: minimal orchestration driving MVP.2–6 nodes + plotlint end-to-end; CSV + question → markdown report. Caravan provider swap (Anthropic ↔ Ollama). | +3 days |
| **L3** | Bedrock AgentCore: outer agent loop migrates to AgentCore; existing MVP.2–6 functionality wrapped as tools the agent invokes. AWS-deployed. | +1 week |
| **L4** | Enterprise hardening: Step Functions for durable workflow, Bedrock Guardrails, OpenTelemetry → CloudWatch, CI eval via Bedrock model-evaluation API. | +1 week |

Each tier ships a coherent demoable artifact; work can stop after any tier.

## Purpose

- To practice and demonstrate familiarity with
  - Agent orchestration on Bedrock AgentCore
  - Multi-step LLM pipelines
  - Multimodal AI (vision + text)
  - Programmatic visual analysis
  - Provider abstraction via `caravan`
- To explore the thesis that **deterministic measurement is the right tool for measurable chart defects** — and VLM critique the right tool for semantic judgment, with the boundary made explicit.

## Tech Stack

**Current implementation (paused at MVP.7):**

- **Pipeline orchestration:** LangGraph (StateGraph, conditional edges)
- **LLM:** Anthropic Claude, Google Gemini (vendor-swappable via `LLMClient` protocol)
- **Data:** pandas
- **Visualization:** matplotlib
- **Testing:** pytest, pytest-asyncio

**Resume target (forward roadmap):**

- **Outer orchestration (cloud):** AWS Step Functions
- **Agent reasoning (cloud):** Bedrock AgentCore
- **Foundation model:** Claude via Bedrock — routed through `caravan`
- **Safety:** Bedrock Guardrails
- **Observability:** OpenTelemetry → CloudWatch
- **Local mode:** plain Python / minimal ReAct loop + Ollama (also caravan-routed)

## Guiding Mantra

> **"Declarative, Modular, SoC"**

| Principle | Meaning |
|-----------|---------|
| **Declarative** | Describe *what*, not *how*. Config over code. Data-driven behavior. |
| **Modular** | Components are self-contained, swappable, and independently testable. plotlint works standalone or inside AutoDash. |
| **SoC** | Each module has ONE job. No god objects. Inspector detects. Patcher fixes. Loop orchestrates. |

## Architecture

Two packages, one monorepo. `plotlint` has ZERO imports from `autodash`.

| Package | Single Responsibility |
|---------|----------------------|
| `plotlint/core/` | Foundation utilities — LLM client, sandbox, parsing, errors, config |
| `plotlint/` | Visual compliance engine — convergence loop, models, renderer, inspector, patcher |
| `autodash/` | End-to-end pipeline — data loading, planning, exploration, chart gen, output |

```
plotlint (standalone)                    autodash (pipeline)
  Convergence Loop                         Agent + Tools (resume target)
  render → inspect → decide                load → plan → explore →
     ▲         ├── patch ──┘               chart → comply → output
     │         └── stop → END
     └──── loop back ◄────┘                comply invokes plotlint
                                           per chart
```

The diagram reflects the resume-target shape (agent + tools). The pause-point code is the LangGraph version of the same pipeline; L3 migrates the outer loop to Bedrock AgentCore without changing tool implementations.

## Current State

Paused after MVP.7 (commit `2d05046`, 2026-02-09). **368 tests passing.** THE CRITICAL TEST validates the plotlint thesis end-to-end: 20 overlapping x-axis labels → MatplotlibExtractor → LabelOverlapCheck → `DefectType.LABEL_OVERLAP` detected.

- LangGraph graph skeletons: convergence loop (render → inspect → patch) and pipeline (6-node linear) ✓
- All model types defined upfront as shared contracts ✓
- Real `plotlint/core/` implementations: subprocess sandbox, LLM response parsing, error hierarchy, config ✓
- `should_continue` closure with 4 stop conditions (perfect score, max iterations, render error, stagnation) ✓
- Data loading + profiling + semantic-type detection (MVP.2) ✓
- Analysis planning (MVP.3), data exploration (MVP.4), chart code generation (MVP.5) ✓
- Matplotlib renderer with Agg subprocess sandbox (MVP.6) ✓
- Inspector with bbox extraction, label-overlap and element-cutoff checks (MVP.7) ✓
- **Not built:** MVP.8 Patcher, MVP.9 Output, MVP.10 packaging — first targets on resume (L1).

## Known Limitations

- **Outer loop is LangGraph, not AgentCore.** Resume migrates the outer agent loop to Bedrock AgentCore at L3; existing nodes become tools the agent invokes.
- **Patcher and Output are not implemented.** L1 closes this; the convergence loop currently has render and inspect nodes but no patch step.
- **Single chart only.** Multi-chart and dashboard layout are post-L4.
- **No CLI yet.** `autodash` and `plotlint` CLI entry points come with L1 / L2.
- **Plotlint thesis revised post-Claude-4.7.** VLMs now produce pixel-mapped coordinates and reason about layout reasonably well, so plotlint is positioned as the deterministic complement (cost / latency / reproducibility wins for measurable defects), not as the only path.

## Planned Features

See [vision.md](vision.md) for the architecture and [development_plan.md](development_plan.md) for the L1–L4 tiered roadmap.

---

### Keywords

- **Language:** `Python`
- **Architecture & Patterns:** `LangGraph StateGraph` · `TypedDict State Machines` · `Protocol-Based DI` · `Closure Factory (Conditional Edges)` · `Subprocess Sandbox` · `Frozen Dataclasses` · `Dual-Package Monorepo` · `Stub-to-Real Node Replacement` · `Layered Config Composition` · `Honest Abstraction Scoping`
- **LLM & AI:** `Anthropic Claude API` · `Google Gemini API` · `Bedrock AgentCore` · `Bedrock Guardrails` · `Claude Agent SDK` · `LLM Code Generation` · `LLM Vision (Critic)` · `Prompt Engineering` · `Hybrid AI (Programmatic + LLM)` · `Convergence Loop` · `Provider Abstraction (caravan)` · `Caravan Integration`
- **Data & Visualization:** `pandas` · `matplotlib` · `Plotly` · `Bounding Box Extraction` · `Collision Detection` · `Spatial Analysis` · `Chart Code Generation` · `Dashboard Composition`
- **Visual Compliance:** `Programmatic Inspection` · `Deterministic Chart Evaluator` · `Defect Taxonomy` · `Label Overlap Detection` · `Element Cutoff Detection` · `WCAG Color Contrast` · `Convergence Scoring` · `FM-Output Evaluation as Architecture`
- **Pipeline:** `Data Profiling` · `Semantic Type Detection` · `Analysis Planning` · `Data Exploration` · `Chart Planning` · `Visual Compliance` · `Output Generation`
- **AWS & Cloud:** `Bedrock AgentCore` · `Step Functions` · `Bedrock Guardrails` · `OpenTelemetry` · `CloudWatch` · `Bedrock Model-Evaluation API`
