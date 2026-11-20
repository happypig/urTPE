# DownloadODFile vs the most recent gazette PDF

**Checked:** 2026-10-25 · **Gazette:** 統計至 2026-10-15 (page stamp 資料更新 115-10-21)
**Sample:** all 80 approvals dated 2026 in that gazette, not a subset.

## Verdict

| Question | Answer |
|---|---|
| Does the portal's approval **date** match the gazette? | **Yes wherever the portal has one** — 67 / 72 matched cases; 4 empty fields, **1 genuine conflict** (2026-02-21 vs 2026-02-11) |
| Does the portal have a **document** for each approval? | **No.** 56 / 72 have some document, but only 49 have a 核定公告 |
| How far behind is `DownloadODFile`? | Newest 核定公告 **2026-08-20**; newest document of any kind **2026-09-15**; **0 / 11** approvals after 2026-09-15 have any document |
| Can the documents be read as text? | **Mostly no** — 9 of 10 downloaded files are image-only scans (`text_chars == 0`) |

In one sentence: the portal knows *that* a case was approved (and usually *when*), but its
document repository lags the gazette by roughly **two months**, so `DownloadODFile` cannot
be used as an independent completeness check on a recent gazette.

---

## 1. The two artefacts

### 1.1 The PDF

| Property | Value |
|---|---|
| Page | `https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E` |
| Stamp on page | `資料更新 115-10-21` |
| File | `…/001/Upload/459/relfile/18558/10496/1d9657b0-55a3-4bbb-8846-f28eeb1a5a85.pdf` |
| Size | 1,816,170 bytes |
| SHA-256 | `9b80a6bcbf7c18e0e9305060e5047f322cb58e84f63ee879dcd97a50a5a8fe67` |
| Pages | 246 |
| Own date line | `統計至115年10月15日` → gazette id **2026-10-15** |
| Rows | 1,442 printed 編號; **1,427 parsed**; 15 excluded (truncated 地號: 67, 79, 570, 672, 719, 796, 851, 863, 902, 912, 919, 930, 944, 997, 1131) |
| Projects | 690 |
| Date range | 2002-03-21 → 2026-10-15 |

**The stamp moved; the document did not.** On 2026-10-24 the same page carried
`資料更新 115-10-15`. The file behind the new `115-10-21` stamp is byte-identical to the
one downloaded then — same size, same SHA-256. The document's own 統計至 line still reads
2026-10-15. This is the same re-upload pattern recorded in `AGENTS.md` (2026-10-05:
page advertised 115-09-29 while the newest gazette was 2026-09-24), and it means a
`Last-Modified`-style poller would report a new gazette that does not exist.

### 1.2 The API chain

`DownloadODFile` is not a data endpoint; it serves one file per call. The documents are
listed by a separate endpoint, and the case id comes from a third:

```
POST Get_updcase_list.ashx      qitem=qland&sectstr=<地段名>&monobuf=<母號>&sunobuf=<子號>
  → case rows; numeric case_id is inside the `details` URL, not the `case_id` field

POST get_project168_top.ashx    case_id=<numeric>
  → NAME, phase, uro_chk_date, uro_chk_date2

POST Get_project168_eighth.ashx case_id=<numeric>
  → [ { "OD_DOCPATH": "/…/<file>.pdf", … } ]

GET  DownloadODFile.ashx?filename=<basename of OD_DOCPATH>
  → the PDF; unknown name → HTTP 404
```

Neither `DownloadODFile` nor `Get_project168_eighth` is used anywhere in this repo (both
are marked unused in [`urotpe_api.md`](urotpe_api.md)); the comparison below was made with
a standalone probe, not through the pipeline.

---

## 2. Method

