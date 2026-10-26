# gis.uro.taipei `/ashx/` API inventory

**Probed:** 2026-10-25 · **Host:** `https://gis.uro.taipei` · **Base path:** `/ashx/`

Every endpoint below was discovered from the site itself — 11 pages (`Main.aspx`,
`R_progress.aspx`, `P_project168.aspx`, `ua_frmEasyQuery.aspx`, `ua_frmEasyCase.aspx`,
`P_ApplyMain.aspx`, `Meet.aspx`, `P_QAlist.aspx`, `P_MyProjects.aspx`, `P_Sitemap.aspx`,
`r_progress_detail.aspx`) plus the JavaScript those pages load — then called live.

**40 distinct endpoints · 37 live · 3 dead · 6 referenced by this repo (5 by the pipeline).**

None of them is documented by the city. §1 records that negative result, and the one API
family on this host that *is* registered — `UpdateAreaWebAPI`, a different namespace that
data.taipei indexes and that does not cover the gazette. The UDD GeoServer WFS, a second
host the recovery adapter reads, is documented in §6.

The integration narrative for the five used endpoints (why they were chosen, what they
replaced) is in [`final_results_json_api.md`](final_results_json_api.md); this file is the
complete inventory and does not repeat it.

---

## 1. How "live" was decided

An unknown `.ashx` on this host answers **HTTP 200** with a generic HTML *Error Page*
(`<title>Error Page</title>`, "Bootsnipp.com"). Status codes therefore prove nothing.

Body length is **not** a usable signature either: the same error page was measured at
**7,597** and **7,635** bytes for different paths (it varies with the requested URL).
Liveness here is decided by body content:

```python
def is_error_page(raw):
    txt = raw.decode("utf-8", "replace")
    return "<title>Error Page</title>" in txt or "Bootsnipp.com" in txt
```

Each endpoint was called twice — `POST` with `case_id=11501034`, and `GET` with no
parameters — and counted live only if **at least one** method returned a non-error body.
(Some endpoints only answer on `POST`: `GetUpdSect` returns `[]` on `POST` and the error
page on `GET`.)

The "Returns" column is what that probe actually produced, not a full contract: several
endpoints need parameters this probe does not know, and answer `[]` or `err` until given
them. Where the correct parameter set is known it is named.

### No official API documentation for these endpoints

Nothing on this host documents the `/ashx/` endpoints. Checked 2026-10-25:

| Probe | Result |
|---|---|
| `/swagger`, `/swagger/v1/swagger.json`, `/openapi.json`, `/api-docs` | 404 |
| `/Service.asmx`, `/WebService.asmx`, `/ws.asmx`, `/api.asmx`, `*.svc` | error page / 404 — no WSDL |
| `/robots.txt`, `/sitemap.xml` | 404 |
| `/ashx/`, `/ashx` | 403 — directory listing disabled |
| `/help`, `/Help.aspx`, `/P_Help.aspx`, `/P_Download.aspx` | 403 / error page |
| `P_Sitemap.aspx` | no developer section; "操作說明" points at the manual below |
| JS bundles loaded by `Main.aspx` | jQuery, Bootstrap, Swiper, SweetAlert2 — no doc links |

The site's only downloadable document is

```
GET ashx/Downloadoperate.ashx?filename=都市開發審議服務平台線上申請_操作手冊.pdf
```

9,265,211 bytes · 67 pages · a **UI operation manual** (系統登入 / 案件列表 / 線上申辦).
Its extractable text — the pages are mostly screenshots, only ~4,900 characters — contains
no occurrence of `API`, `介接`, `ashx`, `JSON` or `Web Service`.

So the inventory below is reverse-engineered from the inline JavaScript of the site's own
pages; there is no published contract to check it against. Two consequences worth keeping
in mind: a parameter rename would surface only as an empty response, and the `[]`/`err`
answers in the table cannot be distinguished from a changed contract without a known-good
call.

### The one registered API family — a different namespace

`data.taipei` does register an API on this host, but it is `UpdateAreaWebAPI`, not `/ashx/`,
and the registration is a three-row CSV rather than a specification. Dataset `00001791`
臺北市自行劃定更新單元查詢 (都發局更新處, updated 2026-09-08) contains only:

