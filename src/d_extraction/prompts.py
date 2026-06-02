"""D-modified extraction prompts + baseline preservation for rollback.

Per D6 + D12: the baseline prompts MUST be preserved here so the feature flag
`paiq.d_extraction.enabled=false` can revert without a code rollback.

T1 + T6 deliverable. STUB — real prompt templates land via Implementation Task T1
once Q3 (which prompts change) closes Week 1.
"""

from __future__ import annotations


# ============================================================================
# TEMPLATE PROMPTS - NOT PRODUCTION-VALIDATED.
# These are functional defaults so the pipeline runs end-to-end. Replace the
# verbatim text with PAIQ's real production prompts when Q3 (which prompts/
# schemas change) closes. The feature flag (paiq.d_extraction.enabled) defaults
# OFF, so the D template never reaches real documents until a human turns it on.
# ============================================================================

_BASELINE_EXTRACT = """\
You are a PBM policy extractor. From the document chunk, extract the existing
field-level criteria (drug name, age limit, effective dates, step-therapy
entries, quantity limits) exactly as PAIQ does today. Do NOT infer relationships.
Return them in the existing_fields map of the document extraction schema."""

_D_EXTRACT = """\
You are a PBM policy extractor with relationship awareness (Approach D). From the
document chunk, extract BOTH:
1. The existing field-level criteria into existing_fields (drug name, age limit,
   effective dates, step-therapy entries, quantity limits) - unchanged from baseline.
2. Structured edge-triples into edges, using the five predicates
   requires / excludes / applies_to / overrides / effective_from, with qualifiers
   (age_min, age_max, dosage_min, dosage_max, ...) where stated.
Emit only relationships the text supports. Do not hallucinate edges in
low-relationship-density text. Conform exactly to the provided JSON schema."""

# Baseline (pre-D) prompts. Preserved verbatim for feature-flag rollback.
# DO NOT MODIFY without updating the rollback path in src/feature_flags/.
BASELINE_PROMPTS: dict[str, str] = {
    "extract_document": _BASELINE_EXTRACT,
}


# D-modified prompts. Each extends the baseline to ALSO emit structured edges
# alongside existing field outputs.
D_PROMPTS: dict[str, str] = {
    "extract_document": _D_EXTRACT,
}

DEFAULT_TEMPLATE_ID = "extract_document"


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


def resolve_prompt(template_id: str) -> str:
    """Production entry point: route to the right prompt based on the feature flag.

    Consults `src.feature_flags.is_d_enabled()` and returns the D-modified prompt
    when the flag is on, or the preserved baseline prompt when off. This is the
    one-config rollback path per D12: flipping `paiq.d_extraction.enabled` to
    false reverts to baseline prompts with no code change.
    """
    from ..feature_flags import is_d_enabled

    return get_prompt(template_id, d_mode=is_d_enabled())
