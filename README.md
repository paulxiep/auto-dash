# AutoDash

An end-to-end pipeline: data tables + natural-language questions → polished, multi-chart dashboards. Its core engine, **plotlint**, closes the visual feedback loop through programmatic spatial analysis — extracting bounding boxes directly from the rendering engine and running geometric collision detection, then dispatching one of two patchers: a deterministic recipe registry for mechanical defects and an LLM fallback for semantic ones. As vision-language models have closed much of the bounding-box gap, plotlint is positioned as the **deterministic complement to VLM chart critics**: cost-, latency-, and reproducibility-superior for measurable defects, with VLM reserved for the semantic judgments that genuinely require it.

The roadmap runs on two orthogonal axes — **Axis A** (Infra / Orchestration, L1–L4) and **Axis B** (AI Workflow Engineering, B1–B3). Each merge request lands one (A-tier, B-stage) cell. L1 × B1.1 + L1 × B1.2 shipped 2026-05-20.

- [Executive Summary](docs/executive_summary.md)
- [Technical Summary](docs/technical_summary.md)
- [Project Vision](vision.md)
- [Architecture](architecture.md)
- [Development Plan](development_plan.md) · [Development Log](development_log.md)

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

### Built (L1 shipped 2026-05-20 · 434 tests passing)

| Milestone | Focus | Tests |
|---|---|---|
| **MVP.1** | Foundation + LangGraph scaffold (state schemas, graph skeletons, `plotlint/core/` utilities, all model types) | 69 |
| **MVP.2** | Data intelligence (loaders, profiling, semantic-type detection) | +46 |
| **MVP.3** | Analysis planning (LLM: profile + questions → validated `AnalysisStep`) | +35 |
| **MVP.4** | Data exploration (LLM pandas code → subprocess sandbox → `InsightResult`) | +33 |
| **MVP.5** | Chart planning + code generation (renderer-agnostic `ChartSpec` → matplotlib code) | +89 |
| **MVP.6** | Matplotlib renderer (Agg subprocess sandbox, pickled Figure + PNG) | +22 |
| **MVP.7** | Inspector foundation — bbox extraction + LabelOverlap + ElementCutoff. **THE CRITICAL TEST validates the plotlint thesis end-to-end.** | +74 |
| **L1 × B1.1 + B1.2** | Delivers originally scoped **MVP.8 (Patcher)** + **MVP.9 (Output)**. MVP.8 reframed from single LLM patcher to two-track `PatchDispatcher`: `FixRecipe` registry + `DeterministicPatcher` (B1.1), `LLMPatcher` fallback (B1.2). MVP.9: `PNGWriter` + `JSONReportWriter`. Also fixes latent loop bugs (iteration / score_history) and adds rotation-aware overlap check. MVP.10 (Docker / CLI packaging) deferred. End-to-end demo: `examples/broken_chart_demo.py`. | +66 |

### Forward — two orthogonal axes (see [development_plan.md](development_plan.md))

The roadmap is a grid: **Axis A — Infra / Orchestration** progresses how the system runs (L1 standalone library → L2 local pipeline → L3 Bedrock AgentCore → L4 enterprise hardening with Step Functions, Bedrock Guardrails, OpenTelemetry, and a CI eval harness). **Axis B — AI Workflow Engineering** progresses what the system is intelligent about (B1 chart patcher complete → B2 single-CSV agent maturity with orchestrator-worker + scratchpad + validation + provenance → B3 multi-CSV agent with join inference, iterative replanning, user clarification, and enterprise-grade audit trail). Each merge request lands one (A-tier, B-stage) cell; work stops cleanly at any cell. The headline next-up step in [development_plan.md](development_plan.md)'s recommended queue is **L2 × B2.1** (local pipeline with orchestrator-worker single-CSV agent), with **L2 × B3.2** (multi-CSV with join inference) as the first publishable AI-agent demo. The frontier-research backing for Axis B is in [frontier_research_2026-05.md](frontier_research_2026-05.md).

## Purpose

- To practice and demonstrate familiarity with
  - Agent orchestration on Bedrock AgentCore
  - Multi-step LLM pipelines
  - Multimodal AI (vision + text)
  - Programmatic visual analysis
  - Provider abstraction via `caravan`
- To explore the thesis that **deterministic measurement is the right tool for measurable chart defects** — and VLM critique the right tool for semantic judgment, with the boundary made explicit.

## Tech Stack

**Current implementation (L1 shipped 2026-05-20):**

