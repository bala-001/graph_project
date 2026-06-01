"""Tests for the batched-write journal per D7 + D2.

Covers ~4 of the 23 edge-focused tests from the coverage diagram:
- Buffer flushes at BATCH_SIZE
- Buffer flushes at BATCH_TIMEOUT_SECONDS
- Crash mid-extraction leaves extraction_complete=false
- Journal replay reconstructs partial state correctly

T5 + T7 + T9 deliverables. All stubs.
"""

from __future__ import annotations

import pytest

from src.journal import JournalWriter, BATCH_SIZE, BATCH_TIMEOUT_SECONDS, replay_journal


def test_journal_flushes_at_batch_size(tmp_path):
    """Appending BATCH_SIZE edges triggers a flush."""
    pytest.skip("T5 deliverable")


def test_journal_flushes_at_timeout(tmp_path):
    """Buffer with fewer than BATCH_SIZE edges flushes after BATCH_TIMEOUT_SECONDS."""
    pytest.skip("T5 deliverable")


def test_crash_mid_extraction_leaves_extraction_complete_false(tmp_path):
    """If extraction crashes before materialize_complete, extraction_complete stays false."""
    pytest.skip("T5 + T7 deliverable")


def test_journal_replay_reconstructs_partial_state(tmp_path):
    """replay_journal reads the journal file and returns the edges that were emitted."""
    pytest.skip("T5 deliverable")
