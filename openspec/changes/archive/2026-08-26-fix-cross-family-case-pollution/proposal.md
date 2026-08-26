# Fix Cross-Family Case Pollution (Fragment Families)

## Why

The Taipei parcel search over-returns sibling/foreign cases (§6.7), and the
consequence one layer deeper is now quantified (§6.8, 2026-08-26): foreign
cases' **construction milestones win the last-write-wins merge**, so 162
construction events across 82 families render attributed to cases that anchor
to no record or to another family. Worst subset: **55 events in 36 family
pairs where the foreign case shares zero parcels** with the family (e.g.
正義段四小段-115地號等4筆 displays 建照 2024/10/07 from case 11102211 —
133地號等1筆's case) — likely **wrong dates** displayed. Additionally, 63
families are fragment splits of single developments (e.g. 南港段一小段
19-1地號等34筆 vs the 2022 approval's own fragment 101地號等41筆 — the
anchor parcel changed 19-1 → 101 between stages and the similarity merge
split the history). Planners reading these graphs see construction dates
from the wrong unit and fragmented histories.

## What Changes

- **Search strictness**: `search_taipei_cases_api` SHALL keep only cases
  whose `case_name` contains the searched parcel (extending the §6.7 guard
  shape to all cross-family pollution, tolerating 之↔- and full-width
  notation drift). Sibling 概要 cases on other land and foreign same-section
  cases are dropped at search time.
- **Fragment merge candidates**: after discovery, a fragment family whose
  discovered cases ALL anchor inside one main family SHALL be flagged as a
  merge candidate (review-flagged, 臨界對-style — auto-merge is NOT attempted;
  e.g. 南港段一小段-101地號等41筆 → 南港段一小段-19-1地號等34筆， 懷生段249
  中正區 → 大安區).
- **Re-merge pass**: after the strictness change, a `--links` regeneration
  re-merges all families from caches; polluted slots drop the foreign values
  and fragment families lose the borrowed construction events.
- **Investigation (in-apply)**: determine whether case 11102211's land list
  includes 正義段115/132/243 (one big case → dates shared but misattributed)
  or not (search false positive → dates wrong) — decides whether B1b families
  need date restoration from their own cases.
- No change to fetch, cache layout, or `schema_version`.
- No part of this scope is gated on the PDF-parsing/similarity POC findings —
  neither the parsing nor the merge/threshold surface is touched. (The
  fragment merge-candidate FLAGS are review output, not auto-merges; the
  similarity-threshold surface itself is untouched.)

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `official-link-discovery`: the Taipei case search SHALL apply the
  case_name parcel guard (§6.7 fix shape) — cases whose name lacks the
  searched parcel (notation-drift tolerant) SHALL NOT enter
  `city_case_ids`.
- `case-merging`: fragment families whose discovered cases all anchor inside
  one main family SHALL be surfaced as merge candidates via review flags
  (detection only; merging stays a human decision).

## Impact

- `urtpe/links.py`: parcel guard in `search_taipei_cases_api`; fragment
  detection + review flags in the attach/emit flow.
- `scripts/fetch_remaining_national_portal.py`: inherits the guard via the
  shared function (no behavior change for the national lane).
- Data: one `--links` regeneration after implementation (re-merge from
  caches; the strictness change alters which cases enter city_case_ids).
- Tests: guard unit tests (own/sibling/foreign cases, notation drift),
  fragment-detection test, corpus re-verification (isolated events drop from
  162 toward the anchored-only baseline; 懷生段249/正義段115 spot-checks).
