"""Tests for the cascade-OCR judge re-calibration per D3.

Covers ~1 test from the coverage diagram + verifies the D3 acceptance gate
(judge-pass-rate >= 95% on D-mode output Wilson lower-bound).

T3 deliverable. All stubs.
"""

from __future__ import annotations

import pytest

from src.cascade_integration import recalibrate_judge, RecalibrationResult


def test_recalibrate_judge_on_d_mode_output(tmp_path):
    """Re-calibration on D-mode output produces RecalibrationResult with threshold_met flag."""
    pytest.skip("T3 deliverable — cascade-OCR eval set dependency")


def test_judge_pass_rate_threshold_uses_wilson_lower_bound():
    """threshold_met is True only when Wilson lower-bound >= 0.95, not point estimate."""
    pytest.skip("T3 + T12 deliverable")
