# TODOS

Captured from eng-review iter-5. Format per gstack convention: what / why / pros / cons / context / depends-on.

## Phase-1 implementation tasks (from eng-review JSONL T1-T14)

Full list at `~/.gstack/projects/projects_poc_innovations/tasks-eng-review-20260526-173441.jsonl`. P1 tasks ordered roughly along the critical path.

> **Implementation status (updated).** The codebase is now engineering-complete
> and deployable offline (68 tests pass, 91.9% coverage, `paiq-d` CLI + Docker +
> CI). Built: T2, T4, T5, T6, T7 (in-process), T9 (edge tests), T12, T13, plus
> the end-to-end pipeline, provider abstraction (mock/openai/anthropic), and
> functional eval runners (T3/T10/T11 against a synthetic sample). Still gated on
> Phase-0 org inputs (cannot complete here): **T1** real provider prompts (Q3),
> **T8** F6 labels, and the **live** T3/T10/T11 runs + the per-field regression
> suite on real labels. Provider+prompts ship as templates behind a flag that
> defaults OFF. See `docs/planning/phase1-implementation-plan.md` and
> `docs/DEPLOYMENT.md`.

- [ ] **T14 (P3, ~3 days)** — Write D integration spec at `docs/architecture/d-integration-spec.md`. **Lands before any code.** F1 deliverable.
- [ ] **T1 (P1, ~3 days)** — Define Pydantic edge schema + wire provider built-in structured outputs (OpenAI `response_format: json_schema` strict OR Anthropic tool-use mode). Output: `src/d_extraction/schema.py` + provider config.
- [ ] **T8 (P1, ~1 wk)** — Extend cascade-OCR eval set with relationship-type labels + contradiction-validity labels per F6 / D5. Can run in parallel with T1.
- [ ] **T2 (P1, ~1 wk)** — Persist-as-you-go partial-edge state with `extraction_complete` flag. Depends on T1.
- [ ] **T5 (P1, ~1 wk)** — Batched-write journal (10 edges OR 5 sec, whichever first). Depends on T2.
- [ ] **T4 (P1, ~2 wks)** — Guardrails component: 4 detection scenarios + reject/retry/exhaust policy + 3-counter FP telemetry with canonicalization. Depends on T2 + T5.
- [ ] **T3 (P1, ~3 days)** — Cascade-OCR judge re-calibration. Confirm judge-pass-rate ≥95% on D-mode output. Depends on T1. Can run in parallel with T2/T5.
- [ ] **T6 (P1, ~1 day)** — `paiq.d_extraction.enabled` feature flag + preserve baseline prompt. Depends on T1.
- [ ] **T7 (P1, ~3 days)** — Downstream consumer policy for `extraction_complete=false` + 24-hour GC of orphaned partials. Depends on T2.
- [ ] **T9 (P1, ~1 wk)** — 23 edge-focused tests covering all detection scenarios + retry counters + crash recovery. Depends on T4.
- [ ] **T10 (P1, ~3 days)** — ~10 iso-precision regression tests across ALL existing field types. **Mandatory per Week-4 Kill Criteria gate.** Depends on T1.
- [ ] **T11 (P1, ~1 wk)** — Shadow harness: D-output vs analyst-corrected GT on cascade-OCR eval set. Depends on T1 + T8.
- [ ] **T12 (P2, ~1 day)** — Apply Wilson / Clopper-Pearson lower-bound to Phase-2 trigger thresholds. Depends on T11.
- [ ] **T13 (P2, ~1 wk)** — D-specific observability: edge precision dashboard, guardrails firing rate, 3-counter FP telemetry. Depends on T4.

## Phase 0 prerequisites (must close before T1 starts)

- [ ] **Q1** — Confirm 2 engineers staffing for Phase 1 (2-2.5 quarters). Owner: engineering manager. Owed Week 1.
- [ ] **Q2** — Phase 0 framing-gate decision tree: if complaint audit reveals non-relationship-shaped pain dominates, what's the Phase 1 scope redirect? Owner: project lead + sponsor. Owed Week 2.
- [ ] **Q3** — Which extraction prompts / schemas change for relationship-aware native extraction? **Blocking T1**. Owner: tech lead. Owed Week 1.
- [ ] **Q8** — Guardrails reject/retry policy bounds (1-15% FP rate per Kill Criteria); retries before falling back to analyst flag. Owner: tech lead. Owed during Phase 1 design phase.

## Phase-2 candidates (DEFERRED — do not pull into Phase 1)

Each has an explicit revisit trigger. Do not start any of these without the trigger condition met AND sponsor sign-off.

