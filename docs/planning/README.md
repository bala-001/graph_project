# Planning Artifacts

JSONL task lists from the planning sessions that produced this project. Both
are direct inputs for `/autoplan` aggregation if you choose to use it.

## Files

- **`eng-review-tasks.jsonl`** — 14 implementation tasks (T1-T14) from the
  `/plan-eng-review` iter-5 pass on the standalone 11.3 CEO plan. This is the
  authoritative work list for Phase 1 implementation. Mirrored in human-readable
  form in `../../TODOS.md`.

- **`ceo-review-tasks.jsonl`** — 7 strategic / political execution tasks from
  the standalone 11.3 `/plan-ceo-review` iter-4 (post-shrink). Pre-Phase-1
  prerequisites (eng headcount confirm, Phase-0 framing gate, D scope confirm,
  descope playbook, Phase-2 revisit-trigger doc).

## Source

These files originate from gstack's project artifacts directory at
`~/.gstack/projects/projects_poc_innovations/`. The copies here are pinned to
the timestamps when this project was scaffolded — if you want the latest gstack
state, re-copy from there.

## JSONL schema

Each line is one task:

```json
{
  "phase": "eng-review" | "ceo-review",
  "run_id": "...",
  "branch": "...",
  "commit": "...",
  "id": "T1",
  "priority": "P1" | "P2" | "P3",
  "component": "d-extraction-schema",
  "files": ["..."],
  "effort_human": "~3 days",
  "effort_cc": "~4 hr",
  "title": "...",
  "source_finding": "..."
}
```

P1 = blocks ship, P2 = land same branch, P3 = follow-up TODO.
