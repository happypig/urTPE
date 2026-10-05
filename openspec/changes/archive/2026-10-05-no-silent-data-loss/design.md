# Design — no-silent-data-loss

## Context

### Actors

| Actor | Concern |
|---|---|
| **Pipeline maintainer** (jeffw) | Runs ingestions; must be told when data is missing rather than infer it from an absence |
| **Viewer reader** | Opens the page and expects every project to render; a blank pane reads as "no data", not "no link data" |
| **Reviewer** | Reads the run report; must be able to trust that a quiet run emitted what it claims |

### Domain events

- A dataset is rebuilt, and the rebuild does not collect everything the previous one did
- A publisher-truncated cell turns out to be completable from another approval
- A reader change re-keys every project identity at once

### System boundary

```
IN SCOPE                          OUT OF SCOPE
────────────────────────────────  ────────────────────────────────────
reporting what an emission lost   re-scraping portal data the caches lack
repairing a truncated cell,       deciding whether the city truncates by date
  under three checks               permanently (parked)
making the viewer degrade         a general browser test suite
teaching the coverage guard       portal sync / event cascade (parked)
  to see a total re-key
```

### The failure this design exists to prevent

Six defects, one shape. In each, a run reported success, every test passed, and the
data was already on disk:

| # | Silent failure | Detected by |
|---|---|---|
| 1 | emission dropped every portal-derived field | nothing |
| 2 | viewer blanked its detail pane for all 709 projects | the user |
| 3 | `coverage_guard` passed while 27 caches stranded | nothing |
| 4 | `--links` optional, so the default path produced a non-conforming dataset | nothing |
| 5 | `統計至` label lost from the header | nothing |
| 6 | a completable truncated cell excluded instead of completed | nothing |

Items 1, 3 and 4 are the same defect at three layers: a requirement exists, and nothing
checks conformance. The requirements were never missing — `official-link-discovery` and
`taipei-implementation-data` already state that links and implementation data SHALL be
attached. What was missing is the *verification*, and a verification that only exists
in the spec text is not one.

## Decisions

### D1 — A guard reads the spec's own requirements, not a duplicate list

**Decision.** The emission check enumerates the fields the affected capabilities require, and derives nothing at runtime from the viewer's source.

**Rationale.** The tempting design is to introspect `app.js` and check every field it
reads. Rejected: it makes a spec requirement depend on a browser script's private
variable names, so a refactor that renames a local would fail a check the spec never
mentions. The field list is a stated contract; the viewer is a consumer of it.

The independent audit in `scripts/audit_viewer_fields.py` stays as a diagnostic, not a
gate. It found the unguarded read; it should not be what enforces the requirement.

**Consequence.** Adding a field the viewer needs is a spec change and a test change,
which is the correct amount of ceremony for a field the dataset contract depends on.

### D2 — Completion requires three independent checks, and the count is the one that refuses

**Decision.** A truncated 地號 cell may be completed from another approval of the same
unit in the corpus only when same-unit, literal-prefix and count-closes all hold.

**Rationale.** Completion was rejected outright in the previous change, on the evidence
that borrowing is unsafe for 17 of 21 truncated records. That evidence stands, and it is
why the rule here is three conjunctive checks rather than a similarity threshold:

```
                          same 段/小段   literal prefix   count closes
編號 1198                        yes             yes      102+8 = 110 = declared   REPAIR
編號 1210                        yes             yes       61+1 = 62 ≠ declared 72  refuse
編號 1141 / 1204 / 1381          no candidate    —                        —        refuse
```

Two of the three checks are about identity and the third is about arithmetic. The
first two can be satisfied by a parcel set that merely *starts* the same way; the third
is what distinguishes "the same list, continued" from "a different list with a shared
opening". `1210` is the case that proves it: prefix match at J=0.984, and both
publications disagree with the 案名 — 1150827 truncates at 61, 1151002 terminates at 62,
the 案名 claims 72. Neither holds the truth, so the system refuses rather than picking
one.

**Alternative rejected — trust the prefix alone.** It repairs 1210 and asserts 62
parcels for a record that should have 72. That is precisely the silent corruption this
change exists to remove.

**Provenance.** Both candidates live in `1151002`, the gazette excluded from the dataset
for carrying 15 truncated cells of its own. Using the worse export as a repair source is
acceptable only because three independent checks agree, and the completion is recorded
with its source gazette and 編號 so it can be audited or reversed.

