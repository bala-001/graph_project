"""Edge precision/recall eval runner (T11).

Drives the Quarter-1 D shadow result Kill Criteria gate. Runs D-mode extraction
over the eval set and compares emitted edges to gold edges (per D5), per edge type
and aggregate. Thresholds use a CI lower bound, not the point estimate (D12).

Default provider is the offline MockProvider over the SYNTHETIC sample dataset, so
this runs in CI with no keys. Point `--eval-set` at the real label store for the
production gate (results are only meaningful there).

Usage:
  python eval/runners/edge_precision.py --eval-set eval/labels/sample
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.datasets import load_dataset, gold_edges  # noqa: E402
from src.config import Config  # noqa: E402
from src.d_extraction import extract_document  # noqa: E402
from src.d_extraction.schema import canonicalize_edge  # noqa: E402
from src.shadow.harness import lower_bound  # noqa: E402

EDGE_TYPES = ["requires", "excludes", "applies_to", "overrides", "effective_from"]


def _ratio(hits: int, total: int) -> float:
    return hits / total if total else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D edge precision/recall eval (Quarter-1 Kill Criteria driver)")
    parser.add_argument("--eval-set", type=Path, required=True, help="Dataset dir or .jsonl")
    parser.add_argument("--precision-threshold", type=float, default=0.85)
    parser.add_argument("--recall-threshold", type=float, default=0.80)
    parser.add_argument("--output", type=Path, help="Write JSON report here (else stdout)")
    args = parser.parse_args(argv)

    records = load_dataset(args.eval_set)
    tmp = tempfile.mkdtemp(prefix="paiq-eval-")
    cfg = Config(provider="mock", d_enabled=True, journal_dir=tmp)

    # Per-edge-type tallies: d_count, gt_count, hits.
    tally = {t: {"d": 0, "gt": 0, "hit": 0} for t in EDGE_TYPES}
    agg = {"d": 0, "gt": 0, "hit": 0}

    for record in records:
        doc = extract_document(record["document_id"], record["chunks"], cfg)
        d_by_type: dict[str, set] = {t: set() for t in EDGE_TYPES}
        gt_by_type: dict[str, set] = {t: set() for t in EDGE_TYPES}
        for edge in doc.edges:
            d_by_type[edge.kind.value].add(canonicalize_edge(edge))
        for edge in gold_edges(record):
            gt_by_type[edge.kind.value].add(canonicalize_edge(edge))
        for t in EDGE_TYPES:
            hit = len(d_by_type[t] & gt_by_type[t])
            tally[t]["d"] += len(d_by_type[t])
            tally[t]["gt"] += len(gt_by_type[t])
            tally[t]["hit"] += hit
            agg["d"] += len(d_by_type[t])
            agg["gt"] += len(gt_by_type[t])
            agg["hit"] += hit

    per_type = {}
    for t in EDGE_TYPES:
        d, gt, hit = tally[t]["d"], tally[t]["gt"], tally[t]["hit"]
        per_type[t] = {
            "precision": _ratio(hit, d),
            "recall": _ratio(hit, gt),
            "precision_lower": lower_bound(hit, d),
            "recall_lower": lower_bound(hit, gt),
            "n_d": d,
            "n_gt": gt,
        }
    prec_lower = lower_bound(agg["hit"], agg["d"])
    rec_lower = lower_bound(agg["hit"], agg["gt"])
    passed = prec_lower >= args.precision_threshold and rec_lower >= args.recall_threshold
    report = {
        "n_documents": len(records),
        "aggregate": {
            "precision": _ratio(agg["hit"], agg["d"]),
            "recall": _ratio(agg["hit"], agg["gt"]),
            "precision_lower": prec_lower,
            "recall_lower": rec_lower,
        },
        "per_edge_type": per_type,
        "thresholds": {"precision": args.precision_threshold, "recall": args.recall_threshold},
        "passed": passed,
        "note": "synthetic sample" if "sample" in str(args.eval_set) else "production labels",
    }
    out = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    print(out)
    print(f"GATE: {'PASS' if passed else 'FAIL'} (precision_lower={prec_lower:.3f}, recall_lower={rec_lower:.3f})", file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
