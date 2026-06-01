"""Tests for the retry policy + 3-counter telemetry per D4 + D12 canonicalization.

- Rejected-then-same-edge increments counter 1 (real FP)
- Rejected-then-different-edge (passes re-check) increments counter 2 (TP)
- Rejected-then-retry-exhausted increments counter 3 (analyst flag)
- Edge canonicalization handles serialization drift correctly (D12)
- Retry threshold enforcement (exhaust fires exactly at MAX_RETRIES)

T4 + T9 deliverables.
"""

from __future__ import annotations

from src.guardrails.retry import handle_verdict, MAX_RETRIES
from src.guardrails.detector import Verdict
from src.guardrails.state import PartialEdgeState
from src.d_extraction.schema import Edge, EdgeKind, DrugNode


def _drug(cid):
    return DrugNode(canonical_id=cid, surface_form=cid)


def _edge(subject, obj, kind=EdgeKind.REQUIRES, qualifiers=None):
    return Edge(kind=kind, subject=_drug(subject), object=_drug(obj), qualifiers=qualifiers or {})


def test_rejected_then_same_edge_increments_counter_1():
    """Retry reproduces the canonically-identical edge -> counter 1 (real FP)."""
    state = PartialEdgeState(document_id="d")
    original = _edge("A", "B")
    outcome = handle_verdict(original, Verdict.REJECT_RETRY, state, lambda err: _edge("A", "B"))
    assert outcome.counter_1_delta == 1
    assert outcome.counter_2_delta == 0 and outcome.counter_3_delta == 0
    assert outcome.accepted_edge is not None


def test_rejected_then_different_edge_increments_counter_2():
    """Retry returns a different edge that now passes the check -> counter 2 (TP)."""
    state = PartialEdgeState(document_id="d")  # empty -> a fresh edge passes
    original = _edge("A", "B")
    outcome = handle_verdict(original, Verdict.REJECT_RETRY, state, lambda err: _edge("A", "C"))
    assert outcome.counter_2_delta == 1
    assert outcome.counter_1_delta == 0 and outcome.counter_3_delta == 0
    assert outcome.accepted_edge.object.canonical_id == "C"


def test_rejected_then_retry_exhausted_increments_counter_3():
    """Retries keep producing different-but-still-bad edges -> counter 3 (analyst flag)."""
    state = PartialEdgeState(document_id="d", edges=[_edge("A", "B", qualifiers={"age_min": 70})])
    original = _edge("A", "B", qualifiers={"age_max": 10})
    sequence = iter([
        _edge("A", "B", qualifiers={"age_max": 11}),
        _edge("A", "B", qualifiers={"age_max": 12}),
        _edge("A", "B", qualifiers={"age_max": 13}),
    ])
    outcome = handle_verdict(original, Verdict.REJECT_RETRY, state, lambda err: next(sequence))
    assert outcome.counter_3_delta == 1
    assert outcome.accepted_edge is None
    assert outcome.counter_1_delta == 0 and outcome.counter_2_delta == 0


def test_canonicalization_handles_serialization_drift_temperature_above_zero():
    """Surface-form drift on retry ('A' vs ' a ') still counts as the same edge -> counter 1."""
    state = PartialEdgeState(document_id="d")
    original = Edge(
        kind=EdgeKind.REQUIRES,
        subject=DrugNode(canonical_id="", surface_form="A"),
        object=DrugNode(canonical_id="", surface_form="B"),
    )
    drifted = Edge(
        kind=EdgeKind.REQUIRES,
        subject=DrugNode(canonical_id="", surface_form=" a "),
        object=DrugNode(canonical_id="", surface_form="B"),
    )
    outcome = handle_verdict(original, Verdict.REJECT_RETRY, state, lambda err: drifted)
    assert outcome.counter_1_delta == 1


def test_max_retries_threshold_enforced():
    """Exhaust fires at MAX_RETRIES, not before."""
    state = PartialEdgeState(document_id="d", edges=[_edge("A", "B", qualifiers={"age_min": 70})])
    original = _edge("A", "B", qualifiers={"age_max": 10})
    calls = {"n": 0}

    def retry(_err):
        calls["n"] += 1
        return _edge("A", "B", qualifiers={"age_max": 10 + calls["n"]})  # different + still bad

    outcome = handle_verdict(original, Verdict.REJECT_RETRY, state, retry)
    assert outcome.counter_3_delta == 1
    assert calls["n"] == MAX_RETRIES
