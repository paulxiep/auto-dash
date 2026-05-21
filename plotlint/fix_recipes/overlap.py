"""Deterministic recipes for DefectType.LABEL_OVERLAP.

Each recipe applies one specific transformation. The dispatcher tries them
in registration order, skipping any (defect_type, recipe_id) pair already
in fix_history.

Recipes here only modify x-axis label overlaps. Y-axis overlap is unusual
and currently handled by the LLM fallback; a future YShrinkRecipe could land
when needed.
"""

from __future__ import annotations

import re

from plotlint.fix_recipes import recipe
from plotlint.models import DefectType, Issue


def _axis_indices_from_issue(issue: Issue) -> list[int]:
    """Extract axis indices from element_ids like 'axes.0.xaxis.tick.3'.

    Returns unique indices in first-seen order. Falls back to [0] when no
    parseable id is present, which is the common single-axes case.
    """
    seen: list[int] = []
    for eid in issue.element_ids:
        match = re.match(r"axes\.(\d+)\.", eid)
        if not match:
            continue
        idx = int(match.group(1))
        if idx not in seen:
            seen.append(idx)
    return seen or [0]


def _targets_x_axis(issue: Issue) -> bool:
    """Detect x-axis overlap from Issue.details ("X-axis labels overlap...")."""
    return "x-axis" in issue.details.lower()


@recipe(DefectType.LABEL_OVERLAP)
class RotateXLabelsRecipe:
    """Append `tick_params(axis='x', rotation=45)` for each affected axes.

    Primary recipe for horizontal label collision. Pairs `rotation=45`
    with `ha='right'` to keep labels anchored to their tick rather than
    drifting away after rotation. Calls `fig.tight_layout()` so the
    rotated labels don't get clipped at the bottom.
    """

    recipe_id = "rotate_x_labels"
    defect_type = DefectType.LABEL_OVERLAP

    def can_apply(self, issue: Issue, code: str) -> bool:
        return _targets_x_axis(issue)

    def apply(self, code: str, issue: Issue) -> str:
        axis_indices = _axis_indices_from_issue(issue)
        lines = ["", "# plotlint: rotate x-axis labels to resolve overlap"]
        for idx in axis_indices:
            lines.append(
                f"plt.gcf().axes[{idx}].tick_params(axis='x', rotation=45)"
            )
            lines.append(
                f"for _lbl in plt.gcf().axes[{idx}].get_xticklabels(): _lbl.set_ha('right')"
            )
        lines.append("plt.gcf().tight_layout()")
        return code.rstrip() + "\n" + "\n".join(lines) + "\n"


@recipe(DefectType.LABEL_OVERLAP)
class ShrinkXTickFontRecipe:
    """Shrink the x-axis tick label font size.

    Secondary fallback for horizontal label collision when rotation alone
    didn't resolve it. Reduces font size to 8pt (matplotlib default is 10pt).
    """

    recipe_id = "shrink_x_tick_font"
    defect_type = DefectType.LABEL_OVERLAP

    def can_apply(self, issue: Issue, code: str) -> bool:
        return _targets_x_axis(issue)

    def apply(self, code: str, issue: Issue) -> str:
        axis_indices = _axis_indices_from_issue(issue)
        lines = ["", "# plotlint: shrink x-axis tick label font to resolve overlap"]
        for idx in axis_indices:
            lines.append(
                f"plt.gcf().axes[{idx}].tick_params(axis='x', labelsize=8)"
            )
        lines.append("plt.gcf().tight_layout()")
        return code.rstrip() + "\n" + "\n".join(lines) + "\n"
