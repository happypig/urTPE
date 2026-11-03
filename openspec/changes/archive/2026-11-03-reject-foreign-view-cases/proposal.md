# Proposal: reject-foreign-view-cases

## Why

Planners reading the viewer graph see another project's dates on a project's
graph. Three nameless 孤 anchors carry milestones of **other** projects
(docs/viewer-UX.md §8, reported 2026-11-03):

| Project | case_id | The city's case name for that id | Owning project |
| --- | --- | --- | --- |
| 中山區-中山段一小段-254地號等13筆 | 10202065 | 變更(第四次)臺北市大安區辛亥段一小段163地號等5筆…權利變換計畫案 | 大安區-辛亥段一小段-163地號等5筆 |
| 大安區-大安段一小段-557地號等16筆 | 09511211 | 擬訂臺北市中山區吉林段四小段603地號等40筆…事業計畫案 [施工中] | 中山區-吉林段四小段-603地號等40筆 |
| 大安區-龍泉段一小段-169地號等29筆 | 09807161 | 擬訂臺北市內湖區康寧段二小段262地號等29筆…事業計畫及權利變換計畫案 | 內湖區-康寧段二小段-262地號等29筆 |

The cause: the ids entered through `view_verified_case_ids` — each project's
own national view page lists the case in 相關連結， and
`openspec/specs/orphan-case-anchoring/spec.md` keeps a view-verified id even
when its similarity is below 0.7, because "the portal itself asserts the case
belongs". The national portal is wrong in two shapes:

- **Shape A — the link names another project.** The 相關連結 label is the
  other project's name; the pipeline takes the id and ignores the label.
  Measured: 10202065 (辛亥段163), 09807161 (康寧段262), 10906092 (莒光段519-3,
  on 中山吉林898), 09608220 (犁和段165, on 信義犁和102).
- **Shape B — the label is right, the id is wrong.** view/178 labels 09511211
  "擬訂臺北市大安區大安段一小段557…", but the city's own case 09511211 is
  吉林段四小段603 (its platform name, live-verified in 603's cache). Only the
  city's own case name shows this.

Because the anchors carry the other project's milestones, the graph shows
another project's 建照 / 開工 dates (09511211 施工中， 09807161 已完工). Wave 4
(bind-national-badge-to-named-node) reads `view_verified_case_ids` for the 國
badge without checking the city's own case name, so a wrong view-verified id
also gives a wrong 國 badge. Inspection board B7 + B8: B7 (a view-verified case
may belong to another project) must land before the badge is trusted; B8 (the
3 nameless anchors) must land before wave 5's orphan placement is trusted for
those 3 nodes.

## What Changes

- The pipeline verifies each view-verified id against the **city's own case
  name** (`get_project168_top` `CASE_NAME`, stored during the refresh): the id
  stays view-verified only when its city name's land core matches the
  project's. The 相關連結 label is compared too, but only for the reason text —
  a label that names another project while the city name matches is accepted
  with the label error logged (decision-table row 4: 10906092).
- A rejected id is **named, not dropped silently**: it moves to a new
  `view_rejected` cache field with its reason (shape A / shape B / ambiguous
  owner / label-not-confirmed).
- A rejected id whose city name's land core matches exactly one other
  project's land core is **offered to that project**: added to its
  `city_case_ids` with milestones fetched, recorded as `adopted_from_view` in
  the target and `view_rejected` in the source. No match or more than one
  match: it stays only in `view_rejected` (ambiguous owner — the same
  no-guess rule `data/project_aliases.json` uses).
- A case id the offer adopts onto a project whose own parcel search would
  have rejected it stays auditable through the two recorded fields.
- A header the refresh could not read is **no evidence**: the id is kept with
  reason "label not confirmed" and is not rejected for missing data (the
  `header_has_no_state` rule).
- Then a targeted refresh + re-emit under the single-writer lock, one run
  writing both the source and the target caches (same commit pattern as §7
  decision 4).

## Capabilities

### Modified Capabilities

- `orphan-case-anchoring`: the view-verified exception gains the city-name
  land-core gate (MODIFIED).
- `cache-freshness`: the refresh verifies view-verified ids by the city's own
  case name, records `view_rejected` / `adopted_from_view`, and reports every
  rejection and offer (MODIFIED).
- `official-link-discovery`: the 相關連結 absorb no longer treats the page's
  assertion as unconditional — the emitted `links.view_verified_case_ids`
  carries only ids whose city name confirms the unit (MODIFIED).

## Impact

Pipeline + cache + payload. 146 caches hold view-verified ids (193 ids); the
decision pass re-checks them, then the 3 nameless 孤 anchors leave the corpus
and 09511211/09807161/10202065 land on their owning projects' caches (09807161
→ 內湖康寧262 and 09608220 → 犁和165 already hold them; 10202065 → 辛亥163
already holds it; 09511211 → 吉林603 already holds it — the offer fills the
remaining fields). 10906092 stays view-verified on 中山吉林898 (city name
matches; the label error is logged). Re-emission rewrites the ~23 MB of
tracked data files.
