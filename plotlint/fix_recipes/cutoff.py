"""Deterministic recipes for DefectType.ELEMENT_CUTOFF.

Element cutoff (text running off the figure edge) is most often a layout
issue: the figure was created without `tight_layout` or `constrained_layout`,
or it was made too small for its content. These recipes address both.
"""

from __future__ import annotations

from plotlint.fix_recipes import recipe
from plotlint.models import DefectType, Issue


@recipe(DefectType.ELEMENT_CUTOFF)
class AddTightLayoutRecipe:
    """Append `plt.gcf().tight_layout()` to make matplotlib reflow margins.

    Primary recipe for cutoff. Idempotent — calling tight_layout twice
    has no additional effect. The dispatcher's dedup prevents this
    recipe from being re-applied within the same convergence run.
    """

    recipe_id = "add_tight_layout"
    defect_type = DefectType.ELEMENT_CUTOFF

    def can_apply(self, issue: Issue, code: str) -> bool:
        # Always applicable when a cutoff is reported; cheap and broadly effective.
        return True

    def apply(self, code: str, issue: Issue) -> str:
        suffix = "\n# plotlint: reflow layout to resolve cutoff\nplt.gcf().tight_layout()\n"
        return code.rstrip() + suffix


@recipe(DefectType.ELEMENT_CUTOFF)
class EnlargeFigureRecipe:
    """Enlarge the figure by 25% in each dimension.

    Secondary fallback when tight_layout alone didn't move all elements
    inside the figure. Modifies the current figure's size — preserves the
    existing aspect ratio.
    """

    recipe_id = "enlarge_figure"
    defect_type = DefectType.ELEMENT_CUTOFF

    def can_apply(self, issue: Issue, code: str) -> bool:
        return True

    def apply(self, code: str, issue: Issue) -> str:
        suffix = (
            "\n# plotlint: enlarge figure 25% in each dimension to resolve cutoff\n"
            "_fig = plt.gcf()\n"
            "_w, _h = _fig.get_size_inches()\n"
            "_fig.set_size_inches(_w * 1.25, _h * 1.25)\n"
            "_fig.tight_layout()\n"
        )
        return code.rstrip() + suffix
