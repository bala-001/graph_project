"""Iso-precision regression suite runner — Week-4 Kill Criteria driver.

Per D11 + REGRESSION RULE: this runner is MANDATORY. It compares D-mode
extraction to baseline extraction on ALL existing field types (drug name,
age limit, dates, step therapy entries, quantity limit, dosage range,
coverage tier, indication, PA criteria, amendment section handling) and
asserts precision delta ≤5%.

When this runner fails: the Week-4 Kill Criteria gate fires, which
automatically flips `paiq.d_extraction.enabled=false` per D12 rollback path.

T10 + T11 deliverable. STUB.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REGRESSION_THRESHOLD = 0.05  # Week-4 Kill Criteria gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Iso-precision regression on existing field types (Week-4 Kill Criteria driver)"
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        required=True,
        help="Path to the eval/labels/ directory",
    )
    parser.add_argument(
        "--baseline-vs-d-mode",
        action="store_true",
        help="Compare baseline-mode extraction against D-mode on the same documents",
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=REGRESSION_THRESHOLD,
        help=f"Max allowed precision delta (default {REGRESSION_THRESHOLD})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report here (otherwise stdout)",
    )
    args = parser.parse_args(argv)

    # STUB — T10 + T11 deliverable
    print("STUB: regression.py — see Implementation Tasks T10 + T11", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
