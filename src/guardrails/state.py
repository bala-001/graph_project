"""Partial-edge state per D2 (persist-as-you-go).

State is loaded from the journal during multi-call extraction and consulted
by guardrails between LLM calls.

T2 + T5 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..d_extraction.schema import Edge


def object_canonical_id(obj) -> str:
    """Resolve a comparable id for an edge object (DrugNode / IndicationNode / str).

    Mirrors the canonical-id-with-surface-form-fallback rule used by
    `schema.canonicalize_edge`, so detectors can group edges by (subject, object)
    pair consistently.
    """
    cid = getattr(obj, "canonical_id", None)
    if cid:
        return cid
    surface = getattr(obj, "surface_form", None)
    if surface is not None:
        return surface.strip().lower()
    return str(obj).strip().lower()


@dataclass
class PartialEdgeState:
    """Accumulated edges for a single document during in-flight extraction.

    Loaded from the journal (T5). Mutated by extraction emissions.
    Consulted by guardrails (T4) BEFORE the next chunk's LLM call.

    The `extraction_complete` flag on the DocumentExtraction is the
    persistence-layer signal; this in-memory state is the active per-document
    accumulator during extraction.
    """
    document_id: str
    edges: list[Edge] = field(default_factory=list)
    # Per-document FP-counter state (D4):
    counter_1_same_edge: int = 0
    counter_2_different_edge: int = 0
    counter_3_retry_exhausted: int = 0

    def append(self, edge: Edge) -> None:
        """Add an edge to the partial state. Caller must canonicalize first if comparing."""
        self.edges.append(edge)

    def edges_about(self, subject_canonical_id: str) -> list[Edge]:
        """All edges where the given drug is the subject. Used by detector scenarios."""
        return [e for e in self.edges if e.subject.canonical_id == subject_canonical_id]

    def edges_between(self, subject_canonical_id: str, object_canonical_id_value: str) -> list[Edge]:
        """All edges from a subject to a specific object (by canonical id).

        Used by the contradiction / prerequisite-mismatch detectors, which reason
        about a single (subject, object) pair at a time.
        """
        return [
            e
            for e in self.edges
            if e.subject.canonical_id == subject_canonical_id
            and object_canonical_id(e.object) == object_canonical_id_value
        ]
