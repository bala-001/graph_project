# D Integration Spec (F1 deliverable)

**Lands BEFORE any Phase-1 code.** Per CEO plan iter-5 + eng-review D6/D10/D2 decisions.
This spec is the contract between the modified extraction pipeline, the guardrails
component, the journal layer, the shadow harness, and the existing PAIQ pipeline.

Status: **STUB — to be authored by tech lead per T14**

## Scope

Specify how Approach D (modified extraction emitting structured edges) integrates
with:

1. The existing PAIQ extraction pipeline (which currently emits field-level
   outputs only)
2. The new guardrails component (consulting partial-edge state between LLM calls)
3. The in-document JSON metadata storage (now extended with structured edges +
   `extraction_complete` flag)
4. The batched-write journal (buffer of 10 edges or 5 sec, whichever first)
5. The shadow harness (D-output vs analyst-corrected ground truth comparison)
6. The cascade-OCR judge (re-calibration step before D ships)

## Data flow (D + guardrails happy path)

```
PBM document
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│  Existing extraction pipeline (chunk-by-chunk)         │
│  - chunks document into N segments                     │
│  - for each chunk i:                                   │
│    ┌────────────────────────────────────────────────┐  │
│    │  D-modified extraction prompt (i)              │  │
│    │  - via provider built-in structured outputs    │  │
│    │    (OpenAI json_schema strict OR Anthropic     │  │
│    │     tool-use)                                  │  │
│    │  - emits: existing field values + new edges    │  │
│    └────────────────────────────────────────────────┘  │
│         │                                              │
│         ▼                                              │
│    ┌────────────────────────────────────────────────┐  │
│    │  Guardrails check (after each chunk)           │  │
│    │  - load partial-edge state from journal        │  │
│    │  - canonicalize new edges                      │  │
│    │  - run 4 detection scenarios:                  │  │
│    │    * circular dependency                       │  │
│    │    * contradictory limits                      │  │
│    │    * prerequisite chain mismatch               │  │
│    │    * age conflict                              │  │
│    │  - decision: accept / reject-retry / exhaust   │  │
│    └────────────────────────────────────────────────┘  │
│         │                  │                            │
│         ▼ accept           ▼ reject-retry / exhaust    │
│    ┌─────────────┐    ┌──────────────────────────────┐ │
│    │ Journal     │    │ Retry with validator error   │ │
│    │ (batched)   │    │ in prompt; max N retries     │ │
│    └─────────────┘    └──────────────────────────────┘ │
│         │                                              │
│         ▼ (if accept OR retry-succeeded)              │
│    proceed to chunk i+1                                │
└─────────────────────────────────────────────────────────┘
   │
   ▼ (all chunks done)
┌─────────────────────────────────────────────────────────┐
│  Materialize document-level state                       │
│  - flush journal buffer                                 │
│  - set extraction_complete = true                       │
│  - write final JSON metadata blob                       │
└─────────────────────────────────────────────────────────┘
   │
   ▼
Downstream consumers (analyst tools, client reports)
   - check extraction_complete flag
   - if false: row is INVISIBLE (treat as not-yet-extracted)
   - if true: surface edges + fields to consumer
```

## Shadow path (parallel to above)

For each document processed:

```
PBM document
   │
   ├──▶ Baseline extraction (existing prompts) ──▶ baseline edges (none)
   │                                                + baseline fields
   │
   └──▶ D-mode extraction (this spec) ──▶ D edges + D fields
                                          │
                                          ▼
                              ┌─────────────────────────────┐
                              │  Shadow comparison          │
                              │  - D fields vs baseline:    │
                              │    iso-precision regression │
                              │    check (Week-4 gate)      │
                              │  - D edges vs analyst-      │
                              │    corrected ground truth:  │
                              │    precision/recall         │
                              │    (Quarter-1 gate)         │
                              └─────────────────────────────┘
                                          │
                                          ▼
                              Telemetry dashboard
                              + Kill Criteria gates
```

## Module boundaries

| Module | Owns | Boundary |
|---|---|---|
| `src/d_extraction/` | Pydantic edge schema, modified extraction prompts, provider-mode swap | Emits edges + fields; does NOT validate guardrails (that's `src/guardrails/`) |
| `src/guardrails/` | 4 detection scenarios, retry policy, 3-counter FP telemetry, canonicalization | Consults journal; decides accept/retry/exhaust |
| `src/journal/` | Batched-write journal + crash-recovery replay | Persists edges; does NOT decide retry (that's `src/guardrails/`) |
| `src/feature_flags/` | `paiq.d_extraction.enabled` flag | Gates prompt-mode swap; baseline prompt path stays in code |
| `src/shadow/` | D-vs-GT comparison harness | Reads finalized edges from journal; does NOT run extraction |
| `src/telemetry/` | 3-counter FP rate metrics | Subscribed to guardrails events |
| `src/cascade_integration/` | Cascade-OCR judge re-cal coordination | Runs once before D ships; does NOT modify guardrails or extraction |

## Open implementation questions (close in Phase 1 Week 1)

- **Q3**: Which extraction prompts / schemas change? Tech lead to enumerate every existing prompt that emits drug-name, age-limit, dates, step-therapy entries, quantity-limit; for each, define the D-mode variant that ALSO emits edges. **Blocking.**
- **Q8**: Guardrails retry exhaust threshold. Recommend N=3 retries before falling back to analyst flag, but confirm.
- **Provider choice**: OpenAI json_schema strict OR Anthropic tool-use, per PAIQ's primary LLM provider. Document choice + provider-fallback policy if PAIQ uses multiple.

## Verification

This spec is complete when:

- All module boundaries are clear enough that two engineers can work in parallel lanes (per worktree parallelization plan)
- Q3 (D scope) is closed in writing
- The shadow comparison fields are concrete enough to drive the eval runner at `eval/runners/edge_precision.py`
