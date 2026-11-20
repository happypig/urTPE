# uro.gov.taipei district case-page inventory

**Probed:** 2026-11-19 · **Host:** `https://uro.gov.taipei` · **Page:**
`cp.aspx?n=E06DCE2A43AF2B4F`

This document covers the server-rendered district case tables. It also compares them with
`P_project168.aspx` and the Viewer. The separate
[`gis.uro.taipei` `/ashx/` API inventory](urotpe_api.md) covers the JSON endpoints used for
case details, milestones and link discovery.

**12 district pages · 3,655 distinct published rows · 3,651 distinct `case_id` values ·
no detail links in the tables.** No code in `urtpe/` currently reads these pages.

All counts in this document describe the dated measurements in §7. They are not a live
contract. The city can add rows, change statuses or replace district URLs.

---

## 1. Request and discovery contract

The entry URL is:

```text
GET https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F
```

It returns HTML, not JSON. The response contains a six-column case table and links to the
other district pages. A district link adds an opaque `s` parameter:

```text
GET https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F&s=<district-token>
```

The URL without `s` and the URL with the 北投 token returned the same 270 rows in this
crawl. Following both without row deduplication produced 3,925 rows: 3,655 distinct rows
plus 270 repeated 北投 rows. This duplication is a crawl artefact, not 270 extra cases.
Deduplicate on the six published fields, not on the source URL.

The 12 measured pages were:

| District | Distinct rows | `s` token |
|---|---:|---|
| 北投區 | 270 | no `s`; the discovered token `066D0E7753C3462E` returned the same rows |
| 士林區 | 308 | `61FBFF4292BEEEAA` |
| 南港區 | 273 | `1FFB993E389D8EB5` |
| 內湖區 | 210 | `859A856D8F9E349F` |
| 大同區 | 312 | `B8C5DB6074AAFE30` |
| 萬華區 | 220 | `BA3EE8F2CE9E2977` |
| 中正區 | 385 | `8433D11627F87AA5` |
| 中山區 | 421 | `C3AE00A5DEF20987` |
| 信義區 | 277 | `C1FEB2DEC57919C7` |
| 松山區 | 258 | `6CD91553578D1CE8` |
| 大安區 | 506 | `C21E0D057C081F16` |
| 文山區 | 215 | `BA69AA1A2C1EE034` |
| **Total** | **3,655** | |

The entry page supplied every district link. No session or login was needed. Responses
could be gzip-compressed. The crawl paused for 0.25 seconds between page requests.

### Parser contract

The probe used Python's `html.parser.HTMLParser`. It collected table cells and ignored
`script` and `style` content. A case row had:

- at least six cells;
- a seven- or eight-digit second cell;
- a first cell other than the header `行政區`.

The second cell became `case_id` after `zfill(8)`. The seven-digit acceptance matters: an
earlier eight-digit-only parser omitted 44 legacy 北投 rows and reported 226 instead of
270.

Whitespace inside cells was collapsed for comparison. The published text was otherwise
preserved. The 3,655 accepted rows had no extra cells and no cell links.

This is an exploratory parser contract. It is not a production completeness gate. A
production adapter must report malformed rows and unexpected table structures rather than
silently dropping them.

---

## 2. Published fields and related case-detail endpoints

| Column | Meaning | Notes |
|---|---|---|
| 行政區 | District | One district table can contain a row whose case name names another district; see §4. |
| 案件編號 | `case_id` | Seven- or eight-digit text in the source. Normalise to eight digits for comparison. |
| 案名 | Case name | Usually carries the land core, track and amendment number. Three rows carry meeting labels instead. |
| 區位 | Location | Free text. It can be blank. |
| 實施者 | Applicant / implementer | Free text. It can be blank or contain publisher text errors. |
| 目前辦理情形 | Current district-page status | Detailed process vocabulary. It can disagree with the live case header. |

