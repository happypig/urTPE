# Design — emit-stage-index

## Context

`graph.py:build_project_graph` builds each node dict by explicit keys; the
cleanser (`cleanse.py:_stage`) derives `stage_index` from the stage text, and
`CleanRecord.stage_index` carries it through the pipeline — but the node dict
never includes it. The `--from-js` loader (`cli.py:_load_projects_from_js`) then
reads `node.get("stage_index", -1)`. `graph.py:108` groups section branches by
`(r.stage_index, r.track)`; with every node at `-1`, distinct stages of one track
collapse into one group and the `section` edges never form.

The `ymd` fix (documented at `urtpe/cli.py:83`) is the precedent: the emitter
never wrote `ymd`, so the loader's `node.get("ymd", (0,0,0))` silently degraded
ordering; the fix derived `ymd` from the ISO date on load. This change applies
the same two-sided repair to `stage_index`.

## Goals / Non-Goals

Goals:

1. Emit `stage_index` on every node from `build_project_graph`.
2. Derive on load when the key is absent — repairing every already-deployed
   `projects.data.js` without re-ingestion.
3. Round-trip losslessness, pinned by test.

Non-Goals:

- Changing the stage text or the `_stage` derivation rule.
- Emitting any other missing CleanRecord fields (a separate audit; `stage_index`
  is the one with a demonstrated consumer).

## Decisions

### D1 — Emit the field the cleanser computed, not a re-derivation

`build_project_graph` writes `r.stage_index` (the cleanser's value, already on
the CleanRecord). The loader-side derivation exists only for documents emitted
before this change. One rule, two application points — never two rules.

### D2 — The loader derivation calls `cleanse._stage`

The loader imports `cleanse_mod._stage(node.get("stage") or "")` — the same
function that produced the original value — rather than reimplementing the
regex. `_stage` is pure text-in/tuple-out, so the adapter stays thin.

### D3 — The section-edge grouping test drives the fixture

The test builds a family with three stages (擬訂/變更/變更(第二次)) whose records
carry distinct `area_section` values (甲/A/B), emits, loads via the real loader,
re-emits, and asserts the `section` edges match the original. This is the
failure the bug produces, stated end-to-end — not a field-presence check that a
partial fix could satisfy.

## Risks / Trade-offs

- **`_stage` is private.** Importing it from the loader couples the adapter to a
  cleanser internal. Accepted: it is the same module the loader already imports
  (`cleanse`), the alternative is duplicating the regex (two rules to keep in
  step), and the function is pure and stable.

## Open Questions

(none)
