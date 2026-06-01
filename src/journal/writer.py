"""Batched-write journal writer per D7.

ASCII diagram (write path):

  emit edge --> in-memory buffer --+
                                   |
              +--------------------+
              v
  +--------------------------------------+
  | trigger flush IF:                    |
  |   - len(buffer) >= BATCH_SIZE        |
  |   - OR time_since_last_flush >=      |
  |       BATCH_TIMEOUT_SECONDS          |
  +--------------------------------------+
              |
              v
  append batch to journal file (one JSON line per edge)
              |
              v
  on extraction_complete:
    - final flush
    - collapse journal into canonical in-document JSON metadata
    - set extraction_complete=true

T5 deliverable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..d_extraction.schema import DocumentExtraction, Edge


BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 5.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class JournalWriter:
    """Per-document batched-write journal writer.

    One JournalWriter per document extraction. The journal file path is
    `{journal_dir}/{document_id}.journal`; the materialized canonical metadata
    is `{journal_dir}/{document_id}.json`.
    """
    document_id: str
    journal_dir: Path
    extraction_started_at: str = field(default_factory=_utc_now_iso)
    _buffer: list[Edge] = field(default_factory=list)
    _last_flush_time: float = field(default_factory=time.time)

    @property
    def journal_path(self) -> Path:
        return Path(self.journal_dir) / f"{self.document_id}.journal"

    @property
    def document_path(self) -> Path:
        return Path(self.journal_dir) / f"{self.document_id}.json"

    def append(self, edge: Edge) -> None:
        """Append an edge to the buffer. Flushes if BATCH_SIZE or timeout hit."""
        self._buffer.append(edge)
        if self._should_flush():
            self.flush()

    def flush(self) -> None:
        """Write the buffer to the journal file. Idempotent if buffer is empty."""
        if not self._buffer:
            return
        Path(self.journal_dir).mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as fh:
            for edge in self._buffer:
                fh.write(edge.model_dump_json() + "\n")
        self._buffer.clear()
        self._last_flush_time = time.time()

    def materialize_complete(self) -> Path:
        """Final flush + collapse the journal into canonical JSON metadata.

        Sets extraction_complete=true. Returns the path to the materialized
        DocumentExtraction file. Until this runs, no `{document_id}.json` exists,
        so downstream consumers (which key on extraction_complete) see nothing.
        """
        # Import here to avoid a writer<->replay import cycle at module load.
        from .replay import replay_journal

        self.flush()
        edges = replay_journal(self.journal_path)
        doc = DocumentExtraction(
            document_id=self.document_id,
            extraction_complete=True,
            edges=edges,
            extraction_started_at=self.extraction_started_at,
            extraction_completed_at=_utc_now_iso(),
            journal_path=str(self.journal_path),
        )
        Path(self.journal_dir).mkdir(parents=True, exist_ok=True)
        self.document_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        return self.document_path

    def _should_flush(self) -> bool:
        if len(self._buffer) >= BATCH_SIZE:
            return True
        return (time.time() - self._last_flush_time) >= BATCH_TIMEOUT_SECONDS
