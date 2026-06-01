# Data Model — Pydantic Edge Schema + Provider Configuration

Per eng-review D1 (provider built-in structured outputs) + D2 (persist-as-you-go
with `extraction_complete` flag).

## Edge schema (Pydantic)

```python
# src/d_extraction/schema.py — STUB

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field


class EdgeKind(str, Enum):
    """The five edge predicates D extracts."""
    REQUIRES = "requires"
    EXCLUDES = "excludes"
    APPLIES_TO = "applies_to"
    OVERRIDES = "overrides"
    EFFECTIVE_FROM = "effective_from"


class DrugNode(BaseModel):
    """Canonical drug identifier. Resolved via PAIQ's existing drug dictionary."""
    canonical_id: str = Field(..., description="PAIQ canonical drug ID (preferred)")
    surface_form: str = Field(..., description="As extracted from the document text")


class IndicationNode(BaseModel):
    """Disease / condition / treatment context for a criterion."""
    canonical_id: Optional[str] = None
    surface_form: str


class Edge(BaseModel):
    """A single edge emitted by D. Canonicalized before FP-counter comparison."""
    kind: EdgeKind
    subject: DrugNode
    object: DrugNode | IndicationNode | str
    qualifiers: dict = Field(default_factory=dict, description="age_min, age_max, dosage_min, dosage_max, etc.")
    source_page: Optional[int] = None
    source_chunk_id: Optional[str] = None
    # Confidence is the model's reported confidence; eval-time precision/recall
    # is measured against analyst-corrected ground truth and not stored on the
    # edge itself.
    model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class DocumentExtraction(BaseModel):
    """Document-level extraction payload. Persisted to in-document JSON metadata."""
    document_id: str
    extraction_complete: bool = False  # Set true ONLY when extraction finishes AND all guardrails pass
    edges: list[Edge] = Field(default_factory=list)
    existing_fields: dict = Field(default_factory=dict)  # drug_name, age_limit, dates, etc. — baseline outputs preserved
    extraction_started_at: str  # ISO 8601
    extraction_completed_at: Optional[str] = None
    journal_path: Optional[str] = None
    # Telemetry counters (per-document; aggregated to per-day rolling in dashboard)
    guardrails_counter_1_same_edge: int = 0  # FP per D4
    guardrails_counter_2_different_edge: int = 0  # TP per D4
    guardrails_counter_3_retry_exhausted: int = 0  # Analyst flag per D4
```

## Canonicalization rules (per D12)

Before comparing two edges for the same-edge FP counter (counter 1):

1. **Drug node canonical IDs**: resolve `surface_form` to `canonical_id` via the
   existing drug dictionary; if no canonical resolution, fall back to lowercased
   stripped surface form.
2. **Tuple ordering**: for order-agnostic predicates (none of the current 5 are
   order-agnostic, but reserve the rule for future bidirectional edges), sort
   `(subject, object)` lexicographically.
3. **Predicate normalization**: `kind` is enum-constrained so already canonical.
4. **Qualifier dict**: sort keys; normalize values via the same surface-form ->
   canonical pipeline; strip trailing whitespace and punctuation on string values.

Two edges with identical canonicalized form are "same edge."

## Provider configuration

### OpenAI path (recommended primary; per D1)

```python
# src/d_extraction/prompts.py — STUB

from openai import OpenAI
from .schema import DocumentExtraction

client = OpenAI()

def extract_with_openai(prompt: str, chunk: str) -> DocumentExtraction:
    response = client.chat.completions.create(
        model="gpt-4o",  # or gpt-4o-mini for cost-sensitive paths
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": chunk},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "document_extraction",
                "schema": DocumentExtraction.model_json_schema(),
                "strict": True,  # strict mode rejects any deviation from schema
            },
        },
    )
    return DocumentExtraction.model_validate_json(response.choices[0].message.content)
```

### Anthropic path (fallback)

```python
import anthropic
client = anthropic.Anthropic()

def extract_with_anthropic(prompt: str, chunk: str) -> DocumentExtraction:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        tools=[{
            "name": "emit_document_extraction",
            "description": "Emit the structured edges + existing fields extracted from this chunk",
            "input_schema": DocumentExtraction.model_json_schema(),
        }],
        tool_choice={"type": "tool", "name": "emit_document_extraction"},
        messages=[
            {"role": "user", "content": f"{prompt}\n\n---\n\n{chunk}"},
        ],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return DocumentExtraction.model_validate(tool_use.input)
```

## Known limit (per D1 outside-voice finding #1)

Provider built-in structured outputs enforce **SHAPE**, not **SEMANTICS**. A
schema-valid `requires(Drug A, Drug B)` edge can be semantically wrong. The
defense against bad relationships lives in:

- **Guardrails** (catch contradictions / circular deps at extraction time)
- **Eval suite** (`eval/runners/edge_precision.py` — measures D's precision/recall
  against analyst-corrected ground truth)
- **Iso-precision regression suite** (T10 — proves D's modifications don't
  regress existing field extraction)

The Week-4 Kill Criteria gate's 5% regression threshold is defended by the
regression test suite, NOT by the schema mechanism.

## Persist-as-you-go semantics (per D2 + D7)

Edges land in the in-document JSON metadata via the batched-write journal at
`src/journal/writer.py`:

1. Extraction emits edge → guardrails check passes → edge added to in-memory
   buffer
2. Buffer flushed to journal file every 10 edges OR every 5 seconds (whichever
   first)
3. On crash mid-document: `extraction_complete` stays `false`; downstream
   consumers treat this as "not yet extracted" (per D12 downstream consumer
   policy); a background GC sweeps `extraction_complete=false` rows older than
   24 hours and re-queues for extraction
4. On extraction-complete: final buffer flush + journal collapsed into the
   canonical in-document JSON metadata + `extraction_complete: true` set

## Feature flag (per D12 rollback path)

`paiq.d_extraction.enabled` gates the prompt-mode swap:

- `true` → D-modified prompts execute; edges emitted; guardrails consulted
- `false` → baseline extraction prompts execute; no edges; no guardrails

Baseline prompts are PRESERVED in `src/d_extraction/prompts.py` under
`BASELINE_PROMPTS = {...}`. Flag flip is instant revert; the Week-4 Kill Criteria
gate uses this mechanism if precision regression >5% fires.
