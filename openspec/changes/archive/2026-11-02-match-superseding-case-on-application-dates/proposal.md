## Why

`supersede-headerless-cases-and-discover-new-ids` (§37) recorded a `無` case as
superseded only when a same-named, newer case shared **every** one of its dates.
The live run left two probable re-filings unmatched, and the maintainer decided
(2026-11-02) to match on application dates instead:

- 雅祥段一小段-227-4: 11009142 (`無`) vs 11510001 — same 案名, same 申請計畫日期 /
  申請權變日期 2024/05/09; the 公展 dates differ because the exhibition was held
  again (2025/05/07 vs 2026/10/13).
- 吉林段四小段-705-3: 10410012 (`無`) vs 11503012 — same 案名, same application
  dates 2024/02/07; one 召開幹事會日期 differs (2026/01/27 vs 2026/01/09).

Measured on the cache before the change: the relaxed rule matches exactly these
two plus the two already recorded (11211211 → 11409026, 10806141 → 11510017),
each with a single candidate; the two other `無` cases carry no milestones and
stay unmatched.

## What Changes

- `find_superseding_case` compares the `無` case's application dates (all five
  application fields it carries; at least one required) instead of every date.
  The name, newer-id, ≥ 3 dated labels and single-candidate rules stay.
- The supersession report names the dated labels whose dates differ, so a
  match on fewer dates stays auditable.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cache-freshness`: "The targeted refresh selects caches awaiting an approval" —
  the successor test compares application dates and reports the differing ones.

## Impact

- Code: `urtpe/links.py` (`find_superseding_case`, the refresh report),
  `scripts/refresh_awaiting_caches.py` (prints the differing labels).
- Data: a live refresh of the two affected projects; a re-emission.
- No change to selection, payload shape or viewer code (the viewer already
  renders `links.superseded_by`).
