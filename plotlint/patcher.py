"""PatchDispatcher — routes one Issue to deterministic-first, LLM-fallback.

Single source of truth for the patching routing policy. The convergence
loop's patch_node delegates to this dispatcher.

Routing rule (declarative):
  1. Read the highest-severity issue from the inspection.
  2. Ask DeterministicPatcher for a PatchResult.
     - Returns one if a registered recipe applies and hasn't been tried.
  3. If None and an LLM patcher is wired, ask LLMPatcher.
  4. If both return None, surface None — the loop will stop on the next pass
     when render_error is set / score doesn't improve.

SoC: the dispatcher chooses WHO patches; it never patches itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from plotlint.models import FixAttempt, InspectionResult, PatchResult
from plotlint.patcher_deterministic import DeterministicPatcher
from plotlint.patcher_llm import LLMPatcher


@dataclass
class PatchDispatcher:
    """Routes the highest-severity Issue to deterministic, with LLM as fallback.

    `llm` is optional: when None, only the deterministic path runs and
    issues without recipes return None (the loop will stop). This is
    useful for offline / no-API-key environments.
    """

    deterministic: DeterministicPatcher
    llm: Optional[LLMPatcher] = None

    async def patch(
        self,
        code: str,
        inspection: InspectionResult,
        fix_history: list[FixAttempt],
    ) -> Optional[PatchResult]:
        issue = inspection.highest_severity_issue
        if issue is None:
            return None

        result = self.deterministic.patch(code, issue, fix_history)
        if result is not None:
            return result

        if self.llm is None:
            return None

        return await self.llm.patch(code, issue, fix_history)