| ItemName | URL |
|---|---|
| 更新單元申請人資料 | `https://gis.uro.taipei/UpdateAreaWebAPI/api/People` |
| 更新單元地號資料 | `https://gis.uro.taipei/UpdateAreaWebAPI/api/Ward` |
| 更新單元案件資料 | `https://gis.uro.taipei/UpdateAreaWebAPI/api/Case` |

All three answer `200 application/json`, and all three are **double-encoded**: the body is a
one-element array holding a JSON string, so reading one takes
`json.loads(json.loads(body)[0])`. Their shapes:

| Endpoint | Bytes | Rows | Fields |
|---|---|---|---|
| `api/People` | 105,495 | 2,110 | `ID`, `ApplyPeople` (masked, e.g. `元******`) |
| `api/Ward` | 6,192,956 | 72,039 | `ID`, `Name`, `No1`, `No2` |
| `api/Case` | 1,051,079 | 2,651 | `ID`, `Dist`, `Define`, `Name`, `Status`, `CaseMode`, `Seat`, `Area`, `ApprovedDate`, `ApprovedNum` |

`api/Case` is malformed on top of that: the leading `[{` is missing (the string starts
`"ID":"115B13"`), and record `ID 102230` has unescaped quotes inside `Seat`, so no wrapper
repair parses the payload whole. Splitting on `},{"` and parsing each fragment recovers
2,650 of 2,651.

This is 自行劃定更新單元 data — designation of renewal units, not approvals. It does not
overlap the gazette, and nothing in `urtpe/` calls it. The catalogue behind it can be pulled
whole, which is how the negative result below was established:

```
GET https://data.taipei/api/frontstage/tpeod/dataset.download?format=json   # 2,815 rows, 4.5 MB
GET https://data.taipei/api/frontstage/tpeod/dataset.view?id=<uuid>         # one dataset's metadata
```

Of those 2,815 datasets, 11 come from 都發局更新處 and **none** is 核定案件: `核定案件`
matches zero titles, and the three 都發局 datasets that mention 核定 are statistics
(容積獎勵案件統計表, 住宅補貼受理情形, 都市設計審議案件核定數). The gazette therefore has
no open-data equivalent; the PDF the poller fetches remains the only source.

---

## 2. Endpoints used by this repository

Line numbers are `urtpe/links.py` unless stated. "Constant" is where the URL is defined;
"call" is where it is actually requested.

| Endpoint | Constant | Call site | What it supplies |
|---|---|---|---|
| `Get_updcase_list.ashx` | `:721` `TAIPEI_SEARCH_API` | `:817` | 地號 → case rows (`details` URL carries the numeric `case_id`) |
| `Get_project168_second.ashx` | `:723` `TAIPEI_STAGE_API` | `:1137` | 階段辦理過程 timeline (34 fields, `STAGE_FIELD_MAP` at `:735`) |
| `Get_project168_third.ashx` | `:724` `TAIPEI_THIRD_API` | `:1175` | 開工 / 使用執照 / 成果報備 dates |
| `Get_project168_fourth.ashx` | `:725` `TAIPEI_FOURTH_API` | `:1180` | 容積獎勵 breakdown |
| `get_project168_top.ashx` | `:722` `TAIPEI_TOP_API` | **recovery only** (`urtpe/recovery_sources.py`) | case header: `NAME`, `phase`, `uro_chk_date`, `uro_chk_date2` |

`TAIPEI_TOP_API` was scripts-only until the truncated-row recovery landed: the recovery
adapter now calls it for every name-matching candidate, because the approval date lives in
`uro_chk_date` or `uro_chk_date2` and only the header row carries both. The six dated
scripts below still call it directly:

| Script | Line |
|---|---|
| `scripts/curated_resolve.py` | `:235` |
| `scripts/resolve_via_view_links_20260829.py` | `:81` |
| `scripts/explore_twurless_status.py` | `:52` |
| `scripts/backfill_names_from_top_api_20260829.py` | `:49` |
| `scripts/resolve_chongren_exception_20260829.py` | `:37` |
| `scripts/schedule_topup_20260829.py` | `:69` |

