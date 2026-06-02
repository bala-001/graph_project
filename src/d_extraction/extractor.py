"""Multi-call extraction protocol per eng-review D10, wired end-to-end.

PAIQ documents are big (multi-page PBM PDFs). Extraction runs chunk-by-chunk.
Guardrails fire AFTER each LLM call and BEFORE the next chunk's call commits.

ASCII (multi-call with between-call guardrails):

  for chunk_i in document.chunks:
    edges, fields = provider.extract_chunk(prompt, chunk_i)
    for edge in edges:
      verdict = guardrails.check(edge, state)
      if verdict == ACCEPT:        journal.append(edge); state.append(edge)
      else:                        retry up to MAX_RETRIES -> counter 1/2/3
  flush journal; write canonical DocumentExtraction with extraction_complete=true

The feature flag (config.d_enabled / PAIQ_D_EXTRACTION_ENABLED) is the D12 rollback
path: when off, baseline field extraction runs and NO edges/guardrails execute.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .provider import get_provider
from .prompts import get_prompt, DEFAULT_TEMPLATE_ID
from .schema import DocumentExtraction, Edge
from ..config import Config
from ..guardrails.detector import Verdict, check
from ..guardrails.retry import handle_verdict
from ..guardrails.state import PartialEdgeState
from ..journal.writer import JournalWriter
from ..telemetry.counters import PerDocumentCounters


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_document(
    document_id: str,
    chunks: Iterable[str],
    config: Config | None = None,
) -> DocumentExtraction:
    """Run the full multi-call extraction with guardrails between calls.

    Returns a finished DocumentExtraction (extraction_complete=True) with edges,
    existing fields, and the 3-counter FP telemetry. Edges are journaled as they
    are accepted (D2/D7); the canonical metadata is written on completion.
    """
    config = config or Config.from_env()
    provider = get_provider(config)
    d_mode = config.d_enabled
    template = get_prompt(DEFAULT_TEMPLATE_ID, d_mode=d_mode)

    state = PartialEdgeState(document_id=document_id)
    counters = PerDocumentCounters(document_id=document_id)
    journal = JournalWriter(document_id=document_id, journal_dir=Path(config.journal_dir))
    existing_fields: dict = {}

    for chunk in chunks:
        edges, fields = provider.extract_chunk(template, chunk)
        existing_fields.update(fields)
        if not d_mode:
            # Baseline rollback path: field extraction only, no edges, no guardrails.
            continue
        for edge in edges:
            _consult_guardrails(edge, state, counters, journal, provider, template, chunk, config)

    journal.flush()  # durability before materialize (crash recovery via replay_journal)
    doc = DocumentExtraction(
        document_id=document_id,
        extraction_complete=True,
        edges=list(state.edges),
        existing_fields=existing_fields,
        extraction_started_at=journal.extraction_started_at,
        extraction_completed_at=_utc_now_iso(),
        journal_path=str(journal.journal_path),
        guardrails_counter_1_same_edge=counters.counter_1_same_edge,
        guardrails_counter_2_different_edge=counters.counter_2_different_edge,
        guardrails_counter_3_retry_exhausted=counters.counter_3_retry_exhausted,
    )
    Path(config.journal_dir).mkdir(parents=True, exist_ok=True)
    journal.document_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return doc


def _consult_guardrails(edge, state, counters, journal, provider, template, chunk, config) -> None:
    """Run guardrails on one emitted edge; accept / retry / exhaust per D4."""
    verdict = check(edge, state)
    if verdict == Verdict.ACCEPT:
        state.append(edge)
        journal.append(edge)
        return

    outcome = handle_verdict(
        edge,
        verdict,
        state,
        retry_llm_call=lambda err: provider.retry_chunk(template, chunk, edge, err),
        max_retries=config.max_retries,
    )
    counters.counter_1_same_edge += outcome.counter_1_delta
    counters.counter_2_different_edge += outcome.counter_2_delta
    counters.counter_3_retry_exhausted += outcome.counter_3_delta
    state.counter_1_same_edge += outcome.counter_1_delta
    state.counter_2_different_edge += outcome.counter_2_delta
    state.counter_3_retry_exhausted += outcome.counter_3_delta
    if outcome.accepted_edge is not None:
        state.append(outcome.accepted_edge)
        journal.append(outcome.accepted_edge)
    # else: retries exhausted -> analyst flag (counter 3); the edge is dropped.


def emit_edges_for_chunk(chunk: str, prior_state_edges: list[Edge]) -> list[Edge]:
    """Single chunk -> emit edges via the configured provider.

    Caller is responsible for guardrails consultation AFTER this returns. Uses
    the D-mode prompt template and the env-configured provider.
    """
    config = Config.from_env()
    provider = get_provider(config)
    template = get_prompt(DEFAULT_TEMPLATE_ID, d_mode=True)
    edges, _fields = provider.extract_chunk(template, chunk)
    return edges
