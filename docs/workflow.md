# Workflow — PAIQ Idea 11.3 Phase 1 (Approach D + Guardrails)

How relationship-aware extraction (Approach D) and extraction-time guardrails
work end to end. These diagrams render natively on GitHub.

Source of truth for each box is cited as `module` so the diagram stays honest
against the code:

- `src/d_extraction/` — Pydantic edge schema + provider structured-output prompts
- `src/guardrails/` — 4 detectors, retry policy, 3-counter FP telemetry, canonicalization
- `src/journal/` — batched-write journal + crash-recovery replay
- `src/feature_flags/` — `paiq.d_extraction.enabled`
- `src/shadow/` — D-output vs analyst ground-truth comparison
- `src/telemetry/` — FP-rate counters / observability
- `src/cascade_integration/` — cascade-OCR judge re-calibration

---

## 1. End-to-end pipeline (happy path)

A PBM document is chunked. Each chunk is extracted via provider built-in
structured outputs, every emitted edge is checked by guardrails BEFORE the next
chunk commits (D10 multi-turn protocol), accepted edges are journaled, and the
document is only materialized (and made visible downstream) once all chunks pass
and `extraction_complete` is set true.

```mermaid
flowchart TD
    DOC([PBM document]) --> FLAG{paiq.d_extraction.enabled?}
    FLAG -- false --> BASE[Baseline extraction<br/>fields only, no edges]
    FLAG -- true --> CHUNK[Chunk document into N segments]

    CHUNK --> LOOP{{for each chunk i}}
    LOOP --> LLM[D-mode extraction prompt i<br/>OpenAI json_schema strict<br/>OR Anthropic tool-use<br/>emits fields + edges]
    LLM --> GR[[Guardrails check per edge<br/>consult partial-edge state]]
    GR --> VERDICT{Verdict}
    VERDICT -- ACCEPT --> JOURNAL[(Batched journal<br/>10 edges OR 5s)]
    VERDICT -- REJECT_RETRY --> RETRY[Retry policy<br/>validator error in prompt<br/>max 3 retries]
    RETRY --> JOURNAL
    JOURNAL --> NEXT{more chunks?}
    NEXT -- yes --> LOOP
    NEXT -- no --> MAT[Materialize document state<br/>final flush -> collapse journal<br/>set extraction_complete = true]
    MAT --> JSON[(In-document JSON metadata)]
    JSON --> DS[Downstream consumers<br/>analyst tools / client reports]
    DS --> CHECK{extraction_complete?}
    CHECK -- false --> INVIS[INVISIBLE<br/>treat as not-yet-extracted<br/>24h GC re-queues]
    CHECK -- true --> SURFACE[Surface fields + edges]

    BASE --> JSON
```

---

## 2. The guardrails loop (per emitted edge)

The detector runs four scenarios in a fixed order; the first hit short-circuits
to `REJECT_RETRY`. On rejection, the retry policy asks the model to re-extract
with the validator error attached, and classifies the outcome into one of three
mutually exclusive FP-telemetry counters.

```mermaid
flowchart TD
    EDGE([Emitted edge]) --> CANON[Canonicalize<br/>canonical drug IDs, sorted qualifiers<br/>shared subject/object key space]
    CANON --> D1{1 Circular<br/>dependency?}
    D1 -- yes --> REJECT
    D1 -- no --> D2{2 Prerequisite<br/>chain mismatch?<br/>requires vs excludes}
    D2 -- yes --> REJECT
    D2 -- no --> D3{3 Contradictory<br/>limits?<br/>min &gt; max range}
    D3 -- yes --> REJECT
    D3 -- no --> D4{4 Age<br/>conflict?<br/>exact age mismatch}
    D4 -- yes --> REJECT
    D4 -- no --> ACCEPT[[ACCEPT -> journal.append]]

    REJECT[[REJECT_RETRY]] --> R{Retry up to MAX_RETRIES = 3}
    R -- same canonical edge --> C1[Counter 1: real FP<br/>accept the edge]
    R -- different edge, now passes --> C2[Counter 2: TP<br/>model corrected, accept]
    R -- exhausted, never converged --> C3[Counter 3: analyst flag<br/>accept nothing]

    C1 --> TEL[(Telemetry<br/>FP rate = counter1 / total<br/>Week-6 gate: 1-15%)]
    C2 --> TEL
    C3 --> TEL
```

---

