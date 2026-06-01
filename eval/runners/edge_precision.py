"""Edge precision/recall eval runner.

Drives the Quarter-1 D shadow result Kill Criteria gate.

Per D5: shadow data = D-output vs analyst-corrected ground truth.
Per D12: thresholds (85% precision / 80% recall) use Wilson lower-bound,
not point estimate.

Per-edge-type breakdown:
- requires
- excludes
- applies_to
- overrides
- effective_from

Output: JSON report with per-edge-type precision/recall (point + Wilson lower
bound) + aggregate. CI gate posts results vs. baseline; PR fails if Wilson
lower-bound drops below threshold for any edge type.

T11 deliverable. STUB.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="D edge precision/recall eval (Quarter-1 Kill Criteria driver)"
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        required=True,
        help="Path to the eval/labels/ directory",
    )
    parser.add_argument(
        "--d-mode-only",
        action="store_true",
        help="Skip baseline comparison; D-mode only (faster, less rigorous)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report here (otherwise stdout)",
    )
    args = parser.parse_args(argv)

    # STUB — T11 deliverable
    print("STUB: edge_precision.py — see Implementation Tasks T11", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