The three pure consumers of a top row (`schedule_from_top`, `classify_case_outcome`,
`project_twur_class`, `:1387`/`:1407`/`:1422`) likewise have no production caller — they
are exercised from `tests/` and the dated scripts. Outside recovery the pipeline still
does not need the header row (the parcel search response carries `case_name`, the stage
timeline carries the dates); the recovery adapter needs it for the two date fields alone.

---

---

## 3. Full inventory (40 endpoints)

`Repo` = referenced by code in `urtpe/`, `scripts/`, `tests/` or `viewer/`. A mention in
`docs/` alone is not counted.

| # | Endpoint | Live | Returns (probe) | Role | Repo |
|---:|---|:--:|---|---|---|
| 1 | `Get_updcase_list.ashx` | ✅ | 2,413 B JSON with `qitem=qland&sectstr=<地段名>&monobuf=<母號>&sunobuf=<子號>` | 地號 → case search | **pipeline** `:721`/`:817`; `scripts/curated_resolve.py:149` |
| 2 | `Get_project168_second.ashx` | ✅ | 119,659 B — `Plan_Open_Date`, `outline_open`, … | 階段辦理過程 timeline | **pipeline** `:723`/`:1137` |
| 3 | `Get_project168_third.ashx` | ✅ | 841 B — `Eng_Start_Date`, `Ulic_Date`, `Report_Date` | 開工 / 使照 / 成果報備 | **pipeline** `:724`/`:1175`; `scripts/probe_third_6projects.py:9` |
| 4 | `Get_project168_fourth.ashx` | ✅ | 689 B — `name_reward_no`, `Park_Area`, `Park_Cars` | 容積獎勵 | **pipeline** `:725`/`:1180` |
| 5 | `get_project168_top.ashx` | ✅ | 666 B — `CASE_ID`, `CASE_NAME`, `NAME`, `phase`, `uro_chk_date`, `uro_chk_date2` | case header / status | **scripts only** `:722` + 6 scripts (§2) |
| 6 | `DownloadODFile.ashx` | ✅ | `?filename=<basename>` → the PDF; unknown name → **HTTP 404** | download a case document | — |
| 7 | `Downloadoperate.ashx` | ✅ | 0 B | file download for operator forms (contract unknown) | — |
| 8 | `Get_announcement.ashx` | ✅ | `err` | announcement list (needs paging params) | — |
| 9 | `Get_dlstTransition.ashx` | ✅ | 77 B — `[{"NO":"0","NAME":"正軌"},{"NO":"1","NAME":"轉軌"}]` | 正軌/轉軌 lookup | — |
| 10 | `Get_project168.ashx` | ✅ | 834 B with `type=project168&pageIndex=0&pageSize=3`; `TotalCount: 467` | paged 168-project list | — |
| 11 | `Get_project168_eighth.ashx` | ✅ | `[]` when the case has no documents; else rows carrying `OD_DOCPATH` | per-case document list | — |
| 12 | `Get_project168_fifth.ashx` | ✅ | 897 B — `VolumeTurn_Area`, `Case_921_311_Area`, `Old_Apart` … | 面積 / 戶數 | — |
| 13 | `Get_project168_First.ashx` | ✅ | 609 B — `District`, `Lie`, `Place` | case location / address | — (described in `final_results_json_api.md:85`) |
| 14 | `Get_project168_Ninth.ashx` | ✅ | 524 B — `Plan_Open_Date3`, `Plan_App_Date3`, `Publand_Ask_*` | 公展 / 申請 dates | — |
| 15 | `Get_project168_Ninth_bottom.ashx` | ✅ | 784 B — `t_no`, `t_name`, `stage_name`, `progress` | stage progress table | — |
| 16 | `Get_project168_release.ashx` | ✅ | `true` | `release` flag | — |
| 17 | `Get_project168_seventhafter.ashx` | ✅ | `[]` | 第七階段 (after) — empty for this case | — |
| 18 | `Get_project168_seventhbefore.ashx` | ✅ | `[]` | 第七階段 (before) — empty for this case | — |
| 19 | `Get_project168_sixth.ashx` | ✅ | 244 B — `Renew_Mon1`, `Renew_Mon2`, `Renew_Mon3` | cost fields (`Renew_Mon*`) | — |
| 20 | `Get_project168_ten.ashx` | ✅ | 0 B | unknown contract | — |
| 21 | `Get_project168_updcase.ashx` | ✅ | 98 B — `case_name` of the related unit | related 更新單元 | — |
| 22 | `Get_Stage_plan_bottom.ashx` | ✅ | `err` | stage-plan bottom table (params unknown) | — |
| 23 | `Get_Stage_plan_top.ashx` | ✅ | 46 B — `STYLE`, `PHASE`, `PROGRESS_NO` | stage-plan header | — |
| 24 | `get_Updated.ashx` | ✅ | `2024/12/9` | site data-update date | — |
| 25 | `get_urolink.ashx` | ✅ | 2,181 B nav tree | site navigation | — |
| 26 | `GetLogin.ashx` | ✅ | `sessionempty` | login state | — |
| 27 | `getRoadList.ashx` | ✅ | `[]` (needs `qitem` / `sec`) | road dropdown | — |
| 28 | `getSectionList.ashx` | ✅ | `[]`; with `qitem=SectionList_20&sec=<行政區>` → `AA48`/`KCNT`/`landname` | 地段 dropdown | — |
| 29 | `GetUpdApply.ashx` | ✅ | `[]` | apply-list query | — |
| 30 | `GetUpdCase.ashx` | ✅ | `[]` | case query | — |
| 31 | `GetUpdQuery.ashx` | ✅ | `[]` | query form | — |
| 32 | `GetUpdSect.ashx` | ✅ | `[]` on `POST`; error page on `GET` | section query | — |
| 33 | `getzoneList.ashx` | ✅ | 1,928 B — 12 行政區 with codes | 行政區 dropdown | — |
| 34 | `Login.ashx` | ✅ | `帳號密碼錯誤！` | login submit | — |
| 35 | `SetLoginInfo.ashx` | ✅ | `Session` | login session write | — |
| 36 | `SetSession.ashx` | ✅ | `false` | session key write — **commented out** in `Main.aspx` | — |
| 37 | `ucBrowseCountl.ashx` | ✅ | `err` | browse counter | — |
| 38 | `setLog.ashx` | ❌ | error page | access logging | — |
| 39 | `GetSession.ashx` | ❌ | error page | session read (`media/js/utils.js`) | — |
| 40 | `GetToday.ashx` | ❌ | error page | server date (`media/js/utils.js`) | — |

