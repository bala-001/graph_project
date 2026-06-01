"""Downstream consumer policy for `extraction_complete` + orphaned-partial GC predicate (D12).

Per D12 downstream consumer policy:
- Downstream consumers (analyst tooling, client-facing outputs, batch reports)
  treat `extraction_complete=false` rows as INVISIBLE - equivalent to "this
  document hasn't been extracted yet."
- A background GC job sweeps `extraction_complete=false` rows older than 24 hours,
  considering them orphaned-from-crash, and re-queues them for re-extraction.

This module owns the IN-PROCESS policy: the visibility filter and the
orphaned-age PREDICATE. The actual GC scheduler / re-queue is a PAIQ
infrastructure-layer background job (see journal/replay.py) and is out of scope
for the in-process Phase-1 code.

T7 deliverable (in-process slice).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from ..d_extraction.schema import DocumentExtraction


GC_TTL_HOURS = 24


def is_visible(doc: DocumentExtraction) -> bool:
    """A document is visible to downstream consumers only when extraction completed."""
    return bool(doc.extraction_complete)


def filter_visible(docs: Iterable[DocumentExtraction]) -> list[DocumentExtraction]:
    """Drop `extraction_complete=false` rows - they are invisible downstream (D12)."""
    return [d for d in docs if is_visible(d)]


def _parse_iso(timestamp: str) -> datetime:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_orphaned(
    doc: DocumentExtraction,
    now: datetime | None = None,
    ttl_hours: int = GC_TTL_HOURS,
) -> bool:
    """True if `doc` is an orphaned partial: not complete AND older than ttl_hours.

    Completed documents are never orphaned. The age is measured from
    `extraction_started_at`. `now` is injectable for deterministic tests.
    """
    if doc.extraction_complete:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - _parse_iso(doc.extraction_started_at)) > timedelta(hours=ttl_hours)


def gc_candidates(
    docs: Iterable[DocumentExtraction],
    now: datetime | None = None,
    ttl_hours: int = GC_TTL_HOURS,
) -> list[DocumentExtraction]:
    """The orphaned partials a GC sweep would re-queue (the scheduler itself is infra)."""
    return [d for d in docs if is_orphaned(d, now=now, ttl_hours=ttl_hours)]
