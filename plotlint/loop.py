"""Convergence loop graph (LangGraph StateGraph).

Graph topology:
    render -> inspect -> decide
                            ├── "patch" -> patch -> render (loop back)
                            └── "stop"  -> END
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from plotlint.config import ConvergenceConfig
from plotlint.models import ConvergenceState, FixAttempt
from plotlint.renderer import Renderer


def _make_render_node(renderer: Renderer):
    """Create a render node that closes over a Renderer instance.

    Follows the same factory pattern as _make_should_continue(config).
    asyncio.to_thread keeps the event loop non-blocking while the
    subprocess renders.
    """

    async def render_node(state: ConvergenceState) -> dict:
        """Execute chart code and capture figure + PNG.

        Increments iteration BEFORE rendering (architecture.md §12.5).
        Exactly one increment per loop pass; counter is available
        during render for logging or correlation.
        """
        next_iteration = state.get("iteration", 0) + 1
        code = state.get("source_code", "")
        result = await asyncio.to_thread(renderer.render, code)
        if result.succeeded:
            return {
                "iteration": next_iteration,
                "png_bytes": result.png_bytes,
                "figure_pickle": result.figure_data,
                "render_error": None,
            }
        return {
            "iteration": next_iteration,
            "render_error": result.error_message
            or f"Render failed: {result.status.value}",
        }

    return render_node


def _make_inspect_node(extractor):
    """Create an inspect node that closes over an Extractor instance.

    Follows the same factory pattern as _make_render_node(renderer).
    """

    async def inspect_node(state: ConvergenceState) -> dict:
        """Run Inspector on rendered figure.

        Reads: figure_pickle (from render_node)
        Writes: inspection, score, score_history (appended), render_error (if extraction fails)
        """
        from plotlint.inspector import inspect_from_figure
        from plotlint.core.errors import ExtractionError

        score_history = list(state.get("score_history", []))

        figure_data = state.get("figure_pickle")
        if not figure_data:
            score_history.append(0.0)
            return {
                "render_error": "No figure data to inspect",
                "score": 0.0,
                "score_history": score_history,
            }

        try:
            inspection = await asyncio.to_thread(
                inspect_from_figure, figure_data, extractor
            )
            score_history.append(inspection.score)
            return {
                "inspection": inspection,
                "score": inspection.score,
                "score_history": score_history,
                "render_error": None,
            }
        except ExtractionError as e:
            score_history.append(0.0)
            return {
                "render_error": f"Extraction failed: {str(e)}",
                "score": 0.0,
                "score_history": score_history,
            }

    return inspect_node


def _make_patch_node(patcher):
    """Create a patch node that closes over the PatchDispatcher.

    Factory pattern, matching _make_render_node and _make_inspect_node.
    Decouples the LangGraph node signature (state-only) from the
    dispatcher dependency.

    Reads: source_code, inspection, fix_history, iteration, score
    Writes: source_code (if patched), fix_history (appended), patch_applied,
            best_code/best_score (if score improved), render_error (if no patch)
    """

    async def patch_node(state: ConvergenceState) -> dict:
        inspection = state.get("inspection")
        if inspection is None or not inspection.has_issues:
            return {"patch_applied": False}

        code = state.get("source_code", "")
        fix_history: list[FixAttempt] = list(state.get("fix_history", []))
        score_before = state.get("score", 0.0)

        result = await patcher.patch(code, inspection, fix_history)

        if result is None:
            return {
                "patch_applied": False,
                "render_error": (
                    "Patcher exhausted: no recipe applies and LLM patcher "
                    "is unavailable or returned no fix."
                ),
            }

        fix_history.append(FixAttempt(
            iteration=state.get("iteration", 0),
            target_issue=result.target_issue,
            description=result.description,
            code_hash=result.code_hash,
            score_before=score_before,
            score_after=score_before,  # updated on next inspect_node
            recipe_id=result.recipe_id,
        ))

        updates: dict = {
            "source_code": result.patched_code,
            "fix_history": fix_history,
            "patch_applied": True,
        }

        # Track best-seen state for potential future rollback (PL-1.2).
        # We optimistically capture the pre-patch state if it was the best so far.
        prev_best_score = state.get("best_score", -1.0)
        if score_before > prev_best_score:
            updates["best_code"] = code
            updates["best_score"] = score_before

        return updates

    return patch_node


def _make_should_continue(config: ConvergenceConfig):
    """Create a should_continue function that captures config.

    G1: LangGraph conditional edge functions only receive state.
    Config access is closed over via this factory.
    """

    def should_continue(state: ConvergenceState) -> str:
        """Conditional edge: decide whether to patch or stop.

        Returns:
            "patch" -> continue to patch_node
            "stop"  -> end the loop

        Stop conditions (checked in order):
        1. score >= target_score (perfect)
        2. iteration >= max_iterations
        3. render_error is set (code doesn't execute)
        4. score stagnant for stagnation_window iterations
        """
        score = state.get("score", 0.0)
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", config.max_iterations)
        render_error = state.get("render_error")
        score_history = state.get("score_history", [])

        # 1. Perfect score
        if score >= config.target_score:
            return "stop"

        # 2. Max iterations reached
        if iteration >= max_iterations:
            return "stop"

        # 3. Render error (code doesn't execute)
        if render_error is not None:
            return "stop"

        # 4. Score stagnation
        if len(score_history) >= config.stagnation_window:
            recent = score_history[-config.stagnation_window :]
            if len(recent) >= 2:
                max_improvement = max(recent) - min(recent)
                if max_improvement < config.score_improvement_threshold:
                    return "stop"

        return "patch"

    return should_continue


def build_convergence_graph(
    config: ConvergenceConfig = ConvergenceConfig(),
    bundle: Optional[Any] = None,
    patcher: Optional[Any] = None,
) -> CompiledStateGraph:
    """Build the plotlint convergence loop as a LangGraph StateGraph.

    Args:
        config: Controls stop conditions.
        bundle: RendererBundle (Renderer+Extractor pair). Default: matplotlib.
        patcher: PatchDispatcher routing Issues to deterministic / LLM.
                 Default: deterministic-only dispatcher (no LLM fallback).

    Returns a compiled StateGraph ready to invoke.
    """
    if bundle is None:
        from plotlint.renderer import matplotlib_bundle

        bundle = matplotlib_bundle()

    if patcher is None:
        from plotlint.patcher import PatchDispatcher
        from plotlint.patcher_deterministic import DeterministicPatcher

        patcher = PatchDispatcher(deterministic=DeterministicPatcher(), llm=None)

    graph = StateGraph(ConvergenceState)

    graph.add_node("render", _make_render_node(bundle.renderer))
    graph.add_node("inspect", _make_inspect_node(bundle.extractor))
    graph.add_node("patch", _make_patch_node(patcher))

    graph.add_edge(START, "render")
    graph.add_edge("render", "inspect")
    graph.add_conditional_edges(
        "inspect",
        _make_should_continue(config),
        {"patch": "patch", "stop": END},
    )
    graph.add_edge("patch", "render")

    return graph.compile()
