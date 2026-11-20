# Project inspection — viewer gen-2 exploration · collected 2026-11-19 (O1–O7)

Seven items. They explore whether the current Viewer interface can be reused for
a generation-2 Viewer that holds district-page applications and Viewer approval
records under one stable `project_uid`. Everything below was measured offline on
the current payload and on saved probe outputs, unless a section says it made
live requests. No probe ran against the pipeline beyond the saved outputs.

**Source and state.** Payload `data/projects.json`: 1,444 records / 675 projects,
統計至 2026-10-28. District pages: 3,655 distinct rows / 3,651 distinct `case_id`
values, read 2026-11-19. `P_project168.aspx` snapshot 2026-11-18T12:31:41Z,
468 IDs, checked live 2026-11-19. Probe outputs live in the session scratchpad,
not in the repo, and are named below where they matter.

**No change is open.** Each item below is a recommendation. The standing rule holds:
an openspec change opens on the user's word, one item at a time. A recommended
option is not a decision.

**Scope.** This board only decides whether gen-2 is plausible and what its
identity layer must prove. It does not design the Viewer UI, and it does not
change `projects.json`, `urtpe/`, `viewer/` or any pipeline contract.

---

## O1 — one `project_uid` for applications and approval records (the gen-2 identity)

**The question.** Can one Viewer show an application from the district pages and an
approval from the gazette as entries of the same project history?

**Measurement.** No repository code currently assigns a stable unit id across the two
sources. The current Viewer keys on `project_id` (the slug of the latest approval's
land core) and every node carries `recno`. District-page rows carry neither.

District pages do not ship `recno`. They ship `case_id`, `case_name`, `district`,
`place`, `implementer` and status. Four `case_id` values name two different cases on
two district pages. The Viewer has 3 `case_id` values absent from the district set,
all of them in the 松山 conflict cluster (`11510011`, `11510014`, `11510015`).

Therefore `project_uid` must be assigned by evidence — land-core similarity, parcel
history and named anchors — never by `case_id`, `recno`, or `project_id` alone.

| Identifier | Meaning | Stable? | Safe as a durable key? |
|---|---|---|---|
| `project_uid` | Stable id of one renewal unit | yes, if assigned by evidence | **yes** |
| `project_id` | Slug of latest approval's land core | churns (~11% of families moved) | no |
| `case_id` | Taipei portal lookup key per application | conflicts exist | no |
| `recno` | Gazette row coordinate within one PDF | not assigned to district rows | no |

**Proposed form.** Each pending application and each approval record points to one
`project_uid`. One unit can hold several applications. A later `project_id` change
never moves the UID. The identity assignment lives in an append-only ledger so a
wrong match can be split or merged later.

**Recommendation: build gen-2 on a new identity layer.** Do not reuse `project_id`
or `case_id` as the durable unit key.

---

## O2 — `case_id` is an application key, not a project key (the four conflicts)

**The question.** Can the Viewer's `links.taipei` set stay as-is under one `project_uid`?

**Measurement.** Four IDs name two different cases each:

| `case_id` | Row A | Row B | Live header names |
|---|---|---|---|
| `11509011` | 大同區 大同段一小段393地號等19筆… (品陽建設) | 松山區 敦化段二小段449-12地號28筆(原25筆)… (金朋建設) | 大同區 row |
| `11509014` | 大同區 圓環段一小段184地號等30筆… (柏合投資) | 松山區 寶清段二小段353-2地號等21筆…(A基地) (北碁建設) | 大同區 row |
| `11509015` | 中正區 臨沂段一小段357地號等16筆… (璞永建設) | 松山區 寶清段二小段353-2地號等21筆…(B基地) (北碁建設) | 中正區 row |
| `11510016` | 信義區 信義段二小段133地號等12筆… (友座建設) | 大安區 仁愛段五小段480地號等2筆(原1筆)… (合作金庫資產管理) | 大安區 row |

