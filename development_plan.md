# AutoDash / plotlint: Development Plan

Refer to [vision.md](vision.md) for the full architecture, problem framing, and guiding principles. This document tracks build state and forward milestones.

This plan covers two orthogonal axes:
- **Axis A — Infra / Orchestration** (L1–L4): *how* the system runs.
- **Axis B — AI Workflow Engineering** (B1–B3): *what* the system is intelligent about.

Each merge request lands one (Axis A tier, Axis B stage) cell. The two axes advance independently. See [vision.md](vision.md) for the two-axis framing and [frontier_research_2026-05.md](frontier_research_2026-05.md) for the landscape audit underlying Axis B.

---

## Philosophy

**Build vertically, not horizontally.**

Each iteration delivers a thin slice through the entire plotlint loop (render, inspect, patch, converge). Every version produces something *runnable* and *demonstrable*.

**Value proposition: Deterministic measurement is the right tool for measurable defects.**

Programmatic bounding-box extraction gives exact, reproducible spatial measurements for effectively zero cost. By offloading "what is broken and by how much" to the Inspector, the LLM's complexity budget can be spent on generating surgical fixes — not guessing what's wrong from a screenshot. This scales independently of model choice: better measurement benefits Haiku and Opus alike.

---

## Build state as of resume (2026-05-20)

The project was paused after MVP.7 on 2026-02-09 (commit `2d05046`). Resume begins from this baseline.

### Built — MVP.1 through MVP.7 (368 tests passing)

| Milestone | Date | Deliverable | Tests |
|---|---|---|---|
| **MVP.1** | 2026-02-08 | Foundation + LangGraph scaffold. State schemas (TypedDicts), convergence loop + pipeline graph skeletons, `plotlint/core/` real implementations (errors, config, llm, parsing, sandbox), all MVP.2–9 model types defined upfront. | 69 |
| **MVP.2** | 2026-02-08 | Data intelligence. `autodash/data.py`: protocol-based loader registry (CSV / Excel / Parquet), semantic-type detection (numeric, categorical, datetime, text, boolean, identifier), `ProfileConfig` thresholds, `load_and_profile()` wired into `load_node`. | +46 |
| **MVP.3** | 2026-02-08 | Analysis planning. `autodash/planner.py` + `prompts/analysis_planning.py`. LLM produces validated `AnalysisStep` objects from profile + user questions. Closure-factory DI pattern established. | +35 |
| **MVP.4** | 2026-02-08 | Data exploration. `autodash/explorer.py` + `prompts/data_exploration.py`. LLM generates pandas code → subprocess sandbox → normalized `InsightResult`. Retry loop with error-context prompting. First module to use sandbox end-to-end. | +33 |
| **MVP.5** | 2026-02-08 | Chart planning + code generation. `autodash/charts.py` + two prompts. Two LLM calls: renderer-agnostic `ChartSpec` (JSON) → self-contained matplotlib code. `DataMapping` validation per chart type. | +89 |
| **MVP.6** | 2026-02-08 | Matplotlib renderer. `plotlint/renderer.py`: `Renderer` protocol, `MatplotlibRenderer` (Agg subprocess sandbox), code-wrapping strategy, `RenderResult` (PNG bytes + pickled Figure). `RendererBundle` factory. | +22 |
| **MVP.7** | 2026-02-09 | Inspector foundation. 8 new modules: `geometry.py`, `elements.py`, `scoring.py`, `checks/` registry with `@check` decorator, `extractors/matplotlib.py`, `inspector.py`. LabelOverlapCheck + ElementCutoffCheck. **THE CRITICAL TEST validates the plotlint thesis end-to-end** (20 overlapping x-axis labels → bbox extraction → DefectType.LABEL_OVERLAP detected). | +74 |

### Not built

- **MVP.8 — Patcher.** LLM fix generation, one issue per iteration.
- **MVP.9 — Output.** Chart PNG writer.
- **MVP.10 — Packaging.** Docker / installable CLI.
- Post-MVP tracks (PL: additional defect types, Critic, Plotly, benchmarks · DI: multi-chart, layout, dashboard compliance).

---

## Axis A — Infra / Orchestration (L1–L4)

The forward direction pivots the outer agent loop from LangGraph to Bedrock AgentCore. Each tier ships a coherent demoable artifact independently — work can stop at any tier and the result still stands. **This axis is orthogonal to Axis B (below): infra tiers can be advanced regardless of which AI-workflow stage the system is currently at.**

### L1 — plotlint complete (~1 week)

