"""Tests for cutoff recipes: AddTightLayoutRecipe, EnlargeFigureRecipe."""

from __future__ import annotations

import ast

from plotlint.fix_recipes.cutoff import (
    AddTightLayoutRecipe,
    EnlargeFigureRecipe,
)
from plotlint.models import DefectType, Issue, Severity


BASE_CHART = """import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(3, 2))
ax.plot([1, 2, 3], [4, 5, 6])
ax.set_title('A very long title that gets clipped')
"""


def _cutoff_issue() -> Issue:
    return Issue(
        defect_type=DefectType.ELEMENT_CUTOFF,
        severity=Severity.HIGH,
        details="Element 'axes.0.title' extends beyond figure: 30% outside boundaries",
        suggestion="Add plt.tight_layout() or increase figure size",
        element_ids=["axes.0.title"],
    )


class TestAddTightLayoutRecipe:
    def test_metadata(self):
        r = AddTightLayoutRecipe()
        assert r.recipe_id == "add_tight_layout"
        assert r.defect_type == DefectType.ELEMENT_CUTOFF

    def test_always_applicable(self):
        r = AddTightLayoutRecipe()
        assert r.can_apply(_cutoff_issue(), BASE_CHART) is True

    def test_apply_appends_tight_layout(self):
        r = AddTightLayoutRecipe()
        patched = r.apply(BASE_CHART, _cutoff_issue())
        assert "tight_layout()" in patched
        assert BASE_CHART.strip() in patched

    def test_apply_produces_valid_python(self):
        r = AddTightLayoutRecipe()
        patched = r.apply(BASE_CHART, _cutoff_issue())
        ast.parse(patched)


class TestEnlargeFigureRecipe:
    def test_metadata(self):
        r = EnlargeFigureRecipe()
        assert r.recipe_id == "enlarge_figure"
        assert r.defect_type == DefectType.ELEMENT_CUTOFF

    def test_always_applicable(self):
        r = EnlargeFigureRecipe()
        assert r.can_apply(_cutoff_issue(), BASE_CHART) is True

    def test_apply_scales_figure(self):
        r = EnlargeFigureRecipe()
        patched = r.apply(BASE_CHART, _cutoff_issue())
        assert "1.25" in patched
        assert "set_size_inches" in patched

    def test_apply_produces_valid_python(self):
        r = EnlargeFigureRecipe()
        patched = r.apply(BASE_CHART, _cutoff_issue())
        ast.parse(patched)


class TestRecipeIndependence:
    def test_tight_layout_and_enlarge_distinct(self):
        assert AddTightLayoutRecipe().recipe_id != EnlargeFigureRecipe().recipe_id
