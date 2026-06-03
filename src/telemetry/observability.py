"""D-specific observability aggregation over the 3-counter FP telemetry (F8 / T13).

`telemetry/counters.py` owns the per-document 3-counter snapshot. This module
rolls those snapshots up (per-day rolling in production; any window here) into an
aggregate FP rate and guardrails firing volume, and exposes the Week-6 Kill
Criteria band check (counter(1)/total in [1%, 15%]).

The dashboard rendering itself is infra; this is the metric-shaping slice that
feeds it, testable now over synthetic counter snapshots.

T13 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .counters import PerDocumentCounters


# Week-6 Kill Criteria operating band for counter(1)/total.
FP_BAND_LOW = 0.01
FP_BAND_HIGH = 0.15


@dataclass
class RollingAggregate:
    """Aggregate of per-document counters across a rolling window."""
    counter_1_same_edge: int = 0
    counter_2_different_edge: int = 0
    counter_3_retry_exhausted: int = 0
    n_documents: int = 0

    @property
    def total(self) -> int:
        """Total guardrail rejections (all three outcomes) across the window."""
        return (
            self.counter_1_same_edge
            + self.counter_2_different_edge
            + self.counter_3_retry_exhausted
        )

    @property
    def fp_rate(self) -> float:
        """Rolling FP rate per D4: sum(counter 1) / sum(total). 0.0 on empty window."""
        return self.counter_1_same_edge / self.total if self.total else 0.0

    @property
    def guardrails_firing_count(self) -> int:
        """How many edges the guardrails rejected across the window."""
        return self.total


def aggregate(snapshots: Iterable[PerDocumentCounters]) -> RollingAggregate:
    """Roll per-document counter snapshots up into a single window aggregate."""
    agg = RollingAggregate()
    for snap in snapshots:
        agg.counter_1_same_edge += snap.counter_1_same_edge
        agg.counter_2_different_edge += snap.counter_2_different_edge
        agg.counter_3_retry_exhausted += snap.counter_3_retry_exhausted
        agg.n_documents += 1
    return agg


def within_fp_band(agg: RollingAggregate, low: float = FP_BAND_LOW, high: float = FP_BAND_HIGH) -> bool:
    """Week-6 Kill Criteria check: is the aggregate FP rate inside [low, high]?

    Outside the band (too aggressive > high, or too permissive < low) trips the
    guardrails-tuning gate.
    """
    return low <= agg.fp_rate <= high
