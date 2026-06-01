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

from src.d_extraction import (
    DocumentExtraction,
    Edge,
    EdgeKind,
    DrugNode,
    extract_document,
)


def test_edge_schema_validates_required_fields():
    """Edge schema rejects missing required fields (kind, subject, object)."""
    pytest.skip("T1 deliverable")


def test_edge_schema_rejects_invalid_kind():
    """Edge with kind outside EdgeKind enum raises ValidationError."""
    pytest.skip("T1 deliverable")


def test_extraction_emits_baseline_fields_alongside_edges(sample_drug_node):
    """D-modified prompt preserves baseline field extraction (drug name, age limit, etc.)."""
    pytest.skip("T1 + T10 deliverable (regression-adjacent)")


def test_multi_call_extraction_protocol_iterates_chunks():
    """extract_document iterates chunks and accumulates edges via the journal."""
    pytest.skip("T1 + T2 deliverable")


def test_extraction_negative_case_zero_edges():
    """Document with no extractable relationships yields edges=[] and no hallucination."""
    pytest.skip("T1 + T9 deliverable")