The three dead endpoints are all session/analytics plumbing, all referenced by the site's
own JavaScript, and none is needed to read public case data.

---

## 4. Request shapes worth knowing

**Parcel search** — `Get_updcase_list.ashx` (POST, form-encoded):

```
qitem=qland&sectstr=通化段四小段&monobuf=336&sunobuf=0
```

- `sectstr` is the **section name**, not the `AA48` code that `getSectionList` returns.
- Hyphenated parcels must be split: `424-8` → `monobuf=424`, `sunobuf=8`. Passing the
  whole string as `monobuf` silently returns no rows.
- The response's `case_id` is an internal code (`R097701-01`); the **numeric** id used by
  every other endpoint is inside the `details` URL
  (`r_progress_detail.aspx?case_id=10011271`).

**Document layer** — two calls, neither used by this repo:

```
POST Get_project168_eighth.ashx   case_id=<numeric>
  → [ { "OD_DOCPATH": "/…/<file>.pdf", … } ]

GET  DownloadODFile.ashx?filename=<basename of OD_DOCPATH>
  → the PDF; HTTP 404 if the name is wrong
```

**Section list** — `getSectionList.ashx` needs `qitem=SectionList_20&sec=<行政區>`;
calling it with `zone` instead returns `[]`.

**Compression** — responses may be gzip-compressed; check magic bytes before decoding
(noted in `final_results_json_api.md`).

---

## 5. Reproducing the probe

