# viewer-related-links Specification

## Purpose

Shows the discovered official links in the browser viewer's detail pane so an
analyst can jump from a project's history graph to the authoritative case
record on the national portal and the Taipei City platform.
## Requirements
### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place: each approval node with an anchored Taipei case SHALL expose its 北 badge as a hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge hyperlink to the project's national view page when one exists; **any approval node whose anchored case is listed in `links.view_verified_case_ids` — the cases the project's own national view page names in 相關連結 — SHALL also expose the 國 badge**, because the portal itself asserts that case belongs to the unit and the node should lead to the page that names it; and each construction-event node SHALL label as a hyperlink to its source portal — Taipei case page (pink) when Taipei-sourced, national view page (green) when national-mapped. A node qualifying both ways (view-verified and 現況) SHALL render exactly one 國 badge. The standalone 相關連結 section SHALL be retired behind an explicit debug toggle that defaults to hidden.

The 國 badge's route set is the pipeline's resolved one
(national-badge-by-registration, user decision 2026-11-12): the viewer SHALL
render the badge from the node's emitted `national_badges` field — which the
pipeline sets for a node the view page names by registration, exact name, or
the 擬訂 section+parcel fallback — and SHALL NOT re-implement the former
per-label stage+date matcher client-side. A node the payload does not mark
SHALL carry no 國 badge, whatever a national label's date says.

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
- **AND** node 5 (現況， anchored 11505020, not view-verified, not the title's 案名) carries
  NO 國 badge — the 現況 rule is retired by national-badge-by-registration; a node
  qualifies only through the view page naming it

#### Scenario: A node qualifying both ways renders one badge
- **WHEN** the 現況 node's anchored case is also listed in `view_verified_case_ids`
- **THEN** the node renders exactly one 國 badge

#### Scenario: A node whose case is not view-verified gains no badge
- **WHEN** a non-current node's anchored case is absent from `view_verified_case_ids`
- **THEN** the node carries only its 北 badge

#### Scenario: The viewer reads the resolved field, not a matcher
- **WHEN** the payload marks a node `national_badges: true`
- **THEN** the node renders exactly one 國 badge
- **AND** a node the payload does not mark renders none, even when a national
  label's date matches its date

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

The release-diff report SHALL be reachable from the site's pages, and the
report SHALL carry a link back into the viewer's pages. The reachability runs
through the about page: the viewer's header SHALL carry a link to the about
page (the 關於 requirement above), and the about page SHALL link the report;
the report's back link SHALL point at the about page (`../viewer/about.html`),
which links the viewer in turn. The chain is therefore:
report → 關於 → viewer and viewer → 關於 → report, every hop a relative path,
so the chain works from the published site, from a `file://` page, and from a
clone — the viewer's normal way of being opened is `file://`, and an absolute
URL would break it there.

The three documentation pages — the release-diff report, the coverage report
and the ETL write-up — SHALL each carry a 關於 link at their header's right
edge, present in the page's markup rather than added by script, so a reader
who lands on a report directly (from a search result or a shared link) can
still reach the license, the data sources and the contact.

In every header that carries site links — the viewer's, the dashboard's and
the three documentation pages' — the 關於 link SHALL be the last (rightmost)
link, with the page's other site links to its left.

#### Scenario: The viewer header carries the link

- **WHEN** the viewer page is loaded
- **THEN** its header carries a link labelled 關於
- **AND** the link's target is a relative path to the about page

#### Scenario: The 關於 link is the rightmost site link

- **WHEN** the viewer's, the dashboard's or a documentation page's header is read
- **THEN** the 關於 link is the last site link in the header
- **AND** the viewer's 政策儀表板 and the dashboard's 專案歷史圖 links sit to its left, unchanged

#### Scenario: The about page links the report

- **WHEN** the about page is opened
- **THEN** it carries a link labelled 歷次公報差異 to the release-diff report
- **AND** the link's target is a relative path to the report

#### Scenario: The report links back to the viewer

- **WHEN** the release-diff report is opened
- **THEN** it carries a 關於 link at its header's right edge
- **AND** the link's target is a relative path to the about page
- **AND** the about page links the viewer's index, so the viewer stays one hop away
- **AND** the report carries no direct 回專案歷史圖 link

#### Scenario: The documentation pages carry the link

- **WHEN** the coverage report or the ETL write-up is opened
- **THEN** its header carries a 關於 link at the right edge
- **AND** the link's target is a relative path to the about page

#### Scenario: The links work from a local file

- **WHEN** the viewer is opened from `file://` with no server running
- **THEN** the 關於 link reaches the about page
- **AND** the about page's report link reaches the report
- **AND** the report's 關於 link reaches the about page

#### Scenario: The link survives a data load failure

- **WHEN** the payload fails to load
- **THEN** the 關於 link is still present in the page's header
- **AND** the about page, needing no data, still renders its report link

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

### Requirement: The site carries an about page

The site SHALL carry an 關於 page (`viewer/about.html`) in zh_TW that answers,
in one place: under what license the site's own content may be reused, where
the data comes from and how it was processed, how far the published figures
can be trusted, and how to reach the maintainer.

The page SHALL be static and self-contained: no script, no stylesheet fetched
from the site's directory or elsewhere, and every link relative, so the page
works from the published site, from a `file://` page, and from a clone — the
same constraint the viewer's other pages work under.

The page SHALL wear the site's one design system: the cream palette the
dashboard and the viewer share (`#fff8f4` ground, `#211d1d` charcoal,
`#f3d9bf` hairlines, `#ad4d2a` terracotta links, the sun-highlighter under
headings), inline, with no dark-mode block — the system is light-only by
construction, the same on every published page. The rule covers the
domain-model page (`docs/domain-model.html`) as well: its palette joins the
cream system, its dark-mode block goes, and the page stays self-contained.
The page SHALL also be listed in `viewer/deploy.json`, so
`scripts/check_deploy.py` compares its served bytes against the committed
build like every other published artifact's.

The page SHALL state the license of the site's own content (the pages and the
emitted dataset) as CC BY 4.0, and SHALL state in a separate line that the
upstream government data — the gazette PDF and both portals — follows its own
terms.

