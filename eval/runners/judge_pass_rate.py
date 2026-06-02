"""Cascade-OCR judge re-calibration pass-rate runner (T3) - D3 driver.

Runs the cascade-OCR judge re-calibration over D-mode extraction output and
reports the judge-pass-rate with its Wilson lower bound (D12). The acceptance
gate for D shipping to production-shadow is Wilson-lower >= 0.95.

Default provider is the offline MockProvider over the SYNTHETIC sample dataset
(treated as cascade pages). Point `--eval-set` at the real cascade-OCR eval set
for the production gate; it is only meaningful there. Per D12, re-cal uses the
EXISTING OCR-quality labels - no new relationship labels.

Usage:
  python eval/runners/judge_pass_rate.py --eval-set eval/labels/sample --use-wilson-lower-bound
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.datasets import load_dataset  # noqa: E402
from src.config import Config  # noqa: E402
from src.d_extraction import extract_document  # noqa: E402
from src.cascade_integration import recalibrate_judge  # noqa: E402

JUDGE_PASS_RATE_THRESHOLD = 0.95


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cascade-OCR judge re-cal pass-rate on D-mode output (D3 driver)")
    parser.add_argument("--eval-set", type=Path, required=True)
    parser.add_argument("--d-mode-only", action="store_true", help="(default) run judge on D-mode output")
    parser.add_argument("--threshold", type=float, default=JUDGE_PASS_RATE_THRESHOLD)
    parser.add_argument("--use-wilson-lower-bound", action="store_true", help="gate on Wilson lower bound (D12; recommended)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    records = load_dataset(args.eval_set)
    tmp = tempfile.mkdtemp(prefix="paiq-judge-")

    # Build a cascade-style pages file (one page per chunk) the recal harness reads.
    pages_path = Path(tmp) / "pages.jsonl"
    page_id = 0
    lines = []
    for record in records:
        for chunk in record["chunks"]:
            lines.append(json.dumps({"page_id": page_id, "text": chunk, "ocr_label": "cheap_ok"}))
            page_id += 1
    pages_path.write_text("\n".join(lines), encoding="utf-8")

    cfg = Config(provider="mock", d_enabled=True, journal_dir=tmp)

    def d_extraction_module(text: str):
        return extract_document(f"page-{abs(hash(text)) % 100000}", [text], cfg)

    result = recalibrate_judge(pages_path, d_extraction_module)
    gate_value = result.judge_pass_rate_wilson_lower if args.use_wilson_lower_bound else result.judge_pass_rate
    passed = gate_value >= args.threshold

    report = {
        "n_pages": result.n_pages_evaluated,
        "judge_pass_rate": result.judge_pass_rate,
        "judge_pass_rate_wilson_lower": result.judge_pass_rate_wilson_lower,
        "threshold": args.threshold,
        "gate_on": "wilson_lower" if args.use_wilson_lower_bound else "point",
        "passed": passed,
        "failure_modes": result.failure_modes,
        "note": "synthetic sample" if "sample" in str(args.eval_set) else "production labels",
    }
    out = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    print(out)
    print(f"GATE: {'PASS' if passed else 'FAIL'} (value={gate_value:.3f}, threshold={args.threshold})", file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
