"""Cascade-OCR judge re-calibration implementation per D3.

ASCII diagram (re-cal flow):

  cascade-OCR eval set (existing OCR-quality labels)
            |
            v
  +---------------------------------------------+
  | For each page in eval set:                  |
  |   1. Run D-modified extraction on the page  |
  |   2. Run cascade-OCR judge on the output    |
  |   3. Record judge verdict                   |
  +---------------------------------------------+
            |
            v
  Compute judge-pass-rate (% pages the judge accepts)
            |
            v
  If Wilson-lower >= 95%: D ready for production-shadow
  If < 95%: ESCALATE to cascade-OCR plan owner.

The live re-cal RUN (real cascade eval set + real judge harness on final D-mode
output) is Phase-0-blocked. The pass-rate + Wilson-threshold LOGIC here is
exercised now by injecting a fake `d_extraction_module` callable over synthetic
pages. Per D12, the threshold uses the Wilson lower bound, NOT the point estimate.

T3 deliverable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..shadow.harness import wilson_lower_bound


@dataclass
class RecalibrationResult:
    """Output of the re-calibration run."""
    judge_pass_rate: float
    judge_pass_rate_wilson_lower: float  # 95% CI lower bound per D12
    n_pages_evaluated: int
    pass_rate_threshold: float = 0.95
    threshold_met: bool = False
    failure_modes: dict = None  # per-failure-mode count keyed by the page's OCR label


def _load_pages(path: Path) -> list[dict]:
    """Load the cascade-OCR eval set (JSONL: one page record per line)."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _judge_passed(extraction_output) -> bool:
    """Simulated judge verdict on D-mode output.

    In production this is the real cascade-OCR LLM judge. For the re-cal logic it
    is the boolean "the judge accepted this D-mode extraction": a finished,
    schema-valid extraction passes; an incomplete one does not.
    """
    return bool(getattr(extraction_output, "extraction_complete", bool(extraction_output)))


def recalibrate_judge(
    cascade_eval_set_path: Path,
    d_extraction_module,  # callable: (page_text) -> DocumentExtraction
) -> RecalibrationResult:
    """Run cascade-OCR judge re-calibration on D-mode extraction output.

    Reuses the existing cascade-OCR eval set (no new labels per D12). Returns a
    RecalibrationResult with threshold_met=True only when the Wilson lower bound
    of the judge-pass-rate is >= 0.95. If False, escalate to the cascade-OCR plan
    owner before D ships to production-shadow.
    """
    pages = _load_pages(Path(cascade_eval_set_path))
    passed = 0
    failure_modes: dict[str, int] = {}
    for page in pages:
        output = d_extraction_module(page.get("text", ""))
        if _judge_passed(output):
            passed += 1
        else:
            mode = page.get("ocr_label", "unknown")
            failure_modes[mode] = failure_modes.get(mode, 0) + 1

    total = len(pages)
    rate = (passed / total) if total else 0.0
    lower = wilson_lower_bound(passed, total)
    threshold = 0.95
    return RecalibrationResult(
        judge_pass_rate=rate,
        judge_pass_rate_wilson_lower=lower,
        n_pages_evaluated=total,
        pass_rate_threshold=threshold,
        threshold_met=lower >= threshold,
        failure_modes=failure_modes,
    )
