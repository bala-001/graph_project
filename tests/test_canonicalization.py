"""Tests for edge canonicalization per D12.

Without canonicalization, temperature > 0 produces serialization drift that
under-counts true false positives. The Week-6 Kill Criteria gate depends on
counter 1 being accurate, which depends on canonicalization being correct.

Covers ~2 of the 23 edge-focused tests:
- Surface-form variations canonicalize to same form
- Predicate name normalization (case-fold, whitespace)
- Qualifier dict key sorting

T4 + T9 deliverables. All stubs.
"""

from __future__ import annotations

import pytest

from src.d_extraction.schema import Edge, EdgeKind, DrugNode, canonicalize_edge


def test_surface_form_drift_canonicalizes_to_same_id():
    """'Drug A' vs 'drug a' vs ' Drug A ' all canonicalize to the same drug ID."""
    pytest.skip("T4 + T1 deliverable")


def test_qualifier_dict_key_ordering_normalized():
    """Same qualifiers in different key orders canonicalize to the same tuple."""
    pytest.skip("T4 deliverable")


def test_predicate_normalization_case_and_whitespace():
    """EdgeKind enum is already canonical; predicate strings outside the enum are rejected upstream."""
    pytest.skip("T1 deliverable — enum-constrained")