**Scope:** Finish plotlint MVP.8 (Patcher) + MVP.9 (Output). Standalone visual-compliance engine: render → inspect → patch → re-render → emit. Local execution. LLM calls caravan-routed (so this tier already exercises caravan).

**New files (in this repo):**
- `plotlint/patcher.py` — LLM fix generation, one issue per iteration
- `plotlint/output.py` — PNG writer
- `plotlint/prompts/patch_generation.md`
- `plotlint/loop.py` — wire patcher into the existing convergence loop (currently has the inspect/render nodes only)

**Reused from current code:**
- All of plotlint MVP.1–7 (geometry, extractors, checks, inspector, renderer)
- `LLMClient` protocol → routed through caravan instead of direct Anthropic
- Sandbox + parsing utilities from `plotlint/core/`

**Exit criteria:**
- `pytest` — all existing 368 + new patcher tests pass
- `python examples/broken_chart_demo.py` — deliberately broken matplotlib script with overlapping labels + clipped title → plotlint loop converges → clean PNG output + JSON inspection report
- Demoable in a short video. Standalone library artifact.

**Signal:** FM-evaluation-as-architecture, deterministic complement to VLM critics, caravan integration begun.

---

### L2 — Local pipeline (+3 days)

**Scope:** Add a simple Python orchestration (or minimal local ReAct loop using the Anthropic Claude Agent SDK or plain Python) that drives the existing autodash MVP.2–6 nodes end-to-end. CSV + question input → analysis report output with plotlint-validated charts. All LLM calls caravan-routed.

**New files:**
- `autodash/local_loop.py` — minimal pipeline orchestration; sequential node calls or a small ReAct loop
- `autodash/report.py` — markdown report emitter with embedded PNGs

**Reused from current code:**
- Data loaders, profiler, analysis planner, data explorer, chart generator (MVP.2–6 plumbing translates as-is)
- plotlint convergence loop (now complete after L1)

**Exit criteria:**
- `python -m autodash.local_loop data/titanic.csv "what predicts survival?"` produces a markdown report with 2–3 plotlint-validated charts and narrative
- Caravan yaml-only swap between Anthropic-direct and Ollama for the LLM calls — same end-to-end run works on both

**Signal:** Agentic plumbing demonstrated end-to-end. Not AWS-native yet but coherent. caravan integration verified across two providers.

---

### L3 — Bedrock AgentCore (+1 week) ← cloud-native sweet spot

**Scope:** Replace the local pipeline with AgentCore as the agent reasoning layer. plotlint, sandbox-pandas-exploration, and sandbox-chart-generation become tools the AgentCore agent invokes. AWS-deployed.

**New files:**
- `autodash/agent.py` — AgentCore agent definition: persona, tool registry, prompt
- `autodash/tools/` — tool wrappers around the existing MVP.2–6 functionality (data_load, explore, chart, inspect)
- `infra/agentcore/` — AgentCore configuration (boto3 / IaC)

**Kept:**
- `local_loop.py` remains as the local-dev fallback; the AgentCore path is the cloud target

**Exit criteria:**
- `python deploy.py` provisions AgentCore agent with tool bindings
- Same CSV + question input invokes the AgentCore agent → tools execute (in subprocess sandbox or via Lambda) → AgentCore returns analysis with plotlint-validated charts
- Console run visible in AWS console with agent trace

**Signal:** Bedrock-native, AgentCore-native, AWS competence demonstrated.

---

### L4 — Enterprise hardening (+1 week)

**Scope:** Wrap AgentCore in Step Functions for durable workflow; add Bedrock Guardrails as a safety node; OpenTelemetry → CloudWatch tracing; CI eval harness using Bedrock model-evaluation API.

**New files:**
- `infra/step-functions/state-machine.json` — Step Functions definition: ingest → validate → AgentCore agent → render → guardrails → emit → audit log
- `autodash/guardrails/` — Bedrock Guardrails configuration (PII, prompt injection, content safety) integrated as a workflow node
- `autodash/telemetry.py` — OpenTelemetry span emitters around agent decisions, tool calls, LLM cost / latency
- `eval/benchmark.py` + `.github/workflows/eval.yml` — small benchmark suite (5–10 CSV + question pairs with expected chart properties) run in CI via Bedrock model-evaluation API

**Exit criteria:**
- Step Functions execution console shows full state-machine trace
- CloudWatch shows OpenTelemetry spans for agent decisions and tool calls with cost attribution
- Guardrails block deliberately injected prompt-injection test inputs
- CI eval runs on every PR and reports pass/fail with metrics

