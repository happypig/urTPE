# viewer-related-links Specification

## Purpose

Shows the discovered official links in the browser viewer's detail pane so an
analyst can jump from a project's history graph to the authoritative case
record on the national portal and the Taipei City platform.
## Requirements
### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place: each approval node with an anchored Taipei case SHALL expose its 北 badge as a hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge hyperlink to the project's national view page when one exists; **any approval node whose anchored case is listed in `links.view_verified_case_ids` — the cases the project's own national view page names in 相關連結 — SHALL also expose the 國 badge**, because the portal itself asserts that case belongs to the unit and the node should lead to the page that names it; and each construction-event node SHALL label as a hyperlink to its source portal — Taipei case page (pink) when Taipei-sourced, national view page (green) when national-mapped. A node qualifying both ways (view-verified and 現況) SHALL render exactly one 國 badge. The standalone 相關連結 section SHALL be retired behind an explicit debug toggle that defaults to hidden.

#### Scenario: Approval node links to its anchored case
- **WHEN** a record anchors to Taipei case 09804142
- **THEN** that node's 北 badge opens `r_progress_detail.aspx?case_id=09804142` in a new tab

#### Scenario: Current node links to the national view
- **WHEN** the project has a national view URL
- **THEN** the 現況 node's 國 badge opens the twur view page in a new tab

#### Scenario: A view-verified case's node links to the national view (303 shape)
- **WHEN** 北投區-關渡段二小段-303's `links.view_verified_case_ids` contains 10105152 and
  10803151, the project's twur URL is view/621, and nodes 829 and 669 anchor those cases
- **THEN** nodes 829 and 669 each carry the 國 badge opening view/621 in a new tab
- **AND** node 5 (現況， anchored 11505020, not view-verified) keeps its 國 badge via the
  existing 現況 rule

#### Scenario: A node qualifying both ways renders one badge
- **WHEN** the 現況 node's anchored case is also listed in `view_verified_case_ids`
- **THEN** the node renders exactly one 國 badge

#### Scenario: A node whose case is not view-verified gains no badge
- **WHEN** a non-current node's anchored case is absent from `view_verified_case_ids`
- **THEN** the node carries only its 北 badge

#### Scenario: Link section hidden by default, available for debugging
- **WHEN** the detail pane renders
- **THEN** no 相關連結 list appears unless the user explicitly enables the 除錯 toggle, which reveals the full link list (with 案名 annotations) for debugging purposes

### Requirement: 相關連結 resolves case names for orphan case_ids via fallback chain

Each city case_id in `links.taipei` (and the orphan/ghost case_ids) SHALL
resolve its display name in 相關連結 via the fallback chain: the case's own
harvested city name (`links.candidate_names`), then the anchored node's 案名,
then the `links.case_milestones` context label (里程碑 N 筆), then the
`links.search_rejected` stored case_name, then the ghost node's case_name,
then the raw case_id. The national link is labelled by the national page's own
name (`links.twur_name`), falling back to the current node's 案名. Per-case
schedule badges render beside each case (已核准 / 已核定 render none — the
default state). D4c (user decision 2026-11-05, board D4c): the family-level
"未曾核定（已駁回/自行撤回/已失效）— 無國土管理署入口網頁" note is removed — a
gazette family holds a gazette approval by construction, and the 4 projects
the note named all carry an approved current node. A project whose
`links.twur` is empty simply shows its 相關連結 list without the note.

#### Scenario: Orphan case_id in search_rejected gets its case name
- **WHEN** `links.search_rejected` = `{"11207021": "擬訂臺北市…概要案"}` and
  相關連結 renders case_id 11207021
- **THEN** the entry is labelled 擬訂臺北市…概要案 (the stored city name)

#### Scenario: Harvested candidate_names precede the milestone-context label
- **WHEN** a case_id appears in both `links.candidate_names` and the
  `links.case_milestones` context
- **THEN** the harvested city name wins

#### Scenario: An anchored case is labelled by its own city name
- **WHEN** a node anchors two cases (the area-split binding) and both carry
  harvested names
- **THEN** each 相關連結 entry shows its own case's name, not the node's
  gazette 案名

#### Scenario: Two cases on one node read apart
- **WHEN** the area-split binding puts 11011241 (-A區) and 11011242 (-B區) on one node
- **THEN** 相關連結 shows two entries, each labelled by its own city name

#### Scenario: The harvest lacks the id — the gazette label stays the fallback
- **WHEN** a node anchors a case absent from `links.candidate_names`
- **THEN** 相關連結 labels it with the node's `case_name` as before

#### Scenario: The 國 label is the national page's own name
- **WHEN** `links.twur_name` is present
- **THEN** the 國 entry is labelled with it

#### Scenario: No cached page — the 國 label falls back
- **WHEN** `links.twur_name` is absent
- **THEN** the 國 entry is labelled with the current node's `case_name` as before

#### Scenario: Rejected/withdrawn 概要 attempts show their status
- **WHEN** `links.case_schedules` = `{"11207021": "已駁回", "11302031": "自行撤回"}` (民生段140-9 shape)
- **THEN** 相關連結 shows "…土地事業概要案 — 已駁回" and "…土地事業概要案 — 自行撤回"
- **AND** no family-level "never approved" note renders

#### Scenario: Never-approved project explains its missing twur link
- **WHEN** every case of the project is 已駁回 / 自行撤回 / 業已失效 and
  `links.twur` is empty
