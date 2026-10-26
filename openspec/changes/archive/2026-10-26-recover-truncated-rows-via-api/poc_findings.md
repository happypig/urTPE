# POC findings — tasks 1.2–1.7 (measured 2026-10-26)

Sources: `probes/t1_matrix.py` (T1/T2/T5), `probes/t8_overlap.py` (T8),
`probes/t4_roc_probe.py` (T4), `probes/t10_vintage.py` (T10), plus the
2026-10-25/26 exploration probes (`pdf_all15.py`, `bim_intersect2/3.py`). All
live reads of `gis.uro.taipei/ashx/` and the UDD GeoServer WFS; the WFS pulls
for T8 are cached in the session temp dir (`wfs_cache/`). No product code was
touched. The gazette under test is 核定案件-2026-10-23.pdf (統計至 2026-10-15,
held in the archive, not yet ingested — the shipped data/ still reflects
1151006).

## T1 — identity matrix: 15/15 exact (the design table said 14/15)

All 15 truncated rows were re-identified from their own 案名 via
`Get_updcase_list(sectstr, monobuf, sunobuf)` + `get_project168_top`, with an
exact-date candidate accepted for every row. No row needed the similarity
fallback and no row lands in the 0.5–0.7 flag band.

| 編號 | gazette date | unit (declared) | accepted ashx case | date field | norm. equality |
|---|---|---|---|---|---|
| 67 | 2026-03-12 | 虎林段四小段38 (138筆) | 11502012 | uro_chk_date | yes |
| 79 | 2026-01-14 | 美仁段二小段694 (74筆) | 11411014 | uro_chk_date (=date2) | yes |
| 570 | 2021-07-20 | 虎林段四小段38 (138筆) | 10908231 | uro_chk_date | yes |
| 672 | 2020-07-14 | 振興段一小段2-6 (101筆) | 09906091 | uro_chk_date | yes |
| 719 | 2020-01-15 | 雙連段二小段203-1 (98筆) | 10506132 | uro_chk_date | yes |
| 796 | 2019-05-28 | 虎林段四小段38 (138筆) | 09403312 | uro_chk_date | yes |
| 851 | 2018-12-04 | 雙連段一小段197 (72筆) | 09902027 | **uro_chk_date2** | yes |
| 863 | 2018-10-04 | 漢中段二小段328 (110筆) | 09703204 | **uro_chk_date2** | yes |
| 902 | 2018-05-03 | 漢中段二小段328 (110筆) | 09703203 | **uro_chk_date2** | yes |
| 912 | 2018-03-27 | 雙連段一小段197 (72筆) | 09902026 | **uro_chk_date2** | yes |
| 919 | 2018-02-08 | 雙連段二小段203-1 (98筆) | 10506131 | uro_chk_date | yes |
| 930 | 2017-12-12 | 雙園段二小段505 (77筆) | 09610233 **+** 09610237 | **uro_chk_date2** | no (−A區/−B區) |
| 944 | 2017-11-14 | 漢中段二小段328 (110筆) | 09703202 | uro_chk_date (=date2) | yes |
| 997 | 2017-03-16 | 雙連段一小段197 (72筆) | 09902025 | **uro_chk_date2** | yes |
| 1131 | 2014-04-25 | 南港段一小段720 (105筆) | 09412311 | uro_chk_date | yes |

- The address core (`臺北市<區><段><parcel>地號等N筆[(原M筆)]`) is a **raw**
  substring of the accepted `CASE_NAME` for all 15 rows — normalization is
  defensive on this gazette, not load-bearing.
- Date-field resolution confirmed: 權利變換 stages close in `uro_chk_date2`
  alone (851, 863, 902, 912, 930, 997); 事業計畫 stages in `uro_chk_date`;
  79/944 carry both fields equal. The two-field check is mandatory.
- 930 is the only multi-candidate row (the −A區/−B區 zone pair, both exact);
  both attach per D-E.
- 919's schedule is 完成成果備查, not 已核定 — the schedule is display-only and
  plays no part in the checks.

## T2 — normalization table and fallback band

- Table applied to both sides before comparison: strip all whitespace/newlines;
  full-width （）→ ASCII `()`; `計劃`→`計畫`; `ㄧ`→`一`. All are corpus-known
  city-side drift (openspec/config.yaml context). On the 15 accepted pairs the
  raw containment already held, so the table is defensive here.
- Normalized `CASE_NAME` == normalized 案名 for 13/15 rows; the 2 exceptions are
  930's zone-suffixed cases (suffix −A區/−B區; similarity 0.965) — expected,
  handled by attachment, not by normalization.
- Chosen band: **unchanged** — link ≥ 0.7, flag 0.5–0.7 (config's provisional
  starting points), with count-fragment containment required for band
  acceptance. Observed accepted-pair similarities: 1.0 (13 rows), 0.965 (zone
  pair) — far above the band; the fallback was exercised 0 times on this
  gazette.

## T5 — request budget (recorded per task)

- Probe ceiling (top called for *every* candidate carrying a details id):
  **187 requests, 50.0 s wall** for the full 15-row pass (≈3.7 req/s; no
  throttling and no WAF observed — consistent with facts_2_portals §1).
