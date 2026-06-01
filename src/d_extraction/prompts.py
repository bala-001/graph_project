"""D-modified extraction prompts + baseline preservation for rollback.

Per D6 + D12: the baseline prompts MUST be preserved here so the feature flag
`paiq.d_extraction.enabled=false` can revert without a code rollback.

T1 + T6 deliverable. STUB — real prompt templates land via Implementation Task T1
once Q3 (which prompts change) closes Week 1.
"""

from __future__ import annotations


# Baseline (pre-D) prompts. Preserved verbatim for feature-flag rollback.
# DO NOT MODIFY without updating the rollback path in src/feature_flags/.
BASELINE_PROMPTS: dict[str, str] = {
    # Populated from existing PAIQ extraction code during T1 scoping (Q3).
    # Keys are prompt-template IDs (e.g., "extract_drug_fields", "extract_age_limits").
    # Values are the verbatim baseline prompt strings.
}


# D-modified prompts. Each one extends the baseline to ALSO emit structured edges
# alongside existing field outputs.
D_PROMPTS: dict[str, str] = {
    # Populated during T1. Mirrors BASELINE_PROMPTS keys + an additive "emit edges"
    # instruction with reference to the structured-output schema (DocumentExtraction).
}


def get_prompt(template_id: str, *, d_mode: bool) -> str:
    """Return the appropriate prompt for the requested template ID.

    `d_mode=False` returns baseline (rollback path).
    `d_mode=True` returns the D-modified version (production-shadow / production path).

    The caller is responsible for reading the feature flag via
    `src.feature_flags.is_d_enabled()` and passing `d_mode` accordingly.
    """
    if not d_mode:
        if template_id not in BASELINE_PROMPTS:
            raise KeyError(f"Unknown baseline prompt template: {template_id}")
        return BASELINE_PROMPTS[template_id]

    if template_id not in D_PROMPTS:
        raise KeyError(f"Unknown D-mode prompt template: {template_id}")
    return D_PROMPTS[template_id]
