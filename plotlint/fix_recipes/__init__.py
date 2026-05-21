"""Deterministic fix recipes for visual chart defects.

A FixRecipe is the deterministic counterpart of an LLM-generated patch:
for one known defect type, it knows exactly which transformation to apply
to the source code. Recipes are registered via the @recipe decorator and
discovered by DeterministicPatcher via get_recipes_for(defect_type).

Design (declarative + SoC):
- One recipe knows ONE transformation; recipes never call each other.
- Recipe metadata (recipe_id, defect_type) is declarative — properties on the class.
- Recipes are pure functions of (issue, code) → patched code.
- No LLM dependency. No I/O. No mutable state.

Each defect type may have multiple recipes (e.g. for label overlap: rotate
first, then shrink font if rotation didn't help). They're tried in
registration order, with the dispatcher filtering out already-attempted
(defect_type, recipe_id) pairs from fix_history.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from plotlint.elements import ElementMap  # noqa: F401 — kept for type-context exports
from plotlint.models import DefectType, Issue


@runtime_checkable
class FixRecipe(Protocol):
    """One deterministic transformation for one defect type.

    Implementations declare which defect_type they handle and provide
    can_apply / apply. The dispatcher consults the registry.
    """

    @property
    def recipe_id(self) -> str:
        """Unique identifier within the (defect_type, recipe_id) pair.

        Used by fix_history for dedup. E.g. "rotate_x_labels".
        """
        ...

    @property
    def defect_type(self) -> DefectType:
        """The defect type this recipe addresses."""
        ...

    def can_apply(self, issue: Issue, code: str) -> bool:
        """True if this recipe is applicable to this specific issue + code.

        Recipes may inspect issue.details / issue.element_ids to decide whether
        their narrow transformation fits. E.g. RotateXLabelsRecipe only applies
        to x-axis label overlaps, not y-axis.
        """
        ...

    def apply(self, code: str, issue: Issue) -> str:
        """Return the modified source code.

        Must be a string transformation: input code → output code. The output
        must be a syntactically valid, runnable matplotlib script.
        """
        ...


# --- Registry ---

# Keyed by defect_type; preserves registration order within each defect type.
_RECIPES: dict[DefectType, list[FixRecipe]] = {}


def recipe(defect_type: DefectType):
    """Class decorator: register a FixRecipe for a defect type.

    Usage:
        @recipe(DefectType.LABEL_OVERLAP)
        class RotateXLabelsRecipe:
            recipe_id = "rotate_x_labels"
            defect_type = DefectType.LABEL_OVERLAP
            def can_apply(self, issue, code): ...
            def apply(self, code, issue): ...
    """

    def decorator(cls):
        instance = cls()
        _RECIPES.setdefault(defect_type, []).append(instance)
        return cls

    return decorator


def get_recipes_for(defect_type: DefectType) -> list[FixRecipe]:
    """Return all registered recipes for a defect type, in registration order.

    Returns an empty list when no recipe exists — signal for the dispatcher
    to fall back to the LLM patcher.
    """
    return list(_RECIPES.get(defect_type, ()))


def clear_registry() -> None:
    """Test helper: remove all registered recipes.

    Tests that need to exercise the recipe-less path (e.g. forcing the LLM
    fallback) can monkey-patch _RECIPES via this helper. Not for production use.
    """
    _RECIPES.clear()


# --- Explicit imports to trigger registration ---
# Mirrors the pattern used by plotlint/checks/__init__.py: each recipe module
# uses @recipe() which registers on import. New recipes: add an import line here.
from plotlint.fix_recipes import overlap  # noqa: E402, F401
from plotlint.fix_recipes import cutoff   # noqa: E402, F401
