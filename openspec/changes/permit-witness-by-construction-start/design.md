## Context

`attach_links_to_projects` (`urtpe/links.py:3516-3527`) attaches the permit
witness:

```python
permits = match_project_permits(permit_index, project_parcels)
if permits:
    best = permits[0]
    project.links["permit"] = {"permit_no": best.permit_no, "date": best.date,
                                "permits": [p.permit_no for p in permits]}
```

`match_project_permits` (`urtpe/permit_sources.py:113-135`) returns every
permit whose parcel overlap ties for the highest count, sorted by permit
number. So `permits[0]` is the alphabetically first number — the **oldest**
permit on that mono parcel.

The permit index keys on the **mono** parcel (`urtpe/links.py:3509`), so a
section that redeveloped over time accumulates one permit per building phase.
寶清57-13's parcel 57 carries four permits, spanning 2004 to 2025.

The disagreement flag (`permit_review_flags`, `urtpe/permit_sources.py:182`)
compares the city and national 使照 dates and names the permit that matches
one of them. It fires only when **both** portal dates exist — so the 43
projects whose witness is wrong (and which have no national 使用核發日期) are
silent.

## Goals / Non-Goals

**Goals:**

- Name the permit the project's own 使照 came from.
- Never show an arbitrary permit as the project's own.

**Non-Goals:**

- Repairing a wrong 使照 date. The permit is a witness; it does not replace
  either portal's value.
- Changing the permit index, the download, or the parcel-overlap match.
- Deciding the tie with the city's 使照 date.

## Decisions

**D1 — The 開工 date is the tie-breaker.**

The permit record carries `construction_start` (開工日期), and the city
platform carries the same field (`Eng_Start_Date`). The two are the same
event, so an equality between them is a **citable** match, not an inference.
It picks the right permit in both of the user's named cases and in 18 of the
33 multi-permit projects that carry a 開工 date.

*Alternative considered:* the city's 使照 date. Rejected — the permit exists to
check that date. A witness that matches the value it witnesses can never
report a disagreement.

**D2 — The 開工 date comes from the source map.**

The merged `milestones_taipei` dict can be stale — that is what D7 fixes. The
source map (`milestones_source`) names the case that holds each value, so the
date read from it is attributable. This is the same rule D4a established for
the construction chain.

*Alternative considered:* the merged dict. Rejected — it inherits the
corruption D7 found, and the source map is already there.

**D3 — An unresolved tie emits no permit.**

When the 開工 date leaves none or several permits, `links.permit` is absent
and `links.permit.ambiguous` carries the candidate list. The viewer then
shows the candidates rather than one arbitrary permit.

*Alternative considered:* keep `permits[0]` as the witness and add an
`ambiguous` marker beside it. Rejected — the arbitrary permit would still be
shown as the project's own, which is the defect.

**D4 — The selection is a pure function.**

`select_permit_witness(permits, city_start_date) -> (PermitRecord | None,
ambiguous: bool)` lives in `permit_sources.py`, next to the matching logic it
belongs with. It takes the permits and the city's 開工 date and returns the
witness or the ambiguity. The call site supplies the date from the source map.

*Alternative considered:* doing the selection inline at the call site.
Rejected — the rule is worth testing on its own, and it belongs beside the
other pure permit logic.

## Risks / Trade-offs

- **[15 of the 33 multi-permit projects lose their single witness]** → They
  gain an explicit ambiguity, which is the honest reading. 4 have no 開工 date
  at all; 11 have a 開工 date that matches zero or several permits.

- **[The viewer reads `links.permit`]** → The viewer must handle the absent
  key and the `ambiguous` key. The viewer's permit display is checked in the
  same change.

- **[The 開工 date is missing]** → Then the tie stays unresolved and the
  project shows the ambiguity. No fallback to the first permit.
