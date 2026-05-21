"""Regression tests for three bugs surfaced by Copilot review (2026-05-21):

1. Render failure left figure_pickle / png_bytes stale, letting inspect_node
   process them and overwrite render_error back to None.
2. Patcher-exhaustion signal went via render_error, which the next successful
   render_node clears, so the loop kept patching the same failing issue.
3. FixAttempt.score_after was set to score_before in patch_node with the
   comment "updated on next inspect_node" — but inspect_node never updated it,
   so FixAttempt.improved was always False and the LLM history was misleading.
"""

from __future__ import annotations

import pytest

from plotlint.config import ConvergenceConfig
from plotlint.loop import (
    _finalise_pending_fix,
    _make_inspect_node,
    _make_render_node,
    _make_should_continue,
)
from plotlint.models import ConvergenceState, DefectType, FixAttempt
from plotlint.renderer import matplotlib_bundle


SIMPLE_CHART = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
"""

BROKEN_CHART = "this is not python and will fail to render"


# --- Bug #1: render failure clears stale figure_pickle / png_bytes ---


class TestRenderFailureClearsStaleFigure:
    @pytest.mark.asyncio
    async def test_failure_clears_figure_pickle(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)

        # Seed state with a stale figure_pickle from a prior successful render
        state: ConvergenceState = {
            "source_code": BROKEN_CHART,
            "figure_pickle": b"stale_pickle_bytes",
            "png_bytes": b"\x89PNG\r\nstale",
        }
        result = await render_node(state)

        assert result.get("render_error") is not None
        # Both must be explicitly cleared, otherwise LangGraph state merge
        # would preserve the stale values from the previous iteration.
        assert "figure_pickle" in result
        assert result["figure_pickle"] is None
        assert "png_bytes" in result
        assert result["png_bytes"] is None

    @pytest.mark.asyncio
    async def test_inspect_after_failed_render_does_not_process_stale(self):
        """End-to-end: a failed render followed by inspect_node should NOT
        re-process the previous figure and clear render_error."""
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        inspect_node = _make_inspect_node(bundle.extractor)

        # First pass: successful render
        state: ConvergenceState = {"source_code": SIMPLE_CHART}
        state = {**state, **(await render_node(state))}
        state = {**state, **(await inspect_node(state))}
        assert state.get("figure_pickle") is not None
        assert state.get("render_error") is None

        # Second pass: broken code → render fails → figure cleared
        state["source_code"] = BROKEN_CHART
        state = {**state, **(await render_node(state))}
        assert state["render_error"] is not None
        assert state["figure_pickle"] is None

        # inspect_node now sees no figure → keeps render_error set
        result = await inspect_node(state)
        assert result.get("render_error") is not None
        assert "No figure" in result["render_error"]


# --- Bug #2: stop_reason survives subsequent renders ---


class TestStopReasonPersistsAcrossRender:
    @pytest.mark.asyncio
    async def test_render_does_not_clear_stop_reason(self):
        """render_node may successfully render after a patch_node set
        stop_reason — but stop_reason must remain set so should_continue
        can read it on the next decision pass."""
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)

        state: ConvergenceState = {
            "source_code": SIMPLE_CHART,
            "stop_reason": "Patcher exhausted: no recipe applies",
        }
        result = await render_node(state)

        # render_node only writes its own fields; LangGraph merge leaves
        # stop_reason intact because render_node didn't touch it.
        assert "stop_reason" not in result

    def test_should_continue_stops_on_stop_reason(self):
        fn = _make_should_continue(ConvergenceConfig())
        state: ConvergenceState = {
            "score": 0.5,
            "iteration": 1,
            "stop_reason": "Patcher exhausted",
        }
        assert fn(state) == "stop"

    def test_should_continue_does_not_stop_without_stop_reason(self):
        fn = _make_should_continue(ConvergenceConfig(max_iterations=5))
        state: ConvergenceState = {
            "score": 0.5,
            "iteration": 1,
            "score_history": [0.3, 0.5],  # improving
        }
        assert fn(state) == "patch"


# --- Bug #3: inspect_node finalises trailing FixAttempt.score_after ---


def _pending_fix(score_before: float) -> FixAttempt:
    return FixAttempt(
        iteration=1,
        target_issue=DefectType.LABEL_OVERLAP,
        description="rotate",
        code_hash="abc",
        score_before=score_before,
        recipe_id="rotate_x_labels",
    )


class TestFinalisePendingFix:
    def test_no_history_returns_empty_list(self):
        result = _finalise_pending_fix([], 0.7)
        assert result == []

    def test_finalises_pending_entry(self):
        history = [_pending_fix(0.5)]
        result = _finalise_pending_fix(history, 0.9)
        assert len(result) == 1
        assert result[0].score_before == 0.5
        assert result[0].score_after == 0.9
        assert result[0].improved is True
        assert result[0].is_finalised is True

    def test_does_not_re_finalise(self):
        """Already-finalised entries are left untouched (idempotency)."""
        history = [
            FixAttempt(
                iteration=1, target_issue=DefectType.LABEL_OVERLAP,
                description="d", code_hash="h", score_before=0.5, score_after=0.7,
            )
        ]
        result = _finalise_pending_fix(history, 0.99)
        assert result[0].score_after == 0.7  # not overwritten

    def test_does_not_mutate_input(self):
        original = [_pending_fix(0.5)]
        _ = _finalise_pending_fix(original, 0.9)
        assert original[0].score_after is None  # input untouched


class TestInspectNodeFinalisesPendingFix:
    @pytest.mark.asyncio
    async def test_inspect_finalises_after_render(self):
        bundle = matplotlib_bundle(timeout_seconds=10)
        render_node = _make_render_node(bundle.renderer)
        inspect_node = _make_inspect_node(bundle.extractor)

        # Simulate: patch_node appended a pending FixAttempt, then render
        # produced a fresh figure. inspect_node should finalise the entry.
        state: ConvergenceState = {
            "source_code": SIMPLE_CHART,
            "fix_history": [_pending_fix(0.5)],
        }
        state = {**state, **(await render_node(state))}
        result = await inspect_node(state)

        assert "fix_history" in result
        assert len(result["fix_history"]) == 1
        finalised = result["fix_history"][0]
        assert finalised.score_after is not None
        assert finalised.is_finalised

    @pytest.mark.asyncio
    async def test_inspect_finalises_pending_fix_on_extraction_failure(self):
        """Even when extraction fails, the pending fix gets finalised (with
        the failure score) so the history doesn't accumulate pending entries."""
        bundle = matplotlib_bundle(timeout_seconds=10)
        inspect_node = _make_inspect_node(bundle.extractor)

        # No figure_pickle → inspect_node returns "no figure" error path
        state: ConvergenceState = {
            "fix_history": [_pending_fix(0.5)],
        }
        result = await inspect_node(state)
        assert result["fix_history"][0].is_finalised
        assert result["fix_history"][0].score_after == 0.0


# --- Bug #9: PNGWriter formats reflects actual writes ---


class TestPNGWriterFormats:
    def test_formats_empty_when_no_png(self, tmp_path):
        from plotlint.output import PNGWriter

        writer = PNGWriter()
        state: ConvergenceState = {"source_code": "import matplotlib"}
        result = writer.write(state, tmp_path, name="failed")
        assert result.formats == []

    def test_formats_contains_png_when_png_written(self, tmp_path):
        from plotlint.output import OutputFormat, PNGWriter

        writer = PNGWriter()
        state: ConvergenceState = {
            "png_bytes": b"\x89PNG\r\nfake",
            "source_code": "import matplotlib",
        }
        result = writer.write(state, tmp_path, name="ok")
        assert OutputFormat.PNG in result.formats
