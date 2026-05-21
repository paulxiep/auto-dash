"""LLMPatcher — fallback patcher that asks the LLM to fix an issue.

Scaffolded for future defect types (PL-1.x and PL-2.x) that lack
deterministic recipes. In L1, both checked defect types (label_overlap
and element_cutoff) have recipes, so this path is NOT exercised by the
broken-chart demo. It IS covered by tests/test_patcher_llm.py via a
synthetic recipe-less Issue (the registry is cleared in the test fixture).

SoC: this module knows how to ask the LLM for a fix and parse the response.
It does NOT know whether the dispatcher will route to it — that's the
dispatcher's job.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from plotlint.core.errors import LLMError
from plotlint.core.llm import LLMClient
from plotlint.core.parsing import parse_code_from_response
from plotlint.models import FixAttempt, Issue, PatchResult
from plotlint.prompts.patching import SYSTEM_PROMPT, build_user_prompt


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass
class LLMPatcher:
    """Calls the LLM to generate a fix for an issue that no recipe handles.

    The dispatcher invokes this only when DeterministicPatcher returned None
    (no recipe for this defect type, or all applicable recipes already tried).
    """

    llm_client: LLMClient
    renderer_type: str = "matplotlib"
    temperature: float = 0.0
    max_tokens: int = 4096

    async def patch(
        self,
        code: str,
        issue: Issue,
        fix_history: list[FixAttempt],
    ) -> Optional[PatchResult]:
        user_prompt = build_user_prompt(
            renderer_type=self.renderer_type,
            code=code,
            issue=issue,
            fix_history=fix_history,
        )
        try:
            raw = await self.llm_client.complete(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except LLMError:
            return None

        try:
            patched_code = parse_code_from_response(raw)
        except ValueError:
            return None

        return PatchResult(
            patched_code=patched_code,
            code_hash=_hash(patched_code),
            target_issue=issue.defect_type,
            description=f"LLM-generated fix for {issue.defect_type.value}",
            used_llm=True,
            recipe_id=None,
        )
