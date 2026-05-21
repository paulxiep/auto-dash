"""Tests for overlap recipes: RotateXLabelsRecipe, ShrinkXTickFontRecipe.

Verifies recipes are pure string transformations, narrow the right axis,
emit syntactically valid Python, and respect axis indices from element_ids.
"""

from __future__ import annotations

import ast

from plotlint.fix_recipes.overlap import (
    RotateXLabelsRecipe,
    ShrinkXTickFontRecipe,
)
from plotlint.models import DefectType, Issue, Severity


BASE_CHART = """import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.bar(['a', 'b', 'c'], [1, 2, 3])
"""


def _x_overlap_issue(axis_idx: int = 0) -> Issue:
    return Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.HIGH,
        details="X-axis labels overlap: 5 of 11 adjacent pairs collide",
        suggestion="Rotate x-axis labels 45-90 degrees",
        element_ids=[f"axes.{axis_idx}.xaxis.tick.{i}" for i in range(12)],
    )


def _y_overlap_issue() -> Issue:
    return Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.MEDIUM,
        details="Y-axis labels overlap: 2 of 6 adjacent pairs collide",
        suggestion="Increase figure height",
        element_ids=["axes.0.yaxis.tick.3", "axes.0.yaxis.tick.4"],
    )


class TestRotateXLabelsRecipe:
    def test_metadata(self):
        r = RotateXLabelsRecipe()
        assert r.recipe_id == "rotate_x_labels"
        assert r.defect_type == DefectType.LABEL_OVERLAP

    def test_can_apply_to_x_axis_overlap(self):
        r = RotateXLabelsRecipe()
        assert r.can_apply(_x_overlap_issue(), BASE_CHART) is True

    def test_does_not_apply_to_y_axis_overlap(self):
        r = RotateXLabelsRecipe()
        assert r.can_apply(_y_overlap_issue(), BASE_CHART) is False

    def test_apply_appends_tick_params(self):
        r = RotateXLabelsRecipe()
        patched = r.apply(BASE_CHART, _x_overlap_issue())
        assert "tick_params(axis='x', rotation=45)" in patched
        assert "tight_layout()" in patched
        assert BASE_CHART.strip() in patched  # original preserved

    def test_apply_targets_axis_index_from_issue(self):
        r = RotateXLabelsRecipe()
        patched = r.apply(BASE_CHART, _x_overlap_issue(axis_idx=2))
        assert "axes[2].tick_params" in patched
        assert "axes[0].tick_params" not in patched

    def test_apply_handles_multiple_axes(self):
        r = RotateXLabelsRecipe()
        issue = Issue(
            defect_type=DefectType.LABEL_OVERLAP,
            severity=Severity.HIGH,
            details="X-axis labels overlap: 3 of 8 adjacent pairs collide",
            suggestion="Rotate",
            element_ids=["axes.0.xaxis.tick.0", "axes.1.xaxis.tick.0"],
        )
        patched = r.apply(BASE_CHART, issue)
        assert "axes[0].tick_params" in patched
        assert "axes[1].tick_params" in patched

    def test_apply_produces_valid_python(self):
        r = RotateXLabelsRecipe()
        patched = r.apply(BASE_CHART, _x_overlap_issue())
        ast.parse(patched)  # raises SyntaxError if invalid


class TestShrinkXTickFontRecipe:
    def test_metadata(self):
        r = ShrinkXTickFontRecipe()
        assert r.recipe_id == "shrink_x_tick_font"
        assert r.defect_type == DefectType.LABEL_OVERLAP

    def test_can_apply_to_x_axis_overlap(self):
        r = ShrinkXTickFontRecipe()
        assert r.can_apply(_x_overlap_issue(), BASE_CHART) is True

    def test_does_not_apply_to_y_axis_overlap(self):
        r = ShrinkXTickFontRecipe()
        assert r.can_apply(_y_overlap_issue(), BASE_CHART) is False

    def test_apply_appends_labelsize(self):
        r = ShrinkXTickFontRecipe()
        patched = r.apply(BASE_CHART, _x_overlap_issue())
        assert "labelsize=8" in patched

    def test_apply_produces_valid_python(self):
        r = ShrinkXTickFontRecipe()
        patched = r.apply(BASE_CHART, _x_overlap_issue())
        ast.parse(patched)


class TestRecipeIndependence:
    def test_rotate_and_shrink_are_distinct(self):
        """Two recipes for the same defect_type must have distinct recipe_ids
        so dedup can tell them apart in fix_history."""
        assert RotateXLabelsRecipe().recipe_id != ShrinkXTickFontRecipe().recipe_id