**Signal:** Senior-architect-level judgment (when to combine durable workflow with agentic reasoning rather than letting the agent own everything). Full enterprise-ready story.

---

### Axis A stopping points

Each tier ships a coherent, demoable artifact. Work can stop after any tier:

- **Stop at L1:** publishable novelty library + caravan integration
- **Stop at L2:** full local agentic pipeline + multi-provider verification
- **Stop at L3:** AgentCore-native cloud deployment
- **Stop at L4:** maximum enterprise signal

Total Axis A full path: ~3–4 weeks. Partial-path stopping points are coherent at every level.

---

## Axis B — AI Workflow Engineering (B1–B3)

The infra axis above describes *how* the system is deployed. This axis describes *what* the system is intelligent about. Each phase below ships AI-workflow capabilities orthogonal to the infra axis — B-stage advances can land in any L-tier.

Source for landscape and methodology choices: [frontier_research_2026-05.md](frontier_research_2026-05.md). The design questions surfaced in [feature_list.md](feature_list.md) §6 are formalised here.

### B1 — Chart patcher track (~1 week total)

Closes plotlint's fix loop with the explicit two-track structure flagged in [feature_list.md](feature_list.md) §6.1: a deterministic fast path for mechanical defects, with the LLM patcher reserved as fallback for semantic defects. Replaces the originally monolithic MVP.8 design.

#### B1.1 — Deterministic mechanical-defect patcher (~3 days)

**Scope.** For the measurable defects the inspector already detects, apply known transformations directly without any LLM call:

- Label overlap → rotate 45° / shrink font / abbreviate / sample every Nth label
- Element cutoff → enlarge figure / enable `constrained_layout` / shrink offending font
- Legend occluding data → reposition with `bbox_to_anchor` / shrink legend font
- Colour-blind-unsafe palette → swap to `viridis` / `cividis` / palettable safe palette
- Raw axis numbers (e.g. `1000000`) → apply `FuncFormatter` with k/M/B suffix or `EngFormatter`

**New files:**
- `plotlint/patcher_deterministic.py` — orchestrator for mechanical fixes
- `plotlint/fix_recipes/` — one recipe module per defect type (`overlap.py`, `cutoff.py`, `legend.py`, `palette.py`, `formatting.py`)

**Operates on:** rendered `Figure` object first; AST rewriter for the subset of recipes that need source-code patching (so the output remains re-runnable code, not just a fixed image).

**Verification:** re-render, re-measure the inspection score, roll back if score regressed. No LLM calls.

**Exit criteria:** the existing broken-chart demo (overlapping x-axis labels + clipped title) converges to score 1.0 on the common defect set without invoking any LLM. New tests covering the mechanical-fix catalogue pass. Demo runs in <2 seconds end-to-end.

#### B1.2 — LLM patcher fallback for semantic defects (~3 days)

