"""Tests for D's extraction layer.

Covers ~5 of the 23 edge-focused tests from the coverage diagram:
- Edge schema validation
- Provider built-in structured-output schema enforcement
- Multi-call protocol (chunk-by-chunk)
- Edge serialization to JSON metadata
- Negative test: document with zero extractable edges

T1 + T9 deliverables. All stubs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.d_extraction import (
    DocumentExtraction,
    Edge,
    EdgeKind,
    DrugNode,
    extract_document,
)
from src.config import Config


def test_edge_schema_validates_required_fields():
    """Edge schema rejects missing required fields (kind, subject, object)."""
    with pytest.raises(ValidationError):
        Edge(kind=EdgeKind.REQUIRES)  # missing subject + object


def test_edge_schema_rejects_invalid_kind():
    """Edge with kind outside EdgeKind enum raises ValidationError."""
    with pytest.raises(ValidationError):
        Edge(
            kind="not_a_real_kind",
            subject=DrugNode(canonical_id="A", surface_form="A"),
            object=DrugNode(canonical_id="B", surface_form="B"),
        )


def test_extraction_emits_baseline_fields_alongside_edges(tmp_path):
    """D-mode extraction preserves baseline field extraction alongside edges (mock provider)."""
    cfg = Config(provider="mock", d_enabled=True, journal_dir=str(tmp_path))
    doc = extract_document("d1", ["FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B"], cfg)
    assert doc.existing_fields == {"drug_name": "Adalimumab"}
    assert len(doc.edges) == 1


def test_multi_call_extraction_protocol_iterates_chunks(tmp_path):
    """extract_document iterates chunks and accumulates edges via the journal."""
    cfg = Config(provider="mock", d_enabled=True, journal_dir=str(tmp_path))
    doc = extract_document("d2", ["EDGE requires DRUG_A DRUG_B", "EDGE applies_to DRUG_A IND_X"], cfg)
    assert len(doc.edges) == 2


def test_extraction_negative_case_zero_edges(tmp_path):
    """Document with no extractable relationships yields edges=[] and no hallucination."""
    cfg = Config(provider="mock", d_enabled=True, journal_dir=str(tmp_path))
    doc = extract_document("d3", ["FIELD drug_name=Adalimumab"], cfg)
    assert doc.edges == []
    assert doc.existing_fields == {"drug_name": "Adalimumab"}
