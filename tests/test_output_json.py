"""Tests for JSONReportWriter."""

from __future__ import annotations

import json
from pathlib import Path

from plotlint.models import (
    ConvergenceState,
    DefectType,
    FixAttempt,
    InspectionResult,
    Issue,
    Severity,
)
from plotlint.output import JSONReportWriter, OutputFormat


def _issue() -> Issue:
    return Issue(
        defect_type=DefectType.LABEL_OVERLAP,
        severity=Severity.HIGH,
        details="X-axis labels overlap",
        suggestion="Rotate labels",
        element_ids=["axes.0.xaxis.tick.0"],
    )


def _fix() -> FixAttempt:
    return FixAttempt(
        iteration=1,
        target_issue=DefectType.LABEL_OVERLAP,
        description="Rotated labels via rotate_x_labels",
        code_hash="abc123",
        score_before=0.5,
        score_after=0.9,
        recipe_id="rotate_x_labels",
    )


def _state() -> ConvergenceState:
    return {
        "iteration": 2,
        "score": 0.9,
        "score_history": [0.5, 0.9],
        "fix_history": [_fix()],
        "inspection": InspectionResult(issues=[], score=0.9, element_count=12),
        "source_code": "import matplotlib.pyplot as plt\n# final code",
        "render_error": None,
    }


class TestJSONReportWriter:
    def test_writes_report(self, tmp_path: Path):
        writer = JSONReportWriter()
        result = writer.write(_state(), tmp_path, name="my_chart")
        report_path = tmp_path / "my_chart_report.json"
        assert report_path.exists()
        assert OutputFormat.JSON in result.formats

    def test_report_schema(self, tmp_path: Path):
        writer = JSONReportWriter()
        writer.write(_state(), tmp_path, name="x")
        report = json.loads((tmp_path / "x_report.json").read_text(encoding="utf-8"))
        assert report["name"] == "x"
        assert report["iterations"] == 2
        assert report["final_score"] == 0.9
        assert report["score_history"] == [0.5, 0.9]
        assert len(report["fix_history"]) == 1
        assert report["fix_history"][0]["recipe_id"] == "rotate_x_labels"
        assert report["fix_history"][0]["target_issue"] == "label_overlap"
        assert report["final_issues"] == []
        assert report["render_error"] is None
        assert "final code" in report["final_code"]

    def test_final_issues_serialized(self, tmp_path: Path):
        writer = JSONReportWriter()
        state = _state()
        state["inspection"] = InspectionResult(
            issues=[_issue()], score=0.5, element_count=12
        )
        writer.write(state, tmp_path, name="y")
        report = json.loads((tmp_path / "y_report.json").read_text(encoding="utf-8"))
        assert len(report["final_issues"]) == 1
        issue_payload = report["final_issues"][0]
        assert issue_payload["defect_type"] == "label_overlap"
        assert issue_payload["severity"] == "high"

    def test_handles_empty_state(self, tmp_path: Path):
        """Even with a near-empty state (e.g. render failed before inspect),
        the writer should produce a valid JSON file."""
        writer = JSONReportWriter()
        state: ConvergenceState = {"render_error": "boom"}
        writer.write(state, tmp_path, name="z")
        report = json.loads((tmp_path / "z_report.json").read_text(encoding="utf-8"))
        assert report["render_error"] == "boom"
        assert report["fix_history"] == []
        assert report["final_issues"] == []

    def test_format_property(self):
        assert JSONReportWriter().format == OutputFormat.JSON
