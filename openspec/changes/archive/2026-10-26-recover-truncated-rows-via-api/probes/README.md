# probes — exploration evidence for recover-truncated-rows-via-api

One-shot archaeology scripts from the 2026-10-25/26 exploration sessions. Each takes no
arguments (edit the constants at the top), writes nothing outside its working directory,
and only reads from the live APIs. They are evidence and calibration tools for task 1.x —
not product code, and not referenced by the pipeline.

| Script | What it proved / calibrates |
|---|---|
| `pdf_all15.py` | All 15 truncated rows have complete 案名; declared/visible counts (uses urtpe.extract helpers; run from repo root) |
| `uro_recover67.py` | Section-enumeration fallback: 編號 67 recovered via 信義區 sections × parcel 38 |
| `uro_recover_rest.py` | Identity matrix for the other 6 excluded units (14/15 exact dates; 930 zone ambiguity) |
| `ab_census2.py` | Zone-marker census: 692 parcels → 2,408 cases → 88 marker names (49 -A/B區, 2 區段, 37 基地 incl. named anchors); saves `ab_census.json` |
| `ab_mapping.py` | Polygon existence per A/B case (25/50) + zone parcel sets (disjoint / identical / nested) |
| `bim_intersect2.py` | 虎林段 R089601: boundary ∩ LAND-ALL = 148 candidates → 138 true (skip-pattern) |
| `bim_intersect3.py` | 美仁段 R098505: 89 vs 74 (needs overlap calibration); numeric ids absent from 5 layers |
| `uro_parcels2.py` | No /ashx/ endpoint carries a parcel list (18-endpoint sweep, 5/22 coincidental) |
| `t1_matrix.py` | Task 1.2/1.3/1.5: four-check identity matrix, all 15 rows → 15/15 exact; per-row normalized equality; request count + wall time (T5). Reads the gazette PDF for each row's surviving cells |
| `t8_overlap.py` | Task 1.4: overlap calibration → pure fraction thresholds REJECTED; calibrated rule = fragment ∪ positional tail with ≥1 vertex inside, accept iff count closes (虎林段 138 CLOSES; 美仁段 75≠74 → refuse). Caches WFS pulls in its working directory |
| `t4_roc_probe.py` | Task 1.5: oldest archived gazette (ROC-dated cells) — 8/9 truncated rows recovered exact, 1 residual; pre-2006 coverage 6/6 exact (2002-03-21 → 2005-03-01) |
| `t10_vintage.py` | Task 1.7: R089305 returns two polygons, neither the 203-1 unit's (9/97, 0/97 overlap) — R-form ids are group-level; triple-check refuse path validated |

Caveats baked into the code: CQL `BBOX` evaluates in native TWD97 meters (use whole-section
pulls); boundary-layer ids are R-form only; `Get_updcase_list` answers at unit granularity.
