"""Multi-call extraction protocol per eng-review D10.

PAIQ documents are big (multi-page PBM PDFs). Extraction runs chunk-by-chunk.
Guardrails fire AFTER each LLM call and BEFORE the next chunk's call commits.

ASCII diagram (multi-call with between-call guardrails):

  for chunk_i in document.chunks:
    edges, fields = LLM_call(chunk_i, schema)
    for edge in edges:
      verdict = guardrails.check(edge, journal.partial_state())
      if verdict == ACCEPT:
        journal.append(edge)
      elif verdict == RETRY:
        edge2, fields = LLM_call(chunk_i, schema, with_validator_error)
        # ... up to MAX_RETRIES; then EXHAUST → analyst flag

This file is a STUB. T1, T2, T4, T10 land the real implementation.
"""

from __future__ import annotations

from typing import Iterator

from .schema import DocumentExtraction, Edge


MAX_CHUNK_RETRIES = 3  # Q8 in CEO plan iter-4 Open Questions: confirm during design phase


def extract_document(document_id: str, chunks: Iterator[str]) -> DocumentExtraction:
    """Run the full multi-call extraction with guardrails between calls.

    Stub. Real implementation depends on:
    - T1 (Pydantic edge schema wired to provider built-in structured outputs)
    - T2 (persist-as-you-go state model with extraction_complete flag)
    - T4 (guardrails component)
    - T5 (batched-write journal)
    - T6 (feature flag for prompt-mode swap)
    """
    raise NotImplementedError(
        "extract_document is a stub. See docs/architecture/d-integration-spec.md "
        "and Implementation Tasks T1, T2, T4, T5, T6 in the eng-review JSONL."
    )


def emit_edges_for_chunk(chunk: str, prior_state_edges: list[Edge]) -> list[Edge]:
    """Single chunk → emit edges via provider structured output.

    Caller is responsible for guardrails consultation AFTER this returns.
    """
    raise NotImplementedError("T1 deliverable")
