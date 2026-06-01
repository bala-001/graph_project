"""Guardrails — extraction-time consistency check that catches logical inconsistencies
before they're committed.

Per D2 + D10: guardrails fire AFTER each LLM call within a multi-call extraction,
consulting the partial-edge state from the journal and deciding accept/retry/exhaust.

Per D4 + D12 (FP canonicalization): three counters per document distinguish
real false positives (rejected-then-same-edge), true positives (rejected-then-
different-edge), and analyst-flag fallbacks (retry exhausted).

Public surface:
- `detector.check`: run all 4 detection scenarios; return Verdict
- `retry.handle`: apply retry policy + increment counters
- `state`: partial-edge state model
"""

from .detector import Verdict, check
from .retry import handle_verdict
from .state import PartialEdgeState

__all__ = ["Verdict", "check", "handle_verdict", "PartialEdgeState"]
