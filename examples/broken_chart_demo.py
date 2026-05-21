"""End-to-end demo of the plotlint convergence loop.

Runs two deliberately broken matplotlib charts through render → inspect → patch
→ re-render until convergence. Emits the fixed PNG, the fixed source code, and
a JSON report per chart under examples/output/.

Defaults to the deterministic patcher only (no LLM, no API key needed).
If ANTHROPIC_API_KEY is set in the environment, an LLMPatcher fallback is
also wired in — though it won't fire in this demo because both defect types
present (label overlap, element cutoff) have deterministic recipes.

Usage:
    python examples/broken_chart_demo.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from plotlint.config import ConvergenceConfig
from plotlint.loop import build_convergence_graph
from plotlint.models import ConvergenceState
from plotlint.output import JSONReportWriter, PNGWriter
from plotlint.patcher import PatchDispatcher
from plotlint.patcher_deterministic import DeterministicPatcher
from plotlint.renderer import matplotlib_bundle


OVERLAP_CHART = """\
import matplotlib.pyplot as plt
months = ['Jan','Feb','Mar','Apr','May','Jun',
          'Jul','Aug','Sep','Oct','Nov','Dec']
values = [3, 7, 2, 8, 5, 9, 4, 6, 7, 3, 5, 8]
fig, ax = plt.subplots(figsize=(4, 3))
ax.bar(months, values)
ax.set_title('Monthly sales')
"""

CUTOFF_CHART = """\
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([1, 2, 3], [4, 5, 6])
ax.set_title('A long chart title that gets clipped')
ax.set_xlabel('Time of day (hours)')
ax.set_ylabel('Clicks per minute')
"""


def _build_dispatcher(llm_enabled: bool) -> PatchDispatcher:
    """Wire the patcher dispatcher.

    Deterministic recipes always available. LLM fallback only wired when
    ANTHROPIC_API_KEY is set and the anthropic package is importable.
    """
    llm_patcher = None
    if llm_enabled:
        try:
            from plotlint.core.config import LLMConfig
            from plotlint.core.llm import AnthropicClient
            from plotlint.patcher_llm import LLMPatcher

            client = AnthropicClient(
                LLMConfig(), api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )
            llm_patcher = LLMPatcher(llm_client=client)
        except Exception as exc:  # noqa: BLE001 — demo: degrade gracefully
            print(f"  (LLM patcher unavailable: {exc.__class__.__name__}; "
                  f"running deterministic-only)")
    return PatchDispatcher(deterministic=DeterministicPatcher(), llm=llm_patcher)


async def _capture_original_png(code: str) -> Optional[bytes]:
    """Render once before the loop so we can save the original alongside fixed."""
    bundle = matplotlib_bundle()
    result = await asyncio.to_thread(bundle.renderer.render, code)
    return result.png_bytes if result.succeeded else None


async def run_one(name: str, code: str, dispatcher: PatchDispatcher, out_dir: Path) -> dict:
    """Run one chart through the loop and emit outputs.

    Returns a small summary dict for the stdout report.
    """
    # Snapshot the original PNG for visual comparison.
    original_png = await _capture_original_png(code)
    if original_png:
        (out_dir / f"{name}_original.png").write_bytes(original_png)

    graph = build_convergence_graph(
        config=ConvergenceConfig(max_iterations=5, target_score=1.0),
        patcher=dispatcher,
    )
    initial_state: ConvergenceState = {
        "source_code": code,
        "original_code": code,
        "max_iterations": 5,
        "fix_history": [],
        "score_history": [],
        "iteration": 0,
    }
    final = await graph.ainvoke(initial_state)

    PNGWriter().write(final, out_dir, name=f"{name}_fixed")
    JSONReportWriter().write(final, out_dir, name=name)

    initial_score = final["score_history"][0] if final["score_history"] else 0.0
    return {
        "name": name,
        "initial_score": initial_score,
        "final_score": final.get("score", 0.0),
        "iterations": final.get("iteration", 0),
        "fixes": len(final.get("fix_history", [])),
        "used_llm": any(getattr(fa, "recipe_id", None) is None for fa in final.get("fix_history", [])),
    }


async def main() -> None:
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    dispatcher = _build_dispatcher(llm_enabled=has_api_key)
    if not has_api_key:
        print("ANTHROPIC_API_KEY not set; running deterministic-only "
              "(no LLM fallback). Both demo defects have recipes — this is the "
              "natural L1 path.")

    summaries = []
    for name, code in (("overlap", OVERLAP_CHART), ("cutoff", CUTOFF_CHART)):
        print(f"\n=== {name} ===")
        summary = await run_one(name, code, dispatcher, out_dir)
        summaries.append(summary)
        print(f"  score {summary['initial_score']:.2f} -> {summary['final_score']:.2f} "
              f"in {summary['iterations']} iteration(s), {summary['fixes']} fix(es)")
        if summary["used_llm"]:
            print("  (LLM patcher was invoked — at least one fix used the fallback)")

    print(f"\nOutputs in {out_dir.resolve()}")
    for s in summaries:
        print(f"  - {s['name']}_original.png, {s['name']}_fixed.png, "
              f"{s['name']}_fixed.py, {s['name']}_report.json")


if __name__ == "__main__":
    asyncio.run(main())
