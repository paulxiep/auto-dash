"""LLM patcher prompt templates, keyed by renderer type.

Architecture: prompts are data, not logic. The LLMPatcher composes a system
prompt + a per-renderer user template + the current code + issue context, then
calls the LLM and parses the response with parse_code_from_response.

Adding a new renderer (e.g. Plotly in PL-1.6) means adding one more user
template here and one branch in the dispatcher — no patcher code changes.
"""

from __future__ import annotations

from plotlint.models import FixAttempt, Issue


SYSTEM_PROMPT = """\
You are a Python charting expert. Your job is to fix one specific visual \
defect in a matplotlib script. The user will give you:

  - The current source code
  - A specific issue detected by an automated inspector (with severity)
  - A list of previously-attempted fixes that did NOT resolve the issue

You must return ONLY the corrected source code, in a single ```python``` code \
block. No explanation, no surrounding prose. The corrected code must:

  - Be a complete, runnable script (preserve all imports and data)
  - Be syntactically valid Python
  - Address ONLY the specific issue described
  - Not introduce new defects (e.g. don't rotate labels if that will push them off-screen)
  - Not use an approach already listed in the previous-attempts section
"""


_USER_TEMPLATE_MATPLOTLIB = """\
## Current chart code

```python
{code}
```

## Issue to fix

{issue_context}

## Previously attempted fixes (did not resolve the issue)

{history}

Return only the corrected Python code in one code block.
"""


_USER_TEMPLATES: dict[str, str] = {
    "matplotlib": _USER_TEMPLATE_MATPLOTLIB,
}


def build_user_prompt(
    renderer_type: str,
    code: str,
    issue: Issue,
    fix_history: list[FixAttempt],
) -> str:
    """Build the user-facing prompt for the LLM patcher.

    Raises KeyError when the renderer type has no template registered —
    surfaces missing-renderer-support loudly rather than silently degrading.
    """
    template = _USER_TEMPLATES[renderer_type]
    return template.format(
        code=code.strip(),
        issue_context=issue.to_prompt_context(),
        history=_format_history(fix_history),
    )


def _format_history(fix_history: list[FixAttempt]) -> str:
    if not fix_history:
        return "(none — this is the first attempt)"
    return "\n".join(
        f"- iter {fa.iteration} | {fa.target_issue.value} | "
        f"{fa.description} | score {fa.score_before:.2f} -> {fa.score_after:.2f}"
        for fa in fix_history
    )
