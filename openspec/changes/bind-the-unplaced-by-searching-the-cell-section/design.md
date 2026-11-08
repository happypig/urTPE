## Context

See proposal.md — Why.

The current state, in the terms the implementation needs:

- `urtpe/links.py:_search_taipei_raw` asks the city for **one** (section,
  parcel) pair at a time. It derives the section from the node's `section`
  field and the parcel from the node's `first_parcel`. `_section_variants`
  already offers a second section form — the same section with a leading place
  name dropped — but the 地號 cell's section is not among the forms it tries.
- `urtpe/links.py:_parse_landcore` cuts a core's section at its **first** 段.
  `compute_landcore_similarity` returns 0.0 unless the two sections are
  *identical*, so a unit the two sides spell differently scores 0.0.
- `urtpe/links.py:_tier3_names_match` is the resolver's name acceptance: the
  stage-with-ordinal must be equal, the plan-type kind must be a subset, and
  the land cores must score >= 0.85.
- `urtpe/cleanse.py:320` sets the record's `section` to the 案名's section
  (`ns`) when it has one, and to the 地號 cell's section (`pl["section"]`)
  otherwise. The 地號 cell's section is parsed and then **discarded** — it
  survives only as the review flag 案名與地號段小段不一致.
- `urtpe/links.py:resolve_node_cases` step 4 walks the node's `parcels`, so
  the all-parcel search is already there; the *section* is not varied.

Measured, over the 5,185 node × candidate pairs the pipeline compares today:

| | count |
|---|---|
| the current rule matches | 1,584 |
| the widened rule matches | 1,587 |
| newly matched | 3 |
| no longer matched | 0 |

The 3 additions are read by hand, and each is a genuine recovery:

| project | node | case | the reason |
|---|---|---|---|
| 文山區-木柵段三小段-389地號等5筆 | recno 983 | 09908302 | the 案名 says 385; the 地號 cell names 389, the city's parcel |
| 松山區-敦化段一小段-510地號等1筆 | recno 72 | 10906301 | the 案名 writes 松**化**區 (a typo); the 地號 cell writes 松山區 |
| 松山區-敦化段一小段-510地號等1筆 | recno 72 | 11501039 | the same node, the case's other approval |

**The baseline is the pipeline's own call.** The resolver builds the node's
core as `extract_landcore_from_case_name(node_name) or
_record_landcore(member)` — the 案名's core, or the record's own when the 案名
does not parse. An earlier measurement of this change called the tier-3 rule
without that fallback, so it counted 1,579 baseline hits and reported 5 of the
additions as new. The pipeline already binds those 5 through the fallback.
The 3 above are the only real additions.

## Goals / Non-Goals

**Goals**

- The 7 unplaced projects bind their 11 nodes to the case ids the live search
  already found.
- The land-core comparison stays a superset of the present one: no pair that
  binds today unbinds tomorrow.
- The change is measured, not assumed. Every count above comes from a probe
  over the emitted corpus and the link cache.

**Non-Goals**

- The merge's family clustering is not changed. The 3 units the section drift
  splits into two families (河堤, 萬華, 復興) are a separate defect: the merge
  groups candidate pairs by `(district, section)` exactly
  (`urtpe/merge.py:22`), so the 案名's section and the 地號 cell's section never
  meet. Re-clustering would move the project count, which is a separate
  change with its own spec.
- The NFKC compatibility-ideograph fix is not part of this change.
- The 168 list's own shape (a subset, not a register) is not changed.

## Decisions

### D1 — Widen the comparison by ADDING readings, never by replacing one

The land-core comparison reads each core **two ways** — the section cut at its
first 段 and at its last — and each side's readings are paired. A pair matches
if any pairing matches.

Measured, over the 5,185 pairs: the first-段 cut alone binds 1,586, the
last-段 cut alone binds 1,587, and both cuts bind 1,587. The last-段 cut
loses nothing against the pipeline — the 31 bindings the earlier measurement
reported it lost came from that measurement's own baseline, not from the cut.
The 1 pair the last-段 cut adds is recno 983 (木柵389), whose 案名 names 385
and whose 地號 cell names 389.

Both readings are kept anyway. The first-段 cut is what the pipeline's own
`_parse_landcore` does, so keeping it preserves the pipeline's reading of
every core; the last-段 cut is what reads 河堤段五小段 as one section name.

### D2 — Keep the four-part weighted score; widen the section and the parcel

`compute_landcore_similarity` scores a pair on four weighted parts and accepts
at >= 0.85. The change keeps that score and widens two of the parts:

- the **section** part scores 1.0 when the two sections name the same 小段 and
  the same 段, with a trailing 段 optional on either side;
- the **parcel** part scores 1.0 when the city's parcel equals the node's
  first parcel **or is one of the node's own parcels**.

