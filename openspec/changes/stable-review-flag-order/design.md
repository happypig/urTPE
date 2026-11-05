## Context

`urtpe/graph.py` writes a node's `review_flags` through `_dedupe`, which
collapses repeated strings and keeps first-appearance order. The flags
themselves are raised at four places, and each appends to a member's list:

- `urtpe/cleanse.py` — the cleansing flags (a fixed order, one per condition);
- `urtpe/merge.py:214` — the family-has-no-count flag;
- `urtpe/links.py:3013` — the 片段家族合併候選 flag;
- `urtpe/links.py:3192, 3226, 3314, 3387` — the conflict and orphan flags,
  raised over the case ids the link pass walks.

The last group is the order-dependent one. The orphan sweep raises one flag
per unplaced case id, and the ids it walks come from the family's member
order. A ledger merge that reorders a family therefore reorders the flags on
the node that anchors it.

The viewer joins the flags with `、` (`viewer/app.js:1463`), so the order is
visible on screen.

## Goals / Non-Goals

**Goals:**

- Make the emitted flag order a function of the flag content alone.
- Leave the flag set untouched.

**Non-Goals:**

- Changing which flags are raised, or when.
- Changing the order of `auto_fixes`, which is a different list with a
  different contract (the auto-fix list reads as a narrative of the
  corrections, in the order the cleanser applied them).
- Fixing the pipeline's traversal order. The order still varies; the emission
  no longer shows it.

## Decisions

**D1 — The sort lives in the emitter, not at the raising sites.**

`graph.py` already owns the flag list (`_dedupe`). Sorting there covers every
raising path at once, including a flag added later. Sorting at each site
would need four edits and would leave the next site unprotected.

*Alternative considered:* sort the ids the orphan sweep walks. Rejected — it
fixes one path and leaves the conflict flags and the fragment flag exposed to
the same traversal order.

**D2 — The key is (case id, flag text).**

The case id is the part that identifies the flag's subject, and it is the part
the order flips on. Comparing it as text keeps the key simple; the ids are
zero-padded serial numbers of the same length, so text order and numeric order
agree.

*Alternative considered:* sort by the flag text alone. Rejected — the text
starts with a Chinese phrase and the case id sits in the middle, so a text
sort would order the orphan flags by the truncated case name, which is the
first 40 characters of a 案名 and carries no order of its own.

**D3 — A flag that names no case id sorts first.**

The cleansing flags (行政區與地號行政區不一致, 階段與平台案件狀態不一致, …) name
no case. Giving them the empty case id places them before the flags that do
name one, and the text breaks the tie. This keeps the cleansing flags — the
ones a reader reads first — at the head of the list.

## Risks / Trade-offs

- **[The emitted order differs from today's on 20 nodes]** → The flag text is
  unchanged and no flag is added or lost; only the positions move. The change
  rides the step 2 re-emit, so the diff is measured against that re-emit, not
  against an unrelated run.

- **[A flag names a number that is not a case id]** → The pattern requires the
  `案` prefix the orphan and conflict flags use. A flag that carries `案` in
  another sense would be read by its number; measured over the 2026-10-15
  payload, 6 nodes carry a flag that names a case id, and all of them are
  orphan or conflict flags.
