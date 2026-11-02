# Proposal: repair-contradicted-single-parcel-cell

## Why

The maintainer asked why 內湖區-文德段二小段-615地號等1筆 and its twin
…-615地號等1筆-2 did not merge. The twin exists because one gazette row
contradicts itself, and no rule repairs it:

- Gazette row 編號 759 (2026/10/15 gazette, p.128) prints the 案名
  `擬訂臺北市內湖區文德段二小段615地號1筆土地都市更新事業計畫案` and the
  地號 cell `臺北市內湖區文德段二小段 1 地號1筆土地`. The PDF itself carries
  the `1` (verified in the source PDF; the reader is not at fault). The city
  introduced the typo when it first listed the row (2026-09-24 gazette) and
  repeats it in every gazette since.
- The three sibling rows of the same unit (編號 84, 314, 536) print
  `615 地號1筆土地` correctly. The city's own platform agrees with the
  案名: a live `Get_updcase_list` probe (2026-11-02) returns all 4 cases of
  the unit — including 2019 case 10410272, the row the typo sits on — with
  names printing `615`; the national portal (view/686) matched the unit on
  615 too. Two official sources say 615; one PDF cell says 1.
- Cleansing derives `first_parcel=615` from the 案名 (the identity
  authority, `urtpe/cleanse.py:249-260`) but derives `parcels=['1']` from
  the printed cell, so one record disagrees with itself. `merge.score`
  then computes parcels Jaccard = 0 between 536 and 759 → 0.65 < 0.70 →
  no link; the family dedup appends `-2`; the fragment-family detector
  flags the whole shape for human review (a flag that exists only because
  the merge missed).

The actors: the maintainer (a viewer project that should not exist), the
pipeline (a self-contradicting record that defeats its own identity
authority), and the publisher (a typo the platform does not repeat).

Census (offline, over all 1,442 cleansed records of the 2026-10-15
gazette, 2026-11-02): the strict condition — 案名 declares exactly 1 筆
and names its exact parcel, the 地號 cell yields exactly one parcel token,
and that token differs from the named parcel — matches exactly **1 record
(759)**. The two other single-count cells that disagree with their 案名
(269: a cross-section 40-parcel list; 957: a `518地號1筆(原15筆)` merge
history) yield more than one token and are correctly outside the rule.
112 of 115 parseable single-count cells already agree with their 案名.

## What Changes

- **Cleansing gains one repair rule** (`urtpe/cleanse.py`): when the 案名
  declares exactly 1 筆 and names its exact parcel, and the 地號 cell
  yields exactly one parcel token that differs from the named parcel, the
  parcel set is set to the named parcel. The rule records an auto_fix
  (`地號欄單筆地號與案名矛盾→依案名`) and a review flag naming the
  printed cell, so the repair is visible and auditable. Everything else
  is untouched: multi-parcel cells, cross-section lists (269), merge
  histories (957), and cells agreeing with the 案名 stay as published.
  The rule runs offline, at parse time, inside the single-writer lock.
- **The platform API is evidence, not a dependency.** The proposal and
  design record the live probe (all 4 platform cases print 615; the
  national page view/686 agrees). The pipeline gains no network call:
  cleansing stays offline and deterministic, like the whole suite. The
  cached `candidate_names` (already in `data/.link_cache/…615…/result.json`)
  carry the same witness for anyone re-verifying without the network.
- **Effect on the corpus (simulated full re-merge, 2026-11-02)**: the
  repaired 759 links to its three siblings at 0.95 (was 0.65); the twin
  project `…-615地號等1筆-2` dissolves; exactly one record's project_id
  changes corpus-wide (759 itself). The fragment-family review flag on
  759 clears with the merge (its four discovered cases then anchor inside
  their own family, the detector's no-flag condition).
- **The viewer cache follows**: the `-2` cache directory migrates through
  `data/project_aliases.json` rules (identity pairing refuses ambiguity;
  a fully-absorbed family has no ambiguity), or is superseded by the
  refreshed main-family cache on the next `--links` run. The refresh and
  re-emission steps are part of acceptance, not of the rule itself.

Scope note: the 0.7 threshold, the feature weights, and the fragment-family
detector are untouched. The change repairs an input to the scorer, not the
scorer. Per config.yaml the weights remain provisional calibration values.

## Impact

- **Affected specs**: `data-cleansing` (new requirement: the
  single-parcel-cell contradiction repair), `land-identity-fallback`
  (the parcel set now also trusts the 案名 when the cell contradicts it
  for a single-count unit — an extension of the existing name-fallback
  requirement's principle), `case-merging` (no rule change; one new
  acceptance scenario documenting the repaired 759 linkage).
- **Affected code**: `urtpe/cleanse.py` (the rule + auto_fix + review
  flag); tests; no I/O adapter changes; no schema changes (`parcels` is
  an existing field).
- **Data**: one record's parcel set changes on the next full run;
  merged.tsv and projects.json re-emit with the twin dissolved. The
  `data/` tracked-file rewrite applies as always.