- **THEN** the 相關連結 lists the cases with their per-case badges and no
  family-level note (the note is removed; board D4c)

#### Scenario: Orphan with no fallback shows raw case_id
- **WHEN** an orphan case_id is absent from nodes, orphan_nodes, candidate_names, case_milestones, and search_rejected
- **THEN** 相關連結 shows "臺北市都市更新審議服務平台 (case_id: 09907223)" without a case name (current fallback behavior)

#### Scenario: Both approved-family words omit the badge
- **WHEN** `links.case_schedules` = `{"10406282": "已核定", "10011271": "已核准"}`
- **THEN** neither 相關連結 entry carries a status badge

#### Scenario: An in-review case shows its badge
- **WHEN** `links.case_schedules` = `{"10406283": "審查中"}`
- **THEN** the 相關連結 entry for 10406283 carries the badge `[審查中]`

#### Scenario: A superseded case names its successor

- **WHEN** `links.superseded_by` = `{"11211211": "11409026"}`
- **THEN** the 相關連結 entry for 11211211 reads `已由 11409026 取代`
- **AND** it carries no status badge

### Requirement: 相關連結 lists case_ids in ascending order

The 相關連結 debug list SHALL render `links.taipei` in **case_id ascending order** regardless of platform search-response order (corpus audit 2026-08-31: 91/564 multi-id arrays unsorted, 34 adjacent swaps = platform order drift). At attach time the pipeline SHALL emit `links.taipei` case_id-ascending, so the 相關連結 list, the graph row order (family-wide case_id interleave), and the platform search order agree by construction. Anchored assignments (`node.links.taipei`) are unaffected — sorting the project-level list never re-anchors cases.

#### Scenario: Platform order drift is normalized
- **WHEN** discovery returns `["10906091", "11403002", "10906092"]` for a family (platform-order, not ascending)
- **THEN** the emitted `links.taipei` is `["10906091", "10906092", "11403002"]` and 相關連結 lists them in that order

### Requirement: Gazette stage anomalies surface as review flags

When the gazette PDF's printed 階段 disagrees with the platform's recorded case state for the anchored case (e.g. 吉林段四小段603 node 920 dated 2018-01-25: the gazette prints 擬訂 but the platform case 09511214 is a 變更 已核准), the record SHALL carry a review flag (案名階段與平台案件狀態不一致 — gazette printing anomaly candidate) instead of silently keeping the stage unexamined. Stage parsing remains faithful to the PDF text; the flag routes the row to human review.

#### Scenario: Gazette 擬訂 anomaly is flagged, not corrected
- **WHEN** a node's printed 階段 is 擬訂 but its anchored case's platform name is 變更… with an approval outcome
- **THEN** the node keeps the printed stage and carries a review flag naming the disagreement
- **AND** no parser rewrite changes the emitted stage for the flagged row

### Requirement: The viewer links to the release-diff report, and the report links back

The viewer's header SHALL carry a link to the release-diff report, and the
report SHALL carry a link back to the viewer. The two links SHALL be relative,
so the pair works from the published site, from a `file://` page, and from a
clone — the viewer's normal way of being opened is `file://`, and an absolute
URL would break it there.

The viewer's link SHALL be present in the page's markup rather than added by
script, so a reader who lands on a payload that fails to load can still reach
the report.

#### Scenario: The viewer header carries the link

- **WHEN** the viewer page is loaded
- **THEN** its header carries a link labelled 歷次公報差異
- **AND** the link's target is a relative path to the release-diff report

#### Scenario: The report links back to the viewer

- **WHEN** the release-diff report is opened
- **THEN** it carries a link back to the viewer
- **AND** the link's target is a relative path to the viewer's index

#### Scenario: The links work from a local file

- **WHEN** the viewer is opened from `file://` with no server running
- **THEN** the link to the report reaches the report
- **AND** the report's back link reaches the viewer

#### Scenario: The link survives a data load failure

- **WHEN** the payload fails to load
- **THEN** the link to the release-diff report is still present in the page

### Requirement: Each release links to the document the city published for it

The release-diff report's per-release table SHALL link a release to the
document the city published for that release, and SHALL say in words when no
such link is known.

A release SHALL link to its own version-specific publisher URL when the
archive index records one. The publisher serves one PDF link at a time and
repoints it on every publication, so the live link names the newest document
rather than any particular one; a release with no recorded URL SHALL NOT be
given the live link, because that would send a reader to a different gazette
while appearing correct.

The newest release SHALL link to the live publisher PDF and SHALL carry the
publisher's 資料更新 stamp beside the link, so the address is dated.

#### Scenario: The newest release links to the live PDF

- **WHEN** the report lists the release the publisher currently serves
- **THEN** that release's row links to the publisher's PDF
- **AND** the publisher's 資料更新 stamp appears beside the link

#### Scenario: An older release links to its own URL

- **WHEN** the archive index records a version-specific publisher URL for a release that is not the newest
- **THEN** that release's row links to that URL
- **AND** it does not link to the live URL

#### Scenario: A release with no recorded URL says so

- **WHEN** no publisher URL is recorded for a release
- **THEN** that release's row carries no publisher link
- **AND** the report states that the URL for that release is unknown
- **AND** the row does not link to the live PDF, which serves a different document

#### Scenario: The link column distinguishes the two kinds of URL

- **WHEN** a report carries both a live-publisher link and a version-specific link
- **THEN** a reader can tell which is which from the link's label

