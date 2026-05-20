# AutoDash / plotlint: Development Plan

Refer to [vision.md](vision.md) for the full architecture, problem framing, and guiding principles. This document tracks build state and forward milestones.

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

## Forward roadmap — tiered deliverables

The forward direction pivots the outer agent loop from LangGraph to Bedrock AgentCore. Each tier ships a coherent demoable artifact independently — work can stop at any tier and the result still stands.

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

## Stopping points

Each tier ships a coherent, demoable artifact. Work can stop after any tier:

- **Stop at L1:** publishable novelty library + caravan integration
- **Stop at L2:** full local agentic pipeline + multi-provider verification
- **Stop at L3:** AgentCore-native cloud deployment
- **Stop at L4:** maximum enterprise signal

Total full path: ~3–4 weeks. Partial-path stopping points are coherent at every level.

---

## Tech stack

| Component | Choice | Caravan-abstracted? |
|---|---|---|
| Outer orchestration (cloud) | AWS Step Functions | No |
| Outer orchestration (local) | Plain Python or minimal ReAct loop | No (different code path) |
| Agent reasoning (cloud) | Bedrock AgentCore | No |
| Agent reasoning (local) | Minimal ReAct loop | No |
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

## Verification per tier

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

---

## Guiding mantra

The "Declarative, Modular, SoC" mantra and the additional principles (Measure-Don't-Guess, Risk-First Validation, Incremental Value, Honest Abstraction) are defined in [vision.md](vision.md) §Guiding Principles. Every implementation decision should be evaluated against them.
