# Final Results: Taipei Platform JSON API Integration

**Date:** 2026-08-23
**Outcome:** 697 / 709 projects (98.3%) resolved with official links and full milestone timelines — up from 3 / 709 (0.4%).

## Results Summary

| Metric | Before | After |
|--------|--------|-------|
| Resolved projects | 3 / 709 (0.4%) | **697 / 709 (98.3%)** |
| With full milestone timelines (階段辦理過程) | 0 | **697** |
| Unresolved | 706 | **12** (named-anchor units, no parcel basis — by design) |

### Sample Output (大同區-玉泉段二小段-40地號等29筆)

```json
{
  "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/771",
  "taipei": ["09708181", "10104121", "10110181", "11502013"],
  "milestones_taipei": {
    "計畫公聽會日期": "2012/10/18",
    "申請計畫日期": "2012/12/28",
    "審議會審議通過日期": "2020/06/08",
    "核定日期": "2020/11/17",
    "建照核發日期": "2021/09/15"
  }
}
```

(29 milestone fields total per case; see `STAGE_FIELD_MAP` in `urtpe/links.py`.)

## Discovery: Internal JSON APIs

The Taipei 都市更新審議服務平台 (gis.uro.taipei) renders its pages via JavaScript,
but the underlying data is served by simple `ashx` POST endpoints that accept
form-encoded parameters and return plain JSON. These endpoints require no
session, no ViewState, and no browser automation.

### 1. Case Search by Land Parcel

```
POST https://gis.uro.taipei/ashx/Get_updcase_list.ashx
Content-Type: application/x-www-form-urlencoded

qitem=qland&sectstr=玉泉段二小段&monobuf=40&sunobuf=0
```

Response: JSON array of cases at that location:

```json
[
  {
    "item": "玉泉段二小段<br>0040 - 0000",
    "case_id": "R091306-02",
    "case_name": "擬訂臺北市大同區玉泉段二小段40地號等29筆...",
    "schedule": "施工中",
    "details": "r_progress_detail.aspx?case_id=10110181",
    "map": "https://bim.udd.gov.taipei/UDDPlanMap/?r=R091306-02"
  }
]
```

**Key detail:** the numeric case_id must be extracted from the `details` URL
query string, not from the `case_id` field (which holds internal codes like
`R091306-02`).

### 2. Milestone Timeline per Case

```
POST https://gis.uro.taipei/ashx/Get_project168_second.ashx
Content-Type: application/x-www-form-urlencoded

case_id=10110181
```

Response: JSON array with all 階段辦理過程 dates (`Plan_Open_Date`,
`Uro_Chk_Date`, `Blic_Date`, ...). Field-to-label mapping is defined in
`urtpe/links.py` (`STAGE_FIELD_MAP`, 30 entries covering 計畫/權變/概要 tracks).

### 3. Supplementary Endpoints

| Endpoint | Purpose |
|----------|---------|
| `get_project168_top.ashx` | Basic info: case name, implementer, key dates |
| `Get_project168_First.ashx` | District, 劃定方式, contacts |
| `Get_project168_third.ashx` | Execution stats (area, doors, parking) |
| `Get_project168_fourth.ashx` | 容積獎勵 breakdown |
| `ashx/getSectionList.ashx` | Section list per district |

All responses may be gzip-compressed — check for magic bytes before decoding.

## Implementation

New functions in `urtpe/links.py`:

- `_post_taipei_api(url, params)` — POST with retry/backoff + gzip handling
- `search_taipei_cases_api(section, parcel)` — parcel search → numeric case_ids
- `fetch_taipei_milestones_api(case_id)` — milestone timeline dict

`discover_project_links()` rewritten as Taipei-first flow:

```
For each project:
  anchor.section + anchor.first_parcel
    → POST Get_updcase_list.ashx → case_ids          (~1s)
    → POST Get_project168_second.ashx → milestones   (~1s/case)
  National portal (supplementary only) → twur view URL + 推動歷程
```

Pure HTTP + JSON. No Playwright, no HTML parsing of JS-rendered content.
Per-project checkpointing (`data/.link_cache/<project>/result.json`) makes runs
resumable across interruptions.

## Bugs Fixed During This Work

1. **Fallback JSON corruption** — writing JSON via Python `json.dump()` from a
   cp1252 Windows terminal mangled characters (區→匠, 玉泉→特朗, 堤→圤).
   Fix: author data files via file-writing tools with explicit UTF-8, never
   through terminal-interpreted string literals. Verified with
   `scripts/verify_encoding.py`.
2. **Status logic bug** — `resolved` was never set because the final status
   check excluded `"unresolved"`, which nothing ever cleared after the initial
   default. Fix: derive status directly from obtained results.
3. **Gzip handling** — `fetch_url()` decoded gzip-compressed responses as
   UTF-8 garbage because `BROWSER_HEADERS` advertise `Accept-Encoding: gzip`.
   Fix: detect gzip magic bytes and decompress before decode.
4. **Case-id extraction** — numeric detail IDs live in the `details` URL query
   string; the `case_id` field holds internal codes. Filter on parsed URL ids.
5. **Stale cache short-circuit** — failed runs cached "unresolved" results that
   blocked retries even after code fixes. Clear per-project caches when
   changing discovery logic.

## Terminal Display Caveat

Chinese characters in `viewer/projects.data.js` are valid UTF-8 (verified by
`scripts/verify_encoding.py`: no U+FFFD replacement chars, correct CJK
codepoints). The `???` seen in terminal output is purely a Windows console
display limitation (cp1252 cannot render CJK). Always verify data through file
reads or codepoint dumps, never through terminal echo.

## Files Changed

- `urtpe/links.py` — Taipei-first API flow, gzip fix, status logic fix
- `urtpe/cli.py` — `--from-js`, `--fresh`, `--playwright` flags
- `urtpe/taipei_playwright.py` — Playwright searcher (kept as fallback tool)
- `viewer/app.js`, `viewer/app.css` — milestone timeline cards + badges
- `data/taipei_case_ids.json` — hand-curated seed mappings (now largely redundant)
- `scripts/verify_encoding.py` — UTF-8 validation proof
