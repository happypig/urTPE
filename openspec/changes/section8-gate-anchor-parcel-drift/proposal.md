## Why

The §8 gate (batch D, `reject-foreign-view-cases`) decides whether a case id
that a project's national view page names really belongs to that project. It
compares the land core of the city's case name with the land core of the
project, at `LINK_THRESHOLD = 0.7`. A land core keys on the **first parcel**.

The gazette prints two parcel lists for one unit, and they can start with
different parcels. 萬華區-華中段一小段-247地號等26筆 is the measured case. The
地號 cell lists 26 parcels and starts at `247`. The 案名 names `201-2、352`.
All three gazette rows (編號 14, 1084, 1131) show this. The project's land core
keys on `247`. The city's case names key on `201-2`. The two cores score 0.45
and the gate says "another project" (shape A).

The effect is visible. The city's parcel search finds seven cases for this unit
by the parcel guard, which accepts a case when its name carries one of the
unit's **own** parcels. The five ids it finds without the view page stay in
相關連結. The two ids that the view page names — `09305081` (擬訂, A區) and
`09407302` (變更, B區) — go through the gate, fail at 0.45, and leave the
project. The gate rejects the five held ids as well when it is run on them
(replayed 2026-11-15). Only the route decides which ids it sees. One id gets
two rules.

The user found this on 2026-11-15 and asked for a full change. The evidence is
in `docs/inspection-batchE.md`, section E10.

## What Changes

- The §8 gate accepts a view-named id when the city's case name declares the
  **same section** as the project and **one of the project's own parcels**.
  This is the rule the parcel search already uses (`own_parcels`), plus a
  section check the search gets from its query. A case in the same section
  that names none of the unit's parcels stays rejected.
- The refresh passes the unit's own parcel list to the gate. Without a parcel
  list the gate behaves as before.
- A rejection recorded under the old rule is **re-decided** under the current
  rule. Today (S3a) a recorded rejection is final. After this change a
  rejection stands only while the current rule still rejects the id. The three
  ids below return to their project on the next refresh.
- One refresh of the affected caches and one re-emit. The re-emit is the last
  step, as in every earlier batch.
- No change to the shape A / shape B reasons, to the missing-city-name rule, to
  the offer step, or to the 0.7 threshold.

### Population (measured 2026-11-15, all 675 payload projects)

`view_rejected` holds **11 ids in 10 projects**. Under the new rule:

| Outcome | Ids | Projects |
| --- | --- | --- |
| Return (anchor-parcel drift) | 09305081, 09407302 | 華中247 |
| Return (anchor-parcel drift: 案名 names `247`, the cell's second parcel) | 09102220 | 吳興163-2 |
| Stay rejected (a district mismatch, **not** drift: the cache's land core says 中正區, the project and the case say 大同區) | 09609301 | 市府220-2 |
| Stay rejected (foreign: another district or section) | 7 ids | 7 projects |

One of the seven foreign ids (09608220 on 犁和段一小段-102) is in the same
section as its project and names parcel `165`, which is not the unit's. It is
the reason the section check alone is not enough. The parcel test must stay.

The 市府220-2 cache has a land core with the wrong district. That is a separate
defect. This change names it and does not repair it.

Scope is gated on the measurement above. It counts only rejected ids that the
payload holds. A view-named id that was never recorded (a cache older than the
gate) is not in the population.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cache-freshness`: the view-verified verification gains the own-parcel
  acceptance, and a recorded rejection is re-decided under the current rule.
- `orphan-case-anchoring`: the portal-verified orphan gate gains the same
  acceptance, so a re-accepted id anchors or becomes a ghost like any other.

## Impact

- `urtpe/links.py`: the gate function, and the refresh step that calls it.
- 569 caches gain the `own_parcels` field (an offline backfill from the payload,
  each `result.json` copied to a dated backup first; 26 more caches hold view ids
  but have no project in the payload and are named and skipped). Only the
  content of three changes: 華中247 (two ids re-added, their milestones fetched,
  two city requests) and 吳興163-2 (one id leaves `view_rejected`, no new
  request).
- The re-emit moves the node badges for nodes that anchor the returned ids. The
  `national_badges` counters in `tests/test_national_badge.py` need a new pin.
- 華中247's A區/B區 cases that share a date join one node, so that node holds
  two cases. A second section in its callout (the E7 shape) appears only if both
  cases have implementation payloads. The re-emit measures that; it is not
  promised.
- Cost: the usual ~24 MB tracked diff from a re-emit. Stage deliberately.
