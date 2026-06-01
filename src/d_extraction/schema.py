"""Pydantic edge schema + DocumentExtraction per docs/architecture/data-model.md.

This schema is the contract between:
- D's modified extraction prompts (emit conforming JSON via provider built-in
  structured output mode)
- The guardrails component (consume edges; check consistency)
- The journal layer (persist edges as they're emitted)
- The shadow harness (compare D output to baseline + ground truth)

Per D1: provider built-ins enforce SHAPE, not SEMANTICS. Semantic correctness
is defended by the eval suite + guardrails, NOT by this schema.

T1 deliverable. STUB — real type definitions land via Implementation Task T1.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field


class EdgeKind(str, Enum):
    """The five edge predicates D extracts. Enum-constrained for canonicalization."""
    REQUIRES = "requires"
    EXCLUDES = "excludes"
    APPLIES_TO = "applies_to"
    OVERRIDES = "overrides"
    EFFECTIVE_FROM = "effective_from"


class DrugNode(BaseModel):
    """Canonical drug identifier. Resolved via PAIQ's drug dictionary."""
    canonical_id: str = Field(
        ...,
        description="PAIQ canonical drug ID; fallback to lowercased stripped surface form if unresolved.",
    )
    surface_form: str = Field(..., description="As extracted from the document text.")


class IndicationNode(BaseModel):
    """Disease / condition / treatment context."""
    canonical_id: Optional[str] = None
    surface_form: str


class Edge(BaseModel):
    """A single edge emitted by D.

    Canonicalized before FP-counter comparison per D12 + docs/architecture/data-model.md.
    """
    kind: EdgeKind
    subject: DrugNode
    object: Union[DrugNode, IndicationNode, str]
    qualifiers: dict = Field(
        default_factory=dict,
        description="age_min / age_max / dosage_min / dosage_max / etc.",
    )
    source_page: Optional[int] = None
    source_chunk_id: Optional[str] = None
    model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class DocumentExtraction(BaseModel):
    """Document-level extraction payload. Persisted via the journal."""
    document_id: str
    extraction_complete: bool = False
    edges: list[Edge] = Field(default_factory=list)
    existing_fields: dict = Field(
        default_factory=dict,
        description="Baseline outputs preserved: drug_name, age_limit, dates, etc.",
    )
    extraction_started_at: str  # ISO 8601
    extraction_completed_at: Optional[str] = None
    journal_path: Optional[str] = None
    # Per-document FP-counter telemetry (D4)
    guardrails_counter_1_same_edge: int = 0
    guardrails_counter_2_different_edge: int = 0
    guardrails_counter_3_retry_exhausted: int = 0


_TRAILING_PUNCT = ".,;:!?"


def _norm_text(value: str) -> str:
    """Lowercase, strip whitespace, strip trailing punctuation."""
    return value.strip().lower().rstrip(_TRAILING_PUNCT).strip()


def _canon_node(node) -> tuple:
    """Canonical key for a subject or object node.

    Uses the canonical drug/indication ID when resolved; falls back to the
    normalized surface form when the ID is empty (the unresolved case per
    docs/architecture/data-model.md). Bare-string objects normalize directly.
    """
    if isinstance(node, DrugNode):
        cid = (node.canonical_id or "").strip()
        return ("drug", cid.lower() if cid else _norm_text(node.surface_form))
    if isinstance(node, IndicationNode):
        cid = (node.canonical_id or "").strip()
        return ("indication", cid.lower() if cid else _norm_text(node.surface_form))
    return ("literal", _norm_text(str(node)))


def _canon_value(value):
    """Canonical, type-tagged qualifier value.

    Numbers and numeric-looking strings collapse to ("num", float) so provider
    serialization drift (18 vs "18") does not split the same logical edge.
    Booleans are tagged separately from ints so True and 1 do not collide.
    Other strings normalize via _norm_text.
    """
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return ("num", float(stripped))
        except ValueError:
            return ("text", _norm_text(value))
    return ("other", value)


def _canon_qualifiers(qualifiers: dict) -> tuple:
    """Sorted, type-normalized qualifier (key, value) pairs.

    Keys are case-folded and sorted; values are canonicalized via _canon_value so
    numeric drift and bool/int aliasing do not under-count the same-edge FP counter.
    """
    return tuple((str(key).strip().lower(), _canon_value(qualifiers[key])) for key in sorted(qualifiers))


def canonicalize_edge(edge: Edge) -> tuple:
    """Canonicalize an edge to a comparable, hashable tuple per D12.

    Two edges with the same canonical tuple are the "same edge" for FP-counter (1).

    Rules:
    1. Drug/indication node canonical IDs (fallback to normalized surface form
       when the canonical ID is unresolved).
    2. Predicate normalization (enum-constrained, so already canonical).
    3. Qualifier dict sorted by key; string values normalized.
    4. Tuple ordering reserved for future order-agnostic predicates; the current
       five predicates are directional, so (subject, object) order is preserved.
    """
    return (
        edge.kind.value,
        _canon_node(edge.subject),
        _canon_node(edge.object),
        _canon_qualifiers(edge.qualifiers),
    )
