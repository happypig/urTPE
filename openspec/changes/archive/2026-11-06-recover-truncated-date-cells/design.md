## Context

`urtpe/recovery_pass.py` resolves **truncated 地號 cells**: the publisher
stopped drawing the parcel list at the printed row height, so the row's
identity is unknown and the surviving **date** anchors it. The reader marks
such a row with `source_fault = "truncated_land_cell"`
(`urtpe/extract.py:680`) and the pass either recovers it or leaves it a
residual.

A truncated **date** is the mirror image. The 案名 and the 地號 cell are
complete; the **date** is missing. So the identity is known from the name and
the date is what has to be recovered — the pass's anchor inverts.

The 2026-10-28 gazette's 編號 3 is the shape:
`變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市更新事業計畫案`,
26 parcels, the 案名 declaring 26, and an **empty** 核定日期 cell with no ink
in it.

## Goals / Non-Goals

**Goals:**

- Recover the date for a row whose date cell the publisher left empty, and
  write the city's own approval date into it.
- Never write a date that is a guess: zero or several candidate dates leave
  the row a residual.
- Keep the 168 list's 核定公告 date as a **flag**, never as the recovered date.
- Keep the recovered row out of the reconciliation's edit and withdrawal
  counts.

**Non-Goals:**

- Changing the 地號 truncation path. It works, and its rule is the same rule
  read in the other direction.
- Repairing the publisher's document. The city reprints; the reader recovers.
- Using the 核定公告 date as a date source. Measured: it is a different date,
  and it is empty for every case where the two sources disagree.

## Decisions

**D1 — The candidate rule is the name alone, with two new checks.**

The existing rule's four checks are: same unit, the name contained, the
declared count appears, and **the date closes**. For a date-truncated row the
date cannot close — it is what is missing — so the rule inverts: the first
three checks stay, the date check is replaced, and two checks are added.

- **the stage ordinal** (擬訂 / 變更 / 變更(第二次)) separates a unit's
  successive revisions, which each carry their own approval date.
- **the track set** (事業計畫 / 權利變換, one or both) separates the
  combined-track twins of an area split.

*Measured:* the name alone leaves **10 of 23** rows ambiguous. The ordinal
resolves 8; the track resolves the rest. With both, the residual is **0
ambiguous** over 59 rows.

*Alternative considered:* match the candidate's name to the row's name in full.
Rejected — it is the same idea as the ordinal and the track, done less
precisely, and it cannot separate an area split.

**D2 — The track relation is equality, not a subset.**

Measured: a subset relation admits the area-split twin (recno 10: `10012274` is
事業計畫, `11507024` is 權利變換, and the row names 權利變換 alone) and creates
a new ambiguity (recno 27). Equality keeps the residual at 0.

**D3 — The counts are compared as numbers.**

The city writes the count as `等N筆` in some names and `地號N筆` in others, on
**both** sides of the comparison. A fragment-string comparison then refuses
rows that agree. Comparing the declared counts also makes a real disagreement
refuse — recno 40: the row says `等12筆`, the city says `等13筆`.

*Alternative considered:* keep the fragment comparison and normalise the
fragment first. Rejected — the numbers are the thing being compared, and a
count comparison is the honest form.

**D4 — NFKC folds the names before they are compared.**

The city writes some characters as CJK compatibility ideographs. Measured:
利 as U+F9DD in one case name, which renders identically but does not match
the keyword `權利變換` — so the case reads as 事業計畫 alone and the row cannot
be paired with it. NFKC folds every compatibility ideograph to its unified
form.

*Measured population:* the corpus's own 1,442 案名 carry compatibility
ideographs in **6** rows, but for 北 / 都 / 更, which sit in the district name
(read from the 行政區 column, so the corpus is unaffected) — and **0** rows
carry a compatibility 利. The city's live names carry exactly **1** in 360
read. So the corpus is clean and the platform side is not; NFKC is the folding
the comparison needs either way.

**D5 — The recovered date is the platform's own approval date.**