The count part keeps its weight, so a count mismatch costs .10 exactly as
before. The alternative — hard tests on district, section, count and parcel —
was measured against the pipeline's own rule: it loses **31** existing
bindings, because the pipeline's score tolerates a count mismatch (中山段二小段
202's node declares 1 筆 and the city declares 12 筆, and that pair binds
today at 0.85).

Measured against the pipeline's rule, the segment cut is **not** the cause of
those 31 losses — the count test is. Both cuts with the weighted score lose
0.

### D3 — Offer the 地號 cell's core as an ALTERNATIVE, not as the record's section

The record's `section` field stays the 案名's section. The comparison is
offered a second core, built from the record's own fields with the 地號 cell's
section: `{district_land}{cell_section}{first_parcel}地號等{land_count}筆`.

Changing the `section` field itself was rejected: it is the merge's grouping
key, so changing it moves the family clustering — the very thing this change
holds out of scope (D-Non-Goals).

### D4 — Search the unit's section forms and all its parcels

`_search_taipei_raw` already tries a section variant and a parcel stem. This
change adds the 地號 cell's section to the section forms and lets the
all-parcel search find a case under any parcel of the unit.

The 临沂 case is indexed under 414 and the 復興 case under 7 — both are in the
unit's own parcel list, so the existing all-parcel walk finds them once the
name comparison accepts them. The 河堤 case needs the section form, because
the search for 河堤五小段 returns **zero** rows for all three of the unit's
parcels.

### D5 — The national portal's title search is a third id source, header-confirmed

The 懷生928 case is indexed by no parcel search under any section form. The
portal's `?title=<段小段>&city_id=2` search finds it, and the page's 相關連結
names case 10002141.

It joins the existing 168-list source in shape: the id is **appended** to the
project's case list only after the case's own header confirms it, and the
existing ids keep their positions (the positional fallback binds by index).

The alternative — reading the id from the portal page without a header
confirmation — was rejected: the 168 list's own spec says why (a list is a
register of cases, not of the project's cases), and the portal's page carries
the same risk.

### D6 — The date gate stays exact in step 4

One of the 11 bindings (復興 recno 1081) rests on a 1-day drift: the node's
date is 2015-11-04 and the case's approval is 2015-11-03. The resolver's
step 3 already applies a 10-day drift rule to a header date, but step 4 does
not.

This change does **not** widen step 4's date gate. The 10-day drift is
already a spec'd rule at the header step; applying it in two places would
make the acceptance rule differ by path, and a reader could not tell which
rule a binding used. The 1-day case is reported here as a fact, not as a
change: if it must bind, the drift rule belongs in one place and applies to
both steps.

## Risks / Trade-offs

- **The widened section rule binds a case of another unit.** → The 小段 suffix
  and the 段 name must both agree; the district and the count keep their
  weight. Measured over 5,185 pairs: 3 additions, 0 removals. Every one of
  the 3 was read by hand — each is a case the gazette's own 地號 cell names
  correctly and its 案名 does not (北投大業401's 案名 writes 401號 without
  地號, so it has no parsable core at all; the pipeline binds it through the
  record-core fallback already).

- **The parcel-set rule binds a case of a sibling unit.** → The parcel must be
  one of the node's OWN parcels, and the district, section and count must all
  agree. The 吳興街二期 unit is a named-area unit whose two cases declare 247
  while the unit's first parcel is 163-2.

- **A second section form multiplies the search's request count.** → The
  second form is tried only when the first returns nothing, and the existing
  three-retry bound on the cross-product stays.

- **The portal's title search adds a second host to the refresh.** → It is
  tried only after the parcel search and the 168 list both return nothing, so
  it runs for the 2 projects that need it, not for all 682.

- **Re-clustering is left undone, so 3 units stay split.** → Deliberate
  (D-Non-Goals). The 7 projects bind their case ids either way; the split is
  a separate defect with its own spec, and fixing it would move the project
  count.

## Migration Plan

1. The test-first group lands (the comparison, the search forms, the portal
   source) and fails against the current code.
2. The implementation lands. The comparison is offline and touches no cache.
3. A full suite run: 1,138 tests.
4. A refresh of the 7 projects' caches writes their case ids. The refresh
   reaches the network, so it obeys the single-writer rule: no
   `data/.pipeline.lock` present, peers notified, >= 1 s between requests.
5. A re-emit: `python -m urtpe.cli --from-js viewer/projects.data.js -o data
   --viewer viewer --links`. The census gate and the partition gate run before
   the tripwire report; the payload's record count and project count must not
   move.
6. `node scripts\viewer_smoke.js` after the re-emit.

Rollback: the change is a code change, so reverting the commit and re-emitting
restores the payload. The caches keep the newly found ids, which is harmless —
the emitted payload is the artefact that matters, and a later run reads the
cache again.

## Open Questions

None. Every decision above is measured against the corpus or the live city,
and the one open item — the 1-day date drift — is recorded as a fact with its
reason, not left as a question.