`11509014` and `11509015` are the A基地 and B基地 amendments of one 寶清段 project
under one implementer. `11510016` names cases in 信義區 and 大安區 with different
implementers; its 2026/10/13 application date belongs to the 大安 amendment
according to the Viewer cache.

**Proposed form.** Each application keeps its own `application_id` and `case_id`.
`case_id` links to `r_progress_detail.aspx?case_id=<id>` for status. `project_uid`
groups applications by unit evidence, not by `case_id`. The four conflicts stay
unmerged until independent evidence decides which row each ID belongs to.

**Recommendation: treat `case_id` as one application's portal key.** One project can
hold several `case_id` values. Do not group pending applications by `case_id` alone.

---

## O3 — meeting-label records cannot join projects

**The question.** Do the three `審議會` rows count as pending cases?

**Measurement.** All three sit in 大安區:

| `case_id` | 案名 | District status | Header status | Note |
|---|---|---|---|---|
| `11011301` | `516次審議會` | 事業計畫階段─業經幹事會審查 | same | no applicant, location or date |
| `11011021` | `511次審議會` | 事業計畫階段─業申請審議會審議 | same | same |
| `11010261` | `第522次審議會` | 事業計畫階段─業申請審議會審議 | same | same |

Their headers repeat the meeting label. They are not case names.

**Proposed form.** Keep them out of project counts. Keep them as labelled rows if
gen-2 ever lists district rows verbatim.

**Recommendation: exclude meeting-label records from pending-project counts.** They
need separate review before any identity assignment.

---

## O4 — the Viewer graph assumes `recno`; district pages have none

**The question.** Can `viewer/app.js` render district rows without changes?

**Measurement.** `viewer/index.html` and `viewer/app.js` read `project_id`,
`anchor_recno`, `member_recnos`, `nodes[].recno`, `published_date`,
`implementation`, `rewards`, `edges`, `links.taipei`. The pipeline fills every
node's `recno` and every project's `anchor_recno`. `viewer/app.js` line 146 checks
`(node.links || {}).taipei` for badge membership; line 935 uses
`p.member_recnos.length`; line 1359 prints `共 ${p.member_recnos.length} 筆`.

District rows carry none of `recno`, `anchor_recno`, `member_recnos`, gazette date,
approval stage, or edge history.

**Proposed form.** Gen-2 can reuse the list page layout and the graph drawing code,
but its payload schema differs:

- `application_id` instead of `recno` per row
- `application_date` instead of `core gazette approval date`
- pending-review stage vocabulary instead of gazette stage
- `links.taipei` still works as a `case_id` set for the detail link
- no `member_recnos`; use `member_applications` or leave it absent
- no edges until amendments link to a base application by unit evidence

**Recommendation: gen-2 needs its own payload and its own field handling.** Reuse
the UI components, not the schema.

---

## O5 — grouping amendments by land core, not by `case_id`

**The question.** Can amendments join an existing unit under one `project_uid`?

**Measurement.** Nine amendments were screened as active-review and outside the
Viewer and outside the 168 list. `11509014` (A基地) and `11509015` (B基地) are
amendments of one 寶清段 project; they share one implementer and one land segment.
`11509011` is another amendment under the same `case_id` conflict as a 大同 case.
None is on the 168 list.

**Proposed form.** Pair each amendment with its base unit by:

1. land-core text similarity,
2. shared implementer where present,
3. shared section and nearby parcels,
4. manual review for the conflicting `case_id` values.

Do not use `case_id` equality. A and B zones remain separate applications inside one
unit's pending history.

**Recommendation: group amendments by land-core evidence.** Keep A基地 and B基地
as separate applications under one `project_uid` only when the land core and other
evidence agree.

---

## O6 — a separate pending dataset is the safe first shape

**The question.** Should pending applications merge into the approved-project graph?

**Measurement.** The approved graph has strict invariants: every node has `recno`,
every project has `anchor_recno`, stages are gazette-approval stages, and the
tripwire and coverage guards run over the emitted caches. Mixing applications with
no `recno` into that graph corrupts it silently rather than raising.

