"""Cascade-OCR judge re-calibration pass-rate eval runner — D3 driver.

Runs cascade-OCR judge against D-mode extraction output on the cascade-OCR
eval set. Confirms judge-pass-rate Wilson lower-bound stays ≥95% — the
acceptance gate for D shipping to production-shadow.

Per D12 clarification: re-cal uses EXISTING cascade-OCR OCR-quality labels.
NO new relationship-quality labels needed for this runner.

If pass-rate drops below threshold: escalate to cascade-OCR plan owner. Judge
prompt may need re-tuning before D can ship.

T3 deliverable. STUB.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


JUDGE_PASS_RATE_THRESHOLD = 0.95


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cascade-OCR judge re-cal pass-rate on D-mode output (D3 driver)"
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        required=True,
        help="Path to the eval/labels/ directory (uses cascade-OCR OCR-quality labels)",
    )
    parser.add_argument(
        "--d-mode-only",
        action="store_true",
        help="Run cascade judge on D-mode extraction output",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=JUDGE_PASS_RATE_THRESHOLD,
        help=f"Pass-rate threshold (default {JUDGE_PASS_RATE_THRESHOLD})",
    )
    parser.add_argument(
        "--use-wilson-lower-bound",
        action="store_true",
        help="Compare Wilson 95% lower bound against threshold (recommended; D12)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report here (otherwise stdout)",
    )
    args = parser.parse_args(argv)

    # STUB — T3 deliverable
    print("STUB: judge_pass_rate.py — see Implementation Tasks T3", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
