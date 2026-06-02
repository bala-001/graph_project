"""Multi-call extraction protocol per eng-review D10, wired end-to-end.

PAIQ documents are big (multi-page PBM PDFs). Extraction runs chunk-by-chunk.
Guardrails fire AFTER each LLM call and BEFORE the next chunk's call commits.

ASCII (multi-call with between-call guardrails):

  for chunk_i in document.chunks:
    edges, fields = provider.extract_chunk(prompt, chunk_i)
    for edge in edges:
      verdict = guardrails.check(edge, state)
      if verdict == ACCEPT:        dedup; journal.append(edge); state.append(edge)
      else:                        retry up to MAX_RETRIES -> counter 1/2/3
  flush journal; write canonical DocumentExtraction with extraction_complete=true

Safety: the feature flag (config.d_enabled) is the D12 rollback path but it only
suppresses edges/guardrails - it does NOT stop the LLM call. The real barriers to
real-document use are the offline MockProvider default and the fail-closed
template-prompt guard below.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .provider import get_provider
from .prompts import get_prompt, DEFAULT_TEMPLATE_ID, are_prompts_templates
from .schema import DocumentExtraction, Edge, canonicalize_edge
from ..config import Config
from ..guardrails.detector import Verdict, check
from ..guardrails.retry import handle_verdict
from ..guardrails.state import PartialEdgeState
from ..journal.writer import JournalWriter
from ..telemetry.counters import PerDocumentCounters


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _guard_template_prompts(config: Config) -> None:
    """Fail closed: refuse a real LLM provider while prompts are still templates.

    The bundled prompts are NOT production-validated. Running a real provider on
    them would send real document text to a model under unvalidated instructions.
    Set PAIQ_ALLOW_TEMPLATE_PROMPTS=true to override (testing only).
    """
    if config.provider == "mock":
        return
    if not are_prompts_templates():
        return
    override = os.environ.get("PAIQ_ALLOW_TEMPLATE_PROMPTS", "").strip().lower() in {"1", "true", "yes"}
    if override:
        return
    raise RuntimeError(
        f"Refusing to run provider '{config.provider}' on the bundled TEMPLATE prompts "
        "(NOT production-validated). Replace src/d_extraction/prompts.py with the real "
        "prompts (Q3), or set PAIQ_ALLOW_TEMPLATE_PROMPTS=true to override for testing."
    )


def extract_document(
    document_id: str,
    chunks: Iterable[str],
    config: Config | None = None,
) -> DocumentExtraction:
    """Run the full multi-call extraction with guardrails between calls.

    Returns a finished DocumentExtraction (extraction_complete=True) with edges,
    existing fields, and the 3-counter FP telemetry. Edges are journaled as they
    are accepted (D2/D7); the canonical metadata is written on completion. On a
    mid-document failure, the journal is flushed and an extraction_complete=False
    record is written so downstream consumers / GC see a real (invisible) row.
    """
    config = config or Config.from_env()
    _guard_template_prompts(config)
    provider = get_provider(config)
    d_mode = config.d_enabled
    template = get_prompt(DEFAULT_TEMPLATE_ID, d_mode=d_mode)

    state = PartialEdgeState(document_id=document_id)
    counters = PerDocumentCounters(document_id=document_id)
    journal = JournalWriter(document_id=document_id, journal_dir=Path(config.journal_dir))
    existing_fields: dict = {}
    seen: set = set()  # canonical keys of already-accepted edges (dedup, D4 hygiene)

    try:
        for chunk in chunks:
            edges, fields = provider.extract_chunk(template, chunk)
            existing_fields.update(fields)
            if not d_mode:
                continue  # baseline rollback path: fields only, no edges/guardrails
            for edge in edges:
                _consult_guardrails(edge, state, counters, journal, provider, template, chunk, config, seen)
    except Exception:
        # Persist a partial, INVISIBLE record (extraction_complete=False) so the
        # 24h GC / re-queue policy acts on a real row, then re-raise.
        _write_doc(journal, config, document_id, state, counters, existing_fields, complete=False)
        raise

    return _write_doc(journal, config, document_id, state, counters, existing_fields, complete=True)


def _write_doc(journal, config, document_id, state, counters, existing_fields, complete: bool) -> DocumentExtraction:
    journal.flush()
    doc = DocumentExtraction(
        document_id=document_id,
        extraction_complete=complete,
        edges=list(state.edges),
        existing_fields=existing_fields,
        extraction_started_at=journal.extraction_started_at,
        extraction_completed_at=_utc_now_iso() if complete else None,
        journal_path=str(journal.journal_path),
        guardrails_counter_1_same_edge=counters.counter_1_same_edge,
        guardrails_counter_2_different_edge=counters.counter_2_different_edge,
        guardrails_counter_3_retry_exhausted=counters.counter_3_retry_exhausted,
    )
    Path(config.journal_dir).mkdir(parents=True, exist_ok=True)
    journal.document_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return doc


def _accept(edge, state, journal, seen) -> None:
    """Accept an edge, deduplicating by canonical form before journaling."""
    key = canonicalize_edge(edge)
    if key in seen:
        return  # exact duplicate already accepted; do not re-journal
    seen.add(key)
    state.append(edge)
    journal.append(edge)


def _consult_guardrails(edge, state, counters, journal, provider, template, chunk, config, seen) -> None:
    """Run guardrails on one emitted edge; accept / retry / exhaust per D4."""
    verdict = check(edge, state)
    if verdict == Verdict.ACCEPT:
        _accept(edge, state, journal, seen)
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
        _accept(outcome.accepted_edge, state, journal, seen)
    # else: retries exhausted -> analyst flag (counter 3); the edge is dropped.


def emit_edges_for_chunk(chunk: str, prior_state_edges: list[Edge]) -> list[Edge]:
    """Single chunk -> emit edges via the configured provider.

    Caller is responsible for guardrails consultation AFTER this returns. Honors
    the feature flag (returns no edges when D is disabled) so it cannot bypass the
    D12 rollback path.
    """
    config = Config.from_env()
    _guard_template_prompts(config)
    if not config.d_enabled:
        return []
    provider = get_provider(config)
    template = get_prompt(DEFAULT_TEMPLATE_ID, d_mode=True)
    edges, _fields = provider.extract_chunk(template, chunk)
    return edges
