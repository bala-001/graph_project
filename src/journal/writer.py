"""Batched-write journal writer per D7.

ASCII diagram (write path):

  emit edge ──▶ in-memory buffer ──┐
                                   │
              ┌────────────────────┘
              ▼
  ┌──────────────────────────────────────┐
  │ trigger flush IF:                    │
  │   - len(buffer) >= BATCH_SIZE        │
  │   - OR time_since_last_flush >=      │
  │       BATCH_TIMEOUT_SECONDS          │
  └──────────────────────────────────────┘
              │
              ▼
  append batch to journal file (one JSON line per edge)
              │
              ▼
  on extraction_complete:
    - final flush
    - collapse journal into canonical in-document JSON metadata
    - set extraction_complete=true

T5 deliverable. STUB.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..d_extraction.schema import Edge


BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 5.0


@dataclass
class JournalWriter:
    """Per-document batched-write journal writer.

    One JournalWriter per document extraction. Journal file path is
    `{journal_dir}/{document_id}.journal`.
    """
    document_id: str
    journal_dir: Path
    _buffer: list[Edge] = field(default_factory=list)
    _last_flush_time: float = field(default_factory=time.time)

    def append(self, edge: Edge) -> None:
        """Append an edge to the buffer. Flushes if BATCH_SIZE or timeout hit."""
        self._buffer.append(edge)
        if self._should_flush():
            self.flush()

    def flush(self) -> None:
        """Write the buffer to the journal file. Idempotent if buffer is empty."""
        raise NotImplementedError("T5 deliverable")

    def materialize_complete(self) -> Path:
        """Final flush + collapse the journal into canonical JSON metadata.

        Sets extraction_complete=true. Returns the path to the materialized
        DocumentExtraction file.
        """
        raise NotImplementedError("T5 deliverable")

    def _should_flush(self) -> bool:
        if len(self._buffer) >= BATCH_SIZE:
            return True
        return (time.time() - self._last_flush_time) >= BATCH_TIMEOUT_SECONDS
