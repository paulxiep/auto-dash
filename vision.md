# AutoDash: End-to-End Data → Dashboard

## Executive Summary

**AutoDash** is an end-to-end pipeline: data tables + natural-language questions → polished, multi-chart dashboards. Its core engine, **plotlint**, closes the visual feedback loop through **programmatic spatial analysis** — extracting bounding boxes directly from the rendering engine and running geometric collision detection.

The first generation of multimodal models could *see* charts but not measure them. That gap has narrowed: recent vision-language models can produce pixel-mapped coordinates for chart elements and reason about layout reasonably well. plotlint's role updates accordingly. It is no longer "the only way to measure" — it is **the deterministic complement to VLM chart critics** for the class of defects where measurement, not judgment, is the right answer.

| Property | VLM critic | plotlint |
|---|---|---|
| **Cost** | ~$0.01–0.03 per call | effectively free |
| **Latency** | 1–3 s per call | <1 ms |
| **Determinism** | non-deterministic; different answer each call | exactly reproducible |
| **Best at** | semantic / aesthetic judgment (color meaning, chart-type fit) | measurable geometric defects (overlap, cutoff, occlusion, contrast) |

Direct artist-tree extraction is strictly superior for measurable defects. VLM critique is reserved for the ~20% of issues that require semantic judgment.

```
$ autodash sales.csv "What drove Q4 revenue? How do regions compare?"
→ Loads & profiles data
→ Plans analysis, explores data, identifies insights
→ Generates charts, each polished by plotlint (visual compliance engine)
→ Composes dashboard with layout intelligence
→ Outputs: dashboard.html (interactive) + dashboard.png (static)
```

```
$ plotlint broken_chart.py
→ Renders chart, inspects for visual defects
→ Fixes: label overlap, legend occlusion, y-axis formatting
→ Converges in 3 iterations (score: 0.30 → 0.72 → 0.88 → 1.00)
→ Outputs: fixed code + convergence GIF
```

---

## The Problem

LLMs generate chart code that is syntactically correct but visually broken: overlapping labels, legends covering data, titles cut off, colors indistinguishable in colorblind mode. The code runs. It just looks terrible.

### Layer 1: The Feedback Loop is Still Manual

Most LLM coding tools (Code Interpreter, Claude artifacts, Copilot) send the rendered image to the user, not back into the model's context. The user screenshots, pastes back, says "fix the labels," gets new code, re-runs, finds the legend is now broken, pastes again. **The human is still the feedback loop.**

### Layer 2: Vision Is Expensive, Slow, and Non-Deterministic

Modern multimodal models *can* see and measure charts. The remaining question is whether to pay for that capability when a cheaper, faster, deterministic alternative exists:

| What you need | Modern VLM | plotlint |
|---|---|---|
| **Cost per inspection** | $0.01–0.03 | effectively free |
| **Latency per inspection** | 1–3 s | sub-ms |
| **Reproducibility** | different answer each call | byte-identical |
| **Suitability for measurable defects** | adequate | exact |
| **Suitability for semantic judgment** | exact | not applicable |

For a convergence loop that may render and inspect a chart 5–10 times before settling, VLM-only inspection adds dollars and seconds per chart. plotlint pushes the measurable-defect work to a deterministic geometric evaluator and reserves VLM calls for the cases that genuinely need judgment.

### Layer 3: Fixes Interact

Visual layout problems are emergent and fixes cascade. Rotating labels changes the figure's effective height, which pushes the legend, which now overlaps the title. A linear "fix one thing" approach doesn't work — you need a convergence loop that re-inspects the *entire* chart after each fix, detects regressions, and rolls back when things get worse.

And even when individual charts look fine, assembling them into a coherent dashboard is another manual process: deciding layout, ensuring consistent styling, creating visual hierarchy.

### plotlint's Approach

**Measure, don't guess.** The Inspector extracts bounding boxes directly from the rendering engine's internal representation (matplotlib's artist tree, plotly's DOM) and runs geometric collision detection. This gives exact, actionable measurements — for free, in milliseconds, deterministically. VLM critique is reserved for the issues that genuinely require semantic judgment.

**AutoDash automates both loops.** plotlint handles per-chart visual compliance. The Dashboard Compliance Agent handles multi-chart composition.

### Why This Requires Agents, Not Scripts

| Capability | Script / Linter | plotlint |
|------------|-----------------|----------|
| **Detection** | Rule-based checks (font size > 8?) | Sees that labels visually overlap at render time |
| **Diagnosis** | One check at a time | Reasons about interactions (fixing overlap might push legend off-canvas) |
| **Repair** | Cannot modify code | Rewrites the specific matplotlib/plotly call to fix the issue |
| **Verification** | Static analysis only | Re-renders and confirms the fix actually worked |
| **Convergence** | Single pass | Loops until all issues resolved or max retries hit |

The core insight: **visual layout problems are emergent**. You cannot statically analyze Python code and know that labels will overlap — it depends on the data, the figure size, the font, the DPI, and how matplotlib's layout engine distributes space. You must render to know.

---

## Architecture Overview

AutoDash targets two execution modes, chosen at deploy time:

### Cloud target

