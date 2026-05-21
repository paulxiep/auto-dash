# AutoDash + plotlint: Executive Summary

## What It Is

A two-product Python project shipping AI-powered data tooling across two orthogonal dimensions. **plotlint** is a chart-quality library: it renders matplotlib code, extracts element bounding boxes from the figure's artist tree, detects visual defects (overlap, cutoff, palette safety), and patches them either via a deterministic recipe registry or, as fallback, via an LLM. **AutoDash** is the end-to-end pipeline that wraps plotlint with data loading, profiling, analysis planning, sandboxed pandas exploration, chart code generation, and output emission. The roadmap is a grid of (Axis A — Infra / Orchestration; Axis B — AI Workflow Engineering) cells; each merge request lands one cell, and we can stop at any cell with a coherent product. As of 2026-05-20 we have shipped MVP.1–7 plus L1 × B1.1 + L1 × B1.2 — completing the originally scoped MVP.8 (Patcher) and MVP.9 (Output) with the patcher reframed as a two-track dispatcher (deterministic recipes + LLM fallback) rather than the original single LLM patcher. 434 tests passing.

## Why It Matters

- **Portfolio value across two genuinely underbuilt territory pieces.** Our frontier-research audit (see [frontier_research_2026-05.md](../frontier_research_2026-05.md) when present) confirms two gaps no shipping product fills: a deterministic chart auto-fix library (everything else either does detection only — `vislint_mpl`, Chartability — or goes straight to a VLM critic), and an autonomous multi-CSV question-to-charts agent that infers joins from raw un-modelled files. Snowflake Cortex Analyst, Databricks AI/BI Genie, Hex Magic, and Microsoft Copilot for Power BI all assume a pre-defined semantic layer; ChatGPT Advanced Data Analysis and Julius accept multi-file uploads but defer joins to the user. The Axis B roadmap targets both gaps explicitly.

- **AI workflow engineering as the differentiator, on AWS-native infra.** The infra axis (Bedrock AgentCore, Step Functions, Bedrock Guardrails, OpenTelemetry → CloudWatch, CI eval via Bedrock model-evaluation API) is standard composition of well-supplied building blocks. Our value sits on the workflow axis: orchestrator-worker dispatch with shared scratchpad (B2.1, after the Anthropic multi-agent research system), validation critic + provenance tracking per number (B2.2), join inference with row-count plausibility + Reflexion-style replanning + confidence-thresholded user clarification (B3.2–B3.3), and the enterprise-credible hardening layer (B3.4) that turns the demo into something a governed organisation could actually deploy.

- **Enterprise-credible by design.** The non-negotiables for any tool aspiring to credibility in regulated organisations — provenance, audit trail, governance integration, on-prem / VPC option, semantic-layer hook, sanity-bound assertions, explainability, cost predictability — are not bolt-ons in B3.4. They are forcing functions that shape `JSONReportWriter`'s schema and `autodash.provenance`'s tagging model from day one.

- **Two-axis composability.** Each MR lands one (Axis A tier, Axis B stage) cell. Work stops cleanly at any cell with a coherent demoable artifact: standalone plotlint with deterministic patcher (L1 × B1.1), local multi-CSV pipeline with join inference (L2 × B3.2), AgentCore-deployed multi-CSV agent (L3 × B3.3), enterprise-hardened multi-CSV agent (L4 × B3.4). No half-states.

## Original MVP Scope vs L1 Delivery

The originally scoped roadmap had three remaining MVP milestones after MVP.7:

| Original Milestone | Original Scope | L1 Delivery | Status |
|---|---|---|---|
| **MVP.8 — Patcher** | LLM fix generation, one issue per iteration | Two-track `PatchDispatcher`: `DeterministicPatcher` over a `FixRecipe` registry (B1.1) + `LLMPatcher` fallback (B1.2). Reframed from a single LLM patcher to a hybrid — surfaced in `feature_list.md` §6.1 as the right design before MVP.8 was built. | **Shipped** |
| **MVP.9 — Output** | Chart PNG writer | `OutputWriter` protocol + `PNGWriter` (final PNG + re-runnable Python) + `JSONReportWriter` (score trajectory, fix history, final issues, final code). | **Shipped** |
| **MVP.10 — Packaging** | Docker / installable CLI | Editable `pip install -e .[dev]` + `python examples/broken_chart_demo.py` as the entry point; CLI (`plotlint script.py`) deferred to PL-1.4; Docker sandbox deferred to PL-3.1. | **Deferred** |

L1 also shipped two pieces not in the original MVP plan: latent loop-bug fixes (`iteration` never incremented, `score_history` never appended) and rotation-aware `LabelOverlapCheck` so the rotate recipe actually resolves overlap as measured.

## Key Features

**plotlint — visual compliance engine (shipped 2026-05-20):**

