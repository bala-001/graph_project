"""3-counter FP rate telemetry implementation per D4.

Counter (1): rejected-then-same-edge AFTER canonicalization = real FP
Counter (2): rejected-then-different-edge = TP (guardrail caught something)
Counter (3): rejected-then-retry-exhausted = analyst flag

Per D12 canonicalization: same-edge comparison happens on canonicalized form
(canonical drug IDs, sorted qualifier dict, normalized predicate). Without
canonicalization, temperature > 0 produces serialization drift that under-counts
true FPs.

T4 + T13 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerDocumentCounters:
    """Per-document counter snapshot. Aggregated to per-day rolling in the dashboard."""
    document_id: str
    counter_1_same_edge: int = 0
    counter_2_different_edge: int = 0
    counter_3_retry_exhausted: int = 0

    @property
    def total(self) -> int:
        return (
            self.counter_1_same_edge
            + self.counter_2_different_edge
            + self.counter_3_retry_exhausted
        )

    @property
    def fp_rate(self) -> float:
        """FP rate per D4 definition: counter_1 / total.

        Returns 0.0 if total is 0 (avoids divide-by-zero in the Week-6 gate).
        The Week-6 gate's OR-clause (<1%) covers the case where total is too
        low to be a meaningful sample.
        """
        if self.total == 0:
            return 0.0
        return self.counter_1_same_edge / self.total


def increment_counter_1_same_edge(state: PerDocumentCounters) -> None:
    """Counter 1: rejected-then-same-edge (real FP per D4).

    Caller must canonicalize edges before deciding "same."
    """
    state.counter_1_same_edge += 1


def increment_counter_2_different_edge(state: PerDocumentCounters) -> None:
    """Counter 2: rejected-then-different-edge (TP)."""
    state.counter_2_different_edge += 1


def increment_counter_3_retry_exhausted(state: PerDocumentCounters) -> None:
    """Counter 3: rejected-then-retry-exhausted (analyst flag)."""
    state.counter_3_retry_exhausted += 1
