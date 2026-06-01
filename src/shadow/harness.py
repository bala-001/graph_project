"""Shadow harness - D output vs analyst-corrected ground truth comparison.

Runs in parallel with the production pipeline on shadowed documents.
Produces per-document precision/recall on relationship-class edges plus
per-existing-field iso-precision check (for the Week-4 regression gate).

The end-to-end shadow RUN (real D output + real analyst ground truth on the
50-doc cascade-OCR eval set) is Phase-0-blocked. The comparison + statistics
LOGIC implemented here is exercised now with synthetic fixtures; the live run
swaps in the real eval set without code change.

T11 + T12 deliverable.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from ..d_extraction.schema import DocumentExtraction, Edge, canonicalize_edge


# Standard normal quantile for a two-sided 95% interval (z_{0.975}).
_Z_95 = 1.959963984540054


@dataclass
class ShadowResult:
    """Per-document comparison output."""
    document_id: str
    # Edge precision/recall (relationship-class):
    edge_precision_point: float  # |D intersect GT| / |D|
    edge_recall_point: float     # |D intersect GT| / |GT|
    edge_precision_wilson_lower: float  # Wilson 95% lower bound
    edge_recall_wilson_lower: float
    n_d_edges: int
    n_gt_edges: int
    # Existing-field iso-precision:
    field_iso_precision_per_field: dict[str, float]  # field_name -> precision delta vs baseline
    regression_detected_fields: list[str]  # fields where iso-precision dropped >5%


def wilson_lower_bound(successes: int, total: int, confidence: float = 0.95) -> float:
    """Standard Wilson interval lower bound for a binomial proportion.

    Used to defend Kill Criteria gates from point-estimate noise on small N.
    Returns 0.0 when total is 0 (the gate's <1% / low-N branch handles this).
    T12 deliverable.
    """
    if total <= 0:
        return 0.0
    if abs(confidence - 0.95) < 1e-9:
        z = _Z_95
    else:
        from scipy.stats import norm

        z = float(norm.ppf(1 - (1 - confidence) / 2))
    p = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = p + z2 / (2 * total)
    margin = z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))
    return max(0.0, (center - margin) / denom)


def _load_ground_truth_edges(path: Path) -> list[Edge]:
    """Load analyst-corrected ground-truth edges from a JSON list or JSONL file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    # Detect format by the first non-whitespace char so a genuinely corrupt JSON
    # file surfaces its real parse error instead of being silently retried as JSONL.
    if text[0] in "[{":
        data = json.loads(text)
        records = data if isinstance(data, list) else data.get("edges", [])
    else:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [Edge.model_validate(r) for r in records]


def compare_d_to_ground_truth(
    d_extraction: DocumentExtraction,
    ground_truth_path: Path,
    baseline_extraction: DocumentExtraction | None = None,
) -> ShadowResult:
    """Compare D's extraction to analyst-corrected ground truth.

    Precision = |D intersect GT| / |D|; Recall = |D intersect GT| / |GT|, where
    membership is by canonicalized edge. If `baseline_extraction` is provided,
    also compute iso-precision regression on existing field types (the Week-4
    gate's input): a field that changed value counts as a regression delta.
    """
    d_set = {canonicalize_edge(e) for e in d_extraction.edges}
    gt_set = {canonicalize_edge(e) for e in _load_ground_truth_edges(Path(ground_truth_path))}
    intersection = d_set & gt_set
    n_d, n_gt, n_hit = len(d_set), len(gt_set), len(intersection)

    field_iso: dict[str, float] = {}
    regressed: list[str] = []
    if baseline_extraction is not None:
        for field_name, baseline_value in baseline_extraction.existing_fields.items():
            d_value = d_extraction.existing_fields.get(field_name)
            delta = 0.0 if d_value == baseline_value else 1.0
            field_iso[field_name] = delta
            if delta > 0.05:  # Week-4 Kill Criteria threshold (5%)
                regressed.append(field_name)

    return ShadowResult(
        document_id=d_extraction.document_id,
        edge_precision_point=(n_hit / n_d) if n_d else 0.0,
        edge_recall_point=(n_hit / n_gt) if n_gt else 0.0,
        edge_precision_wilson_lower=wilson_lower_bound(n_hit, n_d),
        edge_recall_wilson_lower=wilson_lower_bound(n_hit, n_gt),
        n_d_edges=n_d,
        n_gt_edges=n_gt,
        field_iso_precision_per_field=field_iso,
        regression_detected_fields=regressed,
    )
