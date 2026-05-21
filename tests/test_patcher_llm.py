"""Tests for LLMPatcher.

NOTE on the "production gap": in L1 the two checked defect types
(label_overlap, element_cutoff) both have registered deterministic recipes,
so the dispatcher never routes to the LLM patcher in normal operation.
These tests deliberately construct scenarios that exercise the LLM path
(by passing an Issue with whose defect_type has no recipe, or by injecting
a MockLLMClient) so the scaffold is verified end-to-end.
"""

from __future__ import annotations

from typing import Optional

import pytest

from plotlint.core.errors import LLMError
from plotlint.models import DefectType, Issue, Severity
from plotlint.patcher_llm import LLMPatcher


class MockLLMClient:
    """Test double for LLMClient. Returns canned text; tracks call history."""

    def __init__(self, response: str = ""):
        self.response = response
        self.calls: list[dict] = []

    async def complete(self, system, user, model=None, temperature=0.0, max_tokens=4096):
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        return self.response

    async def complete_with_image(self, system, user, image_bytes, model=None, temperature=0.0, max_tokens=4096):
        self.calls.append({"system": system, "user": user, "has_image": True})
        return self.response


class FailingLLMClient:
    """Always raises LLMError. For verifying graceful failure."""

    async def complete(self, system, user, model=None, temperature=0.0, max_tokens=4096):
        raise LLMError("simulated network failure")

    async def complete_with_image(self, system, user, image_bytes, model=None, temperature=0.0, max_tokens=4096):
        raise LLMError("simulated network failure")


SOURCE = """import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.bar(['a', 'b', 'c'], [1, 2, 3])
"""


def _recipeless_issue() -> Issue:
    """Construct an Issue whose defect_type triggers the LLM path in tests.

    We reuse LABEL_OVERLAP here; the surrounding test clears the recipe
    registry before invoking the patcher to ensure the LLM is what
    handles it, NOT the deterministic patcher.
    """
    return Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.HIGH,
        details="hypothetical defect with no registered recipe",
        suggestion="ask the model to fix it",
        element_ids=["axes.0.xaxis.tick.0"],
    )


CANNED_FIX = """```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(['a', 'b', 'c'], [1, 2, 3])
ax.tick_params(axis='x', rotation=45)
```"""


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_returns_patch_result_with_parsed_code(self):
        client = MockLLMClient(response=CANNED_FIX)
        patcher = LLMPatcher(llm_client=client)
        result = await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
        assert result is not None
        assert result.used_llm is True
        assert result.recipe_id is None
        assert "rotation=45" in result.patched_code
        assert result.target_issue == DefectType.LABEL_OVERLAP
        assert result.code_hash  # non-empty

    @pytest.mark.asyncio
    async def test_includes_system_and_issue_context_in_prompt(self):
        client = MockLLMClient(response=CANNED_FIX)
        patcher = LLMPatcher(llm_client=client)
        await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
        assert len(client.calls) == 1
        call = client.calls[0]
        assert "matplotlib script" in call["system"].lower()
        assert "hypothetical defect" in call["user"]
        assert SOURCE.strip() in call["user"]

    @pytest.mark.asyncio
    async def test_temperature_is_zero_for_deterministic_fixes(self):
        client = MockLLMClient(response=CANNED_FIX)
        patcher = LLMPatcher(llm_client=client)
        await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
        assert client.calls[0]["temperature"] == 0.0


class TestGracefulFailure:
    @pytest.mark.asyncio
    async def test_returns_none_on_llm_error(self):
        patcher = LLMPatcher(llm_client=FailingLLMClient())
        result = await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_unparseable_response(self):
        client = MockLLMClient(response="I will not write code today.")
        patcher = LLMPatcher(llm_client=client)
        result = await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
        assert result is None


class TestUnsupportedRenderer:
    @pytest.mark.asyncio
    async def test_unknown_renderer_raises_key_error(self):
        """The Plotly renderer prompt is deferred to PL-1.6. Asking the LLM
        patcher to handle an unknown renderer should fail loudly rather than
        silently degrade."""
        client = MockLLMClient(response=CANNED_FIX)
        patcher = LLMPatcher(llm_client=client, renderer_type="plotly")
        with pytest.raises(KeyError):
            await patcher.patch(SOURCE, _recipeless_issue(), fix_history=[])
