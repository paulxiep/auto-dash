# plotlint/checks/overlap.py

from __future__ import annotations

from plotlint.checks import check
from plotlint.elements import ElementMap, ElementCategory
from plotlint.models import Issue, DefectType, Severity


# Below this rotation angle (degrees), a tick label is considered "upright"
# and standard AABB overlap is meaningful. At or above this angle, the AABB
# overstates the actual visual footprint (the rotated text takes a diagonal
# strip, not the full AABB), so AABB-based collision is skipped.
_ROTATION_TOLERANCE_DEG = 15.0


def _is_rotated(label) -> bool:
    return abs(label.metadata.get("rotation", 0.0)) >= _ROTATION_TOLERANCE_DEG


@check("label_overlap")
class LabelOverlapCheck:
    """Detect overlapping tick labels on x and y axes.

    Algorithm:
    1. Get all tick labels (grouped by axis)
    2. For each adjacent pair, check bbox overlap.
       - If BOTH labels in the pair are rotated >= 15°, skip the AABB test:
         the AABB after rotation overstates the true footprint, and the
         deterministic rotate-x-labels recipe would otherwise never appear
         to resolve overlap. Treat rotated pairs as non-colliding for AABB
         purposes; a future rotation-aware geometry test can replace this.
    3. Compute overlap fraction for severity.

    Severity heuristic:
    - > 50% of pairs collide → HIGH
    - > 20% of pairs collide → MEDIUM
    - any collision         → LOW
    """
    name = "label_overlap"

    def __call__(self, elements: ElementMap) -> list[Issue]:
        issues = []
        for axis in ("x", "y"):
            labels = elements.tick_labels(axis=axis)
            if len(labels) < 2:
                continue

            # Sort by position along the axis
            if axis == "x":
                labels.sort(key=lambda e: e.bbox.x0)
            else:
                labels.sort(key=lambda e: e.bbox.y0)

            collisions = 0
            for i in range(len(labels) - 1):
                a, b = labels[i], labels[i + 1]
                if _is_rotated(a) and _is_rotated(b):
                    continue
                if a.bbox.overlaps(b.bbox):
                    collisions += 1

            if collisions > 0:
                total_pairs = len(labels) - 1
                collision_ratio = collisions / total_pairs

                if collision_ratio > 0.5:
                    severity = Severity.HIGH
                elif collision_ratio > 0.2:
                    severity = Severity.MEDIUM
                else:
                    severity = Severity.LOW

                issues.append(Issue(
                    defect_type=DefectType.LABEL_OVERLAP,
                    severity=severity,
                    details=(
                        f"{axis.upper()}-axis labels overlap: "
                        f"{collisions} of {total_pairs} adjacent pairs collide"
                    ),
                    suggestion=(
                        f"Rotate {axis}-axis labels 45-90 degrees"
                        if axis == "x"
                        else f"Increase figure height or reduce {axis}-axis label count"
                    ),
                    element_ids=[l.element_id for l in labels],
                ))
        return issues