The city platform's case header (`uro_chk_date` / `uro_chk_date2`) and its
data2 核定日期 are the city's own statement about that case. That is what the
record carries when the publication's cell is empty.

*Measured accuracy:* against the corpus's own dates, the recovered date equals
the corpus's date in **55 of 57**. The 2 disagreements are 1 day apart (the
`pm1` case the existing flag exists for) and 16 days apart — and for the
second, **no candidate carries the publication's date**, so no name-only rule
can recover it. The rule writes the platform's date and the difference is
flagged.

**D6 — The 168 list's 核定公告 date is a flag, not a source.**

The user added it as the fourth source, for the rows where the platform's date
disagrees with the publication's. Measured, it cannot serve that role:

- it holds a date for **146** of 466 rows, and the dated rows are exactly the
  announced ones (134 of 137 sit in 核定階段);
- it is **empty for all 33** cases where the publication's date and the
  platform's date disagree — the very rows it would have to settle;
- where it is present it is a **different date**: it agrees with the 核定日期
  in 99 of 109 joinable rows and differs in 10, by weeks or months.

So it joins as a **second confirmation**: where it is present, a disagreement
with the recovered date is recorded as a review flag, and an agreement is a
confirmation. The recovered date itself comes from the platform.

*Alternative considered:* use the MEMO to pick between two candidate dates.
Rejected — one case has one MEMO, so it cannot break a tie among the
candidates of one case; and it is empty for the cases that need it.

**D7 — The date check must refuse an empty wanted date.**

`R.date_check(d1, d2, want)` with an empty `want` returns `("exact",
"uro_chk_date2")` — it matches the **empty** second header field against the
empty `want`. A false "exact".

It is **latent today**: `_recover_one` returns early when the date does not
parse (`urtpe/recovery_pass.py:79-80`), so `date_check` never sees an empty
`want`. The widened path hands it one on **every** call, so the guard moves
with the change: `date_check` refuses an empty `want`, and the widened path
does not call it at all (it has no date to check against).

**D8 — The tripwire exempts the recovered row.**

The tripwire's date rule fires on the **read** rows. The recovered row's date
is written by the recovery pass, which runs between extraction and cleansing —
so the tripwire must see the recovered row's date, or the run it unblocks is
refused for the fault the recovery just repaired.

*Alternative considered:* move the tripwire after the recovery pass.
Rejected — the tripwire's contract is that it evaluates **before any artifact
is written**, and the recovery pass is inside the ingest, so the exemption
belongs in the tripwire's input, not in its order.

**D9 — The recovered row is listed in the reconciliation's `recovered_records`.**

The reconciler compares the predecessor's **unflagged** read against the
current one. A row the publisher reprinted with an empty date is absent from
the previous side by construction, and its identity key — which includes the
date — no longer matches, so it would be reported as **withdrawn from the
previous newest cohort**. The city did not withdraw it; it reprinted it.

The reconciler already has the parameter for this (`recovered_records`), and
its spec already says a recovered row is not an edit. The change is to route
the date-recovered rows into it.

## Risks / Trade-offs

- **[The recovered date is the platform's, and it may differ from what the
  publication would have printed]** → 2 of 57 in the measured sample, and the
  difference is flagged where the 168 list can see it. The publication's date
  remains the authority where it exists; the platform's fills the blank.

- **[A candidate rule that admits the wrong case]** → The acceptance requires
  exactly one date across the approved candidates, and the ordinal + track
  checks remove the revision and area-split ambiguities. Measured: 0 ambiguous
  over 59 rows, and the 2 residuals are a real count disagreement and a
  missing candidate — both must refuse.

- **[The NFKC folding changes names]** → NFKC is a canonicalisation, not a
  repair: it maps compatibility ideographs to their unified forms and leaves
  everything else alone. The comparison is the only thing that reads it.

- **[The 168 list's MEMO is stale]** → It is a 核定公告 date, which is a
  statement about when the city announced. A disagreement is recorded, not
  resolved.
