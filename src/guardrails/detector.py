"""Guardrails detector — 4 detection scenarios per CEO plan iter-4 + iter-5.

The four scenarios:
1. Circular dependency in prerequisite chains (A requires B; B requires A)
2. Contradictory limits on same drug-indication (age >= 5 AND age <= 65 emitted)
3. Prerequisite chain mismatch (new edge contradicts already-extracted chain)
4. Age conflict (new age qualifier contradicts already-extracted age qualifier)

T4 deliverable. STUB.
"""

from __future__ import annotations

from enum import Enum

from ..d_extraction.schema import Edge
from .state import PartialEdgeState


class Verdict(str, Enum):
    """Guardrails verdict per edge."""
    ACCEPT = "accept"
    REJECT_RETRY = "reject_retry"  # ask the LLM to try again with validator error in prompt


def check(edge: Edge, state: PartialEdgeState) -> Verdict:
    """Run all 4 detection scenarios. Return ACCEPT or REJECT_RETRY.

    Caller (retry.handle_verdict) decides what to do on REJECT_RETRY (retry,
    or exhaust → counter 3).

    Implementation order:
    1. detect_circular_dependency
    2. detect_contradictory_limits
    3. detect_prerequisite_chain_mismatch
    4. detect_age_conflict

    First detection that triggers returns REJECT_RETRY.
    """
    raise NotImplementedError("T4 deliverable")


def detect_circular_dependency(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if adding `edge` would create a cycle in the requires/excludes graph."""
    raise NotImplementedError("T4 deliverable")


def detect_contradictory_limits(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge` carries a qualifier that contradicts an existing edge
    on the same drug-indication (e.g., conflicting age ranges, dosage ranges)."""
    raise NotImplementedError("T4 deliverable")


def detect_prerequisite_chain_mismatch(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge` introduces a prerequisite chain that contradicts
    chains already in `state` (e.g., already-extracted Drug A requires Drug B; new
    edge says Drug A excludes Drug B)."""
    raise NotImplementedError("T4 deliverable")


def detect_age_conflict(edge: Edge, state: PartialEdgeState) -> bool:
    """Returns True if `edge` carries an age qualifier that conflicts with an
    already-extracted age qualifier for the same drug-indication pair."""
    raise NotImplementedError("T4 deliverable")
