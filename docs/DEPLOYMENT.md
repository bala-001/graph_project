# Deployment

How to deploy the D-extraction service, roll it out safely behind the feature
flag, and roll it back. Read alongside `docs/architecture/kill-criteria.md` and
`docs/planning/phase1-implementation-plan.md`.

## Safe defaults
The image and package default to `PAIQ_PROVIDER=mock` and
`PAIQ_D_EXTRACTION_ENABLED=false`. In that state the service does baseline field
extraction only, with no edges, no guardrails, no network. Nothing reaches real
documents until a human sets a real provider AND flips the flag on.

## Container

```bash
docker build -t paiq-d:0.1.0 .

# Offline self-check (no keys):
docker run --rm paiq-d:0.1.0 flag

# Real provider, D enabled, journals on a mounted volume:
docker run --rm \
  -e PAIQ_PROVIDER=openai -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e PAIQ_D_EXTRACTION_ENABLED=true \
  -v paiq-journals:/data/journals \
  paiq-d:0.1.0 extract /data/in/policy.txt
```

The container runs as a non-root user and HEALTHCHECKs with `paiq-d flag`.

## Rollout (shadow -> canary -> on), gated by Kill Criteria

The flag is the control surface. Rollout follows the design's shadow-first plan:

1. **Shadow.** Deploy with `PAIQ_D_EXTRACTION_ENABLED=false` for client-facing
   output, but run D-mode in parallel and compare against analyst-corrected
   ground truth with `eval/runners/edge_precision.py`. Downstream consumers treat
   `extraction_complete=false` as invisible (D12); a 24h GC re-queues orphaned
   partials (`src/journal/downstream.py`).
2. **Week-4 gate (regression).** `eval/runners/regression.py` must show no
   existing field type regressing precision by >5%. On failure, the D12 rollback
   is one config change: `PAIQ_D_EXTRACTION_ENABLED=false`.
3. **Week-6 gate (guardrails FP).** Aggregate `counter_1/total` must stay in
   `[1%, 15%]` (`src/telemetry/observability.within_fp_band`). Outside the band:
   tune, then disable guardrails if still out of band.
4. **Cascade re-cal (before any client-facing D).** `eval/runners/judge_pass_rate.py`
   must show judge-pass-rate Wilson-lower >= 95% on the cascade-OCR eval set.
5. **Quarter-1 shadow gate.** Edge precision Wilson-lower >= 85% and recall >= 80%
   before Phase 2 is considered.

All gate thresholds use a CI lower bound (Wilson, or Clopper-Pearson for small N)
per D12, not the point estimate.

## Rollback
`PAIQ_D_EXTRACTION_ENABLED=false` reverts to the preserved baseline prompts with
no code deploy (D12). The baseline path is always retained in
`src/d_extraction/prompts.py`.

## CI and the eval-trigger merge gate
`.github/workflows/ci.yml` runs the test suite + a >=90% coverage gate, and the
eval runners on the synthetic sample (regression must pass; edge/judge are
report-only on synthetic data). Per CLAUDE.md, any change to
`src/d_extraction/prompts.py`, `src/d_extraction/schema.py`,
`src/guardrails/detector.py`, or `src/cascade_integration/recal.py` must run the
FULL eval suite on production labels before merge to a protected branch. Wire
that as a required check once the F6 label store exists.

## Data / PHI handling
- Provider keys come from the environment; never committed.
- The bundled `eval/labels/sample/` is synthetic and non-PHI. Real labels live in
  the access-controlled store and are gitignored (`eval/labels/*.jsonl`).
- Journals hold extracted edges (inherit the source document's data
  classification); store the journal volume per PAIQ's PHI policy and let the 24h
  GC sweep orphaned partials.

## Production prerequisites (cannot ship to real documents without these)
1. Q3: real extraction prompts in `src/d_extraction/prompts.py` (replace templates).
2. Provider credentials + `PAIQ_PROVIDER` set.
3. F6 labels + cascade-OCR eval set in the label store; Kill Criteria certified on them.
4. Week-1 sponsor commitment + Week-2 complaint root-cause audit cleared.
