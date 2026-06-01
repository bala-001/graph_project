"""Batched-write journal for partial-edge state per D2 + D7.

Per D7: buffer flushed to journal every 10 edges OR every 5 seconds, whichever first.
Cuts storage writes by 10-100x vs naive per-edge persistence while preserving D2
crash-recovery semantics.

Per D12 downstream policy: orphaned `extraction_complete=false` rows older than
24 hours get garbage-collected and re-queued for extraction.
"""

from .writer import JournalWriter, BATCH_SIZE, BATCH_TIMEOUT_SECONDS
from .replay import replay_journal

__all__ = ["JournalWriter", "BATCH_SIZE", "BATCH_TIMEOUT_SECONDS", "replay_journal"]
