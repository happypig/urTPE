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

Measured, over the 5,228 node × candidate pairs the pipeline compares today:

| | count |
|---|---|
| the current rule matches | 1,587 |
| the widened rule matches | 1,596 |
| newly matched | 9 |
| no longer matched | 0 |

The 9 additions are read by hand, and each is a genuine recovery:

| project | node | case | the reason |
|---|---|---|---|
| 中正區-河堤五小段-399地號等3筆 | recno 204 | 11005053 | the 案名 says 河堤五小段; the city indexes 河堤段五小段 |
| 信義區-吳興一小段-330地號等43筆 | recno 551 | 10611051 | the 案名 says 吳興一小段; the city indexes 吳興段一小段 |
| 信義區-吳興段二小段-163-2地號等2筆 | recno 706 | 10405235 | the city's parcel is 247, one of the node's own |
| 信義區-吳興段二小段-163-2地號等2筆 | recno 706 | 10103231 | the same node, the case's other approval |
| 萬華區-萬華段一小段-519-2地號等35筆 | recno 993 | 10011301 | the 案名 says 萬華段; the city indexes 萬大段 |
| 萬華區-萬華段一小段-519-2地號等35筆 | recno 483 | 10903061 | the same unit, the 變更 case |
| 文山區-木柵段三小段-389地號等5筆 | recno 983 | 09908302 | the 案名 says 385; the 地號 cell names 389, the city's parcel |
| 松山區-敦化段一小段-510地號等1筆 | recno 72 | 10906301 | the 案名 writes 松**化**區 (a typo); the 地號 cell writes 松山區 |
| 松山區-敦化段一小段-510地號等1筆 | recno 72 | 11501039 | the same node, the case's other approval |

**The measurement moved because the corpus moved.** The first measurement ran
before the refresh, over 5,185 pairs. The refresh wrote 13 more candidate
names into the 7 caches — the cases of the same units the search reached —
so the pair set is 43 pairs larger and 4 of the 9 additions are pairs that
did not exist before. The baseline moved with it: 1,579 → 1,587.

**The baseline is the pipeline's own rule, replayed.** The comparison itself
was widened, so the baseline cannot be measured with the widened function —
the probe replays the old rule over the same inputs: the section cut at its
first 段, the sections compared for exact equality, the parcel compared for
exact equality, and the count term costing .10 on a mismatch. Two earlier
baselines were wrong, and both are corrected here:

- the first omitted the resolver's own record-core fallback
  (`extract_landcore_from_case_name(node_name) or _record_landcore(member)`),
  so it counted 1,579 hits instead of 1,584 and reported 5 already-bound
  pairs as new;
- the second used the widened `compute_landcore_similarity` as its baseline,
  so the comparison was the rule against itself.

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

Measured, over the 5,228 pairs (`scripts/probe_cut_variants.py`): the
first-段 cut alone binds 1,592, the last-段 cut alone binds 1,596, and both
cuts bind 1,596. The last-段 cut loses nothing against the pipeline — the 31
bindings an earlier measurement reported it lost came from that
measurement's own baseline, not from the cut.

The 4 pairs the last-段 cut adds are the ones whose 案名 names a section the
city spells differently: 吳興330 (吳興一小段 vs 吳興段一小段), the two
吳興街二期 pairs, and 木柵389 (whose 案名 names 385 and whose 地號 cell names
389).

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
change adds the 地號 cell's section to the section forms, adds the section
FORM the city uses, and lets the all-parcel search find a case under any
parcel of the unit.

The live search (2026-11-09) shows three separate things the first form
misses, each measured against the city's own answers:

| the unit | what the gazette prints | what the city indexes | the fix |
|---|---|---|---|
| 河堤399 | 河堤五小段 | 河堤段五小段 | the 地號 cell's section |
| 吳興330 | 吳興一小段 | 吳興段一小段 | the section FORM |
| 臨沂412 | 臨沂段三小段 | 臨沂段三小段, under parcel 414 | every parcel, and the guard |

