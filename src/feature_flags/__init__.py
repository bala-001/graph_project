"""Feature flag system per D12 rollback path.

Single flag for Phase 1: `paiq.d_extraction.enabled`.

When `false` (default): baseline prompts run; no edges; no guardrails.
When `true`: D-modified prompts run; edges emitted; guardrails consulted.

The Week-4 Kill Criteria gate uses this flag for instant revert if precision
regression >5% fires.
"""

from .flags import is_d_enabled, set_d_enabled, D_EXTRACTION_FLAG

__all__ = ["is_d_enabled", "set_d_enabled", "D_EXTRACTION_FLAG"]