```powershell
# liveness (content, not length)
Invoke-WebRequest "https://gis.uro.taipei/ashx/Get_project168_second.ashx" `
  -Method POST -Body @{case_id="11501034"} |
  Select-Object -ExpandProperty Content | Select-Object -First 1

# parcel search
Invoke-WebRequest "https://gis.uro.taipei/ashx/Get_updcase_list.ashx" -Method POST `
  -Body @{qitem="qland"; sectstr="通化段四小段"; monobuf="336"; sunobuf="0"}

# a document (name from eighth.ashx)
Invoke-WebRequest "https://gis.uro.taipei/ashx/DownloadODFile.ashx?filename=<basename>.pdf" `
  -OutFile doc.pdf
```

None of the data endpoints requires a session. The only session-related endpoints are
`Login`, `SetLoginInfo` and `SetSession`, and the five endpoints this repo uses answer
without them.

---

## 6. UDD GeoServer WFS — the map service the recovery adapter reads

**Probed:** 2026-10-25/26 · **Host:** `https://zonegeo.udd.gov.taipei` · **Endpoint:**
`/geoserver/Taipei/wfs` (WFS 1.1.0, `outputFormat=json`)

Two layers matter to this repo; both are read keyed, never swept:

| Layer | Features | Fields | Supplies |
|---|---|---|---|
| `Taipei:uro-redevelop-ALL-5` | 7,588 | `ID`, `NO`, `layer` | case-boundary polygons, keyed `ID='<case>'` |
| `Taipei:LAND-ALL-TWD97` | 421,857 | `sect_name`, `land_no`, `land_pnum`, `land_snum` | the cadastral parcel layer, keyed `sect_name='<段小段>'` |

Measured behaviour baked into `urtpe/recovery_sources.py` (full record in
`openspec/changes/recover-truncated-rows-via-api/poc_findings.md` T8/T10):

- **The boundary id space is R-form and group-level.** ids look like `R089601`; numeric
  case ids (`09610233`) have **no** polygons on any probed layer. One id can return
  **several features** — `ID='R089305'` returns two, and *neither* is the 203-1 unit's
  boundary: the id spans sibling units (190/203-1/208/219/517). Any reconstruction
  therefore has to re-prove itself against the unit's own fragment; the adapter unions
  multi-feature returns and the calibrated checks refuse what does not fit.
- **CQL `BBOX` evaluates in native TWD97 metres** — a lat/lon bbox silently matches
  nothing. Pull the whole 段/小段 instead (1,076 and 1,033 parcels measured, far under
  `maxFeatures=3000`) and test containment in-process; coordinates come back as
  EPSG:4326 with `srsName=EPSG:4326` on the request.
- **Containment signal: ≥1 ring vertex strictly inside the boundary.** Centroid-in is
  not a membership test — 17 far parcels measure centroid-in with zero vertices inside
  (boundary artifacts). Membership = fragment ∪ {candidates sorting after the fragment's
  last visible parcel with ≥1 vertex inside}, accepted only when the count closes to the
  案名's declared count (虎林段 `R089601`: 148 candidates → exactly 138; 美仁段
  `R098505`: 75 ≠ 74 → refuse → the fragment stays, flagged partial).
- **The document route is not a recovery source:** `Get_project168_eighth.ashx` →
  `DownloadODFile.ashx` returned 0 documents for the A/B-zone cases probed.
- Requests need no session; the web console answers 403 — only the `/wfs` endpoint speaks.

```powershell
# a case boundary
Invoke-WebRequest "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs?service=WFS&request=GetFeature&version=1.1.0&outputFormat=json&srsName=EPSG:4326&typename=Taipei:uro-redevelop-ALL-5&cql_filter=ID%3D%27R089601%27"

# a whole section's parcels (never a bbox filter — see the SRS trap above)
Invoke-WebRequest "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs?service=WFS&request=GetFeature&version=1.1.0&outputFormat=json&srsName=EPSG:4326&typename=Taipei:LAND-ALL-TWD97&maxFeatures=3000&cql_filter=sect_name%3D%27%E8%99%8E%E6%9E%97%E6%AE%B5%E5%9B%9B%E5%B0%8F%E6%AE%B5%27"
```