```
                 ┌─────────────────────────────────────────────┐
                 │  AWS Step Functions (durable workflow)       │
                 │  ingest → validate → AGENT → render →        │
                 │  guardrails → emit → audit                   │
                 └───────────────────┬─────────────────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │  Bedrock AgentCore         │  ← agent reasoning
                       │  (tool registry: load,     │
                       │   explore, chart, inspect) │
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

### Local mode

```
                 ┌────────────────────────────────────┐
                 │  Plain Python or minimal ReAct loop │
                 │  (sequential or agent-style)        │
                 └──────────────────┬──────────────────┘
                                    │
                       ┌────────────▼────────────┐
                       │  Same tool implementations │
                       │  (plotlint, sandbox)       │
                       └────────────────────────────┘

  Foundation model: Ollama (e.g., Llama 3.x, Qwen) — routed through caravan
```

### Honest abstraction scoping

The two modes share **tool implementations and the LLM-call layer**, not orchestration. Pretending otherwise would create a leaky abstraction that fails the moment a non-trivial cloud-specific feature gets used.

| Layer | Cloud | Local | Caravan-abstracted? |
|---|---|---|---|
| LLM provider call | Bedrock Claude | Ollama | **Yes** — seam is clean (messages in → response out) |
| Agent orchestration | AgentCore | Minimal local ReAct loop | **No** — feature surfaces too different |
| Workflow orchestration | Step Functions | Plain Python | **No** — abstraction would be too thin to be worth it |
| Tool implementations (plotlint, sandbox) | shared | shared | n/a |

Concretely: plotlint patcher, chart-code generation, and data-exploration LLM calls all flow through caravan and can be retargeted between Bedrock and Ollama by a single YAML edit. AgentCore and Step Functions are cloud-only — the local path is a separate code path, not a caravan-swapped equivalent.

---

## What's Novel vs Plumbing

| Component | Status | Why |
|---|---|---|
| Data loading, profiling, planning, pandas execution | plumbing | Every LLM-agent framework does this |
| Agent orchestration on AgentCore + Step Functions | uncommon | Few candidates have built on AgentCore yet |
| Bedrock Guardrails as an architectural node | uncommon | Treated as architecture, not as a wrapper afterthought |
| **plotlint** (programmatic spatial analysis) | **novel** | No mature production tool enforces chart quality this way |
| **Multi-chart dashboard compliance** | **novel** | Static layout checking + style harmony across charts |
| FM-output evaluation as a deterministic side-channel | **novel positioning** | Cost / latency / determinism win for measurable defects; VLM reserved for judgment |

The combination — AgentCore-native agentic dashboarding + deterministic chart evaluator + honestly-scoped provider abstraction at the LLM-call layer — is currently uncommon. Standalone auto-EDA is a commodity (Julius, ChatGPT Advanced Data Analysis, Hex Magic). The composition is what makes this defensible.

---

## Guiding Principles

> **"Declarative, Modular, SoC"**

Every implementation decision should be evaluated against these three principles:

| Principle | Meaning | Example |
|-----------|---------|---------|
| **Declarative** | Describe *what*, not *how*. Config over code. Data-driven behavior. | Defect checks declare their severity thresholds; chart specs define what to render, not how. Inspector checks are data (defect taxonomy), not hardcoded if-else chains. |
| **Modular** | Components are self-contained, swappable, and independently testable. plotlint works standalone or inside AutoDash. | Renderer, Inspector, Patcher, Critic are independent modules. Swap matplotlib backend for plotly without touching collision detection. |
| **SoC** (Separation of Concerns) | Each module has ONE job. No god objects. Clear boundaries. | Inspector detects issues. Patcher fixes them. Convergence loop orchestrates. No component does two things. |

### Additional principles

| Principle | Meaning | Example |
|---|---|---|
| **Measure, Don't Guess** | Prefer programmatic measurement over LLM inference. Use LLM only where judgment is required. | Inspector extracts pixel-precise bounding boxes; Critic invoked only for semantic checks. |
| **Risk-First Validation** | Highest-risk assumptions get validated earliest. | Bounding-box extraction reliability was validated in MVP.7 (THE CRITICAL TEST), not in a separate spike. |
| **Incremental Value** | Each version improves user-facing capability. | MVP produces a working fix loop, not just "rendering works". |
| **Honest abstraction** | Abstract only where seam surfaces converge. Don't paper over feature differences. | caravan abstracts the LLM-call layer; AgentCore and Step Functions are cloud-only by design. |

---

## Modular Design

Every component communicates via well-defined interfaces. plotlint works standalone (`plotlint script.py`) or inside the AutoDash pipeline. Chart and dashboard specifications are renderer-agnostic — the same spec can target matplotlib, plotly, or future renderers.

| Component | Input | Output | Standalone? |
|-----------|-------|--------|-------------|
| Data Intelligence | Raw data | Schema + profile | Yes |
| Analysis Planner | Profile + questions | List[AnalysisStep] | No |
| Data Explorer | AnalysisStep + DataFrame | InsightResult | No |
| Chart Planner | Insights + questions | List[ChartSpec] + code | No |
| **plotlint Renderer** | Chart code | RenderResult (Figure + PNG) | **Yes** |
| **plotlint Inspector** | RenderResult | List[Issue] + score | **Yes** |
| **plotlint Patcher** | Code + Issue | Patched code | **Yes** |
| **plotlint Convergence Loop** | Chart code | Polished code + convergence trace | **Yes** |
| Layout Engine | List[ChartSpec] | LayoutSpec | Yes |
| Dashboard Compliance | LayoutSpec + rendered tiles | List[layout issues] | Yes |

plotlint has **zero imports** from autodash. autodash imports from `plotlint.core` (LLM client protocol, sandbox, parsing, errors, config). The `comply_node` is the bridge.

---

See [development_plan.md](development_plan.md) for the tiered milestone roadmap and current build state.
