"""Tests for the shadow harness per D5 + D12 statistical significance.

- D-output vs analyst-corrected ground truth precision/recall (logic core, synthetic GT)
- Wilson lower-bound applied to Phase-2 trigger thresholds

T11 (logic core) + T12 deliverables. The live shadow run on the real eval set is
Phase-0-blocked; the comparison + statistics logic is exercised here with
synthetic fixtures.
"""

from __future__ import annotations

import json

from src.shadow import compare_d_to_ground_truth, ShadowResult
from src.shadow.harness import wilson_lower_bound, clopper_pearson_lower_bound, lower_bound
from src.d_extraction.schema import DocumentExtraction, Edge, EdgeKind, DrugNode


def _edge(subject, obj):
    return Edge(
        kind=EdgeKind.REQUIRES,
        subject=DrugNode(canonical_id=subject, surface_form=subject),
        object=DrugNode(canonical_id=obj, surface_form=obj),
    )


def test_shadow_compare_computes_precision_recall(tmp_path):
    """compare_d_to_ground_truth returns ShadowResult with point + Wilson-lower-bound precision/recall."""
    d_extraction = DocumentExtraction(
        document_id="doc1",
        extraction_started_at="2026-05-26T00:00:00Z",
        edges=[_edge("A", "B"), _edge("A", "C")],
    )
    ground_truth = [_edge("A", "B"), _edge("A", "D")]  # 1 of 2 D edges correct; 1 of 2 GT recalled
    gt_path = tmp_path / "gt.json"
    gt_path.write_text(
        json.dumps([json.loads(e.model_dump_json()) for e in ground_truth]),
        encoding="utf-8",
    )

    result = compare_d_to_ground_truth(d_extraction, gt_path)
    assert isinstance(result, ShadowResult)
    assert result.n_d_edges == 2 and result.n_gt_edges == 2
    assert result.edge_precision_point == 0.5
    assert result.edge_recall_point == 0.5
    # Wilson lower bound defends the gate against point-estimate noise.
    assert 0.0 <= result.edge_precision_wilson_lower < result.edge_precision_point


def test_wilson_lower_bound_below_point_estimate():
    """Wilson lower bound is strictly below the point estimate for any non-trivial sample."""
    assert wilson_lower_bound(8, 10) < 0.8
    assert wilson_lower_bound(0, 0) == 0.0  # zero-volume guard (no divide-by-zero)
    assert wilson_lower_bound(20, 20) < 1.0  # even a perfect sample is bounded below 1.0


def test_clopper_pearson_lower_bound():
    """Exact interval: below the point estimate, 0.0 on zero successes/total."""
    assert 0.0 < clopper_pearson_lower_bound(8, 10) < 0.8
    assert clopper_pearson_lower_bound(0, 0) == 0.0
    assert clopper_pearson_lower_bound(0, 10) == 0.0


def test_lower_bound_auto_picks_method_by_sample_size(tmp_path):
    """auto: Clopper-Pearson for small N (<30), Wilson otherwise (per D12)."""
    assert lower_bound(5, 5, method="auto") == clopper_pearson_lower_bound(5, 5)
    assert lower_bound(40, 50, method="auto") == wilson_lower_bound(40, 50)
    assert lower_bound(40, 50, method="wilson") == wilson_lower_bound(40, 50)
