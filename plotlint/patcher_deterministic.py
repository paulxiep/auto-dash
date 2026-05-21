"""DeterministicPatcher — applies a registered FixRecipe to source code.

SoC: this module knows how to pick and apply a recipe. It doesn't know about
the convergence loop, the LLM patcher, or the dispatcher routing decision.

The dispatcher calls .patch() with the current code, a single issue, and
fix_history. The patcher returns either a PatchResult or None.
- None means "no recipe is available for this issue, or all applicable
  recipes have already been tried" — the dispatcher uses this as the
  signal to fall back to the LLM patcher.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from plotlint.fix_recipes import get_recipes_for
from plotlint.models import FixAttempt, Issue, PatchResult


def _hash(code: str) -> str:
    """sha256 of the patched code. Used for FixAttempt.code_hash + dedup."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass
class DeterministicPatcher:
    """Applies one registered FixRecipe per call.

    Recipe selection algorithm:
    1. Look up recipes for issue.defect_type.
    2. Filter out (defect_type, recipe_id) pairs already in fix_history.
    3. Filter out recipes whose can_apply() returns False for this issue.
    4. Return PatchResult from the first remaining recipe, in registration order.
    5. If no recipe remains, return None — signals LLM fallback.
    """

    def patch(
        self,
        code: str,
        issue: Issue,
        fix_history: list[FixAttempt],
    ) -> Optional[PatchResult]:
        recipes = get_recipes_for(issue.defect_type)
        if not recipes:
            return None

        already_tried: set[tuple[str, str]] = {
            (fa.target_issue.value, fa.recipe_id)
            for fa in fix_history
            if fa.recipe_id is not None
        }

        for recipe in recipes:
            pair = (issue.defect_type.value, recipe.recipe_id)
            if pair in already_tried:
                continue
            if not recipe.can_apply(issue, code):
                continue
            patched = recipe.apply(code, issue)
            return PatchResult(
                patched_code=patched,
                code_hash=_hash(patched),
                target_issue=issue.defect_type,
                description=f"Applied recipe '{recipe.recipe_id}' for {issue.defect_type.value}",
                used_llm=False,
                recipe_id=recipe.recipe_id,
            )

        return None
