"""Shadow harness — D output vs analyst-corrected ground truth comparison.

Runs in parallel with the production pipeline on shadowed documents.
Produces per-document precision/recall on relationship-class edges plus
per-existing-field iso-precision check (for the Week-4 regression gate).

T11 + T12 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..d_extraction.schema import DocumentExtraction


@dataclass
class ShadowResult:
    """Per-document comparison output."""
    document_id: str
    # Edge precision/recall (relationship-class):
    edge_precision_point: float  # |D ∩ GT| / |D|
    edge_recall_point: float     # |D ∩ GT| / |GT|
    edge_precision_wilson_lower: float  # Wilson 95% lower bound
    edge_recall_wilson_lower: float
    n_d_edges: int
    n_gt_edges: int
    # Existing-field iso-precision:
    field_iso_precision_per_field: dict[str, float]  # field_name -> precision delta vs baseline
    regression_detected_fields: list[str]  # fields where iso-precision dropped >5%


def compare_d_to_ground_truth(
    d_extraction: DocumentExtraction,
    ground_truth_path: Path,
    baseline_extraction: DocumentExtraction | None = None,
) -> ShadowResult:
    """Compare D's extraction to analyst-corrected ground truth.

    If `baseline_extraction` is provided, also compute iso-precision regression
    on existing field types (T10 dependency for the Week-4 gate).

    STUB — T11 deliverable.
    """
    raise NotImplementedError("T11 deliverable")


def wilson_lower_bound(successes: int, total: int, confidence: float = 0.95) -> float:
    """Standard Wilson interval lower bound for a binomial proportion.

    Used to defend Kill Criteria gates from point-estimate noise on small N.
    T12 deliverable.
    """
    raise NotImplementedError("T12 deliverable")