**Scope.** What was originally scoped as MVP.8 (a single LLM patcher for everything) is reframed here as the *fallback*. Triggered when B1.1 reports "no mechanical recipe applies" or the defect type is semantic (wrong chart type, axis range hides the signal, colour encoding doesn't match meaning).

**New files:**
- `plotlint/patcher_llm.py` — LLM fix generation
- `plotlint/prompts/patch_generation.md` — prompt template

**LLM calls** routed through `plotlint.core.llm.LLMClient` (caravan-routed at deploy time).

**Trigger logic** lives in `plotlint/loop.py`: loop tries B1.1 first; if no recipe applies or score doesn't improve, fall through to B1.2.

**Exit criteria:** broken-chart demo with a deliberately mis-typed chart (e.g. scatter plot of a categorical-by-time series) converges via the LLM patcher. Demo with mechanical defects only does *not* invoke the LLM (proves the fallback gating works).

---

### B2 — Single-CSV agent maturity (~1 week total)

Apply research-agent design patterns (see [frontier_research_2026-05.md](frontier_research_2026-05.md) §6) to the existing single-CSV pipeline (MVP.2–6, already built). Closes the gap between "small agent" and "real agent."

#### B2.1 — Orchestrator-worker + scratchpad refactor (~3 days)

**Scope.** Replace the linear LangGraph pipeline with an explicit orchestrator agent that dispatches per-step workers, and a shared scratchpad accumulating discovered schema, profile findings, analysis-step results, chart specs, and defect findings.

**Pattern source:** Anthropic multi-agent research system (orchestrator-worker); LangGraph deep agents.

**New files:**
- `autodash/orchestrator.py` — lead agent: parses question, dispatches workers, aggregates results
- `autodash/scratchpad.py` — typed shared-memory structure persisting across pipeline steps

Existing per-step modules (`planner.py`, `explorer.py`, `charts.py`) become workers invoked by the orchestrator instead of LangGraph nodes called sequentially.

**Exit criteria:** pipeline traces show explicit planner → executor → critic decomposition. Scratchpad persists across steps and is inspectable. Existing 368 tests still pass.

#### B2.2 — Validation critic + provenance tracking (~3 days)

**Scope.** Add an explicit critic pass after each step (planning critic, exploration critic, chart critic) — lightweight deterministic checks plus LLM-as-judge for semantic plausibility. Add provenance tracking: every number in every chart is tagged with `(source_file, column, transformation, aggregation, join_path)`.

**New files:**
- `autodash/critic.py` — per-step validation
- `autodash/provenance.py` — number → lineage tracking
- `autodash/report.py` — markdown report emitter with embedded PNGs and hover/click-through provenance per number

**Exit criteria:** generated report shows clickable provenance for each number. Critic flags catch a deliberately wrong analysis in a test fixture (e.g. mean of a categorical column).

---

### B3 — Multi-CSV agent (~3–4 weeks total)

The headline AI-workflow capability. Lands the project in the underbuilt area identified in [feature_list.md](feature_list.md) §6.2 and confirmed by [frontier_research_2026-05.md](frontier_research_2026-05.md) §3.

#### B3.1 — Multi-file profiling + question routing (~3 days)

**Scope.** Accept multiple files in one invocation. Profile each. Label each by inferred grain ("one row per customer," "one row per order," "one row per click"), candidate key columns, temporal columns. Analysis planner picks *which file* per analysis step. No joins yet.

**New files:**
- `autodash/multi_file.py` — multi-file profiling and per-file labelling; extends existing `autodash/data.py`

**Exit criteria:** demo with 3 unrelated CSVs (e.g. weather, sales, support tickets — no shared keys) answers per-file questions correctly without confusion. Planner trace shows which file was picked for each step.

#### B3.2 — Join inference (single-pass) (~1 week)

**Scope.** Propose join keys via name overlap + type overlap + sampled value-set overlap. Optional LLM-as-judge ranks ambiguous candidates. Validate joins: row-count plausibility, null-rate post-join, type integrity, sample spot-check. One join attempt per question; report what was joined and why with a confidence score.

**Pattern source:** HyperJoin (LLM-augmented hypergraph join discovery, +21% Precision@15), Magneto (hybrid small+large LLM schema matching), Snoopy (semantic join discovery via proxy columns) — see [frontier_research_2026-05.md](frontier_research_2026-05.md) §4.

**New files:**
- `autodash/join_inference.py` — candidate-key proposal
- `autodash/join_validation.py` — row count, null rate, type, sample checks

The worker pattern from B2.1 is used for parallel candidate-key validation.

**Exit criteria:** demo with related CSVs (orders ↔ customers ↔ products, implicit foreign keys, no human schema) infers correct joins on the first attempt. Report shows validation evidence: which key was chosen, why, row-count check passed, sample rows.

#### B3.3 — Iterative replanning + user clarification (~1 week)

**Scope.** Reflexion-style memory: if a join fails (0 rows, type mismatch, implausible row-count explosion), record why; propose alternative paths. Bounded retry budget (max 2–3 replans). Orchestrator-worker dispatches parallel hypothesis testing on candidate join paths. Confidence-thresholded escalation: when the top hypotheses score within a threshold of each other, surface a clarification question to the user with ranked options and evidence.

**Pattern source:** Reflexion (linguistic-feedback memory loop); Anthropic multi-agent research system (orchestrator-worker with parallel subagents); research-agent stop-criteria-and-escalate pattern — see [frontier_research_2026-05.md](frontier_research_2026-05.md) §6.

**New files:**
- `autodash/replanner.py` — Reflexion-style memory + bounded retry
- `autodash/clarification.py` — confidence-thresholded escalation; emits structured clarification request

**Exit criteria:** demo with ambiguous CSVs (two plausible join keys, e.g. `customer_id` and `email`) triggers either a replan that succeeds *or* a clarification question to the user. Decision-tree transcript exportable. Worst-case wall time bounded by the retry budget.

#### B3.4 — Enterprise hardening of the multi-CSV agent (~1 week)

**Scope.** Drive the non-negotiables surfaced in [frontier_research_2026-05.md](frontier_research_2026-05.md) §2.7:

- **Provenance audit trail.** Every step logged with timestamp, model, tools, input/output hashes. Exportable as JSON.
- **Sanity bounds.** Configurable assertions (e.g. "post-join row count should be within X% of input"); fail loud rather than silently producing wrong numbers.
- **Semantic-layer integration hook.** If a metric definition file is provided (dbt-style YAML, Cube schema, or custom), prefer it over inferred aggregation.
- **Cost telemetry per analysis.** Per-question token spend, model attribution.

**New files:**
- `autodash/audit.py` — exportable audit-log emitter
- `autodash/semantic_layer.py` — hook surface only; actual integrations (LookML / dbt / Cube) left to deployers

**Exit criteria:** end-to-end multi-CSV analysis produces an exportable JSON audit log with full per-step lineage. A metric definition file overrides inferred aggregation in a test fixture. Sanity-bound violations cause hard failure with a clear error pointing to the offending step.

---

### Axis B stopping points

- **Stop at B1.2** — plotlint is a complete visual-compliance library with a hybrid deterministic + LLM patcher. Publishable open-source artifact.
- **Stop at B2.2** — the single-CSV pipeline is a "real" agent with orchestrator-worker, validation critic, and provenance. Demo-quality.
- **Stop at B3.2** — multi-CSV joins work for cooperative cases. Headline differentiator versus shipping products.
- **Stop at B3.3** — multi-CSV agent is genuinely agentic (replans, escalates). Frontier-credible.
- **Stop at B3.4** — multi-CSV agent is enterprise-credible (audit, sanity bounds, semantic-layer hook).

---

## Merge-request grid

Each MR addresses one (Axis A tier, Axis B stage) cell. Examples of coherent cells:

| Cell | What it ships | Demoable as |
|---|---|---|
| **L1 × B1.1** | plotlint standalone library with deterministic patcher only | `plotlint broken.py` — no LLM call, free, sub-second |
| **L1 × B1.2** | plotlint standalone library with hybrid det+LLM patcher | `plotlint broken_semantic.py` falls through to LLM |
| **L2 × B2.1** | local pipeline driven by orchestrator-worker single-CSV agent | `python -m autodash titanic.csv "..."` shows agent trace |
| **L2 × B2.2** | local pipeline with critic + provenance | clickable report lineage on local output |
| **L2 × B3.1** | local pipeline accepting multiple files (no joins) | demo with 3 unrelated CSVs answers per-file questions |
| **L2 × B3.2** | local pipeline with join inference | demo with 3 related CSVs joins automatically; shows validation evidence |
| **L3 × B3.2** | AgentCore-deployed multi-CSV agent with join inference | AWS console shows agent trace; join validated |
| **L3 × B3.3** | AgentCore-deployed multi-CSV agent with replanning + clarification | console shows replan decision tree + clarification question to user |
| **L4 × B3.4** | enterprise-hardened multi-CSV agent on Step Functions + Guardrails + audit + CI eval | exportable audit log; Guardrails blocks an injection test; OTel cost attribution per analysis |

Most (A, B) cells make sense. Some don't — L4 with anything below B2.2 has nothing meaningful to harden; L1 with B3.x has no orchestration to run the agent. The grid is a thinking tool; the MR queue is whichever cell the team picks next.

### Recommended initial queue (post-resume, 2026-05 baseline)

Priority order, each step a single MR:

1. **L1 × B1.1** — finish plotlint deterministically. Fast, no LLM dependency, ships first.
2. **L1 × B1.2** — add the LLM fallback. plotlint complete.
3. **L2 × B2.1** — orchestrator-worker refactor of the single-CSV pipeline. Foundation for B3.
4. **L2 × B2.2** — critic + provenance. Single-CSV demo-quality.
5. **L2 × B3.1** — multi-file no-joins. Cheap stepping stone.
6. **L2 × B3.2** — multi-CSV with join inference. **The headline differentiator. First publishable AI-agent demo.**
7. **L3 × B3.2** — re-deploy on Bedrock AgentCore. AWS-native signal.
8. **L3 × B3.3** — replanning + clarification on AgentCore. Frontier-credible.
9. **L4 × B3.4** — enterprise hardening on Step Functions + Guardrails + OTel + eval CI. Enterprise-credible.

---

## Tech stack

| Component | Choice | Caravan-abstracted? |
|---|---|---|
| Outer orchestration (cloud) | AWS Step Functions | No |
| Outer orchestration (local) | Plain Python or minimal ReAct loop | No (different code path) |
| Agent reasoning (cloud) | Bedrock AgentCore | No |
| Agent reasoning (local) | Minimal ReAct loop | No |
| Agent design pattern (B2.1+) | Orchestrator-Worker (Anthropic pattern) | No (implementation, not swappable concern) |
| Join inference (B3.2) | Name + type + value-set overlap; LLM tiebreaker via caravan | LLM tiebreaker only |
| Replanning (B3.3) | Reflexion-style memory; bounded retry | No |
| Provenance store (B2.2+) | In-process structured log; JSON export | No |
| Foundation model (cloud) | Claude via Bedrock | **Yes** — caravan-routed |
| Foundation model (local) | Ollama (e.g., Llama 3.x or Qwen) | **Yes** — caravan-routed |
| Safety | Bedrock Guardrails | No (cloud-only) |
| Observability | OpenTelemetry → CloudWatch | No |
| Chart quality engine | plotlint (own) | n/a (consumes caravan-routed LLM internally) |
| Sandbox | subprocess (already built) | No |
| Data | pandas, matplotlib | No |
| Eval | Bedrock model-evaluation API + pytest in GH Actions | No |
| Lint / format | ruff | No |

---

## Verification per Axis A tier

### L1
1. `pytest` — plotlint convergence loop tests pass
2. `python examples/broken_chart_demo.py` → fixed PNG + JSON inspection report
3. Same demo runs with `LLM_PROVIDER=ollama` (caravan-routed local LLM) without code changes

### L2
1. `python -m autodash.local_loop data/titanic.csv "what predicts survival?"` produces a markdown report
2. Same command runs cleanly on both Anthropic-direct and Ollama via caravan yaml

### L3
1. AgentCore agent provisioned via deploy script
2. Same CSV + question input runs end-to-end through AgentCore in AWS
3. Agent trace visible in console; tools invoke correctly; plotlint-validated charts in output

### L4
1. Step Functions execution shows full state-machine trace
2. CloudWatch shows OpenTelemetry spans with cost attribution
3. Bedrock Guardrails blocks injected prompt-injection test inputs
4. CI eval harness runs on PR and reports pass/fail

## Verification per Axis B stage

### B1.1 — Deterministic patcher
1. `pytest tests/test_patcher_deterministic.py` — recipe catalogue tests pass
2. `python examples/broken_chart_demo.py` converges to score 1.0 without invoking any LLM (check trace shows zero LLM calls)
3. Wall-clock time of demo < 2 seconds

### B1.2 — LLM patcher fallback
1. `python examples/broken_chart_semantic_demo.py` (deliberately mis-typed chart) converges via the LLM patcher; trace shows fallback was triggered
2. The B1.1 demo still passes with zero LLM calls — proves the fallback gating works

### B2.1 — Orchestrator-worker + scratchpad
1. Existing 368 tests still pass
2. Pipeline trace shows explicit planner → executor → critic decomposition
3. Scratchpad is inspectable mid-run (dump-to-JSON utility)

### B2.2 — Validation critic + provenance
1. Generated report shows clickable / hoverable provenance per number
2. `pytest tests/test_critic_catches_wrong_analysis.py` — critic catches deliberately wrong analysis (e.g. mean of categorical column)

### B3.1 — Multi-file profiling
1. Demo with 3 unrelated CSVs answers per-file questions correctly
2. Planner trace shows which file was picked for each step

### B3.2 — Join inference
1. Demo with related CSVs (orders, customers, products with implicit foreign keys) infers correct joins on first attempt
2. Report shows validation evidence: which key, why, row-count check, sample rows
3. `pytest tests/test_join_validation.py` — row-count plausibility checks catch a known-bad join

### B3.3 — Iterative replanning + clarification
1. Demo with ambiguous CSVs (two plausible join keys) triggers either a successful replan or a clarification question
2. Decision-tree transcript exportable
3. Worst-case wall time bounded by the retry budget

### B3.4 — Enterprise hardening
1. End-to-end multi-CSV analysis produces an exportable JSON audit log with full per-step lineage
2. A metric definition file overrides inferred aggregation in a test fixture
3. Sanity-bound violations cause hard failure with a clear error pointing to the offending step

---

## Guiding mantra

The "Declarative, Modular, SoC" mantra and the additional principles (Measure-Don't-Guess, Risk-First Validation, Incremental Value, Honest Abstraction) are defined in [vision.md](vision.md) §Guiding Principles. Every implementation decision should be evaluated against them.