**Proposed form.** A separate dataset, e.g. `projects.pending.json` (name to be
decided), keyed by `project_uid`, holding:

- one entry per pending unit,
- one entry per application with `application_id`, `case_id`, status, district,
  applicant, location, application date,
- links to any approved Viewer project only where evidence supports it,
- flags for conflicting IDs, missing headers, meeting-label names,
- observation time so status age is visible.

The Viewer can render both datasets from one shell page, but they remain two
payloads with two contracts.

**Recommendation: keep a separate pending dataset.** Merge only after the identity
ledger and the count rule have been exercised on known approvals.

---

## O7 — gen-2 proof population

**The question.** Which projects prove the UID design without guessing?

**Measurement.** Use units where both sources name the same land core:

| Project | District | Evidence |
|---|---|---|
| 北投大業段三小段-184-1等10 | 北投 | amendment `11509024`, application date 2026/09/22, in Viewer cache |
| 南港玉成段二小段-253-1等16 | 南港 | amendment `10405044` |
| 內湖文德段二小段-232等4 | 內湖 | amendment `11511010` |
| 內湖東湖段一小段-14-2等1 | 內湖 | amendment `11508005`, no applicant on cp |
| 大同雙連段三小段-98等25(原23) | 大同 | amendment `11511007` |
| 松山寶清段二小段-353-2等21(A/B) | 松山 | `11509014`, `11509015` conflict rows |
| 大安仁愛段五小段-480等2(原1) | 大安 | `11510016` conflict row |

These seven units cover the four conflicts and the amendment shapes. They are the
natural first population for the identity ledger.

**Recommendation: prove gen-2 on these seven units first.** Add units only by user
decision after each match is checked.

---

## Order

| Step | Item | Priority | Form | Depends on | Notes |
|---|---|---|---|---|---|
| 1 | O1 — assign `project_uid` by evidence | P2 | new identity layer, append-only ledger | — | not `case_id`, `recno` or `project_id` |
| 2 | O2 — keep `case_id` per application | P2 | schema field, no grouping by ID alone | O1 | four conflicts stay flagged |
| 3 | O3 — exclude meeting-label rows | P2 | filter rule | O1 | 3 rows |
| 4 | O4 — separate pending payload | P2 | `projects.pending.json` shape | O1 | reuse UI, not schema |
| 5 | O5 — group amendments by land core | P3 | match rule, manual review | O1 | A/B zones separate applications |
| 6 | O6 — prove on seven units | P3 | ledger entries, no graph change | O1–O5 | first population |
| 7 | O7 — Viewer UI reuse decision | P4 | direct fix after payload exists | O4 | component reuse only |

---

## Decisions to make

None yet. Each item above is a recommendation. An openspec change opens on the user's
word, one item at a time.

---

## Appendix — method

- **Viewer payload:** read `data/projects.json`; counted projects, nodes, `recno`,
  `anchor_recno`, `member_recnos`, `implementation`, `rewards`, `edges`, `links`.
- **District rows:** read saved `dashboard-data/cp-rows.json` (3,655 rows) and
  `dashboard-data/duplicates.json` (4 conflicts) from the session scratchpad; counted
  distinct `case_id` values (3,651) and district counts (12).
- **Viewer vs district vs 168:** compared distinct `case_id` sets from
  `dashboard-data/viewer-ids.json` (2,022 IDs), `dashboard-data/p168-rows.json`
  (468 IDs) and `dashboard-data/cp-rows.json` (3,651 IDs).
- **Amendments and meeting labels:** read saved
  `dashboard-data/special-records.json` (9 amendments, 3 meeting labels).
- **Header evidence:** read `district_header_summary.json` from the session
  scratchpad (594 candidates, 495 successful active rows, 4 failures).
- **Viewer graph fields:** read `viewer/app.js` lines 146–148, 935, 1359 and
  `viewer/index.html` for the field names the UI depends on.

No live requests were made for this board beyond the previously saved probes. The
pipeline was not run. No files under `urtpe/` or `viewer/` were changed.