### Approach B — In-house PageIndex-equivalent + extracted-fact graph as Phase-2 query layer
- **What**: Build the structural index over PBM PDFs + a graph query surface ON TOP of D's structured-edge output. Phase-2 architecture.
- **Why**: Once D ships and emits edges natively, B becomes a query system over D's output, not a parallel engine. Analysts and clients can ask "what are the full prerequisites for Drug A?" with traversal queries.
- **Pros**: Catches missed-relationship complaints clients can't articulate without a query language; enables Phase 3 cross-document queries; enables OSS release if differentiation story emerges.
- **Cons**: Engineering load is similar to D itself (~quarter+); commits to maintaining a graph-query surface long-term.
- **Context**: Was in iter-3 maximalist Phase 1; deferred in iter-4 per outside voice. Architectural relationship: B is a query layer over D, NOT a parallel engine. Phase 0 boundary-identification POC (5-doc kill + 50-doc greenlight, Cohen's kappa ≥ 0.7, F1 ≥ 85%) is gated to this Phase-2 work.
- **Revisit trigger**: D Phase-1 shadow data shows relationship-extraction precision ≥85% AND analyst feedback identifies query patterns that would benefit from a graph query layer.

### Approach F — Embedding-based semantic similarity layer (feature, not architecture)
- **What**: Embedding-based fuzzy-match layer that catches paraphrase / semantic-equivalence relationships explicit edges miss.
- **Why**: Pharma policy paraphrase ("must fail 2 drugs" ↔ "two prior therapy failures required") slips past explicit-edge extraction.
- **Pros**: Catches a class of false-negative complaints that D can't.
- **Cons**: Adds embedding-model dependency; less debuggable than explicit edges; ~2 weeks build.
- **Context**: Reclassified iter-4 from architecture to feature per outside voice. Sits inside B's Phase-2 scope as an enhancement.
- **Revisit trigger**: D Phase-1 shadow data shows ≥20% of remaining false-negative complaints are paraphrase / semantic-equivalence class.

### Approach D5-#3 — Open-source release of PageIndex-equivalent
- **What**: Release the in-house structural-index engine as OSS (Apache 2.0 or MIT) post B Phase-2 ship.
- **Why**: Reputation + recruiting + IP-stance coherence — if Cognizant is going to own the IP, owning it as a public asset is the strongest position.
- **Pros**: External-facing manifestation of the "build it ourselves" IP stance.
- **Cons**: Outside voice flagged differentiation question — generic PageIndex already exists; need a clear pharma-policy-specialized story before OSS makes sense.
- **Context**: Deferred iter-4 after outside voice; concrete differentiation gate added.
- **Revisit trigger**: B Phase-2 ships AND a differentiation story emerges AND Cognizant legal cleared OSS license.

### Approach D5-#4 — Research publication (ML4H / EMNLP healthcare / HEALTH-NLP)
- **What**: Publish complaint taxonomy + boundary-identification rubric + graph approach.
- **Why**: Personal + Cognizant credibility play.
- **Pros**: Career asset; defensible IP after publication.
- **Cons**: Outside voice flagged conflict-of-interest / external-validity concern. Needs external co-author or independent validation.
- **Context**: Deferred iter-4. Submission gated on data sufficiency + external collaborator.
- **Revisit trigger**: D Phase-1 shadow data N ≥ 50 documents AND external collaborator identified AND venue submission window aligns.

### Phase 3+ — Cross-document corpus graph (multi-PBM-plan consistency queries)
- **What**: Build a cross-document graph layer that enables queries like "is Drug A treated consistently across all 50 PBM plans?"
- **Why**: New product surface; commercial intelligence; differentiates Cognizant's PBM offering.
- **Context**: Captured in CEO plan; explicitly Phase 3+.
- **Revisit trigger**: B Phase-2 ships AND contradiction-detection precision sustained ≥85% AND cross-tenant or cross-PBM-plan query becomes a sponsor priority.

### Phase 0 boundary-identification POC (B-only, not Phase-1 D)
- **What**: 5-doc structure-prototype POC + 50-doc greenlight POC with Cohen's kappa ≥ 0.7 inter-analyst floor and ≥85% F1.
- **Context**: Design doc Premise 3 mitigation; ONLY relevant for Approach B (the structural index work). NOT a Phase-1 gate for D + guardrails.
- **Revisit trigger**: When Approach B promotes from Phase-2-candidate to Phase-2-committed.

### Approach C — VectifyAI managed-service hybrid (user-rejected)
- **What**: Use VectifyAI's PageIndex API for structural indexing instead of building in-house.
- **Why**: Faster path; eliminates structural-index engineering risk.
- **Cons**: Vendor lock-in; IP concern; procurement bureaucracy. User explicitly rejected in office-hours.
- **Revisit trigger**: ONLY if a Phase-0 bake-off (when B Phase-2 reactivates) shows VectifyAI quality is comparable AND sponsor explicitly signs off on the build-vs-buy reversal.

## Stale / closed items

- ~~Approach E (sequenced hybrid)~~ — deferred as the canonical Phase-1 descope fallback per Kill Criteria capacity gate. Not pulled forward.
- ~~T4 embedding-model-evaluation~~ — defers with Phase-2 Approach F.
- ~~T5 OSS legal approval~~ — defers with Phase-2 OSS candidate.
- ~~T6 paper-coauthor-and-draft~~ — defers with Phase-2 paper candidate.
- ~~T8 multi-arch-attribution-harness~~ — replaced with T8a D-only attribution (in current task list as T8a → relabeled to fit eng-review T1-T14 numbering above).
- ~~T10 design-doc-supersede~~ — unnecessary after iter-4 shrink restored design-doc baseline staffing.
