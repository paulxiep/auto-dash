# AutoDash + plotlint: Technical Summary

## Architecture

Two packages, one monorepo. Strict dependency direction: `plotlint` has zero imports from `autodash`. `plotlint.core` is the shared foundation imported by both. The convergence loop and the autodash pipeline both run on LangGraph `StateGraph` for local Python; the cloud target (L3+) replaces the autodash outer orchestrator with Bedrock AgentCore while preserving the inner convergence loop verbatim.

```
        plotlint/core/
       (llm, sandbox, parsing,
        errors, config)
           ↑          ↑
           │          │
      plotlint/     autodash/
     (compliance   (pipeline,
      engine)       planning,
                    exploration)
```

| Package | Single Responsibility |
|---|---|
| `plotlint/core/` | Foundation utilities — `LLMClient` protocol + `AnthropicClient` / `GeminiClient`, subprocess sandbox (`execute_code`), response parsing (`parse_code_from_response`, `parse_json_from_response`), error hierarchy, config dataclasses |
| `plotlint/` | Convergence loop infrastructure — `loop.py`, `models.py` (`ConvergenceState` TypedDict, `Issue`, `InspectionResult`, `FixAttempt`, `PatchResult`, `RenderResult`), `geometry.py`, `elements.py`, `scoring.py`, `renderer.py`, `inspector.py`, `config.py` |
| `plotlint/checks/` | Defect detection — `@check`-registered `LabelOverlapCheck`, `ElementCutoffCheck`. Inspector queries the registry; never hardcoded. |
| `plotlint/extractors/` | Renderer-specific bbox extraction — `MatplotlibExtractor` walks the artist tree |
| `plotlint/fix_recipes/` | Deterministic mechanical-fix recipes — `@recipe`-registered, one transformation per file |
| `plotlint/patcher.py`, `plotlint/patcher_deterministic.py`, `plotlint/patcher_llm.py` | Patcher track (MVP.8, reframed) — `PatchDispatcher` routes deterministic-first / LLM-fallback |
| `plotlint/prompts/patching.py` | LLM prompt templates keyed by renderer type |
| `plotlint/output.py` | Output writers (MVP.9) — `OutputWriter` protocol + `PNGWriter` + `JSONReportWriter` + registry |
| `autodash/` | End-to-end pipeline — `data.py` (loaders, profiling), `planner.py`, `explorer.py`, `charts.py`, `pipeline.py` (LangGraph graph); outer orchestrator B2.1+ pending |
| `autodash/prompts/` | Pipeline LLM prompts — analysis planning, data exploration, chart planning, code generation |

## Original MVP Scope vs L1 Delivery

The originally scoped roadmap had three remaining MVP milestones after MVP.7. L1 delivers MVP.8 and MVP.9 with the MVP.8 patcher reframed as a hybrid two-track dispatcher. MVP.10 (packaging) is deferred.

| Original Milestone | Original Scope | L1 Delivery | Status |
|---|---|---|---|
| **MVP.8 — Patcher** | LLM fix generation, one issue per iteration. Single LLM patcher. | `PatchDispatcher` routes deterministic-first / LLM-fallback. `DeterministicPatcher` consults a `FixRecipe` registry; `LLMPatcher` only fires when no recipe applies or all are exhausted. The two-track reframe was surfaced during the 2026-05 post-pause rescope before MVP.8 was built. | **Shipped** as L1 × B1.1 + B1.2 |
| **MVP.9 — Output** | Chart PNG writer. | `OutputWriter` protocol + `PNGWriter` (final PNG + re-runnable Python) + `JSONReportWriter` (score trajectory + fix history + final issues + final code) + registry / factory. | **Shipped** as L1 supporting |
| **MVP.10 — Packaging** | Docker / installable CLI. | Editable `pip install -e .[dev]`; `python examples/broken_chart_demo.py` is the user entry point. Standalone `plotlint` / `autodash` CLI deferred to PL-1.4; Docker sandbox deferred to PL-3.1. | **Deferred** |

L1 also shipped two not-in-original-MVP items: latent loop-bug fixes (`iteration` was never incremented, `score_history` was never appended) and rotation-aware `LabelOverlapCheck` so the rotate recipe actually resolves overlap as measured.

## Convergence Loop Pipeline

The plotlint convergence loop is a LangGraph `StateGraph` with three nodes and a conditional edge. Each node reads / writes a narrow slice of `ConvergenceState` (a `TypedDict, total=False`).

