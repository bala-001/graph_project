"""Guardrails detector - 4 detection scenarios per CEO plan iter-4 + iter-5.

The four scenarios:
1. Circular dependency in prerequisite chains (A requires B; B requires A)
2. Contradictory limits on same drug-indication (numeric ranges that cannot be
   simultaneously satisfied, e.g. an effective lower bound above the upper bound)
3. Prerequisite chain mismatch (new edge contradicts an already-extracted edge on
   the same pair, e.g. requires vs excludes)
4. Age conflict (new exact age qualifier contradicts an already-extracted exact age
   qualifier for the same drug-indication)

ASCII (detection order; first hit short-circuits to REJECT_RETRY):

    edge --> circular? --> prereq mismatch? --> contradictory limits? --> age conflict?
               |                |                      |                       |
               +----------------+----------------------+-----------------------+--> REJECT_RETRY
                                            (none) --> ACCEPT

T4 deliverable.
"""

from __future__ import annotations

from enum import Enum

from ..d_extraction.schema import Edge, EdgeKind
from .state import PartialEdgeState, object_canonical_id


class Verdict(str, Enum):
    """Guardrails verdict per edge."""
    ACCEPT = "accept"
    REJECT_RETRY = "reject_retry"  # ask the LLM to try again with validator error in prompt


# Numeric range qualifier pairs checked for unsatisfiable (empty) combined ranges.
_RANGE_PAIRS = (
    ("age_min", "age_max"),
    ("dosage_min", "dosage_max"),
    ("quantity_min", "quantity_max"),
)


def check(edge: Edge, state: PartialEdgeState) -> Verdict:
    """Run all 4 detection scenarios. Return ACCEPT or REJECT_RETRY.

    Caller (retry.handle_verdict) decides what to do on REJECT_RETRY (retry,
    or exhaust -> counter 3). First detection that triggers returns REJECT_RETRY.
    """
    if (
        detect_circular_dependency(edge, state)
        or detect_prerequisite_chain_mismatch(edge, state)
        or detect_contradictory_limits(edge, state)
        or detect_age_conflict(edge, state)
    ):
        return Verdict.REJECT_RETRY
    return Verdict.ACCEPT


def detect_circular_dependency(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if adding `edge` would create a cycle in the requires graph."""
    if edge.kind != EdgeKind.REQUIRES:
        return False
    start = object_canonical_id(edge.object)  # B, in "A requires B"
    target = edge.subject.canonical_id  # A
    # Adjacency over already-extracted REQUIRES edges.
    adjacency: dict[str, list[str]] = {}
    for e in state.edges:
        if e.kind == EdgeKind.REQUIRES:
            adjacency.setdefault(e.subject.canonical_id, []).append(object_canonical_id(e.object))
    # Is there an existing requires-path from B back to A? If so, A->B closes a cycle.
    seen: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency.get(node, []))
    return False


def detect_contradictory_limits(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge`'s numeric range qualifiers cannot be satisfied together
    with those on existing edges for the same (subject, object) pair.

    Contradiction = greatest lower bound exceeds least upper bound for any range
    qualifier (age / dosage / quantity).
    """
    related = state.edges_between(edge.subject.canonical_id, object_canonical_id(edge.object))
    population = related + [edge]
    for min_key, max_key in _RANGE_PAIRS:
        mins = [e.qualifiers[min_key] for e in population if e.qualifiers.get(min_key) is not None]
        maxs = [e.qualifiers[max_key] for e in population if e.qualifiers.get(max_key) is not None]
        if mins and maxs and max(mins) > min(maxs):
            return True
    return False


def detect_prerequisite_chain_mismatch(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge` introduces a prerequisite relationship that contradicts
    an already-extracted one on the same pair (requires vs excludes)."""
    if edge.kind not in (EdgeKind.REQUIRES, EdgeKind.EXCLUDES):
        return False
    opposite = EdgeKind.EXCLUDES if edge.kind == EdgeKind.REQUIRES else EdgeKind.REQUIRES
    for e in state.edges_between(edge.subject.canonical_id, object_canonical_id(edge.object)):
        if e.kind == opposite:
            return True
    return False


def detect_age_conflict(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge` carries an exact age qualifier that conflicts with an
    already-extracted exact age qualifier for the same drug-indication pair."""
    new_exact = edge.qualifiers.get("age_exact")
    if new_exact is None:
        return False
    for e in state.edges_between(edge.subject.canonical_id, object_canonical_id(edge.object)):
        existing_exact = e.qualifiers.get("age_exact")
        if existing_exact is not None and existing_exact != new_exact:
            return True
    return False
