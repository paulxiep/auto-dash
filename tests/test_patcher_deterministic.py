"""Tests for DeterministicPatcher — recipe selection, dedup, fallback signal."""

from __future__ import annotations

import pytest

from plotlint.fix_recipes import _RECIPES, clear_registry, recipe
from plotlint.models import DefectType, FixAttempt, Issue, Severity
from plotlint.patcher_deterministic import DeterministicPatcher


BASE_CHART = """import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.bar(['a', 'b', 'c'], [1, 2, 3])
"""


@pytest.fixture
def saved_registry():
    snapshot = {k: list(v) for k, v in _RECIPES.items()}
    yield
    _RECIPES.clear()
    _RECIPES.update(snapshot)


def _x_overlap_issue() -> Issue:
    return Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.HIGH,
        details="X-axis labels overlap: 5 of 11 adjacent pairs collide",
        suggestion="Rotate x-axis labels 45-90 degrees",
        element_ids=["axes.0.xaxis.tick.0", "axes.0.xaxis.tick.1"],
    )


def _cutoff_issue() -> Issue:
    return Issue(
        defect_type=DefectType.ELEMENT_CUTOFF,
        severity=Severity.HIGH,
        details="Element 'axes.0.title' extends beyond figure: 30% outside boundaries",
        suggestion="Add plt.tight_layout()",
        element_ids=["axes.0.title"],
    )


def _fix_attempt(defect: DefectType, recipe_id: str) -> FixAttempt:
    return FixAttempt(
        iteration=1,
        target_issue=defect,
        description="prior",
        code_hash="abc",
        score_before=0.5,
        score_after=0.5,
        recipe_id=recipe_id,
    )


class TestRecipeSelection:
    def test_picks_first_applicable_recipe(self):
        patcher = DeterministicPatcher()
        result = patcher.patch(BASE_CHART, _x_overlap_issue(), fix_history=[])
        assert result is not None
        assert result.recipe_id == "rotate_x_labels"
        assert result.used_llm is False
        assert "rotation=45" in result.patched_code

    def test_skips_already_tried_recipe(self):
        patcher = DeterministicPatcher()
        history = [_fix_attempt(DefectType.LABEL_OVERLAP, "rotate_x_labels")]
        result = patcher.patch(BASE_CHART, _x_overlap_issue(), fix_history=history)
        assert result is not None
        assert result.recipe_id == "shrink_x_tick_font"  # next in order

    def test_returns_none_when_all_recipes_exhausted(self):
        patcher = DeterministicPatcher()
        history = [
            _fix_attempt(DefectType.LABEL_OVERLAP, "rotate_x_labels"),
            _fix_attempt(DefectType.LABEL_OVERLAP, "shrink_x_tick_font"),
        ]
        result = patcher.patch(BASE_CHART, _x_overlap_issue(), fix_history=history)
        assert result is None  # signals LLM fallback

    def test_returns_none_for_unregistered_defect(self, saved_registry):
        """The dispatcher uses None to route to the LLM patcher."""
        clear_registry()
        patcher = DeterministicPatcher()
        result = patcher.patch(BASE_CHART, _x_overlap_issue(), fix_history=[])
        assert result is None

    def test_skips_non_applicable_recipe(self):
        """RotateXLabelsRecipe rejects y-axis overlap (can_apply returns False).
        The patcher should skip it and either find another recipe or return None."""
        y_issue = Issue(
            defect_type=DefectType.LABEL_OVERLAP,
            severity=Severity.MEDIUM,
            details="Y-axis labels overlap: 2 of 6 adjacent pairs collide",
            suggestion="Increase figure height",
            element_ids=["axes.0.yaxis.tick.3"],
        )
        patcher = DeterministicPatcher()
        result = patcher.patch(BASE_CHART, y_issue, fix_history=[])
        # Both overlap recipes are x-axis only, so should return None.
        assert result is None


class TestDedupKeysIgnoreLLMAttempts:
    def test_llm_attempts_do_not_block_deterministic(self):
        """A FixAttempt without recipe_id (LLM attempt) must not be treated
        as having tried any deterministic recipe."""
        patcher = DeterministicPatcher()
        llm_attempt = FixAttempt(
            iteration=1,
            target_issue=DefectType.LABEL_OVERLAP,
            description="LLM attempt",
            code_hash="xyz",
            score_before=0.5,
            score_after=0.5,
            recipe_id=None,
        )
        result = patcher.patch(BASE_CHART, _x_overlap_issue(), fix_history=[llm_attempt])
        assert result is not None
        assert result.recipe_id == "rotate_x_labels"  # not skipped


class TestPatchResultShape:
    def test_result_carries_recipe_id_and_no_llm(self):
        patcher = DeterministicPatcher()
        result = patcher.patch(BASE_CHART, _cutoff_issue(), fix_history=[])
        assert result is not None
        assert result.used_llm is False
        assert result.recipe_id is not None
        assert result.target_issue == DefectType.ELEMENT_CUTOFF
        assert result.code_hash  # non-empty
        assert "plotlint" in result.description.lower() or "applied" in result.description.lower()