The page SHALL name the three data sources: the gazette PDF
(臺北市都市更新核定案件一覽表), the Taipei platform (`gis.uro.taipei`), and
the national portal (`twur.nlma.gov.tw`), and SHALL give a concise abstract of
the processing flow from PDF to the per-project history graph the pages
render, including that records the publisher truncated are excluded and named
rather than repaired.

The page SHALL state the corpus's scope in the same breath as its size: the
graph holds **approved** cases only (680 projects / 1,444 records at the
2026-10-28 gazette), and the applications still under review are by design
absent from it — 臺北市報核 1,480 事業計畫 of which 630 were approved, and the
national portal's statistics table names 433 報核中 for 臺北市 (統計至
2026/09/30). The page SHALL link the two official statistics pages the scope
statement is read from, so a reader comparing the site's 680 against an
official total can see which population each number names. A scope statement
without its sources would read as an excuse rather than a measurement.

The page SHALL link the release-diff report (歷次公報差異) and the coverage
report (資料覆蓋度報告) by their published relative paths, with one abstract
sentence each on what the report establishes, and SHALL carry the maintainer's
contact address.

The viewer's header and the dashboard's header SHALL each carry a link to the
about page, in the page's markup rather than added by script, so the link is
reachable even when the page's data fails to load.

Every published page that carries site links in its header SHALL carry the
same 關於 control: the navlink chip the viewer and the dashboard wear
(terracotta text, hairline border, 8px radius), as the header's last element,
so the header closes at the right edge on every page. The rule covers the
domain-model page (`docs/domain-model.html`) too: its header SHALL carry the
chip, so a reader who lands on it from a search result can still reach the
license, the data sources and the contact.

#### Scenario: The about page answers the four questions

- **WHEN** the about page is opened
- **THEN** it states the CC BY 4.0 license of the site's own content
- **AND** it names the gazette PDF, the Taipei platform and the national portal as the data sources
- **AND** it links the release-diff report and the coverage report
- **AND** it carries the maintainer's contact address

#### Scenario: The license line does not overreach

- **WHEN** the about page states the license
- **AND** it mentions the upstream government data
- **THEN** the CC BY 4.0 statement is scoped to the site's own content
- **AND** the upstream data is covered by a separate line deferring to its own terms

#### Scenario: The scope statement names its official sources

- **WHEN** the about page states that the graph holds approved cases only
- **THEN** the statement carries the site's own count (projects and records) and the gazette date it names
- **AND** the city's 報核 figure (1,480 事業計畫, 630 核定實施) and the national portal's 報核中 figure (433, 統計至 2026/09/30) are each linked to the official page they come from
- **AND** the in-review pool is stated as absent by design, not as a gap

#### Scenario: The page wears the site's one design system

- **WHEN** the about page's inline styles are read
- **THEN** they declare the cream palette's tokens (`#fff8f4`, `#211d1d`, `#f3d9bf`, `#ad4d2a`)
- **AND** the page carries no dark-mode block and no slate tokens (`#0f172a`, `#cbd5e1`)

#### Scenario: The domain-model page wears the same system

- **WHEN** the domain-model page's inline styles are read
- **THEN** they declare the cream palette's tokens (`#fff8f4`, `#211d1d`, `#f3d9bf`, `#ad4d2a`)
- **AND** the page carries no dark-mode block and no slate tokens (`#0f172a`, `#cbd5e1`)
- **AND** the page makes no external request to render

#### Scenario: The domain model is a checked deploy artifact

- **WHEN** `viewer/deploy.json` is read
- **THEN** `docs/domain-model.html` is named in the artifact list
- **AND** `scripts/check_deploy.py` compares its served bytes against the committed build

#### Scenario: The page works from a local file

- **WHEN** the about page is opened from `file://` with no server running
- **THEN** every link on the page resolves to its target
- **AND** the page makes no external request to render

#### Scenario: Both headers carry the link

- **WHEN** the viewer page or the dashboard page is loaded
- **THEN** its header carries a link labelled 關於 whose target is a relative path to the about page
- **AND** the link is present in the page's markup, not added by script

#### Scenario: The domain-model header carries the chip

- **WHEN** the domain-model page is opened
- **THEN** its header carries the navlink chip labelled 關於 whose target is a relative path to the about page
- **AND** the chip is the header's last element

#### Scenario: The link survives a data load failure

- **WHEN** the viewer's or the dashboard's payload fails to load
- **THEN** the 關於 link is still present in the page's header

