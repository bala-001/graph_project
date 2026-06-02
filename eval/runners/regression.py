"""Iso-precision regression runner (T10) - Week-4 Kill Criteria gate.

Runs BASELINE (flag off) and D-mode (flag on) extraction over the eval set and
compares each existing-field type's precision against gold. The gate fires if D
regresses any field type's precision by more than the threshold (default 5%).

Default provider is the offline MockProvider over the SYNTHETIC sample dataset.
Point `--eval-set` at the real label store for the production gate; the gate is
only meaningful there. Per the D12 rollback path, a real regression triggers
`paiq.d_extraction.enabled=false`.

Usage:
  python eval/runners/regression.py --eval-set eval/labels/sample
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.datasets import load_dataset, gold_fields, dataset_is_synthetic  # noqa: E402
from src.config import Config  # noqa: E402
from src.d_extraction import extract_document  # noqa: E402

REGRESSION_THRESHOLD = 0.05  # Week-4 Kill Criteria gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Iso-precision regression on existing field types (Week-4 gate)")
    parser.add_argument("--eval-set", type=Path, required=True)
    parser.add_argument("--baseline-vs-d-mode", action="store_true", help="(default behavior) compare baseline vs D-mode")
    parser.add_argument("--regression-threshold", type=float, default=REGRESSION_THRESHOLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    records = load_dataset(args.eval_set)
    fields: dict[str, dict] = {}

    with tempfile.TemporaryDirectory(prefix="paiq-reg-") as tmp:
        baseline_cfg = Config(provider="mock", d_enabled=False, journal_dir=tmp)
        d_cfg = Config(provider="mock", d_enabled=True, journal_dir=tmp)
        for record in records:
            gold = gold_fields(record)
            if not gold:
                continue
            base = extract_document(record["document_id"], record["chunks"], baseline_cfg)
            dmode = extract_document(record["document_id"], record["chunks"], d_cfg)
            for key, gold_value in gold.items():
                slot = fields.setdefault(key, {"total": 0, "base_hit": 0, "d_hit": 0})
                slot["total"] += 1
                if base.existing_fields.get(key) == gold_value:
                    slot["base_hit"] += 1
                if dmode.existing_fields.get(key) == gold_value:
                    slot["d_hit"] += 1

    per_field = {}
    regressed = []
    for key, slot in fields.items():
        total = slot["total"]
        base_p = slot["base_hit"] / total if total else 0.0
        d_p = slot["d_hit"] / total if total else 0.0
        delta = base_p - d_p  # positive = D worse than baseline
        per_field[key] = {"baseline_precision": base_p, "d_precision": d_p, "delta": delta}
        if delta > args.regression_threshold:
            regressed.append(key)

    passed = not regressed
    report = {
        "n_documents": len(records),
        "per_field": per_field,
        "regression_threshold": args.regression_threshold,
        "regressed_fields": regressed,
        "passed": passed,
        "note": "synthetic sample" if dataset_is_synthetic(records) else "production labels",
    }
    out = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    print(out)
    print(f"GATE: {'PASS' if passed else 'FAIL'} (regressed={regressed})", file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
