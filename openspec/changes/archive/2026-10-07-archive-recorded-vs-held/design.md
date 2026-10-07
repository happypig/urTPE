## Context

See `proposal.md` — Why for the motivation. What shapes the approach is narrower:

`predecessor_of()` has exactly **one** production call site (`cli.py:253`, the reconcile
block of `_ingest_pdf`). Its two siblings are dead in production: `newest()` and
`publication_count()` have no callers outside `tests/` and one archived openspec task
file. That was measured rather than assumed, and it is why this design can add a second
accessor instead of reinterpreting an existing one.

`index_ids_on_disk()` is not dead and cannot be removed: `verify()` uses it as the disk
side of a disk-versus-index comparison. It is also semantically correct where it is —
a digest comparison legitimately asks "what files are here right now".

The reconcile block currently reads:

```python
prev_id = archive.predecessor_of(gazette_id)
prev_path = archive.path_of(prev_id)
if prev_path is not None:
    previous, _ = extract(prev_path, corpus=_corpus_excluding(prev_id))
# else: silence
```

and then reconciles unconditionally. Two of the three states are already expressible in
the reconciler (`comparable=False` with a `note`); the third — recorded but not held —
is not, because nothing can produce that `prev_id`.

## Goals / Non-Goals

**Goals:**

- One accessor per tense, so a caller cannot silently get the wrong answer.
- The absence of a predecessor becomes a *sentence*, not a fallthrough.
- Archive damage becomes visible on the ordinary path that already runs.
- `verify()` costs no extra read: it already compares digests, and a member is read by
  the corpus builder anyway.

**Non-Goals:**

- Not reconstructing 09-24's chain position. The document is gone; inferring a position
  to make a comparison look adjacent is fabricating provenance.
- Not repairing `2026-10-01.json`. The correct conclusion survives only in
  `2026-10-01.superseded-with-09-24.json`, and rewriting history to hide the gap would
  be worse than the gap.
- Not blocking ingestion on archive damage. See D3.
- Not changing `publication_count()`'s or `newest()`'s contracts, even though both now
  read the disk. Their docstrings say "archived", which is present tense, and they are
  unused in production, so there is nothing to gain and a contract to lose.

## Decisions

**D1 — Add `recorded_ids()`; do not reinterpret `archived_ids()`.**

```python
def recorded_ids(self) -> list[str]:
    """Publications the index says were ingested — history, not presence."""
    return sorted({e.gazette_id for e in self.entries()})
```

`predecessor_of()` switches to it. *Alternative considered:* repurpose `archived_ids()`
to mean history and let `verify()` keep the glob. Rejected — it would rename a
present-tense accessor into a historical one, and `archived_ids()`'s two live-ish
consumers (`newest()`, `publication_count()`) would silently change meaning. Two
accessors named for their tense makes the question explicit at the call site, which is
where the original confusion lived.

**D2 — The chain's input is the record; the file check stays a separate step.**

`predecessor_of()` returns the recorded predecessor whether or not its document is
present. Presence is then `path_of()`'s separate answer, and the caller compares the two.
*Alternative considered:* have `predecessor_of()` return `None` when the document is
missing. Rejected — that is the bug in its current form (it returns the wrong
publication instead); folding presence into the chain lookup destroys the distinction
this change exists to preserve.

**D3 — Report, do not block, on archive damage.**

`verify()` output is printed and carried in the run log. A missing older gazette does not
invalidate the one being ingested. *Alternative considered:* blocking, on the reasoning
that a damaged archive should not produce output. Rejected — the gate cannot repair the
archive, so blocking converts a recoverable filesystem accident into a permanent halt,
and the operator's only remedy would be manual index surgery. The tripwire already
exists to refuse on incompleteness; refusing here would duplicate that authority on a
condition it cannot judge.

**D4 — Absence reuses the reconciler's existing `note` channel.**

Three states in `_ingest_pdf`, not two:

| condition | outcome |
| --- | --- |
| `prev_id is None` | `no previous gazette archived` (existing) |
| `prev_id` set, `path_of` returns `None` | `previous gazette <id> is recorded but its document is not held` |
| readable | compare |

*Alternative considered:* a new exception type or a distinct result field. Rejected —
`comparable=False` plus a `note` is already the truthful shape for "no comparison was
possible", and it already round-trips into `change_sets/*.json`. Reusing it means the
absence reaches the persisted record with no new plumbing.

**D5 — One openspec change, not three.**

The three fixes are one idea — *the archive must distinguish what it recorded from what
it holds* — landing in two capabilities. Splitting them would triple the ceremony for
roughly 25 lines and would let fix 2 be reviewed without fix 1, which is the one that
makes fix 2 reachable at all.

## Risks / Trade-offs

- **`verify()` reads every member on every ingestion.** → ~8 MB of SHA-256 at four
  members; negligible, and the corpus builder reads the same bytes regardless. If the
  archive grows by an order of magnitude this becomes the first thing to gate behind a
  flag, and the digest cache already keyed on the file makes that cheap.
- **Fix 1 is inert until a member goes missing.** → This is the point, not a defect: an
  inert-until-needed safety net cannot destabilise working code. It also means no
  end-to-end test can fail *today* unless it constructs the scenario (index records X,
  disk lacks X), so that construction is the test's job.
- **A `note` value appears that no reader has seen before.** → `change_sets/*.json`
  gains a reason string previously reserved for "no previous gazette archived". Both are
  already valid `note` values; consumers that switch on the old string would treat the
  new one as unknown, which is the safe direction.
- **The emitted dataset does not change.** → Verified: 10-01 reads 1,439 records
  identically with and without 09-24 present, because all 14 of its completions are
  sourced from 2026-08-20. So this change carries no data risk — only reporting risk.