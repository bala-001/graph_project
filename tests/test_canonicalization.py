"""Tests for edge canonicalization per D12.

Without canonicalization, temperature > 0 produces serialization drift that
under-counts true false positives. The Week-6 Kill Criteria gate depends on
counter 1 being accurate, which depends on canonicalization being correct.

Covers:
- Surface-form variations canonicalize to the same key (unresolved-id fallback)
- Qualifier dict key ordering normalized
- Predicate is enum-constrained (out-of-enum rejected upstream)

T4 + T1 deliverables.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.d_extraction.schema import Edge, EdgeKind, DrugNode, canonicalize_edge


def _edge(subj_id, subj_surface, obj_id, obj_surface, qualifiers=None):
    return Edge(
        kind=EdgeKind.REQUIRES,
        subject=DrugNode(canonical_id=subj_id, surface_form=subj_surface),
        object=DrugNode(canonical_id=obj_id, surface_form=obj_surface),
        qualifiers=qualifiers or {},
    )


def test_surface_form_drift_canonicalizes_to_same_id():
    """'Drug A' vs 'drug a' vs ' Drug A ' canonicalize the same via the unresolved-id
    fallback to a normalized surface form (per data-model.md)."""
    e1 = _edge("", "Drug A", "", "Drug B")
    e2 = _edge("", "drug a", "", "drug b")
    e3 = _edge("", " Drug A ", "", "Drug B.")
    assert canonicalize_edge(e1) == canonicalize_edge(e2) == canonicalize_edge(e3)


def test_qualifier_dict_key_ordering_normalized():
    """Same qualifiers in different key orders canonicalize to the same tuple."""
    e1 = _edge("DRUG_A", "Drug A", "DRUG_B", "Drug B", {"age_min": 18, "age_max": 65})
    e2 = _edge("DRUG_A", "Drug A", "DRUG_B", "Drug B", {"age_max": 65, "age_min": 18})
    assert canonicalize_edge(e1) == canonicalize_edge(e2)


def test_predicate_normalization_case_and_whitespace():
    """EdgeKind enum is canonical by construction; a predicate outside the enum is
    rejected at construction time, so canonicalization never sees drift on `kind`."""
    with pytest.raises(ValidationError):
        Edge(
            kind="Requires ",  # not a valid EdgeKind value
            subject=DrugNode(canonical_id="A", surface_form="A"),
            object=DrugNode(canonical_id="B", surface_form="B"),
        )
