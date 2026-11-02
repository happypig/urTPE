## Context

Actors: the city platform (`Get_updcase_list` parcel search, `get_project168_top`
case header, `Get_project168_second` data2), the operator running
`scripts/refresh_awaiting_caches.py`, the per-project link cache (durable middle
layer, not in git), the emission and the viewer. The change stays in the link
layer beside PDF → raw → clean → merged → projects.json (+ viewer); no
cleansing, merge, identity, gate or exit code moves.

Measured 2026-11-02: the two `無` cases (11211211, 10806141) each have exactly
one same-project case with the identical header `CASE_NAME`, a greater id, and a
data2 map that is a superset of theirs. 10806141's successor 11510017 is absent
from its cache; the parcel search for 虎林段四小段 38 returns it with 審查中.
`無` is observed on these two only — a sample, not a law, so the "no successor
found" bucket is reported by name.

## Goals / Non-Goals

**Goals:** a `無` case stops wearing a stale status; a re-filed case is recorded
as superseded and stops being selected; a case filed after the cache was
written is found for every selected project; every addition and supersession
is auditable.

**Non-Goals:** discovery for unselected projects (the 336 shape); graph changes
for superseded virtual nodes; teaching `fresh=True` discovery to keep the new
fields.

## Decisions

### D1 — `refreshed_schedule(cached, derived, milestones, no_state=False)`

`no_state` is true when the header row exists and its `NAME` is `無` or empty.
Then: cached ∈ {審查中, 已核准, 已核定} → ""; anything else (terminal, later stage,
"") → cached. Without `no_state` the §36 rule stands. A missing row
(`{}`) never sets `no_state` and records no header.

### D2 — `find_superseding_case(cid, case_milestones, header_names) -> (succ, why)`

Pure. Candidates: other cases with `header_names[other] == header_names[cid]`
(both non-empty), `int(other) > int(cid)`, and
`all(case_milestones[other].get(k) == v for k, v in dated(cid))`, with
`len(dated(cid)) >= 3`. One → `(other, "")`; none → `("", "none")`; several →
`("", "ambiguous")`. The header name is the second witness beside the date
subset (a subset alone can match by accident on sparse cases).

### D3 — New cache fields, append-only case list

`DiscoveryResult` gains `case_headers: {cid: NAME}` and
`superseded_by: {old: new}`; old caches load with empty defaults
(`DiscoveryResult(**data)`). New search ids are appended to `city_case_ids`
after the existing ones — never sorted — and get `case_milestones[cid] = {}`
plus `candidate_names` / `case_schedules` (search status) before the per-case
loop re-reads them, so the loop and the twin pass see them.

### D4 — Search key comes from the emitted anchor, adapter defaults like D4 of §36

`refresh_project(..., search=None, search_key=None)`. `search_key =
(section, first_parcel, anchor_name)` is read by the script from
`viewer/projects.data.js` (the anchor node; all 693 carry 地段 + 地號), never
parsed from `project_id` (churns; 6 ids do not parse). `search` defaults to
`search_taipei_cases_api` only on the production path (`fetch` also defaulted);
an injected `fetch` alone keeps tests offline. No `search_key` → reported "not
searched". A raising search returns an error before any write.

### D5 — Selector

`cached_cases_awaiting_approval(case_milestones, case_schedules=None,
case_headers=None, superseded_by=None)` skips terminal, header-`無` and
superseded cases. The script passes all four.

### D6 — Payload and viewer

The attach copies `superseded_by` into `links.superseded_by` when non-empty; the
`--from-js` reload copies it back (field-by-field object — a missing line
drops it silently, so a round-trip test pins it). The viewer's 相關連結 entry
for a key of the map renders `已由 <succ> 取代` instead of the badge.

## Risks / Trade-offs

- [`無` means something other than "superseded" elsewhere] → only in-review /
  approved words are cleared; no-successor cases are reported by name.
- [Search adds a case owned by a neighbouring project] → same guard discovery
  uses; the attach's landcore gate still filters orphans downstream; every
  addition is reported; growth of `links.taipei` is checked against the report.
- [A superseded case revived] → not re-selected; re-read whenever its project is
  refreshed for another case.
- [`fresh=True` discovery drops the fields] → recorded residual.
