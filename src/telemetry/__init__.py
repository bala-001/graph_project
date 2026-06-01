"""3-counter FP rate telemetry per D4 + D12 canonicalization.

Per document AND aggregated to per-day rolling. The Week-6 Kill Criteria gate
fires on counter (1) / total in [1%, 15%].
"""

from .counters import (
    PerDocumentCounters,
    increment_counter_1_same_edge,
    increment_counter_2_different_edge,
    increment_counter_3_retry_exhausted,
)
from .observability import RollingAggregate, aggregate, within_fp_band

__all__ = [
    "PerDocumentCounters",
    "increment_counter_1_same_edge",
    "increment_counter_2_different_edge",
    "increment_counter_3_retry_exhausted",
    "RollingAggregate",
    "aggregate",
    "within_fp_band",
]