1. Parse the PDF into a temp tree (`--archive-root` / `--ledger` pointed at temp, so the
   live archive at `D:\project\urtpe-gazettes\` was untouched).
2. Take **every** row dated 2026 (80 rows).
3. Resolve each row by parcel: `Get_updcase_list` → candidate cases → keep the one whose
   `case_name` equals the gazette 案名 (NFKC-normalised, 臺/台 folded, brackets unified).
4. For the matched case, read `get_project168_top` (`uro_chk_date`, `uro_chk_date2`,
   `NAME`, `phase`) and `Get_project168_eighth` (document list).
5. Download 10 distinct documents and inspect them with pymupdf (page count, text layer).

"Resolved" means a case whose name matches exactly; 8 rows did not match (see §5.3) and
are excluded from the ratio, not counted as failures of the API.

---

## 3. Dates

| Result | Rows |
|---|---:|
| Gazette date == portal `uro_chk_date` or `uro_chk_date2` | **67** |
| Portal date fields empty | 4 |
| Portal date differs | **1** |
| Total resolved | 72 |
| Unresolved (no name match) | 8 |

**There is one genuine date conflict in the whole year:**

| Gazette | Portal | Case | 案名 |
|---|---|---|---|
| 2026-02-21 | 2026-02-11 (`uro_chk_date` and `uro_chk_date2`) | `11502008` | 擬訂臺北市內湖區東湖段一小段34地號1筆土地都市更新事業計畫及權利變換計畫案 |

The case carries a matching 核定公告, so the match itself is sound; the two sources
disagree by 10 days. The gazette column is 本府核定日期, and no other row in the year has
two differing dates, so this is not a systematic 核定→公告 offset — it is an anomaly in one
record.

The four empty-date rows are 2026-10-06, 2026-07-01, 2026-06-01 and 2026-03-31. Two of
them are 已核定 with no date at all; the 2026-10-06 row is the 已駁回 case in §5.1; and the
2026-03-31 row is a **事業概要** (`已核准`, a different stage vocabulary), so its date
probably lives in a field this probe does not read.

### Status field lags the date

Two rows carry the correct approval date while their `schedule` still says **審查中**:

| Gazette date | Case | `schedule` | `uro_chk_date` | `NAME` |
|---|---|---|---|---|
| 2026-09-10 | `11010191` | 審查中 | 2026-09-10 | `無` |
| 2026-06-04 | `11407009` | 審查中 | 2026-06-04 | `無` |

So `schedule` and `uro_chk_date` are not updated together. A check that reads only
`schedule` would report these as not yet approved.

---

## 4. Documents

### 4.1 Coverage by month

| Month | Approvals | Resolved | With ≥1 doc | With 核定公告 |
|---|---:|---:|---:|---:|
| 2026-10 | 3 | 3 | 0 | 0 |
| 2026-09 | 11 | 11 | 1 | 0 |
| 2026-08 | 12 | 12 | 10 | 6 |
| 2026-07 | 12 | 11 | 11 | 10 |
| 2026-06 | 9 | 8 | 7 | 7 |
| 2026-05 | 6 | 5 | 5 | 5 |
| 2026-04 | 8 | 7 | 7 | 7 |
| 2026-03 | 7 | 6 | 6 | 5 |
| 2026-02 | 7 | 5 | 5 | 5 |
| 2026-01 | 5 | 4 | 4 | 4 |

- 56 of 72 resolved cases have at least one document — **73 files** in total
  (42 cases with 1, 11 with 2, 3 with 3).
- **49** have a 核定公告. The newest is **2026-08-20** — 56 days before the gazette's
  2026-10-15.
- **7** have only pre-approval documents (公展公告 / 核准公告); the newest of those is
  **2026-09-15**, a 公展公告.
- **11 resolved approvals after 2026-09-15; 0 have any document.**

The newest approval in the gazette (2026-10-15, 大安區通化段四小段336, case `11501034`)
is the clean illustration: the portal has the case, the schedule says 已核定, the date is
2026-10-15 — and the document list is `[]`.

### 4.2 Document types

Across the 73 files:

| Type | Files |
|---|---:|
| 核定公告 | 50 |
| 公展公告 | 22 |
| other | 1 |

A 公展公告 is published **before** approval; finding one attached to an approved case does
not confirm the approval itself. Six cases have only that.

### 4.3 The files themselves

10 documents downloaded (660,872 – 961,540 bytes, 2–4 pages each):

| Text layer | Files |
|---|---:|
| Image-only (`text_chars == 0`) | **9** |
| Has text | 1 (708 chars, a 公展公告) |

So the documents cannot be used to verify content or dates by text extraction — they are
scans. Date consistency (§3) therefore rests on the portal's own metadata, not on reading
the 核定公告.

---

## 5. What does not reconcile

### 5.1 The 574 case — a status contradiction that is not provable

Gazette row 2: 2026-10-06, 北投區大業段四小段574, 變更…事業計畫案. The parcel search
returns **four** cases:

| case_id | schedule | 案名 |
|---|---|---|
| `109B02` | 已核准 | 劃定…574地號…為更新單元 |
| `10909181` | 自行撤回 | 擬訂…574地號…事業計畫案 |
| `10909182` | 施工中 | 擬訂…574地號…事業計畫案 |
| `10909183` | **已駁回** | 變更…574地號…事業計畫案 |

The exact-name match lands on `10909183`, whose `NAME` is
`事業計畫階段─業經本府駁回`, with an empty `uro_chk_date` and zero documents. Read
literally, the gazette says 核定 while the portal says 駁回.

It is **not** safe to call that a contradiction. The same parcel carries two 擬訂 cases
with an identical name and different outcomes (自行撤回 / 施工中) — direct evidence that
one name can map to more than one case on this portal. The repo's own rule is that
`case_name` is parsed, never compared. Either the gazette's approval is newer than any case
the portal has created, or the portal's record is stale; this data cannot decide which.

### 5.2 One date conflict

See §3 — 2026-02-21 vs 2026-02-11, the only row in 80 where both sides carry a date and
the dates differ.

### 5.3 Eight rows that could not be matched

Every one returned candidates for the parcel, but no candidate name matched the gazette
案名. These are wording differences, not API failures:

| Gazette date | Candidates | 案名 (truncated) | Why it differs |
|---|---:|---|---|
| 2026-07-29 | 9 | 變更…木柵段三小段623地號等39筆…(甲區段) | portal writes `-甲區段(A1基地、B基地)` |
| 2026-06-30 | 1 | 變更…金華段四小段455-3地號等12筆(原508地號等11筆)… | portal says **13筆** |
| 2026-05-14 | 4 | 變更…懷生段三小段249地號等26筆…權利變換計畫案 | portal adds 事業計畫及 |
| 2026-04-28 | 5 | 變更…直興段二小段500地號等12筆(原9筆)…事業計畫案 | portal has only the 擬訂 case |
| 2026-03-17 | 4 | 變更(第二次)…大業段三小段762地號等31筆… | portal: 權利變換計畫案, no 事業計畫 |
| 2026-02-26 | 2 | 擬訂…**松化區**敦化段一小段510地號1筆… | gazette typo for 松山區 |
| 2026-02-24 | 3 | 變更…學府段一小段509-1地號等15筆(原26筆)…(含釐正圖冊)案 | portal omits the 含釐正圖冊 suffix |
| 2026-01-07 | 6 | 變更(第三次)…金華段一小段719地號等1筆(原11筆)… | portal: 變更…及擬訂權利變換計畫案 |

Two more rows — 2026-09-29 and 2026-08-04 — failed only because the gazette prints
**compatibility ideographs** (`北` U+2F63, `都` U+2FA6, `利` U+2F1D) instead of the normal
characters. NFKC folding resolves both, and is applied in the counts above. Any matcher
that compares these names byte-for-byte will under-count by about 2 %; the gazette also
contains at least one plain typo (松化區 for 松山區), so equality alone is not enough even
after folding.

### 5.4 The stamp is not the publication

Covered in §1.1: `資料更新 115-10-21` and `統計至 2026-10-15` describe the same bytes that
were already being served on 2026-10-24.

---

## 6. What this means for the pipeline

- **Do not use `DownloadODFile` as a completeness source.** For approvals in the last month
  it returns nothing at all, and for many older ones it returns only pre-approval notices.
  A "no document" result is the normal state, not evidence that the gazette row is wrong.
- **The portal's date fields are usable, with two caveats**: they are sometimes blank
  (4 / 72 here) and one row in 80 disagreed by 10 days. `schedule` must not be used as a
  proxy for approval — two cases were still 審查中 while carrying the approval date.
- **Documents are scans.** Any future use (e.g. extracting 核定函 dates) needs OCR; text
  extraction returns nothing for 9 of 10 files.
- **The gazette remains the authority.** `DownloadODFile` adds documents when they exist,
  but it cannot confirm that the gazette is complete, and it lags far enough behind that
  a recent gazette will always look "missing" from the portal side.

---

## 7. Reproducing

```powershell
# parse the current gazette into a throwaway tree (never the live archive)
$t = "$env:TEMP\opencode\g1021"
python -m urtpe.cli g1021.pdf -o $t\out --archive-root $t\archive --ledger $t\ledger.jsonl
# → [INFO] gazette_id: 2026-10-15 · 1427 records · 690 projects · 15 excluded · tripwire: PASS

# the chain for one row
Invoke-WebRequest "https://gis.uro.taipei/ashx/Get_updcase_list.ashx" -Method POST `
  -Body @{qitem="qland"; sectstr="通化段四小段"; monobuf="336"; sunobuf="0"}
Invoke-WebRequest "https://gis.uro.taipei/ashx/get_project168_top.ashx" -Method POST `
  -Body @{case_id="11501034"}
Invoke-WebRequest "https://gis.uro.taipei/ashx/Get_project168_eighth.ashx" -Method POST `
  -Body @{case_id="11501034"}
Invoke-WebRequest "https://gis.uro.taipei/ashx/DownloadODFile.ashx?filename=<basename>.pdf" `
  -OutFile doc.pdf
```

Endpoint inventory and liveness rules: [`urotpe_api.md`](urotpe_api.md).
