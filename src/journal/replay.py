"""Crash-recovery replay per D2.

If extraction crashes mid-document, the journal file holds the edges emitted so
far. On the next pipeline run, the journal can be replayed to recover state.

Per D12 downstream policy: `extraction_complete=false` rows older than 24 hours
get GC'd and re-queued (preferred over journal replay, which assumes the LLM
will reproduce the same outputs on re-extraction; with temperature > 0 it won't).

GC policy is implemented in the background-job system at the PAIQ infrastructure
layer, not in this module. This module covers in-process replay only for the
case where a worker restarts within a document's extraction.

T5 deliverable.
"""

from __future__ import annotations

from pathlib import Path

from ..d_extraction.schema import Edge


def replay_journal(journal_path: Path) -> list[Edge]:
    """Read a journal file and return the edges emitted before the crash.

    One JSON object per line (as written by JournalWriter.flush). Missing file or
    blank lines yield an empty / shorter list. Caller uses these to reconstruct
    PartialEdgeState before continuing extraction from the next chunk.
    """
    journal_path = Path(journal_path)
    if not journal_path.exists():
        return []
    edges: list[Edge] = []
    for line in journal_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        edges.append(Edge.model_validate_json(line))
    return edges
