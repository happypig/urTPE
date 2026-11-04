# Proposal: building-permit-adapter (S15 — C5)

## Why

The 使照 (使用執照) date is issued by the building authority
(臺北市建築管理工程處); both portals copy it. The two copies disagree for
**22 of 282** projects holding the date from both (吉林811 2013-09-11 vs
2013-11-12; 榮星306 year; 虎林310 month), 13 projects hold it national-only,
32 city-only, and 橋北574-1's national `291.08.02` renders as 2202-08-02 in
the 推動歷程 card. Today the pipeline emits both with no flag, and the
viewer shows the disagreement silently.

A city-API probe (2026-11-04) cannot decide the disagreements — both portal
values pass the city's own date ordering. The building authority's permit
summaries on data.taipei are the third source that can:

| Dataset | Resource id | Size | Cover |
| --- | --- | --- | --- |
| 臺北市歷年使用執照摘要 | `0f3f9675-8356-4f1a-9908-1ce8892012fa` | 65.25 MB | ROC 90–114 |
| 臺北市115年度使用執照摘要 | `74a8b311-906e-44c4-91fb-7f413842d4e1` | 2.01 MB | current year |

Tested against the payload (2026-11-04, by parcel overlap): the control set
agrees 22/22; the 22 disagreements resolve **8 city + 9 national + 4 permit
matches neither + 1 no permit**; the 13 national-only confirm 12. Neither
portal is the better one — the permit record is.

## What changes

- A new adapter (`urtpe/permit_sources.py`): downloads both datasets (XML,
  no key) into the archive root (the gazettes' home, keyed by SHA-256 per
  `AGENTS.md`'s detection rule), parses each `<Data>` record (執照號碼,
  發照日期 ROC `YYYMMDD`, 原核發執照, 開工日期, 地址, 地段號
  `臺北市中山區吉林段三小段0811-0000號`), and indexes by (section, parcel).
- `discover_project_links` (or the attach path) attaches, per project, the
  建字-origin permit(s) whose parcels overlap the project's parcel list most
  — as `links.permit` `{permit_no, date, source}` with review flags when the
  portals disagree: `使照兩源不一致(城市X/國 Y/執照 Z)` naming the permit that
  confirms, `使照僅國源` / `使照僅城市源` when one side is blank.
- Multiple permits on one site (奇岩13, 龍泉712, 懷生931, 仁愛54): the rule
  takes the permit whose `原核發執照` is a 建字 number; for an area split one
  per area. A 雜字 permit is a 雜項 or second building, not the 使照.
- The viewer's `fmtDate` gains the range guard: an out-of-range ROC year
  (year > 115, i.e. later than the current 民國 year) renders as the raw
  text plus a warning class, not a fabricated 2202 date.
- Never repair by inference: when no permit matches (榮星306, 德惠573 — the
  permit sits on parcels the gazette lists under another number), both
  portal dates stay and the disagreement flag remains.

## What does not change

- The two portals' own milestones: the permit is a third witness, not a
  replacement. The 使照 slot keeps preferring the city value; the permit
  date rides beside it in `links.permit`.
- D5's one-payload statistics rule and the plan-case date rule (C8a).
- The gazette cadence layer (the archive root gains a new subdirectory, not
  a new mechanism).

## Capabilities

### Modifications

- `official-link-discovery`: ADDED requirement — the permit adapter's
  download, index, match and flag rules (the spec's "Fetch milestone
  timelines" requirement stays; this is a new source beside it).
- `viewer-milestone-timeline`: MODIFIED — the construction-chain requirement
  renders the permit witness and the disagreement flag; `fmtDate` gains the
  out-of-range ROC guard.

## Risks

- 65 MB yearly download: cached under the archive root keyed by SHA-256, so
  a re-run fetches only when the file changes; the monthly dataset (2 MB)
  covers the current year.
- Parcel-list misses (2 measured): the permit record's 地段號 must appear in
  the project's own parcel list; an address or 建照-number key would catch
  the misses — deferred, they keep the flag.
