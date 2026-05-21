"""End-to-end convergence loop tests with real renderer + real recipes.

These validate the complete render → inspect → patch → re-render cycle on
real matplotlib code, without any LLM. They are the closest analogue to the
demo's exit criterion (`python examples/broken_chart_demo.py`) inside pytest.
"""

from __future__ import annotations

import pytest

from plotlint.config import ConvergenceConfig
from plotlint.loop import build_convergence_graph
from plotlint.models import ConvergenceState


OVERLAP_CHART = """import matplotlib.pyplot as plt
months = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']
values = [3, 7, 2, 8, 5, 9, 4, 6, 7, 3, 5, 8]
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(months, values)
ax.set_title('Monthly sales')
"""


CUTOFF_CHART = """import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(3, 2))
ax.plot([1, 2, 3], [4, 5, 6])
ax.set_title('A very long chart title that gets clipped at the edges')
ax.set_xlabel('Time of day in hours since midnight')
ax.set_ylabel('Clicks per minute averaged')
"""


def _initial_state(code: str, max_iter: int = 5) -> ConvergenceState:
    return {
        "source_code": code,
        "original_code": code,
        "max_iterations": max_iter,
        "fix_history": [],
        "score_history": [],
        "iteration": 0,
    }


class TestOverlapConvergence:
    @pytest.mark.asyncio
    async def test_overlap_chart_improves(self):
        graph = build_convergence_graph()
        final = await graph.ainvoke(_initial_state(OVERLAP_CHART))

        # Score history was populated by inspect_node each pass.
        assert len(final["score_history"]) >= 1
        initial_score = final["score_history"][0]
        final_score = final["score"]

        # At least one fix was attempted (the chart has overlapping months).
        assert len(final["fix_history"]) >= 1

        # Score should not regress overall.
        assert final_score >= initial_score


class TestCutoffConvergence:
    @pytest.mark.asyncio
    async def test_cutoff_chart_improves(self):
        graph = build_convergence_graph()
        final = await graph.ainvoke(_initial_state(CUTOFF_CHART))

        assert len(final["score_history"]) >= 1
        # At least one fix attempt for the cutoff defect.
        # (Some matplotlib defaults may auto-pad such that cutoff is mild;
        # we accept zero fixes if the initial score was already at target.)
        if final["score_history"][0] < 1.0:
            assert len(final["fix_history"]) >= 1


class TestLoopTerminates:
    @pytest.mark.asyncio
    async def test_loop_respects_max_iterations(self):
        """The loop must terminate within max_iterations even if it can't
        reach the target score. Without the Off-1 fix this could spin
        forever — this test guards against regression."""
        graph = build_convergence_graph()
        final = await graph.ainvoke(_initial_state(OVERLAP_CHART, max_iter=2))
        assert final["iteration"] <= 3  # at most max_iter+1 (final render after last patch)

    @pytest.mark.asyncio
    async def test_loop_terminates_within_budget(self):
        """The loop must always terminate. With a small max_iterations and a
        broken chart, we want the loop to hit the budget and stop cleanly
        rather than spin. The previous Off-1 bug allowed infinite-style
        behaviour because iteration was never incremented."""
        graph = build_convergence_graph(
            config=ConvergenceConfig(max_iterations=3, target_score=1.0)
        )
        final = await graph.ainvoke(_initial_state(OVERLAP_CHART, max_iter=3))
        # Loop ran a bounded number of passes; final iteration <= max+1.
        assert 1 <= final["iteration"] <= 4
        # No infinite re-application of the same recipe (dedup contract).
        seen = set()
        for fa in final["fix_history"]:
            key = (fa.target_issue, fa.recipe_id)
            assert key not in seen
            seen.add(key)


class TestDedupAcrossIterations:
    @pytest.mark.asyncio
    async def test_each_recipe_tried_at_most_once_per_defect(self):
        """Once a recipe is in fix_history, the dispatcher must not try it
        again for the same defect_type. This is the dedup contract from
        DeterministicPatcher."""
        graph = build_convergence_graph(
            config=ConvergenceConfig(max_iterations=10, target_score=1.0)
        )
        final = await graph.ainvoke(_initial_state(OVERLAP_CHART, max_iter=10))

        # No (defect_type, recipe_id) pair should appear more than once.
        seen = set()
        for fa in final["fix_history"]:
            key = (fa.target_issue, fa.recipe_id)
            assert key not in seen, f"recipe {fa.recipe_id} re-applied for {fa.target_issue}"
            seen.add(key)
