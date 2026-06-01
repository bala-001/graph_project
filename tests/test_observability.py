"""Tests for D-specific observability aggregation over the 3-counter telemetry (T13, F8).

Metric-shaping slice: roll per-document counter snapshots up into an aggregate FP
rate + firing volume, and apply the Week-6 Kill Criteria band check.
"""

from __future__ import annotations

from src.telemetry.counters import PerDocumentCounters
from src.telemetry.observability import aggregate, within_fp_band


def test_aggregate_sums_counters_across_documents():
    snapshots = [
        PerDocumentCounters(document_id="a", counter_1_same_edge=1, counter_2_different_edge=4),
        PerDocumentCounters(document_id="b", counter_1_same_edge=0, counter_2_different_edge=5),
    ]
    agg = aggregate(snapshots)
    assert agg.counter_1_same_edge == 1
    assert agg.total == 10
    assert agg.n_documents == 2
    assert agg.fp_rate == 0.1
    assert agg.guardrails_firing_count == 10


def test_fp_rate_zero_when_no_rejections():
    agg = aggregate([PerDocumentCounters(document_id="a")])
    assert agg.fp_rate == 0.0
    assert within_fp_band(agg) is False  # 0% is below the 1% floor (too permissive)


def test_within_fp_band_detects_too_aggressive():
    snapshots = [PerDocumentCounters(document_id="a", counter_1_same_edge=3, counter_2_different_edge=1)]
    agg = aggregate(snapshots)  # fp_rate = 3/4 = 0.75
    assert within_fp_band(agg) is False


def test_within_fp_band_accepts_healthy_rate():
    snapshots = [PerDocumentCounters(document_id="a", counter_1_same_edge=1, counter_2_different_edge=9)]
    agg = aggregate(snapshots)  # fp_rate = 1/10 = 0.10, inside [0.01, 0.15]
    assert within_fp_band(agg) is True
