"""Tests for the 4 guardrails detection scenarios.

- Circular dependency detection
- Contradictory limits detection (unsatisfiable numeric range)
- Prerequisite chain mismatch detection (requires vs excludes on same pair)
- Age conflict detection (conflicting exact age qualifiers)

T4 + T9 deliverables.
"""

from __future__ import annotations

from src.guardrails.detector import (
    Verdict,
    check,
    detect_circular_dependency,
    detect_contradictory_limits,
    detect_prerequisite_chain_mismatch,
    detect_age_conflict,
)
from src.guardrails.state import PartialEdgeState
from src.d_extraction.schema import Edge, EdgeKind, DrugNode


def _drug(cid):
    return DrugNode(canonical_id=cid, surface_form=cid)


def _edge(kind, subject, obj, qualifiers=None):
    return Edge(kind=kind, subject=_drug(subject), object=_drug(obj), qualifiers=qualifiers or {})


def test_detect_circular_dependency_fires_on_simple_cycle():
    """A requires B; B requires A -> REJECT_RETRY."""
    state = PartialEdgeState(document_id="d", edges=[_edge(EdgeKind.REQUIRES, "A", "B")])
    new = _edge(EdgeKind.REQUIRES, "B", "A")
    assert detect_circular_dependency(new, state) is True
    assert check(new, state) == Verdict.REJECT_RETRY


def test_detect_contradictory_limits_age_range_overlap():
    """Existing age_max=65 plus a new age_min=70 makes an empty range -> REJECT_RETRY."""
    state = PartialEdgeState(document_id="d", edges=[_edge(EdgeKind.REQUIRES, "A", "B", {"age_max": 65})])
    new = _edge(EdgeKind.REQUIRES, "A", "B", {"age_min": 70})
    assert detect_contradictory_limits(new, state) is True
    assert check(new, state) == Verdict.REJECT_RETRY


def test_detect_prerequisite_chain_mismatch_against_existing_edges():
    """New 'A excludes B' contradicts already-extracted 'A requires B' -> REJECT_RETRY."""
    state = PartialEdgeState(document_id="d", edges=[_edge(EdgeKind.REQUIRES, "A", "B")])
    new = _edge(EdgeKind.EXCLUDES, "A", "B")
    assert detect_prerequisite_chain_mismatch(new, state) is True
    assert check(new, state) == Verdict.REJECT_RETRY


def test_detect_age_conflict_against_existing_qualifier():
    """New exact age conflicts with an already-extracted exact age for same pair -> REJECT_RETRY."""
    state = PartialEdgeState(document_id="d", edges=[_edge(EdgeKind.REQUIRES, "A", "B", {"age_exact": 18})])
    new = _edge(EdgeKind.REQUIRES, "A", "B", {"age_exact": 21})
    assert detect_age_conflict(new, state) is True
    assert check(new, state) == Verdict.REJECT_RETRY
    # A non-conflicting edge on a fresh pair passes all four detectors.
    assert check(_edge(EdgeKind.REQUIRES, "A", "C"), state) == Verdict.ACCEPT


def _unresolved_edge(kind, subject_surface, object_surface):
    """Edge whose drug nodes have NO canonical id (the surface-form fallback path)."""
    return Edge(
        kind=kind,
        subject=DrugNode(canonical_id="", surface_form=subject_surface),
        object=DrugNode(canonical_id="", surface_form=object_surface),
    )


def test_circular_dependency_detected_for_unresolved_drugs():
    """Cycle detection must work when drugs are unresolved (canonical_id empty)."""
    state = PartialEdgeState(document_id="d", edges=[_unresolved_edge(EdgeKind.REQUIRES, "Aspirin", "Beta")])
    new = _unresolved_edge(EdgeKind.REQUIRES, "Beta", "Aspirin")
    assert detect_circular_dependency(new, state) is True
    assert check(new, state) == Verdict.REJECT_RETRY


def test_no_false_positive_across_distinct_unresolved_drugs():
    """Two DIFFERENT unresolved subjects must not collide on an empty-string key."""
    state = PartialEdgeState(document_id="d", edges=[_unresolved_edge(EdgeKind.REQUIRES, "Aspirin", "Beta")])
    # Different subject (Zantac) excluding the same object must NOT be a prereq mismatch.
    new = _unresolved_edge(EdgeKind.EXCLUDES, "Zantac", "Beta")
    assert detect_prerequisite_chain_mismatch(new, state) is False
    assert check(new, state) == Verdict.ACCEPT