### D3 — The viewer degrades; it does not blank

**Decision.** Every field read in the viewer is optional at the point of use. A missing
value omits the element it feeds.

**Rationale.** The blank pane cost one unguarded line: `n.links.taipei[0]`, the only
unguarded read of that field in the file, in a document where all 18 other reads go
through `(n.links || {}).taipei || []`. One throw inside `renderDetail` left the
`index.html` placeholder on screen for 709 projects, and the failure presented as *absence
of data* rather than *absence of one field*.

The asymmetry is the point: a single missing field has a blast radius of one element when
guarded and the whole page when not.

**Consequence for the contract test.** It asserts that no field the viewer reads
*unguarded* exists on every record — which makes "unguarded" a defect in its own right,
independent of whether today's dataset happens to carry the field.

### D4 — The coverage guard observes a total re-key

**Decision.** Report an identity set with no overlap as a distinct outcome, and treat
wholesale orphaning as a fault rather than as information.

**Rationale.** `coverage.py:51` iterates `set(before) & set(after)`; line 81 raises only
on `d["regressions"]`. A total re-key empties the intersection, so `regressions = {}` and
the guard passes while every cache is orphaned — and `d["lost"]`, which holds the
evidence, is written and ignored.

This was recorded as a parked observation through a previous change and is now
demonstrated rather than predicted: the stranded set moved 27 → 2 during that change and
the guard noticed neither step. It is also the shape of the 2026-08-24 incident, where a
check that could not observe its own failure mode let four writers wipe 47 caches.

**Not attempted here.** Proposing a threshold for "too many lost" would be a judgement
about acceptable churn. Only the unambiguous case — zero overlap, or every cache
orphaned — is treated as a fault; everything else stays informational as before.

### D5 — `--links` stays advisory, and the guard covers it

**Decision.** A repository rebuild does not require `--links`. The emission check reports
when link-derived fields are absent.

**Rationale.** Measured cost of `--links` on a warm cache: **147 seconds**, against
roughly 45 for the whole rebuild without it. Mandating it would make every quick
rebuild three times slower to protect against a mistake the guard can catch in
milliseconds.

The alternative — mandating it — was genuinely defensible, and the reason it loses is
that it trades a cheap check for a slow invariant. A guard that reports is sufficient
because the failure it catches is not silent once reported.

**Reconsider if** the portal data becomes load-bearing enough that a wrong dataset is
more expensive than three minutes.

### D6 — The header keeps both the label and the normalised date

**Decision.** Render `統計至 <ISO date>`, not the bare ISO date.

**Rationale.** Normalising the publication date to ISO-8601 was correct, but it silently
removed the word that distinguishes it from a generation timestamp. `· 2026-08-27` reads
as either. Both facts matter and cost nothing together.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Completion is applied to a case where the prefix matches but the unit differs | Low | Three conjunctive checks; the count check is the one that refuses, and it refused 1210 |
| A repair source gazette is itself defective | Realised | Recorded with provenance; auditable from the run report and reversible per record |
| The emission check drifts from what the viewer actually reads | Medium | The field list is a spec contract; `scripts/audit_viewer_fields.py` is a diagnostic that cross-checks it and is expected to disagree loudly |
| The coverage guard becomes too strict and blocks legitimate churn | Medium | Only zero-overlap and wholesale-orphan are faults; everything else stays informational |
| The `--links` guard is ignored because it is only a warning | Medium | It is printed with the affected counts and names the step that did not attach the data, so it cannot be mistaken for a count that shrank |
| A future field the viewer needs is added without a contract entry | Medium | The contract test asserts the viewer has no unguarded reads and that the dataset carries the required fields; adding either without the other fails |

## Migration

```
1  Contract test first, against the dataset as emitted. It must fail on the
   unguarded read before anything is fixed, or it proves nothing.
2  Guard the viewer, restore the 統計至 label. Re-run the smoke test.
3  Emission report for absent link and implementation fields.
4  Coverage guard: report zero-overlap as a total re-key; fault on wholesale orphan.
5  Bounded completion for truncated cells. Re-ingest 1150827; expect 1423 records
   and 4 excluded rather than 1422 and 5.
6  Regenerate the viewer and confirm the header, the list and a sampled set of
   detail panes.
```

Step 5 changes the emitted record count, so it lands after the guards: a repair that
silently altered the dataset before anything could report it is the failure mode this
change is about.
