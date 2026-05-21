"""Regression tests for loop.py — iteration counter and score_history accumulation.

Covers the Off-1 fix from the L1 plan: previously render_node didn't increment
iteration and inspect_node didn't append to score_history. The stagnation check
based on score_history therefore never fired.
"""

from __future__ import annotations

import pytest

from plotlint.loop import _make_render_node, _make_inspect_node
from plotlint.models import ConvergenceState, RenderResult, RenderStatus
from plotlint.renderer import matplotlib_bundle


SIMPLE_CHART = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
ax.set_title('A simple chart')
"""

BROKEN_CHART = """
this is not python and should fail
"""


class TestRenderNodeIncrementsIteration:
    @pytest.mark.asyncio
    async def test_increments_from_zero(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        state: ConvergenceState = {"source_code": SIMPLE_CHART}
        result = await render_node(state)
        assert result["iteration"] == 1

    @pytest.mark.asyncio
    async def test_increments_from_existing_count(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        state: ConvergenceState = {"source_code": SIMPLE_CHART, "iteration": 4}
        result = await render_node(state)
        assert result["iteration"] == 5

    @pytest.mark.asyncio
    async def test_increments_even_on_render_error(self):
        """Iteration counter advances even when the render fails — otherwise
        the loop could spin indefinitely on a broken patch attempt."""
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        state: ConvergenceState = {"source_code": BROKEN_CHART, "iteration": 2}
        result = await render_node(state)
        assert result["iteration"] == 3
        assert result.get("render_error") is not None


class TestInspectNodeAppendsScoreHistory:
    @pytest.mark.asyncio
    async def test_appends_to_empty_history(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        inspect_node = _make_inspect_node(bundle.extractor)

        state: ConvergenceState = {"source_code": SIMPLE_CHART}
        rendered = await render_node(state)
        state = {**state, **rendered}

        result = await inspect_node(state)
        assert "score_history" in result
        assert len(result["score_history"]) == 1
        assert result["score_history"][0] == result["score"]

    @pytest.mark.asyncio
    async def test_appends_to_existing_history(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        inspect_node = _make_inspect_node(bundle.extractor)

        state: ConvergenceState = {
            "source_code": SIMPLE_CHART,
            "score_history": [0.2, 0.5],
        }
        rendered = await render_node(state)
        state = {**state, **rendered}

        result = await inspect_node(state)
        assert len(result["score_history"]) == 3
        assert result["score_history"][:2] == [0.2, 0.5]
        assert result["score_history"][2] == result["score"]

    @pytest.mark.asyncio
    async def test_appends_zero_on_missing_figure(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        inspect_node = _make_inspect_node(bundle.extractor)

        state: ConvergenceState = {"score_history": [0.5]}
        result = await inspect_node(state)
        assert result["score"] == 0.0
        assert result["score_history"] == [0.5, 0.0]
        assert result.get("render_error") is not None

    @pytest.mark.asyncio
    async def test_does_not_mutate_caller_history(self):
        """inspect_node must not mutate the input list — LangGraph state
        semantics rely on returning fresh values."""
        bundle = matplotlib_bundle(timeout_seconds=10)
        inspect_node = _make_inspect_node(bundle.extractor)

        original_history = [0.3, 0.4]
        state: ConvergenceState = {"score_history": original_history}
        await inspect_node(state)
        assert original_history == [0.3, 0.4]  # unchanged