**The section FORM.** The gazette prints 吳興一小段 where the city indexes
吳興段一小段 — the same 小段 under a 段 name with or without its trailing 段.
The comparison reads both (D2); the search must ask for both too, or the
case is never reached. Only the direction the city takes is offered: a name
that already carries a 段 keeps it, so 臨沂段三小段 spends no extra request.

**The walk continues past a body the guard empties.** The first form may
answer with cases of OTHER units — 萬華段一小段 returns five of them, and
the wanted one lives under the 地號 cell's form. Stopping at the first
non-empty body hid it. The walk now continues while a form yields nothing
that survives the guard, and still stops at the first form that yields a
kept case, so a project whose 案名 is right spends no extra request.

**The guard keeps a case naming any of the unit's OWN parcels.** The city
indexes a case under whichever parcel it lists first, and that is not
always the unit's first: 臨沂段三小段412's case 10305021 is indexed under
414 while its name declares 412. The §6.7 guard threw it away, because the
guard keys on the SEARCHED parcel. The guard now accepts the unit's own
parcel set, and still drops a case of a different unit.

### D5 — The national portal's title search is a third id source, header-confirmed

The 懷生928 case is indexed by no parcel search under any section form. The
portal's `?title=<段小段>&city_id=2` search finds it, and the page's 相關連結
names case 10002141.

It joins the existing 168-list source in shape: the id is **appended** to the
project's case list only after the case's own header confirms it, and the
existing ids keep their positions (the positional fallback binds by index).

**The portal's rows are scoped by the unit's own parcel.** The title search
returns EVERY unit in the 段小段, not the one asked for: 臨沂段三小段's page
names four units (412, 318, 370, …), and 懷生段一小段's names four (928,
121-4, 32, 931). An unscoped row is another unit's case. The scope is the
same one the 168 list uses, and for the same reason — a list is a register of
cases, not of one project's cases.

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
  weight. Measured over 5,228 pairs: 9 additions, 0 removals. Every one of
  the 9 was read by hand — each is a case of the unit the node belongs to,
  named by the gazette's own 地號 cell (or by the city's own spelling of the
  段小段) and not by its 案名.

- **The parcel-set rule binds a case of a sibling unit.** → The parcel must be
  one of the node's OWN parcels, and the district, section and count must all
  agree. The 吳興街二期 unit is a named-area unit whose two cases declare 247
  while the unit's first parcel is 163-2.

- **A second section form multiplies the search's request count.** → The
  second form is tried only when the first returns nothing, and the existing
  three-retry bound on the cross-product stays.

- **The portal's title search adds a second host to the refresh.** → It is
  tried only after the parcel search and the 168 list both return nothing, so
  it runs for the projects that need it, not for all 682.

- **Re-clustering is left undone, so 3 units stay split.** → Deliberate
  (D-Non-Goals). The 7 projects bind their case ids either way; the split is
  a separate defect with its own spec, and fixing it would move the project
  count.

## Migration Plan

1. The test-first group lands (the comparison, the search forms, the portal
   source) and fails against the current code.
2. The implementation lands. The comparison is offline and touches no cache.
3. A full suite run: 1,175 tests.
4. A refresh of the 7 projects' caches writes their case ids. The refresh
   reaches the network, so it obeys the single-writer rule: no
   `data/.pipeline.lock` present, peers notified, >= 1 s between requests.
5. A re-emit: `python -m urtpe.cli --from-js viewer/projects.data.js -o data
   --viewer viewer --links`. The census gate and the partition gate run before
   the tripwire report; the payload's record count and project count must not
   move.
6. `node scripts\viewer_smoke.js` after the re-emit.

The refresh writes candidate names into the 7 caches, so the corpus the
comparison is measured over grows: 5,185 pairs before the refresh, 5,228
after. Every count in this document is measured over the CURRENT corpus, and
the probe that reads it is `scripts/probe_proposed_rule.py`.

Rollback: the change is a code change, so reverting the commit and re-emitting
restores the payload. The caches keep the newly found ids, which is harmless —
the emitted payload is the artefact that matters, and a later run reads the
cache again.

## Open Questions

None. Every decision above is measured against the corpus or the live city,
and the one open item — the 1-day date drift — is recorded as a fact with its
reason, not left as a question.