- Product pass: 15 keyed `Get_updcase_list` lookups (8 distinct units —
  cacheable per unit) + `get_project168_top` only for the 68 name-hit
  candidates ⇒ **≤ 83 requests, est. ~25 s**. One transient read timeout
  occurred in ~300 requests; the adapter retries 4× with backoff (as the probe
  does).

## T8 — overlap calibration (the core POC finding)

- **Pure vertex-fraction thresholds cannot close the anchors.** 虎林段's in-gap
  surplus parcels (44/85/87/92) measure 0.6 — the same fraction as true tail
  members (93-28/31/32/35); no threshold yields 138 or 74. A threshold-only
  test is REJECTED.
- **Calibrated rule (accepted):** reconstructed list = fragment ∪ {candidates
  sorting after the fragment's last visible parcel in gazette order, with ≥1
  ring vertex strictly inside the boundary}; accept iff the count closes to the
  案名's declared count, else refuse → fragment+partial. The positional term is
  deterministic: the printed list is complete-sorted up to the cut, so a true
  member outside the fragment must sort after the last printed parcel.
- 虎林段 `R089601`: fragment 113 unique (read from the PDF cell itself; the
  exploration transcript's 112-unique count was a transcription loss — the cell
  holds 113, including 71-11) + tail `93-17…93-41` (25) = **138 = declared;
  CLOSES.** All 25 tail members have vertex-fraction ≥ 0.2; the 10 in-gap
  surplus (37, 42, 43, 44, 70, 85, 87, 89, 91, 92) sort before the cut. The 17
  centroid-only far parcels (94…338, fraction 0.0) are excluded by the
  ≥1-vertex candidate definition — **centroid-in must not be a containment
  signal** (36 parcels are centroid-in for 虎林段, incl. the 17 far artifacts).
- 美仁段 `R098505`: tail candidates {742 (0.5), 743-9 (0.273), 742-1 (0.25)} ⇒
  72 + 3 = 75 ≠ 74 → **REFUSE → fragment+partial** (the fail-safe the task
  allows). Refuse-to-ambiguous rule: never pick a subset to force the count —
  that would be inference from the declared count, forbidden by D-D.
- Typo repair (D-F) verified live: the cadastre holds `718-1`, not `78-1`; with
  the repair the fragment ⊆ candidates precondition holds, and no unrepaired
  fragment parcel is missing from the GIS set.

## T4 — ROC-era coverage (premise adapted, question answered)

The archive holds **no ROC-era publication** (7 gazettes, oldest 2026-08-11;
publications are Gregorian-dated while cells stay ROC-dated until 1151002).
Adaptation: (A) run the four-check recovery on the *oldest archived* gazette's
truncated rows — its cells are ROC-dated, so the ROC→ISO path is exercised end
to end; (B) probe the APIs directly with pre-2006 corpus rows.

- Part A: 9 truncated rows in 核定案件-2026-08-11.pdf; `to_iso` converted every
  ROC cell (114/11/12→2025-11-12 … 96/7/6→2007-07-06); **8/9 recovered exact**
  (R111002, R091007-02, 09810272, 09703201, 09611281, 09902024, R089212-03,
  09012313); 1 genuine residual (編號 100, 114/7/15: 22 candidates, 0
  count-fragment hits) — exercising the residual path on real data.
- Part B: **6/6 pre-2006 samples returned exact-date cases**: 2002-03-21
  R089708-01, 2002-12-31 R090502-01, 2003-11-03 R089501-02, 2004-07-13 R091202,
  2005-02-02 R091808-01, 2005-03-01 R091808-03 (27 of the corpus's rows predate
  2006; 6 sampled across the range).
- Conclusion: the APIs cover the corpus's entire date range back to its first
  approval; no new calendar code is needed (the adapter consumes ISO; ROC
  parsing stays in extraction, already covered offline).

## T10 — boundary vintage (premise dissolved; refuse path validated)

- `ID='R089305'` returns **two features** (NO 1411 and 1445, both layer 17).
  Neither is the 203-1 unit's boundary: candidate sets of 231 and 118 parcels
  overlap the unit's published 97-parcel list by **9 and 0**; `list ⊆
  candidates` fails for both.
- The R-form id space is **group-level**: the ashx family under R089305 spans
  sibling units (190, 203-1, 208, 219, 517 — 事業概要s, 駁回s, and the unit's own
  擬訂 `R089305-07` 2018-02-08 / 變更 `R089305` 2020-01-15). One id, many
  polygons, many units.
- The corpus holds no 2013 row for this unit — its 2018 and 2020 lists are
  identical (97 parcels) — so the "2013 vs 2020 lists" comparison has no
  subject; the vintage question collapses into "wrong-unit polygons are
  refused".
- Handling: unchanged from the spec. The triple check (fragment ⊆ candidates,
  count closes, positional tail) refuses both polygons → fragment+partial. The
  fail-safe designed for vintage mismatch is validated on a wrong-unit polygon.
  The adapter SHALL union multi-feature returns and rely on the checks — never
  assume one feature = one case.
