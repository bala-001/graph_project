"""Tests for the shadow harness per D5 + D12 statistical significance.

Covers ~2 of the 23 edge-focused tests:
- D-output vs analyst-corrected ground truth precision/recall
- Wilson lower-bound applied to Phase-2 trigger thresholds

T11 + T12 deliverables. All stubs.
"""

from __future__ import annotations

import pytest

from src.shadow import compare_d_to_ground_truth, ShadowResult
from src.shadow.harness import wilson_lower_bound


def test_shadow_compare_computes_precision_recall(tmp_path):
    """compare_d_to_ground_truth returns ShadowResult with point + Wilson-lower-bound precision/recall."""
    pytest.skip("T11 deliverable — eval-set dependency")


def test_wilson_lower_bound_below_point_estimate():
    """Wilson lower bound is strictly below the point estimate for any non-trivial sample."""
    pytest.skip("T12 deliverable; standard scipy.stats applies")
