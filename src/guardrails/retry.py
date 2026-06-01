"""Retry policy + 3-counter FP telemetry per D4 + D12 canonicalization.

When guardrails reject an edge, the caller asks the LLM to retry with the
validator error attached. Three outcomes:

1. Retry returns the SAME canonicalized edge → counter 1 (real FP — guardrail was wrong)
2. Retry returns a DIFFERENT canonicalized edge → counter 2 (TP — guardrail caught something)
3. Retry-exhaust after N retries → counter 3 (analyst flag)

The 1-15% bound on counter (1) / total is the Week-6 Kill Criteria gate.

T4 deliverable. STUB.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..d_extraction.schema import Edge
from .detector import Verdict
from .state import PartialEdgeState


MAX_RETRIES = 3  # Q8 in CEO plan iter-4 Open Questions: confirm during design phase


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
    """Apply retry policy on a REJECT_RETRY verdict.

    Returns RetryOutcome with the accepted edge (or None on exhaust) and counter deltas.
    Caller is responsible for applying the deltas to `state` and persisting via the journal.

    STUB — T4 deliverable.
    """
    raise NotImplementedError("T4 deliverable")