```
                  ┌────────────────────────────────────────────────────────────┐
                  │ ConvergenceState (TypedDict)                                │
                  │   source_code, original_code, png_bytes, figure_pickle,     │
                  │   render_error, inspection, score, score_history,           │
                  │   iteration, max_iterations, fix_history, patch_applied,    │
                  │   renderer_type, ...                                        │
                  └────────────────────────────────────────────────────────────┘

   START
     │
     ▼
  render_node ──── reads:  source_code
     │             writes: iteration (++), png_bytes, figure_pickle, render_error
     ▼
  inspect_node ── reads:  figure_pickle
     │             writes: inspection, score, score_history (.append)
     ▼
  should_continue (conditional edge)
     │
     ├── "patch" ── score < target_score, iteration < max, no render_error, no stagnation
     │     ▼
     │   patch_node ─ reads:  source_code, inspection, fix_history
     │     │          writes: source_code (patched), fix_history (.append), patch_applied
     │     │
     │     └──── back to render_node
     │
     └── "stop" ──── END
```

Stop conditions are evaluated in `_make_should_continue(config)` (a closure factory that captures `ConvergenceConfig`): perfect score (`score >= target_score`), max iterations reached, render error present, or score stagnant for `stagnation_window` iterations within `score_improvement_threshold`. See [plotlint/loop.py:96](../plotlint/loop.py#L96).

## Patching Architecture (MVP.8 reframed)

`PatchDispatcher` is the single source of truth for routing. It receives the current `source_code`, the current `inspection`, and `fix_history`, and returns an `Optional[PatchResult]`.

```
   inspection.highest_severity_issue ─── None → return None
                  │
                  ▼
   DeterministicPatcher.patch(code, issue, fix_history)
                  │
                  │  1. get_recipes_for(issue.defect_type)
                  │  2. filter out (defect_type, recipe_id) in fix_history
                  │  3. filter out recipes whose can_apply() is False
                  │  4. return first remaining recipe's apply() result
                  │
                  ├── PatchResult ──────────────────── return
                  │
                  └── None (no recipe / all exhausted)
                              │
                              ▼
                   if llm is not None:
                     LLMPatcher.patch(code, issue, fix_history)
                              │
                              │  - build_user_prompt(renderer_type, code, issue, history)
                              │  - llm_client.complete(SYSTEM_PROMPT, user_prompt)
                              │  - parse_code_from_response(raw)
                              │
                              ├── PatchResult (used_llm=True) ─── return
                              │
                              └── None ──────────────────────── return
                                  (LLM error / unparseable response)
```

The recipe registry is keyed by `DefectType`; each defect type maps to a list of recipes in registration order:

| `DefectType` | Recipes (in registration order) |
|---|---|
| `LABEL_OVERLAP` | `rotate_x_labels` → `shrink_x_tick_font` |
| `ELEMENT_CUTOFF` | `add_tight_layout` → `enlarge_figure` |

See [plotlint/fix_recipes/__init__.py](../plotlint/fix_recipes/__init__.py), [plotlint/fix_recipes/overlap.py](../plotlint/fix_recipes/overlap.py), [plotlint/fix_recipes/cutoff.py](../plotlint/fix_recipes/cutoff.py).

## Output Architecture (MVP.9)

Two writers, both pure functions of `ConvergenceState`. Registry + factory pattern matches the loader / check / recipe registries elsewhere.

| Writer | Format | Outputs |
|---|---|---|
| `PNGWriter` | `OutputFormat.PNG` | `<name>.png` (final rendered chart from `state.png_bytes`), `<name>.py` (final source from `state.source_code`) |
| `JSONReportWriter` | `OutputFormat.JSON` | `<name>_report.json` — name, iterations, final_score, score_history, fix_history (with recipe_id), final_issues, render_error, final_code |

The demo captures the *original* PNG itself by invoking the renderer once before the loop. Writers never re-render or re-inspect — they emit what is already in state. See [plotlint/output.py](../plotlint/output.py).

## Pipeline Architecture (autodash, partial)

The autodash pipeline graph topology is in place; nodes through `chart` are real, with `comply` invoking the plotlint convergence loop. `output` consumes `plotlint/output.py`. The outer orchestrator (per-step worker dispatch with scratchpad) lands in B2.1; multi-file support and join inference in B3.

```
   START
     │
     ▼
   load_node     ─── DataProfile + DataFrame (via load_and_profile)
     │
     ▼
   plan_node     ─── LLM: DataProfile + questions → list[AnalysisStep]
     │
     ▼
   explore_node  ─── LLM pandas code → sandbox.execute_code → InsightResult (retry × 3)
     │
     ▼
   chart_node    ─── LLM × 2: ChartSpec (JSON) → matplotlib code → ChartPlan
     │
     ▼
   comply_node   ─── per chart: invoke plotlint convergence loop
     │                          (build_convergence_graph + dispatcher)
     │
     ▼
   output_node   ─── PNGWriter / JSONReportWriter per chart
     │
     ▼
    END

   B2.1: replace linear-pipeline orchestration with explicit orchestrator +
         worker dispatch + shared scratchpad accumulating profile + steps +
         insights + chart specs + defect findings.
   B2.2: add per-step critic + per-number provenance tagging.
   B3.1: accept multiple files; per-question file routing.
   B3.2: join inference (name + type + value-set overlap; LLM tiebreaker).
   B3.3: Reflexion-style replanning + user clarification escalation.
   B3.4: exportable audit trail + sanity bounds + semantic-layer hook.
```

## `ConvergenceState` Schema

`ConvergenceState` is a LangGraph `TypedDict, total=False` — fields are optional and grow additively across milestones. Each node reads / writes a narrow slice.

| Field | Type | Owner (writes) | Consumer (reads) |
|---|---|---|---|
| `source_code` | `str` | graph init; `patch_node` | `render_node` |
| `original_code` | `str` | graph init | (preserved for output) |
| `iteration` | `int` | `render_node` (++) | `should_continue` |
| `max_iterations` | `int` | graph init | `should_continue` |
| `png_bytes` | `bytes` | `render_node` | output writers |
| `figure_pickle` | `bytes` | `render_node` | `inspect_node` |
| `render_error` | `Optional[str]` | `render_node`, `inspect_node` | `should_continue` |
| `inspection` | `Optional[InspectionResult]` | `inspect_node` | `patch_node`, `JSONReportWriter` |
| `score` | `float` | `inspect_node` | `should_continue`, `JSONReportWriter` |
| `score_history` | `list[float]` | `inspect_node` (.append) | `should_continue`, `JSONReportWriter` |
| `fix_history` | `list[FixAttempt]` | `patch_node` (.append) | `patch_node` (dedup), `JSONReportWriter` |
| `patch_applied` | `bool` | `patch_node` | (debug / logging) |
| `renderer_type` | `str` | graph init | `LLMPatcher` (prompt selection) |
| `best_code`, `best_score` | `str`, `float` | reserved | reserved for PL-1.2 active rollback |
| `critic_feedback`, `critic_invoked` | `Optional[str]`, `bool` | reserved | reserved for PL-1.3 (VLM critic) |
| `spec_context` | `Optional[str]` | reserved | reserved for PL-1.3 |

See [plotlint/models.py:139](../plotlint/models.py#L139).

## Key Design Decisions

1. **Dual-package monorepo with strict dependency direction.** `plotlint` has zero imports from `autodash`. `autodash` may import from `plotlint` (including `plotlint.core`). Enforced architecturally so `pip install plotlint` ships a fully self-contained visual-compliance tool. See [architecture.md §2](../architecture.md).

2. **LangGraph for all local Python (locked-in framework choice).** Inner plotlint convergence loop runs on LangGraph `StateGraph`; future autodash outer orchestrator (B2.1) also LangGraph (deep-agents pattern). Bedrock AgentCore replaces the outer orchestrator only in cloud (L3+). Avoids introducing a second agent framework while leaving room for the cloud-native target.

3. **MVP.8 reframed as a two-track patcher: deterministic-first, LLM fallback.** Original MVP.8 specced a single LLM patcher; L1 ships `PatchDispatcher` routing by `FixRecipe` registry presence — defect types with a registered recipe → `DeterministicPatcher`; otherwise → `LLMPatcher`. Cheaper, faster, fully reproducible for mechanical defects; LLM reserved for semantic / long-tail defects. See [plotlint/patcher.py](../plotlint/patcher.py).

4. **Recipe registry pattern mirrors the `@check` decorator.** `@recipe(DefectType.LABEL_OVERLAP)` registers a `FixRecipe` class; `get_recipes_for(defect_type)` returns recipes in registration order. Adding a recipe is one new file + one import line in `plotlint/fix_recipes/__init__.py`; the dispatcher and patcher never change. See [plotlint/fix_recipes/__init__.py:65](../plotlint/fix_recipes/__init__.py#L65) and the parallel `@check` decorator at [plotlint/checks/__init__.py:46](../plotlint/checks/__init__.py#L46).

5. **Recipes are pure string transformations on source code.** Each `FixRecipe.apply(code, issue) → str` returns modified Python. Recipes append narrow matplotlib snippets at the end of user code (e.g. `plt.gcf().axes[i].tick_params(axis='x', rotation=45)`). AST rewriting is deferred — string injection works for the current recipe set and the deliverable (`PatchResult.patched_code`) is re-runnable code, matching the architecture.md spec.

6. **Recipe deduplication via `(defect_type, recipe_id)` tuples in `fix_history`.** `DeterministicPatcher` filters out already-tried `(defect_type, recipe_id)` pairs before selecting a recipe. Prevents loop spin on a fix that didn't improve score. `FixAttempt` was extended with a `recipe_id` field (None for LLM patches) to support this. See [plotlint/patcher_deterministic.py:31](../plotlint/patcher_deterministic.py#L31).

7. **Rotation-aware overlap detection.** `MatplotlibExtractor` captures `label.get_rotation()` in element metadata. `LabelOverlapCheck` skips AABB-based collision when both adjacent labels are rotated ≥15°. Reason: matplotlib's `get_window_extent()` returns the AABB of the rotated text, which substantially overstates the actual visual footprint. Without this guard the rotate recipe couldn't resolve overlap as measured. See [plotlint/checks/overlap.py:11](../plotlint/checks/overlap.py#L11) and [plotlint/extractors/matplotlib.py:122](../plotlint/extractors/matplotlib.py#L122).

8. **Protocol-based DI for `LLMClient` (caravan-ready, currently direct).** All LLM-calling modules depend on the `LLMClient` `Protocol` via dependency injection — no module instantiates the Anthropic or Gemini SDK directly. `AnthropicClient` (default model `claude-sonnet-4-6`) and `GeminiClient` implement the protocol. `MockLLMClient` in tests. Caravan integration deferred to L2; the protocol seam is the caravan plug-in point. See [plotlint/core/llm.py:18](../plotlint/core/llm.py#L18).

9. **Frozen dataclasses for all cross-module data types.** `Issue`, `InspectionResult`, `FixAttempt`, `PatchResult`, `RenderResult`, `BoundingBox`, `ElementInfo`, `DataProfile`, `AnalysisStep`, `InsightResult`, `ChartSpec`, `ChartPlan`, `OutputResult` — all `@dataclass(frozen=True)`. Immutable communication contracts between modules; safe to share across LangGraph state updates.

10. **Subprocess sandbox for code execution.** `plotlint/core/sandbox.py` provides `execute_code(code, timeout_seconds, inject_globals)` — generic Python execution in a child process via temp-file IPC. Reused by `plotlint/renderer.py` (matplotlib scripts) and `autodash/explorer.py` (pandas code). Returns an `ExecutionResult` with categorised status (syntax error, runtime error, timeout, import error, success). No pandas / matplotlib specifics in the sandbox itself.

11. **Closure factories for LangGraph node configuration.** LangGraph nodes have signature `(state) -> dict` and cannot accept arbitrary parameters. Closure factories (`_make_render_node(renderer)`, `_make_inspect_node(extractor)`, `_make_patch_node(dispatcher)`, `_make_should_continue(config)`) capture dependencies at graph construction time. Established in MVP.1; extended in L1 for the patcher. See [plotlint/loop.py:22](../plotlint/loop.py#L22).

12. **Convergence stop conditions as a `ConvergenceConfig`-driven closure.** `_make_should_continue(config)` reads four stop conditions in priority order: perfect score, max iterations, render error, score stagnation. State `max_iterations` overrides config `max_iterations` to support per-invocation tuning. Behaviour is data, not if-else chains.

13. **Two-axis roadmap structure — each MR addresses one (A, B) cell.** Infra (L1–L4) progresses how the system runs; AI workflow (B1–B3) progresses what the system is intelligent about. The axes are independent — multi-CSV agent (B3.2) can land first locally (L2) and only later re-deploy on Bedrock AgentCore (L3) without changing the agent design. See [development_plan.md](../development_plan.md) and [vision.md](../vision.md).

14. **Inspector never knows which checks exist — registry-driven.** `inspect()` calls `get_registered_checks()` and iterates. Adding a new check is one new file + one import line in `plotlint/checks/__init__.py`; the inspector source is unchanged. Mirrors the recipe registry pattern (same shape). See [plotlint/inspector.py:11](../plotlint/inspector.py#L11).

15. **`PNGWriter` and `JSONReportWriter` are pure functions of `ConvergenceState`.** Writers never re-render or re-inspect — they emit what's already in state. The demo captures the original PNG itself by invoking the renderer once before the loop. SoC: writers emit; renderers render; demos compose. See [plotlint/output.py](../plotlint/output.py).

## Test Architecture

Three tiers per architecture.md §10.1:

| Tier | What | Dependencies | Count (L1 post-resume) |
|---|---|---|---|
| **Unit** | Pure functions: geometry, scoring, parsing, checks, recipes, models | none (no LLM, no subprocess) | majority — 31 recipe tests, 7 iteration tests, others |
| **Integration** | Modules with real renderer + MockLLMClient: renderer subprocess, extractor, inspector, patcher pipeline | matplotlib subprocess, MockLLMClient | 5 e2e tests in `test_loop_e2e_real_recipes.py` plus per-module |
| **System** | End-to-end with real LLM (off by default) | live Anthropic API, network | not in default `pytest` run |

`MockLLMClient` lives in test modules where needed (e.g. `tests/test_patcher_llm.py`) — it implements the `LLMClient` `Protocol` and returns canned text keyed by call number or content match.

L1 added 66 tests (368 → 434). Total wall-clock for the full suite: ~40 s.

## Build & Run

From the repo root:

```
# Create venv and install editable + dev extras
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run the full test suite (~40 s)
.venv\Scripts\python.exe -m pytest

# Run the end-to-end demo (no API key needed; deterministic-only path)
.venv\Scripts\python.exe examples\broken_chart_demo.py

# Verify the fixed code is standalone-runnable
.venv\Scripts\python.exe examples\output\overlap_fixed.py
.venv\Scripts\python.exe examples\output\cutoff_fixed.py

# Run the demo with the LLM patcher fallback wired (won't fire on current defects)
$env:ANTHROPIC_API_KEY = "sk-..."
.venv\Scripts\python.exe examples\broken_chart_demo.py
```

Demo outputs land under `examples/output/`: per chart, `<name>_original.png`, `<name>_fixed.png`, `<name>_fixed.py`, `<name>_report.json`. `examples/output/` is gitignored.

## Two-Axis Roadmap Mapping

Currently shipped cells:

| Cell | Maps to original MVP | Modules |
|---|---|---|
| **L1 × B1.1** | MVP.8 (Patcher) — deterministic half of the reframe | `plotlint/fix_recipes/{__init__,overlap,cutoff}.py`, `plotlint/patcher_deterministic.py` |
| **L1 × B1.2** | MVP.8 (Patcher) — LLM-fallback half of the reframe | `plotlint/patcher_llm.py`, `plotlint/prompts/patching.py`, `plotlint/patcher.py` (`PatchDispatcher`) |
| **L1 supporting** | MVP.9 (Output) + loop-bug fixes + rotation-aware check | `plotlint/output.py`, `plotlint/loop.py` (Off-1 fix + wire), `plotlint/models.py` (`PatchResult`), `examples/broken_chart_demo.py` |

Recommended next-queue cells (see [development_plan.md](../development_plan.md) "Merge-request grid"):

| Cell | Headline modules |
|---|---|
| **L2 × B2.1** | `autodash/orchestrator.py`, `autodash/scratchpad.py` |
| **L2 × B2.2** | `autodash/critic.py`, `autodash/provenance.py`, `autodash/report.py` |
| **L2 × B3.1** | `autodash/multi_file.py` |
| **L2 × B3.2** | `autodash/join_inference.py`, `autodash/join_validation.py` |
| **L3 × B3.2 / B3.3** | `infra/agentcore/`, `autodash/replanner.py`, `autodash/clarification.py` |
| **L4 × B3.4** | `infra/step-functions/`, `autodash/audit.py`, `autodash/semantic_layer.py`, `eval/benchmark.py` |

MVP.10 (Docker / CLI packaging) is not in this queue — deferred to PL-1.4 (CLI) and PL-3.1 (Docker sandbox) per architecture.md extension points. The demo script `python examples/broken_chart_demo.py` is the current entry point and does not require packaging to demonstrate the full L1 surface.

See [frontier_research_2026-05.md](frontier_research_2026-05.md) for the landscape audit and methodology choices underlying Axis B.
