"""Tests for the FixRecipe protocol and the @recipe registry."""

from __future__ import annotations

import pytest

from plotlint.fix_recipes import (
    FixRecipe,
    _RECIPES,
    clear_registry,
    get_recipes_for,
    recipe,
)
from plotlint.models import DefectType, Issue, Severity


@pytest.fixture
def saved_registry():
    """Snapshot+restore the recipe registry so tests don't pollute each other."""
    snapshot = {k: list(v) for k, v in _RECIPES.items()}
    yield
    _RECIPES.clear()
    _RECIPES.update(snapshot)


class TestRegistry:
    def test_overlap_recipes_registered(self):
        recipes = get_recipes_for(DefectType.LABEL_OVERLAP)
        ids = [r.recipe_id for r in recipes]
        assert "rotate_x_labels" in ids
        assert "shrink_x_tick_font" in ids

    def test_cutoff_recipes_registered(self):
        recipes = get_recipes_for(DefectType.ELEMENT_CUTOFF)
        ids = [r.recipe_id for r in recipes]
        assert "add_tight_layout" in ids
        assert "enlarge_figure" in ids

    def test_unknown_defect_returns_empty(self, saved_registry):
        """A defect type with no registered recipe returns []; the dispatcher
        uses this as the signal to fall back to LLM."""
        # Synthesize a fake defect by adding then removing — confirm semantics.
        # (Using LABEL_OVERLAP after clearing would test the same path.)
        clear_registry()
        assert get_recipes_for(DefectType.LABEL_OVERLAP) == []

    def test_registration_order_preserved(self, saved_registry):
        clear_registry()

        @recipe(DefectType.LABEL_OVERLAP)
        class First:
            recipe_id = "first"
            defect_type = DefectType.LABEL_OVERLAP
            def can_apply(self, issue, code): return True
            def apply(self, code, issue): return code

        @recipe(DefectType.LABEL_OVERLAP)
        class Second:
            recipe_id = "second"
            defect_type = DefectType.LABEL_OVERLAP
            def can_apply(self, issue, code): return True
            def apply(self, code, issue): return code

        ids = [r.recipe_id for r in get_recipes_for(DefectType.LABEL_OVERLAP)]
        assert ids == ["first", "second"]

    def test_get_recipes_returns_copy(self):
        """Mutating the returned list must not affect the registry."""
        recipes = get_recipes_for(DefectType.LABEL_OVERLAP)
        original_len = len(recipes)
        recipes.clear()
        assert len(get_recipes_for(DefectType.LABEL_OVERLAP)) == original_len


class TestRegisteredRecipesSatisfyProtocol:
    """Every registered recipe must conform to the FixRecipe protocol."""

    def test_overlap_recipes(self):
        for r in get_recipes_for(DefectType.LABEL_OVERLAP):
            assert isinstance(r, FixRecipe)

    def test_cutoff_recipes(self):
        for r in get_recipes_for(DefectType.ELEMENT_CUTOFF):
            assert isinstance(r, FixRecipe)
