"""Output writers for the plotlint convergence loop.

Writers are pure functions of the final ConvergenceState + an output directory.
They never re-render or re-inspect — they emit what's already in state.

Two writers ship in L1:
- PNGWriter: writes the final PNG + the fixed source code
- JSONReportWriter: writes a structured report of the convergence trail
  (initial score, fix history, score trajectory, final issues, final code)

Future writers (HTMLWriter, PDFWriter) implement the same OutputWriter
protocol and are registered via register_writer().
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

from plotlint.core.errors import ConfigError
from plotlint.models import ConvergenceState


class OutputFormat(str, Enum):
    PNG = "png"
    JSON = "json"


@dataclass(frozen=True)
class OutputResult:
    """Record of what a writer emitted."""

    files_written: list[Path] = field(default_factory=list)
    formats: list[OutputFormat] = field(default_factory=list)


@runtime_checkable
class OutputWriter(Protocol):
    """Protocol for emitting one chart's convergence outputs."""

    @property
    def format(self) -> OutputFormat: ...

    def write(
        self,
        state: ConvergenceState,
        output_dir: Path,
        name: str = "chart",
    ) -> OutputResult: ...


# --- PNG writer ---


@dataclass
class PNGWriter:
    """Writes <name>.png (final rendered chart) and <name>.py (fixed source code).

    Reads ConvergenceState.png_bytes and ConvergenceState.source_code.
    The demo is responsible for capturing the *original* PNG separately
    (typically by invoking the renderer once before the loop) — this writer
    only emits the final state.
    """

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.PNG

    def write(
        self,
        state: ConvergenceState,
        output_dir: Path,
        name: str = "chart",
    ) -> OutputResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files: list[Path] = []

        png_bytes = state.get("png_bytes")
        if png_bytes:
            png_path = output_dir / f"{name}.png"
            png_path.write_bytes(png_bytes)
            files.append(png_path)

        code = state.get("source_code")
        if code:
            code_path = output_dir / f"{name}.py"
            code_path.write_text(code, encoding="utf-8")
            files.append(code_path)

        return OutputResult(files_written=files, formats=[OutputFormat.PNG])


# --- JSON report writer ---


@dataclass
class JSONReportWriter:
    """Writes <name>_report.json with the convergence trail.

    Schema (minimal; revisit in DI-4.3 if consumers need a stable contract):
        {
          "name": str,
          "iterations": int,
          "final_score": float,
          "score_history": [float, ...],
          "fix_history": [
            {"iteration": int, "target_issue": str, "description": str,
             "code_hash": str, "score_before": float, "score_after": float,
             "recipe_id": str | null},
            ...
          ],
          "final_issues": [
            {"defect_type": str, "severity": str, "details": str,
             "suggestion": str, "element_ids": [str, ...]},
            ...
          ],
          "render_error": str | null,
          "final_code": str
        }
    """

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.JSON

    def write(
        self,
        state: ConvergenceState,
        output_dir: Path,
        name: str = "chart",
    ) -> OutputResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        inspection = state.get("inspection")
        final_issues = []
        if inspection is not None:
            for issue in inspection.issues:
                final_issues.append({
                    "defect_type": issue.defect_type.value,
                    "severity": issue.severity.value,
                    "details": issue.details,
                    "suggestion": issue.suggestion,
                    "element_ids": list(issue.element_ids),
                })

        fix_history_serialized = []
        for fa in state.get("fix_history", []):
            d = asdict(fa)
            # DefectType is an Enum; asdict gives the Enum, JSON wants the value
            d["target_issue"] = fa.target_issue.value
            fix_history_serialized.append(d)

        report = {
            "name": name,
            "iterations": state.get("iteration", 0),
            "final_score": state.get("score", 0.0),
            "score_history": list(state.get("score_history", [])),
            "fix_history": fix_history_serialized,
            "final_issues": final_issues,
            "render_error": state.get("render_error"),
            "final_code": state.get("source_code", ""),
        }

        report_path = output_dir / f"{name}_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return OutputResult(files_written=[report_path], formats=[OutputFormat.JSON])


# --- Registry ---


_WRITERS: dict[OutputFormat, OutputWriter] = {}


def register_writer(writer: OutputWriter) -> None:
    _WRITERS[writer.format] = writer


def get_writer(format: OutputFormat = OutputFormat.PNG) -> OutputWriter:
    if format not in _WRITERS:
        raise ConfigError(f"No writer registered for format: {format.value}")
    return _WRITERS[format]


# Register defaults
register_writer(PNGWriter())
register_writer(JSONReportWriter())