- Programmatic bounding-box extraction from matplotlib's artist tree — sub-millisecond, free, deterministic. Rotation-aware: `LabelOverlapCheck` skips AABB collision when both adjacent labels are rotated ≥15° so the AABB doesn't overstate footprint.
- Convergence loop on LangGraph (`StateGraph`) with four stop conditions: perfect score, max iterations, render error, score stagnation. `render_node` increments `iteration`; `inspect_node` appends to `score_history`; `patch_node` invokes the dispatcher.
- Two-track patcher via `PatchDispatcher`. `DeterministicPatcher` consults the `FixRecipe` registry (recipes register via `@recipe(DefectType)` decorator), filters out `(defect_type, recipe_id)` pairs already in `fix_history`, and returns a `PatchResult` from the first applicable recipe. `LLMPatcher` fallback runs only when no recipe applies or all are exhausted — currently scaffolded with an explicit "no production defect type exercises this in L1" gap documented in the module docstring and tested via a `clear_registry()` monkeypatch.
- Four shipped recipes: `rotate_x_labels`, `shrink_x_tick_font` for `LABEL_OVERLAP`; `add_tight_layout`, `enlarge_figure` for `ELEMENT_CUTOFF`. Each recipe is a pure string transformation on source code, emitting matplotlib snippets that are runnable standalone.
- Output writers: `PNGWriter` emits the fixed PNG plus the re-runnable Python file; `JSONReportWriter` emits a structured report with score trajectory, fix history, final issues, and final code. Both are pure functions of `ConvergenceState`.
- Subprocess sandbox isolation for chart code execution; Agg backend forced; pickled `Figure` flows through `RenderResult.figure_data` for the inspector to unpickle and walk.

**autodash — end-to-end pipeline (partial, awaiting B2/B3):**

- Data loading and profiling for CSV / Excel / Parquet via a protocol-based loader registry; semantic-type detection (numeric, categorical, datetime, text, boolean, identifier) with configurable thresholds via `ProfileConfig`.
- Analysis planning: LLM converts `DataProfile` + user questions into validated `AnalysisStep` objects with column-existence and semantic-compatibility checks in `planner.py`.
- Data exploration: LLM generates pandas code; subprocess sandbox executes; retry-with-error-context up to three attempts; result normalised to a DataFrame, summarised, returned as `InsightResult`.
- Chart planning + code generation: two LLM calls — renderer-agnostic `ChartSpec` (JSON) then self-contained matplotlib code. Per-chart-type `DataMapping` validation.
- LangGraph pipeline graph with stub `comply` and `output` nodes awaiting B2.1's orchestrator-worker refactor and B2.2's provenance critic.

## Quick Start

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
python examples/broken_chart_demo.py
```

The demo runs without an API key — both shipped defect types have deterministic recipes, so zero LLM calls are made. Outputs land in `examples/output/`: original + fixed PNGs, the fixed re-runnable Python, and a JSON report per chart. Setting `ANTHROPIC_API_KEY` wires the `LLMPatcher` fallback in, though no defect type currently triggers it.

## Current Quality Metrics

| Metric | Value |
|---|---|
| Tests passing | **434** (up from 368 at MVP.7 baseline) |
| Demo convergence — overlap chart | 0.80 → **1.00** in 1 fix |
| Demo convergence — cutoff chart | 0.00 → **0.80** in 2 fixes |
| Demo wall-clock (both charts, deterministic-only) | ~3 s |
| LLM calls in natural demo path | **0** |

The deterministic-only convergence on the overlap demo is direct evidence for the two-track thesis behind the MVP.8 reframe: a known mechanical fix (rotate, anchor right, reflow) resolves the defect end-to-end with no model spend and full reproducibility. The cutoff demo's 0.00 → 0.80 partial-recovery similarly demonstrates the limit of mechanical recipes — the remaining LOW-severity issue is recipe-recoverable in principle (e.g. shrink-title-font), surfacing the next recipe to write rather than a thesis problem.

## Current State

Paused after MVP.7 on 2026-02-09 (commit `2d05046`); resumed 2026-05-20 with L1 × B1.1 + L1 × B1.2 (MVP.8 + MVP.9) shipped. The recommended initial queue (see [development_plan.md](../development_plan.md)) calls L2 × B2.1 (local pipeline with orchestrator-worker single-CSV agent) and L2 × B2.2 (validation critic + provenance) next, building toward **L2 × B3.2 — local multi-CSV pipeline with join inference** as the headline first publishable AI-agent demo. We have intentionally split infra (Axis A) from AI workflow (Axis B) so the team can advance either axis without entangling the other — for example, the multi-CSV agent (B3.2) can land first locally (L2) and only later re-deploy on Bedrock AgentCore (L3) without changing the agent design itself. MVP.10 (Docker / CLI packaging) remains deferred to PL-1.4 (CLI) and PL-3.1 (Docker sandbox) and is not a prerequisite for any Axis B work.