The district table supplies no application date, approval date, parcel list, milestone
history or document link. Do not infer those fields from the row.

A numeric ID can be used to open the related detail client:

```text
https://gis.uro.taipei/r_progress_detail.aspx?case_id=<case_id>
```

That page calls the `/ashx/` endpoints. In particular:

```text
POST https://gis.uro.taipei/ashx/get_project168_top.ashx
Content-Type: application/x-www-form-urlencoded

case_id=<case_id>
```

The header can supply `CASE_NAME`, `NAME`, `PLACE`, `EXE_NAME`, `phase`,
`plan_app_date`, `plan_app_date2`, `uro_chk_date` and `uro_chk_date2`. See
[`urotpe_api.md` §2–§4](urotpe_api.md#2-endpoints-used-by-this-repository) for the endpoint
inventory and request cautions.

A successful header response does not prove that its name matches the district row. The
four conflicts in §4 show why the caller must compare identity fields.

---

## 3. Comparison with `P_project168.aspx`

`P_project168.aspx` renders JSON from `Get_project168.ashx`. The saved list snapshot had
468 unique IDs. A live check on 2026-11-19 matched that snapshot. All 468 IDs occurred in
the district tables. This is a measured subset relation for this snapshot, not a promise
that every future 168 row will appear there.

| Concept | District pages | `P_project168.aspx` |
|---|---|---|
| Case ID | 案件編號 | `case_id` |
| Case name | 案名 | `T_name` |
| District | 行政區 | No separate field |
| Location | 區位 | Not supplied; the detail API can supply it |
| Applicant | 實施者 | Not supplied; the detail header supplies `EXE_NAME` / `exe_name2` |
| Review state | 目前辦理情形 | `stage`; different programme vocabulary |
| Schedule state | Not supplied | `progress` |
| Delay reason | Not supplied | `reason` |
| Completion rate | Not supplied | `COMPLETION_RATE` |
| Programme note | Not supplied | `MEMO` |
| List size | No total field | `TotalCount`, repeated on each row |
| Selection | One HTML table per district | Paged JSON, with `type`, `TRANSITION_NO`, `pageIndex`, `pageSize` |
| Detail link | None in the table | The page renders one from `case_id` |

Both ID spaces feed `r_progress_detail.aspx?case_id=<id>`. The 168 list is a programme
list. It is not a complete register of pending cases.

### Measured overlap with the Viewer

The comparison used distinct Taipei `case_id` values from Viewer node links and project
candidate-name mappings. It did not treat a Viewer project as a `case_id`. The Viewer
payload described the 2026-11-12 gazette.

| Source | Distinct IDs |
|---|---:|
| Viewer | 2,022 |
| `P_project168.aspx` | 468 |
| District pages | 3,651 |

| Region | IDs |
|---|---:|
| Viewer only | 3 |
| Viewer + 168 only | 0 |
| Viewer + district only | 1,638 |
| All three | 381 |
| 168 only | 0 |
| 168 + district only | 87 |
| District only | 1,545 |

The three Viewer-only IDs were `11510011`, `11510014` and `11510015`. They are not extra
projects, and they are not themselves conflicts. On 2026-11-20 each one's live header
named a 松山區 case. That case is the 松山區 row that the district tables print under
`11509011`, `11509014` or `11509015`. The Viewer holds each 松山區 case under the
`11510xxx` id. So the district tables print one id for it and the case header answers
under another. The pairing rests on the case name, which matches exactly for `11510011`
and for `11510015`. For `11510014` it matches but for a suffix (`A基地及道路用地` against
`A基地`). Section 4 holds the conflicts themselves.

The district set had 1,632 IDs absent from the Viewer set. Eighty-seven of those IDs were
on the 168 list. These set counts differ from row counts because four IDs name two rows.

**These counts are one payload old.** They describe the Viewer before commit `6b97a83`
(2,022 IDs). That commit's refresh added six IDs to the Viewer. All six are in the district
tables, and none is on the 168 list. Four read `無` in the district table. Two read as
approved (`09909271`, `10804122`). Re-measured on 2026-11-20 against the current payload:

| Region | Before `6b97a83` | Current |
|---|---:|---:|
| Viewer IDs | 2,022 | 2,028 |
| Viewer + district only | 1,638 | 1,644 |
| District only | 1,545 | 1,539 |
| District IDs absent from the Viewer | 1,632 | 1,626 |

The other regions do not move. The 87 IDs of the 168 + district region are unchanged.

---

## 4. Why 3,655 rows contain only 3,651 IDs

Four IDs occur on two district pages with different case names. Each ID contributes one
extra row. The live detail header names only one side of each conflict.

| `case_id` | District rows and published case names | Header match |
|---|---|---|
| `11509011` | 大同區: 擬訂臺北市大同區大同段一小段393地號等19筆土地都市更新事業計畫案. 松山區: 變更臺北市松山區敦化段二小段449-12地號28筆(原25筆)土地都市更新事業計畫及變更(第二次)權利變換計畫案. | 大同區 row |
| `11509014` | 大同區: 擬訂臺北市大同區圓環段一小段184地號等30筆土地都市更新事業計畫與權利變換計畫案. 松山區: 變更(第三次)臺北市松山區寶清段二小段353-2地號等21筆土地都市更新事業計畫及權利變換計畫案(A基地). | 大同區 row; header uses 及 where the district row uses 與 |
| `11509015` | 中正區: 擬訂臺北市中正區臨沂段一小段357地號等16筆土地 都市更新事業計畫案. 松山區: 變更(第三次)臺北市松山區寶清段二小段353-2地號等21筆土地都市更新事業計畫及權利變換計畫案(B基地). | 中正區 row |
| `11510016` | 信義區: 擬訂臺北市信義區信義段二小段133地號等12筆及信義段三小段4地號1筆土地都市更新事業計畫及權利變換計畫案. 大安區: 變更(第二次)臺北市大安區仁愛段五小段480地號等2筆(原1筆)土地都市更新權利變換計畫案. | 大安區 row |

For three of the four conflicts, the 松山區 row has a second id. The Viewer holds it as
`11510011` (for `11509011`), `11510014` (for `11509014`) and `11510015` (for `11509015`).
The evidence is the Viewer's `candidate_names`, which pair each id with a case name. The
live headers of `11510014` and `11510015` carry the same case name, with no A基地 or B基地
suffix. So the headers do not tell those two apart. For `11510016` the 信義區 row has no
second id and no Viewer unit.

The evidence does not establish why the district tables print the `11509xxx` id for the
松山區 rows. Preserve both rows, record the header evidence and flag the conflict. Do not
repair an id by inference. Do not group records by `case_id` alone.

---

## 5. Pre-approval screening

The screen removed rows that matched the Viewer by `case_id` or by exact case name after
whitespace removal. It then retained rows whose district status contained one of eleven
review-stage phrases:

```text
業已提出申請審查
業申請幹事會審查
業已辦理公開展覽
業經幹事會審查
業申請幹事會複審
業經幹事會複審完竣
業申請聽證
業已辨理聽證
業申請審議會審議
業經審議會審議通過
申請報府核定中
```

The allowlist is deliberate. `核定` alone is not a rejection rule because `申請報府核定中`
is still pre-approval. The screen compared names against the node case names only. It did
not read the Viewer's `candidate_names`. Re-run on 2026-11-20 on the saved distinct rows
and the current payload, with and without them:

| Result | As run 2026-11-19 | With `candidate_names`, 2026-11-20 |
|---|---:|---:|
| District rows absent from the Viewer | 1,610 | 1,598 |
| Active-review rows among them | 497 | **493** |
| Of those, outside the 168 list | 421 | **417** |
| New applications (擬訂) | 485 | 485 |
| Amendments (變更) | 9 | **5** |
| Meeting-label records | 3 | 3 |
| Unknown-status rows (`無`, `其他` or blank) | 93 | 87 |

The 2026-11-19 run found 97 unknown-status rows on the older payload. It found 93 on the
current payload.

The first column overstates the amendments. Four of the nine amendments are held in the
Viewer under another id and drop out of the screen when `candidate_names` are read:
`11508005`, `11509011`, `11509015` and `11505026`. The Viewer holds them as `10806012`,
`11510011`, `11510015` and `11510009`. The five that stay are `11509024`, `10405044`,
`11511010`, `11511007` and `11509014`. The last stays only because its case name differs by
a suffix from the Viewer's.

The 493 is a row-screen result, not a project count. It still includes conflicting ids and
a row whose header was unavailable. A future gen-2 viewer must retain application identity
and project identity separately. The 594 header candidates of §6 were drawn from the first
column, so §6 also holds a few rows that this screen no longer names.

### The nine amendments

All nine were absent from the Viewer screen of 2026-11-19 and outside the 168 list. Four
of the nine are in the Viewer under another id (see §5 above). They are marked below. The
statuses are the district-page statuses unless noted.

| `case_id` | District | Published case name | Evidence note |
|---|---|---|---|
| `11509024` | 北投區 | 變更(第二次)臺北市北投區大業段三小段184-1地號等10筆土地都市更新事業計畫及權利變換計畫案 | 業已提出申請審查; header application date 2026/09/22; no approval date |
| `10405044` | 南港區 | 變更臺北市南港區玉成段二小段253-1地號等16筆土地都市更新事業計畫及權利變換計畫案 | District: 業申請幹事會審查; header had advanced to 業經幹事會審查 |
| `11511010` | 內湖區 | 變更(第二次)臺北市內湖區文德段二小段232地號等4筆土地都市更新事業計畫及權利變換計畫案 | 業已提出申請審查 |
| `11508005` | 內湖區 | 變更臺北市內湖區東湖段一小段14-2地號等1筆土地都市更新事業計畫及權利變換計畫案 | 業已提出申請審查; district row supplied no applicant or location. Held in the Viewer as `10806012`. |
| `11511007` | 大同區 | 變更臺北市大同區雙連段三小段98地號等25筆(原23筆)土地都市更新權利變換計畫案 | 權利變換計畫階段─業已提出申請審查 |
| `11509015` | 松山區 | 變更(第三次)臺北市松山區寶清段二小段353-2地號等21筆土地都市更新事業計畫及權利變換計畫案(B基地) | ID conflict; header names the 中正區 case. Held in the Viewer as `11510015`. |
| `11509014` | 松山區 | 變更(第三次)臺北市松山區寶清段二小段353-2地號等21筆土地都市更新事業計畫及權利變換計畫案(A基地) | ID conflict; header names the 大同區 case |
| `11509011` | 松山區 | 變更臺北市松山區敦化段二小段449-12地號28筆(原25筆)土地都市更新事業計畫及變更(第二次)權利變換計畫案 | ID conflict; header names the 大同區 case. Held in the Viewer as `11510011`. |
| `11505026` | 大安區 | 變更臺北市大安區仁愛段一小段92地號等11筆土地都市更新事業計畫及權利變換計畫案 | 業已提出申請審查; header check returned no header row. Held in the Viewer as `11510009`. |

The 大安 row prints the applicant as `德運建設股份有限公司 嗎`. Preserve that published
text or record an explicit correction. Do not silently remove the trailing character.

### The three meeting-label records

All three were in the 大安區 table. Their detail headers repeated the meeting label. They
had no applicant, location or application date in the district rows.

| `case_id` | Published 案名 | District and header status |
|---|---|---|
| `11011301` | `516次審議會` | 事業計畫階段─業經幹事會審查 |
| `11011021` | `511次審議會` | 事業計畫階段─業申請審議會審議 |
| `11010261` | `第522次審議會` | 事業計畫階段─業申請審議會審議 |

A meeting label is not an ordinary case name. Keep these rows out of project counts unless
other evidence resolves their identity.

---

## 6. Header verification and open issues

The follow-up check called `get_project168_top.ashx` once for each of 594 candidate rows, on
2026-11-19. The candidates came from the screen of §5 as it ran then (497 active rows and 97
unknown-status rows). Re-screening with `candidate_names` (§5) leaves 580 of those 594 as
candidates: 493 active rows and 87 unknown-status rows. All 580 were already in the saved
check, so the corrected figures below come from the saved replies. No new request was made.

| Check | As run 2026-11-19 | Corrected set, 2026-11-20 |
|---|---:|---:|
| Candidate rows | 594 | 580 |
| Successful header responses among active rows | 495 | 492 |
| Successful header responses among unknown rows | 95 | 85 |
| Failed checks | 4 | 3 |
| Active rows with a different header status | 82 | 80 |
| Active rows whose header already reported approval | 1 | 1 |
| Active rows whose header reported a closed outcome | 3 | 3 |
| Unknown-status rows whose header reported an active status | 2 | 2 |
| Active rows with a different header name / place / applicant | 9 / 7 / 3 | 7 / 5 / 1 |

The 14 rows that left the candidate set fall in three groups. Four are the amendments of §5
that the Viewer holds under another id. Six are `無` rows whose case name the Viewer holds under
another id. Four are `無` rows that joined the Viewer in commit `6b97a83` under the same id
(`11501012`, `11501044`, `11507015`, `11508008`). One of the four earlier failures, for
`11505026`, left with the amendments. The three failures that remain are two `no header row`
results (`10503041`, `11409034`) and one connection reset (`11410052`). A failed check is
unknown evidence, not proof that a case is absent or inactive.

The 80 status disagreements show that the district table and detail header are not
interchangeable. Store both values with their observation times. Do not choose one silently
as the universal current status.

Open issues for any production adoption:

- Resolve the four conflicting IDs with independent evidence.
- Keep meeting-label rows outside project counts.
- Define how amendment applications relate to an existing renewal unit.
- Preserve unknown statuses and missing fields without inference.
- Add a completeness check for every discovered district and every accepted or rejected
  table row.
- Record content hashes and observation times. Do not treat a changed page timestamp as a
  new case release.

---

## 7. Measurement dates and reproduction

| Input | Measurement |
|---|---|
| District pages | Read 2026-11-19; 12 districts; 3,655 distinct published rows |
| Detail headers | Checked 2026-11-19; 594 candidates |
| `P_project168.aspx` | Snapshot 2026-11-18T12:31:41Z; checked live 2026-11-19 |
| Viewer payload | `data/projects.json`; `published_date` 2026-11-12; generated 2026-11-18T22:36:36+08:00; 676 projects |

The exploration used dated one-shot scripts, not a repository pipeline module. They write
only under `data_test/district_probe/`, which git ignores. To reproduce the measurements:

1. Run `python scripts/probe_district_pages_20261119.py`. It crawls the 12 pages, removes
   the duplicate 北投 rows, and compares the rows with the Viewer and the saved 168 snapshot.
   It writes `preapproval_rows.json` (3,925 rows), `preapproval_distinct_rows.json`
   (3,655 rows) and `preapproval_analysis.json`.
2. Run `python scripts/probe_district_headers_20261119.py`. It asks
   `get_project168_top.ashx` about the screened candidates only, three requests at a time.
   Use `--limit 3` for a smoke run.
3. Run `python scripts/build_district_dashboard_data_20261119.py`. It works offline. It
   writes the dashboard data files described in §8.

The scripts follow these rules. Keep them in any rewrite:

- Fetch each discovered district once. Deduplicate on the six published fields, not on the
  source URL.
- Accept seven- or eight-digit IDs and normalise them with `zfill(8)`.
- Report every district, accepted row, rejected row and duplicate before comparing sources.
- Call the header endpoint only for named candidate IDs. Never sweep it.
- Save the source URL, observation time and raw fields with each result.

Step 1 and 2 reach the network. Step 3 does not. A rerun gives today's data. It does not
reproduce the 2026-11-19 counts, because the city and the Viewer payload both move.

Example requests:

```powershell
Invoke-WebRequest "https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F" `
  -OutFile district-entry.html

Invoke-WebRequest "https://gis.uro.taipei/ashx/get_project168_top.ashx" `
  -Method POST -Body @{case_id="11509024"}
```

These requests read public case data. They do not ingest the district rows or change the
Viewer payload. Acquisition and ingestion must remain separate.

---

## 8. Companion dashboard

The measurements above are also shown in a Claude artifact, "Taipei Case Sources":
`https://claude.ai/artifact/3Xk8sdtJ1CqEhhy8B5Vbge`. It is external state. It is not
pipeline output, and nothing in the repository reads it or writes to it.

**What it shows.**

- A Venn diagram of the Viewer, the 168 list and the district pages, with the seven region
  counts. A region with fewer than 100 IDs lists its `case_id` values.
- The explanation of 3,655 rows against 3,651 IDs, with the four conflicting IDs.
- The field comparison of §3.
- The nine amendments and the three meeting-label records of §5.

**What it holds.** The page is `files/index.html`, at version 3. Seven datasets feed it:
`cp`, `p168`, `viewer`, `duplicates`, `special`, `fields` and `meta-source`. They are fixed
copies. They do not refresh themselves. Five of them are dated 2026-11-19. Two were
replaced on 2026-11-20: `viewer` and `special`.

The `viewer` dataset is the exception. On 2026-11-20 it was replaced with a rebuild from
the payload at commit `6b97a83`. It now holds 2,028 case IDs, as in the "Current" column
of §3. The first copy held 2,022. The Venn counts are computed in the browser from the
datasets. The page text holds no fixed copy of them. After the replacement, the user opened
the page and saw the new counts in the Venn diagram. This is a manual check, not a test. It
was made on 2026-11-20 and records the page as it stood then.

Any later change to the Viewer payload makes the `viewer` dataset old again. Updating it is
a manual step: run the build script in §7, upload `viewer-ids.json` to the artifact, and
point the `viewer` dataset at the new file. The first upload stays in the artifact until
someone deletes it.

**The 87 IDs.** The 168 + district-only region holds 87 IDs. This document does not list
them, because a list goes stale with the next snapshot. The artifact shows the list for the
date of its data. To get the current list:

1. Take the case IDs of the district rows.
2. Keep the ones on the 168 snapshot.
3. Remove the ones the Viewer holds.

`scripts/build_district_dashboard_data_20261119.py` builds the three input files for this
difference. The artifact page does the subtraction in the browser.

**One file has no script.** `special-records.json` (the nine amendments, the three
meeting labels and the screening counts) was written by hand. It is a reading of the header
evidence of §5 and §6, not a computation. The build script does not make it.

**The 2026-11-20 corrections.** The page and `special-records.json` now carry the corrected
screen of §5 and §6. The file keeps both sets of counts: `as_run_2026_11_19` (497, 421, 9)
and `corrected_2026_11_20` (493, 417, 5). The page uses the corrected counts. It marks the
four amendments that the Viewer holds under another id, and it no longer says that the city
typed an id wrongly. `check` read `passed` after the change. The user has not yet looked at
the new text, so what the page shows is not confirmed here.

**One manual fact.** The header check never asked about `11510016`. It is a conflicting ID
that the screen did not select. Its header was read once on 2026-11-19, and the build script
records that reply as a constant.
