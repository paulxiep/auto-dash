"""Tests for PNGWriter."""

from __future__ import annotations

from pathlib import Path

from plotlint.models import ConvergenceState
from plotlint.output import OutputFormat, PNGWriter


def _state(png: bytes = b"\x89PNG\r\nfakepng", code: str = "import matplotlib"):
    state: ConvergenceState = {
        "png_bytes": png,
        "source_code": code,
    }
    return state


class TestPNGWriter:
    def test_writes_png_and_code(self, tmp_path: Path):
        writer = PNGWriter()
        result = writer.write(_state(), tmp_path, name="my_chart")
        assert OutputFormat.PNG in result.formats
        assert (tmp_path / "my_chart.png").exists()
        assert (tmp_path / "my_chart.py").exists()
        assert (tmp_path / "my_chart.png").read_bytes().startswith(b"\x89PNG")

    def test_creates_missing_directory(self, tmp_path: Path):
        writer = PNGWriter()
        nested = tmp_path / "nested" / "dir"
        result = writer.write(_state(), nested, name="x")
        assert nested.exists()
        assert (nested / "x.png").exists()

    def test_default_name(self, tmp_path: Path):
        writer = PNGWriter()
        writer.write(_state(), tmp_path)
        assert (tmp_path / "chart.png").exists()
        assert (tmp_path / "chart.py").exists()

    def test_no_png_skips_png(self, tmp_path: Path):
        """When png_bytes is missing (render failed), don't write a corrupt PNG."""
        writer = PNGWriter()
        state: ConvergenceState = {"source_code": "import matplotlib"}
        result = writer.write(state, tmp_path, name="failed")
        assert not (tmp_path / "failed.png").exists()
        assert (tmp_path / "failed.py").exists()  # code still saved

    def test_format_property(self):
        assert PNGWriter().format == OutputFormat.PNG
