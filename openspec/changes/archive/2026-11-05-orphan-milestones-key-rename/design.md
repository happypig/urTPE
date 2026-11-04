## Context

Board D1 (name wrong, data right — verified by code path, date shapes, live
probe) + the D4a pipeline half (first-holder provenance; board-decided
2026-11-05). One re-emit covers both.

## Goals / Non-Goals

**Goals:**
- The payload stops claiming Taipei data is national.
- An equal construction date credits the first case read.
- Old payloads keep rendering (`--from-js` alias).

**Non-Goals:**
- No rename of the project-level `milestones_national` (that one IS national).
- No `_ghost_node_date` change (D2a is a separate change, rides the next emit).

## Decisions

### D1 — the new key is `milestones_taipei_case`

The dict holds ONE case's ashx milestones (the orphan's), so it is neither the
merged `milestones_taipei` nor national. `_case` names the per-case scope; the
alternative `milestones_case` loses the source-space truth D1 exists to
restore.

Emit site: `urtpe/links.py:3287` writes the orphan dict under the new key.
Viewer read site: the virtual-node build (`viewer/app.js:906`) maps
`milestones_taipei_case` into the node's badges. Load alias in
`_load_projects_from_js`: `node["milestones_taipei_case"] =
node.pop("milestones_national")` when the new key is absent AND the node is an
orphan (project-level dicts are untouched).

### D2 — first holder wins: two merge sites stop overwriting

- `merge_stage_milestones` (`urtpe/links.py:2218`): `if label in all_ms and
  all_ms[label] == v: return` — keep the first credit for an equal value; a
  DIFFERENT value keeps last-write-wins (a re-dated row is new information).
- `pick_implementation_payload` (`urtpe/links.py:2190-2191`): the conflict
  branch stays for differing values; for an equal value `source.setdefault` —
  actually the loop keeps the first value already; only `source[label] = cid`
  must move under the `dates[label] != value` guard.

### D3 — the re-emit runs once, after the code lands

`python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer
viewer --links` under the single-writer lock. Expect: 682 projects unchanged;
orphan keys renamed; 15 dates in 11 projects re-credited (榮星53 建照+使照 →
09001120; 蘭雅52 建照+開工 → 10210081; 寶清353-2 建照+開工 → 10001251; 懷生16
建照 → 09503203; the rest). Viewer measurement after: 榮星53's recno → 使照
edge gone (only 南港729 keeps one, completing D4a).

## Risks / Trade-offs

- [Old payloads without the alias break] → the alias covers them; a test
  loads a fixture with the old key.
- [The alias masks a future accidental `milestones_national` on an orphan] →
  the emit site writes the new key; the alias only fires when the new key is
  absent, and D1's spec scenario pins the name.
- [Equal-value semantics change] → the provenance validation and the viewer
  tests both assert the first holder; the 15-date list is the acceptance set.

## Migration Plan

Code + tests → re-emit → corpus checks (acceptance list above) → commit the
emitted state.

## Open Questions

None.
