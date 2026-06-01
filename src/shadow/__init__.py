"""Shadow harness per D5.

D-output vs analyst-corrected ground truth on the cascade-OCR eval set.
Precision = D ∩ GT / D. Recall = D ∩ GT / GT.

The Quarter-1 D shadow result Kill Criteria gate depends on this harness.
Per D12 statistical-significance gate: thresholds (85% precision, 80% recall)
use the lower bound of a 95% confidence interval (Wilson / Clopper-Pearson),
NOT the point estimate.
"""

from .harness import compare_d_to_ground_truth, ShadowResult

__all__ = ["compare_d_to_ground_truth", "ShadowResult"]