## 3. Journal write path (D7 — persist-as-you-go)

Accepted edges land in an in-memory buffer flushed to a per-document journal file
every 10 edges OR 5 seconds. On completion the journal is replayed and collapsed
into canonical JSON. A crash mid-document leaves `extraction_complete=false`, so
the partial row is invisible downstream and is GC'd / re-queued after 24h.

```mermaid
flowchart LR
    E([accepted edge]) --> BUF[in-memory buffer]
    BUF --> T{len &gt;= 10<br/>OR 5s elapsed?}
    T -- no --> BUF
    T -- yes --> APP[append batch to<br/>document_id.journal<br/>one JSON line per edge]
    APP --> BUF
    APP --> DONE{extraction complete?}
    DONE -- no --> BUF
    DONE -- yes --> COLLAPSE[final flush -> replay journal<br/>write document_id.json<br/>extraction_complete = true]

    APP -. crash .-> RECOVER[replay on restart<br/>flag stays false<br/>24h GC re-queues]
```

---

## 4. Shadow path (how we measure D before it ships)

Runs in parallel with the production pipeline. Baseline (existing prompts) and
D-mode run on the same document; the harness computes edge precision/recall vs
analyst-corrected ground truth (Quarter-1 gate) and iso-precision regression on
existing fields (Week-4 gate). Wilson lower bounds defend the gates against
small-N point-estimate noise.

```mermaid
flowchart TD
    DOC([PBM document]) --> B[Baseline extraction<br/>fields only, edges = none]
    DOC --> D[D-mode extraction<br/>fields + edges]
    B --> CMP[[Shadow comparison<br/>src/shadow/harness.py]]
    D --> CMP
    GT[(Analyst-corrected<br/>ground-truth edges)] --> CMP

    CMP --> M1[Edge precision / recall<br/>+ Wilson 95% lower bound]
    CMP --> M2[Field iso-precision delta<br/>regression if &gt; 5%]
    M1 --> DASH[(Telemetry dashboard)]
    M2 --> DASH
    DASH --> KILL{Kill Criteria gates}
    KILL --> W4[Week-4: &gt;5% field regression -> revert flag]
    KILL --> W6[Week-6: FP rate outside 1-15% -> tune/disable]
    KILL --> Q1[Quarter-1: edge precision &lt;85% OR recall &lt;80% -> no Phase 2]
```

---

## 5. Module boundaries

Who owns what, and the one-directional dependencies between modules.

```mermaid
flowchart TD
    subgraph EXTRACT[src/d_extraction]
      SCHEMA[schema.py<br/>Edge / DocumentExtraction<br/>canonicalize_edge]
      PROMPTS[prompts.py<br/>D-mode + BASELINE_PROMPTS]
      EXTRACTOR[extractor.py<br/>multi-call loop]
    end
    subgraph GUARD[src/guardrails]
      DETECT[detector.py<br/>4 scenarios]
      RETRYM[retry.py<br/>policy + 3 counters]
      STATE[state.py<br/>PartialEdgeState]
    end
    JOURNALM[src/journal<br/>writer + replay]
    FLAGS[src/feature_flags<br/>paiq.d_extraction.enabled]
    SHADOWM[src/shadow<br/>harness]
    TELEM[src/telemetry<br/>FP counters]
    CASCADE[src/cascade_integration<br/>OCR judge re-cal]

    EXTRACTOR --> DETECT
    DETECT --> STATE
    RETRYM --> DETECT
    DETECT --> SCHEMA
    EXTRACTOR --> JOURNALM
    JOURNALM --> SCHEMA
    FLAGS --> PROMPTS
    SHADOWM --> JOURNALM
    SHADOWM --> SCHEMA
    RETRYM --> TELEM
    CASCADE -. one-time pre-ship .-> EXTRACTOR
```

---

## Key invariants

- Provider structured outputs enforce **shape, not semantics** — a schema-valid
  edge can still be logically wrong. Guardrails + the eval suite are the semantic
  defense, not the schema.
- Guardrails fire **after each LLM call, before the next chunk commits** (D10).
- `extraction_complete=false` rows are **invisible** to downstream consumers and
  GC'd after 24h (D12).
- FP rate is **counter 1 / total** with canonicalization (D4); the Week-6 gate is
  1-15%.
- The feature flag `paiq.d_extraction.enabled` is the **instant-revert** path; the
  baseline prompt path stays in the code.
