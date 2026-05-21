"""Tests for PatchDispatcher routing behaviour."""

from __future__ import annotations

import pytest

from plotlint.fix_recipes import _RECIPES, clear_registry
from plotlint.models import DefectType, InspectionResult, Issue, Severity
from plotlint.patcher import PatchDispatcher
from plotlint.patcher_deterministic import DeterministicPatcher
from plotlint.patcher_llm import LLMPatcher


SOURCE = """import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.bar(['a', 'b', 'c'], [1, 2, 3])
"""

CANNED_LLM_FIX = """```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(['a', 'b', 'c'], [1, 2, 3])
ax.tick_params(axis='x', rotation=45)
```"""


class MockLLMClient:
    def __init__(self, response: str = CANNED_LLM_FIX):
        self.response = response
        self.call_count = 0

    async def complete(self, system, user, model=None, temperature=0.0, max_tokens=4096):
        self.call_count += 1
        return self.response

    async def complete_with_image(self, *args, **kwargs):
        self.call_count += 1
        return self.response


@pytest.fixture
def saved_registry():
    snapshot = {k: list(v) for k, v in _RECIPES.items()}
    yield
    _RECIPES.clear()
    _RECIPES.update(snapshot)


def _overlap_inspection() -> InspectionResult:
    issue = Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.HIGH,
        details="X-axis labels overlap: 5 of 11 adjacent pairs collide",
        suggestion="Rotate x-axis labels",
        element_ids=["axes.0.xaxis.tick.0"],
    )
    return InspectionResult(issues=[issue], score=0.5, element_count=12)


def _empty_inspection() -> InspectionResult:
    return InspectionResult(issues=[], score=1.0, element_count=8)


class TestRouting:
    @pytest.mark.asyncio
    async def test_deterministic_used_when_recipe_available(self):
        llm_client = MockLLMClient()
        dispatcher = PatchDispatcher(
            deterministic=DeterministicPatcher(),
            llm=LLMPatcher(llm_client=llm_client),
        )
        result = await dispatcher.patch(SOURCE, _overlap_inspection(), fix_history=[])
        assert result is not None
        assert result.used_llm is False
        assert llm_client.call_count == 0  # LLM not invoked

    @pytest.mark.asyncio
    async def test_falls_back_to_llm_when_no_recipe(self, saved_registry):
        clear_registry()
        llm_client = MockLLMClient()
        dispatcher = PatchDispatcher(
            deterministic=DeterministicPatcher(),
            llm=LLMPatcher(llm_client=llm_client),
        )
        result = await dispatcher.patch(SOURCE, _overlap_inspection(), fix_history=[])
        assert result is not None
        assert result.used_llm is True
        assert llm_client.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_no_recipe_and_no_llm(self, saved_registry):
        clear_registry()
        dispatcher = PatchDispatcher(deterministic=DeterministicPatcher(), llm=None)
        result = await dispatcher.patch(SOURCE, _overlap_inspection(), fix_history=[])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_issues(self):
        dispatcher = PatchDispatcher(
            deterministic=DeterministicPatcher(),
            llm=LLMPatcher(llm_client=MockLLMClient()),
        )
        result = await dispatcher.patch(SOURCE, _empty_inspection(), fix_history=[])
        assert result is None
