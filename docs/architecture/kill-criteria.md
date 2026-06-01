# Kill Criteria Reference Card

All gates from the CEO plan iter-5 in one place. Decision owner where named.
Before flipping any production-touching change, walk this list.

## Phase-0 gates (Weeks 1-2)

| Gate | Trigger | Decision | Owner |
|---|---|---|---|
| **Week-1 sponsor commitment** | Written conditional Phase-2 funding terms (metric threshold, headcount, fiscal quarter, replacement-signoff chain) not produced within 7 days | Downgrade to Approach A (contradiction-only wedge); reframe Phase 1 as a publishable internal whitepaper deliverable | Project lead |
| **Week-2 complaint root cause** | Audit of 30-50 client complaint tickets shows <50% are missed-relationship / contradiction class (per rubric in design doc) | Downgrade to Approach A or pause for re-scoping | Project lead + sponsor |
| **Week-2 VectifyAI bake-off** | VectifyAI managed service produces comparable-or-better structural indexing quality on PBM PDFs AND procurement is plausible within Quarter 1 | Pause Approach B (Phase-2 candidate); revisit with bake-off data; do NOT commit custom-build engineering without sponsor sign-off on the build-vs-buy reversal | Project lead + sponsor |

## Phase-1 gates (Weeks 3-6)

| Gate | Trigger | Decision | Owner |
|---|---|---|---|
| **Week-3 structure prototype (kill — Phase-2-only)** | 5-doc POC achieves <85% F1 on boundary identification per Premise 3 rubric (kappa ≥ 0.7 inter-analyst floor required) | Pause Approach B; reclassify P3 as research not engineering. **NOT a Phase-1 gate for D + guardrails.** | Tech lead |
| **Week-4 D extraction precision regression (CRITICAL — Phase 1)** | D's modified extraction shows extraction-precision regression >5% on existing field types (per iso-precision regression suite, T10) | Pause D rollout; flip `paiq.d_extraction.enabled` to `false` (revert to baseline prompts via feature flag); root-cause regression before continuing | Tech lead |
| **Week-6 guardrails FP rate (CRITICAL — Phase 1)** | Guardrails counter (1) / total > 15% (too aggressive) OR < 1% (too permissive). Counter (1) = rejected-then-same-edge AFTER canonicalization | Tune guardrails thresholds; if still out of band after 1-week tuning, disable guardrails and continue with D-only | Tech lead |

## Phase-1 / Phase-2 boundary gates (end of Q1)

| Gate | Trigger | Decision | Owner |
|---|---|---|---|
| **Quarter-1 latency gate** | Graph construction + queries on representative document exceed 20% of confirmed per-document SLA budget (SLA confirmation owed Week 1) | Performance optimization required before Phase 2; failing that, restrict graph features to async / post-extraction surface | Tech lead |
| **Quarter-1 D shadow result (Phase-2 promotion gate)** | D-mode extraction precision on relationship-class edges <85% per Wilson lower-bound (NOT point estimate) OR recall <80% per Wilson lower-bound | Pause Phase 2 commitment; D is not yet ready for client-facing rollout; consider longer Phase-1 shadow OR triage to Approach E (consistency-only fallback) | Project lead + sponsor |
| **Capacity overrun (biweekly check)** | Engineering capacity over-committed against actual sprint throughput on either track in biweekly cross-project review (NOT phase-boundary only — 11.3 and Cascade-OCR phases are not aligned) | Sponsor sign-off required to continue both; otherwise sequence (finish 11.1-B Phase 0/1 first, then start 11.3-B) | Project lead + engineering manager |

## Phase-2 candidate revisit triggers (deferred from iter-4 + iter-5)

These are NOT Phase-1 gates. They're the conditions under which a deferred
Phase-2 candidate can be promoted to active scope.

| Candidate | Revisit trigger |
|---|---|
| Approach B (graph engine as query layer) | D Phase-1 shadow data shows relationship-extraction precision ≥85% (Wilson lower-bound) AND analyst feedback identifies query patterns that would benefit from a graph query layer |
| Approach F (embedding similarity) | D Phase-1 shadow data shows ≥20% of remaining false-negative complaints are paraphrase / semantic-equivalence class that explicit-edge extraction cannot catch |
| OSS release | B Phase-2 ships AND differentiation story documented AND Cognizant legal cleared OSS license (Apache 2.0 or MIT preference) |
| Research publication | D Phase-1 shadow data N ≥ 50 documents AND external collaborator identified AND venue submission window aligns |
| Cross-document corpus graph (Phase 3+) | Per-document graph ships AND contradiction-detection precision sustained ≥85% AND cross-tenant or cross-PBM-plan query becomes a sponsor priority |

## Statistical significance gate (applies to ALL precision/recall thresholds)

Per D12: all percent thresholds in the Kill Criteria above use the **lower bound
of a 95% confidence interval**, NOT the point estimate. Standard Wilson interval
for binomial proportions; Clopper-Pearson if Wilson assumptions don't hold (small
N). Prevents point-estimate noise from triggering kill or pass on N=50 shadow docs
with sparse relationship-class events.

## Decision flow visualization

```
       Sponsor commitment in writing (Week 1)?
         │
         ├──no──▶ Downgrade to Approach A
         │
         └──yes─▶ Complaint audit shows ≥50% relationship-shaped (Week 2)?
                   │
                   ├──no──▶ Downgrade to Approach A or re-scope
                   │
                   └──yes─▶ Iso-precision regression on existing fields ≤5% (Week 4)?
                             │
                             ├──no──▶ Flip paiq.d_extraction.enabled=false; revert
                             │
                             └──yes─▶ Guardrails FP rate in [1%, 15%] (Week 6)?
                                       │
                                       ├──no──▶ Tune 1 wk → if still bad, disable
                                       │        guardrails, continue with D-only
                                       │
                                       └──yes─▶ Quarter-1 latency ≤20% SLA AND
                                                D shadow precision Wilson-lower
                                                ≥85% AND recall ≥80%?
                                                  │
                                                  ├──no──▶ Pause Phase-2 commit
                                                  │
                                                  └──yes─▶ Phase 2 promotion possible
                                                          (cherry-pick from candidates)
```
