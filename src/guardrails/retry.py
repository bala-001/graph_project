"""Retry policy + 3-counter FP telemetry per D4 + D12 canonicalization.

When guardrails reject an edge, the caller asks the LLM to retry with the
validator error attached. Three mutually-exclusive outcomes per rejected edge
(so counter (1) / total is a clean FP rate for the Week-6 Kill Criteria gate):

1. Retry returns the SAME canonicalized edge -> counter 1 (real FP; the model
   insists, so the guardrail was likely wrong). Accept the edge.
2. Retry returns a DIFFERENT canonicalized edge that passes the check -> counter 2
   (TP; the guardrail caught something and the model corrected it). Accept it.
3. Retries exhausted after MAX_RETRIES without converging on an acceptable edge ->
   counter 3 (analyst flag). Accept nothing.

The 1-15% bound on counter (1) / total is the Week-6 Kill Criteria gate.

T4 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..d_extraction.schema import Edge, canonicalize_edge
from .detector import Verdict, check
from .state import PartialEdgeState


MAX_RETRIES = 3  # Q8 in CEO plan iter-4 Open Questions: confirm during design phase

_VALIDATOR_ERROR = (
    "guardrail rejected edge: it is logically inconsistent with already-extracted "
    "edges for this document. Re-extract this relationship or omit it."
)


@dataclass
class RetryOutcome:
    """Result of handling one rejected edge through the retry policy."""
    accepted_edge: Edge | None  # None if exhausted
    counter_1_delta: int = 0
    counter_2_delta: int = 0
    counter_3_delta: int = 0


def handle_verdict(
    original_edge: Edge,
    verdict: Verdict,
    state: PartialEdgeState,
    retry_llm_call,  # callable: (validator_error: str) -> Edge
) -> RetryOutcome:
    """Apply the retry policy on a REJECT_RETRY verdict.

    Returns RetryOutcome with the accepted edge (or None on exhaust) and the
    counter deltas. Caller applies the deltas to `state` and persists via the
    journal.
    """
    if verdict == Verdict.ACCEPT:
        return RetryOutcome(accepted_edge=original_edge)

    prev_key = canonicalize_edge(original_edge)
    for _attempt in range(1, MAX_RETRIES + 1):
        new_edge = retry_llm_call(_VALIDATOR_ERROR)
        new_key = canonicalize_edge(new_edge)
        if new_key == prev_key:
            # Model reproduced the same edge -> real false positive (counter 1).
            return RetryOutcome(accepted_edge=new_edge, counter_1_delta=1)
        if check(new_edge, state) == Verdict.ACCEPT:
            # Model produced a different edge that now passes -> true positive (counter 2).
            return RetryOutcome(accepted_edge=new_edge, counter_2_delta=1)
        # Different edge but still inconsistent -> chase it and keep retrying.
        prev_key = new_key

    # Retries exhausted without converging -> analyst flag (counter 3).
    return RetryOutcome(accepted_edge=None, counter_3_delta=1)
