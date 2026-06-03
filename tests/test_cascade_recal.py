"""Tests for the cascade-OCR judge re-calibration per D3.

Verifies the D3 acceptance-gate logic (judge-pass-rate >= 95% on D-mode output
via Wilson lower-bound). The live re-cal on the real cascade-OCR eval set is
Phase-0-blocked; the pass-rate + Wilson-threshold logic is exercised here with an
injected fake d_extraction_module over synthetic pages.

T3 (logic core) + T12 deliverables.
"""

from __future__ import annotations

import json

from src.cascade_integration import recalibrate_judge, RecalibrationResult
from src.d_extraction.schema import DocumentExtraction


def _doc(complete: bool) -> DocumentExtraction:
    return DocumentExtraction(
        document_id="page-doc",
        extraction_started_at="2026-05-26T00:00:00Z",
        extraction_complete=complete,
    )


def _write_pages(directory, n: int, label: str = "cheap_ok"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "eval.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"page_id": i, "text": f"page {i}", "ocr_label": label}) for i in range(n)
        ),
        encoding="utf-8",
    )
    return path


def test_recalibrate_judge_on_d_mode_output(tmp_path):
    """Re-calibration produces a RecalibrationResult with a threshold_met flag."""
    path = _write_pages(tmp_path / "set", 5)
    result = recalibrate_judge(path, lambda text: _doc(True))
    assert isinstance(result, RecalibrationResult)
    assert result.n_pages_evaluated == 5
    assert result.judge_pass_rate == 1.0
    assert isinstance(result.threshold_met, bool)


def test_judge_pass_rate_threshold_uses_wilson_lower_bound(tmp_path):
    """threshold_met is True only when the Wilson lower-bound >= 0.95, not the point estimate."""
    # 19 all-pass pages: point estimate 1.0 but Wilson lower < 0.95 -> NOT met.
    small = recalibrate_judge(_write_pages(tmp_path / "small", 19), lambda text: _doc(True))
    assert small.judge_pass_rate == 1.0
    assert small.judge_pass_rate_wilson_lower < 0.95
    assert small.threshold_met is False
    # 200 all-pass pages: Wilson lower >= 0.95 -> met.
    big = recalibrate_judge(_write_pages(tmp_path / "big", 200), lambda text: _doc(True))
    assert big.threshold_met is True
