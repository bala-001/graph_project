"""Cascade-OCR judge re-calibration per D3.

When D modifies extraction prompts, the cascade-OCR LLM-judge sees different
output than what it was calibrated on (judge was calibrated on baseline
extraction output). Need to re-calibrate.

Per D12 clarification: re-cal uses the EXISTING OCR-quality labels on the
cascade-OCR eval set. NO new relationship-quality labels needed for re-cal.
The verification is "judge-pass-rate stays ≥95% when its input distribution
shifts from baseline-extraction-output to D-mode-extraction-output."

Runs ONCE in Phase 1 BEFORE D ships to production-shadow. If pass-rate drops
below 95%, the judge prompt itself may need re-tuning (escalate to cascade-OCR
plan owner).
"""

from .recal import recalibrate_judge, RecalibrationResult

__all__ = ["recalibrate_judge", "RecalibrationResult"]
