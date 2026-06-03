"""Tests for the downstream consumer policy + orphaned-partial GC predicate (T7, D12).

In-process slice only: the visibility filter and the orphaned-age predicate. The
24h GC scheduler / re-queue itself is a PAIQ infrastructure-layer background job
and is out of scope for the in-process Phase-1 code.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.journal.downstream import is_visible, filter_visible, is_orphaned, gc_candidates
from src.d_extraction.schema import DocumentExtraction


NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _doc(doc_id: str, complete: bool, started: datetime) -> DocumentExtraction:
    return DocumentExtraction(
        document_id=doc_id,
        extraction_complete=complete,
        extraction_started_at=_iso(started),
    )


def test_complete_doc_is_visible():
    assert is_visible(_doc("a", True, NOW)) is True


def test_incomplete_doc_is_invisible():
    assert is_visible(_doc("b", False, NOW)) is False


def test_filter_visible_drops_incomplete():
    docs = [_doc("a", True, NOW), _doc("b", False, NOW)]
    assert [d.document_id for d in filter_visible(docs)] == ["a"]


def test_old_incomplete_doc_is_orphaned():
    old = _doc("c", False, NOW - timedelta(hours=25))
    assert is_orphaned(old, now=NOW) is True


def test_recent_incomplete_doc_is_not_orphaned():
    recent = _doc("d", False, NOW - timedelta(hours=1))
    assert is_orphaned(recent, now=NOW) is False


def test_complete_doc_never_orphaned_even_if_old():
    old_complete = _doc("e", True, NOW - timedelta(hours=100))
    assert is_orphaned(old_complete, now=NOW) is False


def test_gc_candidates_selects_only_old_partials():
    docs = [
        _doc("c", False, NOW - timedelta(hours=25)),  # orphaned
        _doc("d", False, NOW - timedelta(hours=1)),   # too recent
        _doc("e", True, NOW - timedelta(hours=100)),  # complete
    ]
    assert [d.document_id for d in gc_candidates(docs, now=NOW)] == ["c"]