- **Convergence-loop orchestration:** LangGraph (StateGraph, conditional edges). LangGraph stays for all local Python — both the inner convergence loop and the future autodash outer orchestrator (B2.1).
- **Patcher:** `PatchDispatcher` routes by `FixRecipe` registry presence — `DeterministicPatcher` first (no LLM), `LLMPatcher` as fallback for defect types without recipes.
- **LLM:** Anthropic Claude (`claude-sonnet-4-6` default), Google Gemini — vendor-swappable via `LLMClient` protocol. `caravan` integration deferred to L2.
- **Output writers:** `PNGWriter` (fixed PNG + re-runnable Python), `JSONReportWriter` (score trajectory + fix history + final issues + final code).
- **Data:** pandas. **Visualization:** matplotlib (Agg backend in subprocess sandbox).
- **Testing:** pytest, pytest-asyncio.

**Resume target (forward roadmap):**

- **Outer orchestration (cloud, L3+):** Bedrock AgentCore replaces LangGraph as the outer orchestrator; durable workflow via AWS Step Functions at L4.
- **Foundation model:** Claude via Bedrock — routed through `caravan` from L2 onward.
- **Safety:** Bedrock Guardrails (L4).
- **Observability:** OpenTelemetry → CloudWatch (L4).
- **Local mode:** LangGraph + Ollama (caravan-routed) — local-pipeline target stays LangGraph; only the cloud path is AgentCore.

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
| `plotlint/core/` | Foundation utilities — `LLMClient` protocol + `AnthropicClient` + `GeminiClient`, subprocess sandbox, response parsing, error hierarchy, config |
| `plotlint/` | Convergence loop — `models`, `renderer`, `inspector`, `loop`, `scoring`, `geometry`, `elements` |
| `plotlint/checks/` | Defect detection — `@check`-registered `LabelOverlapCheck`, `ElementCutoffCheck` |
| `plotlint/extractors/` | Renderer-specific bbox extraction — `MatplotlibExtractor` |
| `plotlint/fix_recipes/` | Deterministic mechanical-fix recipes — `@recipe`-registered overlap / cutoff transformations |
| `plotlint/{patcher, patcher_deterministic, patcher_llm}` | Patcher track — `PatchDispatcher` routes to `DeterministicPatcher` first, `LLMPatcher` as fallback |
| `plotlint/prompts/` | LLM prompt templates (per renderer) |
| `plotlint/output.py` | Output writers — `PNGWriter`, `JSONReportWriter` |
| `autodash/` | End-to-end pipeline — data loading, planning, exploration, chart gen, output. Outer orchestrator B2.1+ |

```
plotlint convergence loop (L1, shipped):           autodash pipeline (partial, awaiting B2.1+):
  render → inspect → decide ──┐                       load → plan → explore →
     ▲         ├── patch ─────┘                       chart → comply → output
     │         └── stop → END                            ▲
     └──── loop back ◄────────────                       │ B2.1 orchestrator-worker refactor
                                                         │ B3.1 multi-file profiling
  patch dispatches:                                      │ B3.2 join inference
    deterministic recipe ──→ patched code               │ B3.3 replanning + clarification
    OR LLMPatcher fallback ──→ patched code             │ B3.4 audit + sanity bounds
```

The plotlint convergence loop is the resume-target's inner loop, fully wired. The autodash pipeline node stubs await B2.1 (orchestrator-worker refactor) onwards. L3 migrates the autodash outer orchestrator to Bedrock AgentCore in cloud only — local Python stays LangGraph throughout.

## Current State

L1 shipped 2026-05-20 (resumed from a 3-month pause). **434 tests passing.** The convergence loop now closes end-to-end. THE CRITICAL TEST still validates the plotlint thesis: 20 overlapping x-axis labels → `MatplotlibExtractor` → `LabelOverlapCheck` → `DefectType.LABEL_OVERLAP` detected. Demo behaviour (no API key): the overlap chart converges 0.80 → 1.00 in one fix (`rotate_x_labels`); the cutoff chart improves 0.00 → 0.80 in two fixes. Zero LLM calls in the natural demo path.

