"""Tests for the batched-write journal per D7 + D2.

Covers:
- Buffer flushes at BATCH_SIZE
- Buffer flushes at BATCH_TIMEOUT_SECONDS
- Crash mid-extraction leaves extraction_complete=false (no materialized doc);
  materialize_complete flips it to true
- Journal replay reconstructs partial state correctly

T5 + T7 + T9 deliverables.
"""

from __future__ import annotations

import json

from src.journal import JournalWriter, BATCH_SIZE, BATCH_TIMEOUT_SECONDS, replay_journal
from src.d_extraction.schema import DocumentExtraction, Edge, EdgeKind, DrugNode


def _edge(i: int) -> Edge:
    return Edge(
        kind=EdgeKind.REQUIRES,
        subject=DrugNode(canonical_id=f"DRUG_{i}", surface_form=f"Drug {i}"),
        object=DrugNode(canonical_id=f"DRUG_{i}_B", surface_form=f"Drug {i} B"),
        qualifiers={},
        source_page=1,
        source_chunk_id=f"chunk-{i}",
    )


def test_journal_flushes_at_batch_size(tmp_path):
    """Appending BATCH_SIZE edges triggers a flush."""
    writer = JournalWriter(document_id="doc-batch", journal_dir=tmp_path)
    for i in range(BATCH_SIZE):
        writer.append(_edge(i))
    assert writer._buffer == []  # flushed at the BATCH_SIZE-th append
    assert writer.journal_path.exists()
    assert len(replay_journal(writer.journal_path)) == BATCH_SIZE


def test_journal_flushes_at_timeout(tmp_path):
    """Buffer with fewer than BATCH_SIZE edges flushes once the timeout elapses."""
    writer = JournalWriter(document_id="doc-timeout", journal_dir=tmp_path)
    writer.append(_edge(0))
    writer.append(_edge(1))
    assert len(writer._buffer) == 2  # below batch size, not yet flushed
    # Simulate the flush interval elapsing.
    writer._last_flush_time -= (BATCH_TIMEOUT_SECONDS + 1)
    writer.append(_edge(2))
    assert writer._buffer == []
    assert len(replay_journal(writer.journal_path)) == 3


def test_crash_mid_extraction_leaves_extraction_complete_false(tmp_path):
    """A crash before materialize_complete leaves no canonical doc (invisible downstream);
    materialize_complete flips extraction_complete to true."""
    writer = JournalWriter(document_id="doc-crash", journal_dir=tmp_path)
    writer.append(_edge(0))
    writer.append(_edge(1))
    writer.flush()
    # Crash: materialize_complete never ran.
    assert not writer.document_path.exists()
    assert DocumentExtraction(
        document_id="doc-crash", extraction_started_at="2026-05-26T00:00:00Z"
    ).extraction_complete is False
    # Partial edges are still recoverable from the journal.
    assert len(replay_journal(writer.journal_path)) == 2
    # Completing the document flips the flag and materializes the canonical doc.
    path = writer.materialize_complete()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["extraction_complete"] is True
    assert len(data["edges"]) == 2


def test_journal_replay_reconstructs_partial_state(tmp_path):
    """replay_journal reads the journal file and returns the edges that were emitted."""
    writer = JournalWriter(document_id="doc-replay", journal_dir=tmp_path)
    edges = [_edge(0), _edge(1), _edge(2)]
    for edge in edges:
        writer.append(edge)
    writer.flush()
    recovered = replay_journal(writer.journal_path)
    assert [e.subject.canonical_id for e in recovered] == [e.subject.canonical_id for e in edges]
    assert recovered[0].kind == EdgeKind.REQUIRES
