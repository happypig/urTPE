# Project inspection — Batch D · collected 2026-11-04

Findings from the post-Batch-B+C session (2026-11-04, payload at `47453f9`:
1,442 records / 682 projects, the corpus converged after waves 1–3 of the
Batch B + C plan). Two findings, both measured. The board follows the
`docs/inspection-batchBC.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

## D1 — the orphan `milestones_national` key holds Taipei data (name wrong, data right)

**Finding.** On every orphan node, the payload's `milestones_national` dict
carries **Taipei-platform** milestones, not national ones. The date values are
correct; the key name is false. Verified three ways:

1. **Code path.** `urtpe/links.py:3287` builds the orphan's
   `milestones_national` from `disc.case_milestones[cid]`, and
   `case_milestones` is filled **only** by `fetch_taipei_milestones_api`
   (the `Get_project168_second.ashx` call; the discovery loop, the view
   absorb and the refresh path). No national page data enters it.
   The genuine national data (twur 推動歷程, ROC-dot dates) sits one level
   up at project-level `links.milestones_national`
   (`extract_tuidui_history_from_view`).
2. **Date shapes.** The orphan dicts carry slash-Gregorian dates
   (`2011/03/08`). The real national portal emits ROC dots (`100.03.08`).
3. **Live probe** (2026-11-04): `Get_project168_second.ashx` for
   09906012 / 10202021 / 10012111 reproduces the payload's orphan dicts
   field-for-field (`outline_ok_date` → 概要核准日期， …).

**Corpus effect measured on the trace set** (雅祥492's 09906012 + 10202021,
文德231-3's 10012111, 寶清599's 09303272, 南海段364's 09210162): the date
values are right in every case — `_ghost_node_date`
(`urtpe/links.py:2298`) reads 概要核准日期 from the Taipei ashx, and the
platform really holds it. No value is misinterpreted.

**Risk.** A future consumer that trusts the key name joins Taipei data as
if it were national (the viewer reads it at `viewer/app.js:906` for the
virtual node's badges; the 國/北 distinction is exactly what the key
claims to carry). The G2/`case-record-join` dual-id-space lesson applies:
an id-space (or here, a source-space) mismatch read as truth.

**Form:** openspec change (payload schema rename on `orphan_nodes`; the
viewer read site updates in the same change; a load-side alias keeps
already-emitted `projects.data.js` files rendering — `--from-js` repair,
the `emit-stage-index` precedent). Spec surfaces: `virtual-milestone-nodes`
(payload field requirement) + the viewer label spec.

| Key on an orphan node | Actual source | Correct? |
| --- | --- | --- |
| `milestones_national` | Taipei ashx (`case_milestones`) | **name wrong, data right** |
| `milestones_taipei` | twin-bridge / source-map merge | right |
| project-level `milestones_national` | twur view page 推動歷程 | right |
| project-level `milestones_taipei` | merged taipei milestones | right |

## D2 — ghost dates read the family's 概要核准, and the row order could read dates (revisit D12)

Two related findings from the same session's measurement.

### D2a — `_ghost_node_date` echoes the family 概要 onto plan cases

`_ghost_node_date` (`urtpe/links.py:2298`) walks
核定日期 → 權變核定日期 → 概要核准日期 with **no track test**. A 計畫/權變
case that never won approval (已駁回/自行撤回/已失效) still carries the
family's 概要核准日期 in its city record (the city echoes the 概要's
approval into every descendant case's 階段辦理過程 — verified live on
吉林717's triple: `outline_ok_date = 2007/01/30` on all of
09506200/09506202/09608051), so the ghost node is **dated with an approval
that is not the case's own event**.

Measured shapes:

- 吉林717's triple: 概要 [已失效] 2007-01-30, 計畫及權變 [已駁回] node_date
  2007-01-30 (its own event is 申請計畫 2013/11/18), 計畫 [自行撤回]
  node_date 2007-01-30 (own event 申請計畫 2008/12/31).
- 雅祥492's 10202021 [已駁回]: node_date = the 概要's 2011-03-08.
- Corpus: **25 cross-case member pairs share one date**; 18 of them carry a
  terminal schedule — the same 概要核准 echoed, not independent events.
  Inverse check: **0 case_ids carry 2 distinct node dates** (case_id is a
  strict key; date is not).

**Fix:** `_ghost_node_date` becomes track-aware. A plan-track case skips
概要核准日期 (leave the node undated → renders `(未核定)`, the honest
label — the 寶清375 shape). A 概要-track case keeps 概要核准日期 as its own
approval. Re-measure after: the 25 same-date pairs drop to ~7 (genuine
same-day serials only); the "dead-track-leads" inversions disappear from
the 51-project list (D12's known cost, `docs/viewer_sort_rules.md`).

**Form:** openspec change (`virtual-milestone-nodes` delta: ghost dates
read only the case's own track approval; payload re-emit).

### D2b — sort by distinct approval date (own-event fallback) instead of case_id

The user's question (2026-11-04): can rows sort by a distinct approval
date — falling back to the application date when no approval exists —
instead of case_id? Measured end to end with the refined key:

- Key: 概要-track cases read 概要核准 → 申請概要 → 申請計畫; plan-track
  cases read 核定 → 權變核定 → 申請計畫 → 申請權變 → 申請概要 (**never** the
  echoed 概要核准); ties and the undated tail break by case_id.

| | D12 (case_id first) | date-first with own-event key |
| --- | --- | --- |
| Cross-case same-date ties | 25 | 18 (all genuine same-day events; case_id separates) |
| Undated members | 30 | 21 |
| Order pairs vs case_id | — | 106 reorder |
| Non-chronological reads | **51 projects / 95 pairs** | **~0 by construction** |
| 相關連結 order match | by construction | no (cosmetic; the list renders separately) |

What it fixes: the 95-pair non-chronology (the 51-project list) dissolves;
same-day serial pairs read in approval order; the 9 row-between 概要
orphans land at their date position.

What it costs (all placement rules, not data):

1. **Mixed event kinds on one axis.** A dead attempt renders by its
   application date, before the approval that came years later. The row
   must name its kind: an application-dated node keeps `(未核定)` beside
   the date.
2. 21 undated members render last, by case_id (same tail as today).
3. The 相關連結 order guarantee (D12 Amendment 3) no longer holds in the
   graph; the pipeline-side `links.taipei` ascending emit stays.
4. Real nodes date by the gazette print today; a re-date moves a row.
   Optional mitigation (do not bundle): date real nodes from the case's
   own data2 核定 too.
5. **D12 is a recorded user decision in the spec**
   (`virtual-milestone-nodes`, `openspec/changes/archive/2026-09-02-add-virtual-node-ordering-and-chain/design.md`
   D12 + Amendment 3). Overturning it needs the change + the re-measure
   recorded on the board, with `docs/viewer_sort_rules.md` rewritten
   (its "do not sort by date" section becomes the history).

**Dependency: D2a first.** D2b's key reads the same fields D2a fixes. Run
the attachment fix, then re-measure the sort key on the re-emitted payload
(the table above was measured on today's payload; the 18 ties and 21
undated will move — expect fewer, since undated plan ghosts stop borrowing
the echo and get the application fallback instead).

**Form:** one openspec change covering D2a + D2b (same re-emit, same spec
surface `virtual-milestone-nodes` + viewer sort spec), test-first.

## Order

| Step | Finding | Form | Gate |
| --- | --- | --- | --- |
| D1 | rename the orphan `milestones_national` key (source-space truth) | openspec change + `--from-js` load alias + re-emit | — |
| D2 | `_ghost_node_date` track-aware, then the date-primary sort key (user decision 2026-11-04 pending on the re-measure) | one openspec change, `virtual-milestone-nodes` + viewer | D1 (same re-emit rides D1's payload) |

## Decisions waiting on the user

| Entry | Question | Blocks |
| --- | --- | --- |
| D2b | Confirm the sort-key swap after D2a's re-emit re-measure (expect: 51 → ~13 non-chronological projects by the old count, ties all case_id-resolved) | D2b implementation |