- Full plotlint convergence loop: render → inspect → decide → patch → render, with stop on perfect score / max iterations / render error / score stagnation ✓
- Two-track patcher: `DeterministicPatcher` over a `FixRecipe` registry + `LLMPatcher` fallback via `PatchDispatcher` ✓
- Four recipes (`rotate_x_labels`, `shrink_x_tick_font`, `add_tight_layout`, `enlarge_figure`); registry keyed on `DefectType`; dedup via `(defect_type, recipe_id)` pairs in `fix_history` ✓
- Rotation-aware overlap check (skips AABB collision when both adjacent labels are rotated ≥15°) ✓
- Output writers: `PNGWriter` (fixed PNG + re-runnable Python) and `JSONReportWriter` (score trajectory + fix history + final issues + final code) ✓
- End-to-end demo: [examples/broken_chart_demo.py](examples/broken_chart_demo.py) ✓
- Data loading + profiling + semantic-type detection (MVP.2) ✓
- Analysis planning (MVP.3), data exploration (MVP.4), chart code generation (MVP.5) ✓
- Matplotlib renderer with Agg subprocess sandbox (MVP.6) ✓
- Inspector with bbox extraction, label-overlap and element-cutoff checks (MVP.7) ✓
- **Next on the recommended queue (see [development_plan.md](development_plan.md)):** L2 × B2.1 (local pipeline with orchestrator-worker single-CSV agent) → L2 × B2.2 (validation critic + provenance) → L2 × B3.1 / B3.2 (multi-CSV + join inference, the first publishable AI-agent demo).

## Known Limitations

- **Caravan integration deferred to L2.** L1 ships with the existing `LLMClient` protocol implementations (`AnthropicClient`, `GeminiClient`) called directly. Provider-abstracted routing via the sibling `caravan` repo lands when L2's local pipeline forces the question.
- **Outer autodash orchestrator is not built yet.** The plotlint convergence loop is wired and tested; the autodash pipeline graph still has stub nodes for `plan`, `explore`, `chart`, `comply`, `output` at the LangGraph topology level. Closing those is B2.1 (orchestrator-worker refactor) onwards.
- **Inspector overlap detection is rotation-aware only for x-axis labels.** Y-axis rotated labels and multi-line tick labels may be over-flagged on AABB. A future rotation-aware geometry test can replace the current 15° skip-rule.
- **Multi-chart and dashboard layout are post-L4 / Axis B3+.** Current loop processes one chart at a time.
- **No CLI yet.** `autodash` and `plotlint` CLI entry points are scoped to PL-1.4. For now, the demo script (`python examples/broken_chart_demo.py`) is the end-user entry point.
- **Plotlint thesis revised post-Claude-4.7.** VLMs now produce pixel-mapped coordinates and reason about layout reasonably well, so plotlint is positioned as the deterministic complement (cost / latency / reproducibility wins for measurable defects), not as the only path.

## Planned Features

See [vision.md](vision.md) for the architecture and [development_plan.md](development_plan.md) for the L1–L4 tiered roadmap.

---

### Keywords

- **Language:** `Python`
- **Architecture & Patterns:** `Two-Axis Roadmap (Infra × AI Workflow)` · `LangGraph StateGraph` · `TypedDict State Machines` · `Protocol-Based DI` · `Closure Factory (Conditional Edges)` · `Decorator-Based Registries (@check, @recipe)` · `Subprocess Sandbox` · `Frozen Dataclasses` · `Dual-Package Monorepo` · `Stub-to-Real Node Replacement` · `Layered Config Composition` · `Honest Abstraction Scoping`
- **LLM & AI:** `Anthropic Claude API` · `Google Gemini API` · `Bedrock AgentCore` · `Bedrock Guardrails` · `Claude Agent SDK` · `Orchestrator-Worker (Anthropic Pattern)` · `LLM Code Generation` · `LLM Vision (Critic)` · `Prompt Engineering` · `Hybrid AI (Programmatic + LLM)` · `Convergence Loop` · `Recipe-LLM Hybrid Patcher` · `PatchDispatcher` · `Reflexion-Style Memory` · `Multi-Agent Research System` · `Provider Abstraction (caravan)`
- **Data & Visualization:** `pandas` · `matplotlib` · `Plotly` · `Bounding Box Extraction` · `Collision Detection` · `Spatial Analysis` · `Chart Code Generation` · `Dashboard Composition` · `Multi-CSV Join Inference (planned)`
- **Visual Compliance:** `Programmatic Inspection` · `Deterministic Chart Patcher` · `FixRecipe Registry` · `Rotation-Aware Overlap Detection` · `Defect Taxonomy` · `Label Overlap Detection` · `Element Cutoff Detection` · `WCAG Color Contrast` · `Convergence Scoring` · `FM-Output Evaluation as Architecture`
- **Pipeline:** `Data Profiling` · `Semantic Type Detection` · `Analysis Planning` · `Data Exploration` · `Chart Planning` · `Visual Compliance` · `Provenance Tracking (planned)` · `Output Generation`
- **AWS & Cloud:** `Bedrock AgentCore` · `Step Functions` · `Bedrock Guardrails` · `OpenTelemetry` · `CloudWatch` · `Bedrock Model-Evaluation API`
