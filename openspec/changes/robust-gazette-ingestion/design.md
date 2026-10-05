# Design — robust-gazette-ingestion

## Context

### Actors

| Actor | Concern |
|---|---|
| **Pipeline maintainer** (jeffw) | Runs ingestions; must not silently lose data or orphan caches |
| **Periodical updater** | Fetches the newest gazette; needs a cheap way to tell whether anything changed |
| **Reviewer** | Reads the review report after each run; must see applied corrections and unexplained changes |
| **臺北市都市更新處** (external) | Publishes the gazette; controls its layout, calendar, and column order |

### Domain events

- The city publishes a new gazette (new approvals prepended; layout may change without notice)
- A person corrects a record after reading the review report
- The reviewer accepts or rejects a change between two publications
- A schema of change the reader cannot interpret is encountered

### System boundary

```
IN SCOPE (this change)                OUT OF SCOPE
──────────────────────                ─────────────────────────────
gazette PDF → raw rows                portal (twur / Taipei ashx) discovery
cleansing rule application            the 28 h national-portal sweep
similarity merge (unchanged)          .link_cache migration of moved ids
project identity (unchanged)          viewer UI beyond a label
archive + diff + tripwire
```

### The failure this design exists to prevent

The reader parsed gazette `1151002` without raising. It produced 1,681 rows of which **1,677 had an empty 案名**, **all** had `ymd=(0,0,0)`, and 行政區 contained the entire case name. Three independent causes:

```
(a) 核定日期  115/8/27  中山區     (ROC, separate cells)   → worked
(b) 核定日期  2026/9/24中山區                              → glued; strict fullmatch
                                                              failed → (0,0,0)
    then: pick_anchor() max(ymd) is a tie for every record
          → falls through to min(recno) → anchors OLDEST
          → 1,436 garbage project_ids → all 709 caches orphaned
          → coverage.py:51 set(before)&set(after) == ∅ → regressions={} → PASSES

(c) case-name column x0: 185.1 → 177.5, band edge is exactly 185
    → the whole 案名 column lands in the 行政區 band

(d) 編號 1 repeated in the header of all 245 remaining pages
    → 245 phantom anchors; record boundaries are midpoints between
      consecutive numbers, so each phantom TRUNCATES the page's last record
```

Cause (b) is the one that matters: **the reader had no way to report that it had failed.** The zero-date cascade into `project_id` is the reason a tripwire is a requirement and not a nicety.

## Decisions

### D1 — Cell boundaries come from ruling lines, not coordinates

**Decision.** Replace `BANDS` (`extract.py:19-27`) with `page.find_tables()` at `strategy="lines"`, taking each cell's text from the rectangle the table detector resolves.

**Rationale.** Measured on both publications:

| | 1150827 | 1151002 |
|---|---|---|
| pages yielding a table | 202/202 | 246/246 |
| distinct 編號 | 1427 | 1436 |
| contiguous 1..N | yes | yes |
| empty 案名 | 0 | 0 |
| empty 核定日期 | 0 | 0 |

100% on both, including the file the positional reader fails on completely. The column shift and the calendar change are both invisible to it because neither is expressed as a coordinate it stored.

**Alternative rejected — fix the bands.** The bands are 7 numbers tuned to one export. The city changed the calendar and shifted the columns in a single publication; the next change is equally unforecastable. Tuning constants against observed drift treats a moving target as a fixed one.

**Alternative rejected — `pymupdf_layout`.** Evaluated, not assumed. Process-isolated A/B over pages 1-3 of `1151002`, output written by separate processes and compared on disk:

```
plain  臺北市中山區長春段一小段 764、764-1 地號等2筆土地
layout 臺北市中山區長春段 一小段 764、764 -1 地號等2筆土地
                 ▲                      ▲
      space inside 段小段        space before every sub-parcel
```

**17 of 18 records corrupted.** The GNN's whitespace normalization is correct for prose and destructive for an identifier stream:

- `長春段一小段` → `段 一小段` breaks `SECTION_RE` → `section` empty → `slug_for()` garbage
- `764-1` → `764 -1` breaks `ALIAS_RE` (the `689地號(原726地號)` renumbering bridge at `cleanse.py:24`)
- record 7's `231-3` → `231\n-\n3`, the hyphen isolated on its own line

It is also proprietary ("may not be copied, modified or distributed except as expressly authorized"), pinned to `pymupdf==1.28.2` exactly, and ~35× slower per page (0.06 s → 2.19 s). Rejected on correctness; the cost arguments are secondary.

### D2 — Reject spans; never fall back to text strategy

**Decision.** A cell spanning more than one row or column aborts the run with its location. A page yielding no table aborts the run. No positional or whitespace-aligned fallback exists in the new reader.

**Rationale.** PyMuPDF models spans explicitly:

```
SpanCell  "One reconstructed table cell after span resolution… colspan/rowspan
           how many grid columns/rows it covers."
to_markdown(clean=False, fill_empty=True)
          "If fill_empty then cell content None is replaced by the values…"
table.py:1756   # replace None cells with empty string
```

`extract()` returns `None` at grid positions owned by a span anchored elsewhere, and `fill_empty=True` is the **default** in `to_markdown()` — the library fills spans because the correct answer is not derivable from geometry. Fill forward or fill down? Genuinely undecidable.

In this domain it is decidable, and the answer is to refuse: a 地號 cell spanning two printed rows means we cannot know which approval owns those parcels, and `first_parcel` feeds `slug_for` → `project_id` → the `.link_cache` directory name. A guess orphans a cache and mints a bogus id — the same failure class as D1, arrived at from a different direction.

Empirically this costs nothing today: **0 `None` cells across 23,177 cells** in both publications (11,403 + 11,774), every row exactly 7 cells. It is insurance against a structure we have not yet seen, and it fails loudly when it triggers.

`strategy="text"` is specifically excluded because it was measured to be destructive on a ruled table: it collapsed a 4-column grid to 2 and merged two cells into one field (`'10 SPAN'`). If ruling lines ever vanish, text strategy would corrupt 編號 — the one field everything keys on.

### D3 — Completeness tripwire, evaluated before any write

**Decision.** Every emission is gated on: 編號 contiguous from 1 to max with no gaps; every 核定日期 parsed; exactly one table per page; no `None` cells; no row-shape mismatch; duplicate-編號 count within the known header-artifact tolerance.

**Rationale.** 編號 is contiguous in both publications (1427 and 1436, no gaps). That makes "no gaps" a three-line, format-agnostic assertion that catches a whole class of silent truncation — including a page the reader failed on entirely, which under D2 aborts anyway.

Critically, the gate must run **before any artifact is written**. The 2026-08-24 incident (four concurrent writers, 47 caches wiped) and the current `coverage.py` blind spot have the same shape: a check that runs after the damage, or that cannot see the failure. `coverage.py:46-59` diffs only `set(before) & set(after)`; a total re-key empties that intersection, so the guard passes while every cache is orphaned. The tripwire must be upstream of the write, and reconciliation (D6) must special-case total re-keying.

**Provisional.** The duplicate-編號 tolerance and expected records-per-page are calibrated against three gazettes and may need adjustment at the next ingestion.

### D4 — Calendar sniffed per cell, normalized once at the boundary

**Decision.** Replace `roc_to_iso` with a `to_iso` that reads a 1-to-4-digit year and adds 1911 when below 1911, applied per cell. All downstream comparison uses ISO.

**Rationale.** ROC began in 1912, so no ROC year reaches 1911 and `y < 1911` is an unambiguous discriminator. Deciding per cell means a publication that mixes calendars — plausible mid-transition — is handled without a special case.

Normalization happens once in `cleanse`, so `ymd`, `pick_anchor`, the viewer's year facet (`app.js:543-551` slices `node.date`), and `_match_case_by_date` (`links.py:1149-1184`) all compare like with like. `graph.py:22` already emits `date` as ISO, so **the viewer needs no code change**.

The old failure is the argument for this: the glued `2026/9/24中山區` failed `re.fullmatch` and silently produced `(0,0,0)` for every record. A sniffing parser that cannot interpret a cell now aborts instead.

### D5 — Publication date read from the document

**Decision.** Delete the hardcoded return at `extract.py:62-73` and use the `統計至` pattern already present at `extract.py:37`.

**Rationale.** The function ignores its `page` argument and returns `"統計至 115年8月11日"` for any input. Measured: `1150827` → `統計至115年8月27日`, `1151002` → `統計至115年9月24日`, both extract cleanly. `projects.json` currently stamps 8/11 after ingesting a 9/24 publication — the header lies about its own vintage.

This also means the existing spec requirement (`pdf-tsv-extraction/spec.md:41-53`), which names `115年8月11日` as the expected value, must be replaced rather than supplemented.

### D6 — Reconciliation reports additions authoritatively and historical movement as a separate signal

**Decision.** Match the newest-approval cohort by content and count it; report historical
row movement (re-dated, edited) as its own counted signal; block only when the total
record count shrinks or the previous newest cohort is withdrawn. `--strict-reconcile`
promotes historical disappearance to blocking, satisfiable by a ledger acceptance.

**Rationale — the recno model no longer holds.** The shift is not affine:

```
1150820 → 1150827   every one of 1,421 matched records moved exactly +5   (uniform)
1150827 → 1151002   old#1 → +8    old#100 → +6    old#300 → +5
                     old#1000 → −13 ◄── moved UP past 13 records
                     old#1420 → +10
```

Non-monotonic. Date-order violations fell from **9** to **1** between the two
publications: the earlier export was insertion-ordered, the newer one re-sorts history
by 核定日期. So recno is a coordinate in a mutable list, not a rank with an offset, and
any remap keyed on it is arithmetic on an unknown function.

**Rationale — why per-record content diffing was rejected.** The first implementation
matched on `(行政區, land, ISO date)` and reported **74 removals** for 1151002. Every one
was a false positive, from two measured causes:

```
                          1150820 → 1150827    1150827 → 1151002
content keys changed                 5                       79
approval-year gained          2026: +5      2026: +8  and 2006..2016: +22
approval-year lost                   none      2000..2024: −21
```

1. **The new export re-dates history** — 22 historical approvals moved later, 21 earlier.
2. **The city edits historical cells** — 59 land cells differ in text between the two
   publications, so an edit makes a row look simultaneously added and removed.

Matching cannot distinguish a deletion from an edit, because in the published data they
are the same observation. Only three things survive that:

| Signal | 0820→0827 | 0827→1002 | Authoritative |
|---|---|---|---|
| approvals newer than the previous maximum date | 5 | 8 | yes |
| net change in total records | +5 | +9 | yes |
| calendar | unchanged | roc → gregorian | yes |

This is the same constraint `openspec/config.yaml` already states for the merge stage —
*"parcel coverage changes and parcel renumbering break exact-key matching, so unit
identity must be found by similarity, not equality"* — applied here as a scoping
decision rather than a scoring strategy. Similarity matching was considered and
rejected: ~1400² comparisons per run to resolve rows that are, in the cases that
matter, genuinely ambiguous.

**Consequence, recorded honestly.** The genuine 89/9/29 disappearance
(`大安區仁愛段四小段114地號等6筆`) is a 2000-vintage row, so it now falls in the historical
signal rather than the blocking one. It is reported, prominently, with its district and
land description — but it does not stop a run. Task 13.3's original wording ("aborts on
the removed 2000 record") is therefore not satisfiable as written and was revised; a
per-record deletion assertion cannot be made against this source.

**Blocking conditions, and why each is sound:**

- *Total record count shrinks.* Arithmetic on a quantity the reader has already proven
  contiguous via the tripwire.
- *Previous newest cohort withdrawn from the current newest cohort.* Both cohorts are
  bounded by a date the reader parsed, so absence is meaningful here in a way it is not
  for edited historical rows.
- *Total re-keying.* `coverage.py` cannot express it (see D3).

**Also measured, and not defects:** the source carries long-standing typos that are
identical in both publications — `臺北市投區崇仰段` (missing 北), `臺北大安區辛亥段`
(missing 市), and two rows whose 案名 leaks into the 地號 cell. `cleanse.py:16` already
handles the `松化區` district typo; the others are untreated and become unreconcilable
noise. Recorded for a separate cleansing change rather than fixed here.

### D7 — Corrections are ledger rows keyed on land core + date

**Decision.** Replace dated patch scripts with an append-only ledger, applied after `cleanse_all` and before `merge`.

**Rationale.** `scripts/repair_621_track_2026_08_26.py` documents its own problem:

> *"The cleanse.py normalization (事業換計畫 → 事業計畫) landed after the last `--from-js` regeneration… This script patches the emitted data to exactly what the next full PDF build will produce."*

It compensates for a fix already in code, because artifacts and code drifted apart. Worse, it patches by `recno 621` — a coordinate that under Option A becomes a different row next gazette, at which point it silently no-ops or patches the wrong record.

Keying on `land_core` + `核定日期` makes corrections position-independent: the same case at 編號 621 in one publication and 631 in the next still matches. Applying post-cleansing, pre-merge means a correction to an identity-bearing field propagates into `project_id`, which reconciliation then reports. Reporting applied/unmatched counts in the review report makes corrections visible in normal operation rather than only in the ledger file.

Unmatched entries are reported, not fatal — a correction for a record that has not been re-published yet is normal, not an error.

### D8 — Archive outside git

**Decision.** Store gazettes outside the working tree, referenced by an append-only index. Add an explicit `.gitignore` entry as a guard against accidental staging.

**Rationale.** `.gitignore` already carries `data/**` and `data_test/**`, so `data/` is untracked and git history holds 14 commits of `projects.json` but only 2 of `clean.tsv` — no gazette dimension at all. The PDFs are upstream artifacts, roughly 2 MB each, about 100 MB/year.

The deciding factor is durability of the *old* ones: the city's URL is version-specific (`www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/c5ff4f68-….pdf`, a UUID path), so only the newest is reachable. Older gazettes must be kept locally or they are gone. Keeping them out of git avoids repo growth for artifacts that are, by construction, re-downloadable only while the city still serves them.

Cost: the archive is a separate durability concern from the repo. Mitigated by the index recording what each file yielded, so a missing archive member is detectable rather than silent.

### D9 — Rebuild layers 0–2 in full; keep layer 3 incremental

**Decision.** Full rebuild of parse → cleanse → merge on every ingestion. No incremental path for the PDF-derived layers.

**Rationale.** Measured cost of a full rebuild: `find_tables()` over 448 pages ≈ 42 s, cleanse + merge ≈ 0.3 s, graph emit ≈ 2 s. Roughly **45 seconds**. Incremental would buy nothing and would guarantee the failure mode that produced `repair_621`: 2019 records parsed under old rules, 2026 under new, in one dataset. Full rebuild is the only way a reader change reaches historical records uniformly.

The portal layer is the opposite and is already correct: `.link_cache/<project_id>/` is keyed on an identity that survives, measured at **704 of 709 unchanged** (712 vs 713 families, 5 degenerate ids where the positional reader had extracted no parcel number or produced a `-2` collision suffix). Caches are consulted, not rebuilt.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| A future publication has no ruling lines | Low | D2 hard-fails; no unsafe fallback exists. Re-evaluate `pymupdf_layout` **only** at that point, when whitespace heuristics are the only alternative |
| Tripwire thresholds too strict, blocking a valid ingestion | Medium | Thresholds are parameters, not constants; a blocked run names the failing check |
| Archive diverges from index | Low | Index records what each file yielded; a missing member is detectable |
| The 2000 record was a parser bug, not a city deletion | Unknown | D6 aborts and forces the question; the previous gazette stays archived so the record is recoverable |
| Ledger grows unwieldy | Low | Append-only, content-keyed, superseded entries retained as history |
| Records dropped by a reader bug never reach the tripwire | Low | D3's contiguity check catches the common case; D6's diff catches subtler losses by content |

## Migration

```
1  Archive the three known gazettes (1150820, 1150827, 1151002) under their
   統計至 dates; append index entries. Nothing is derived from them yet.
2  Swap the reader. Regenerate from the newest archived gazette.
3  Reconciliation reports against the previous gazette. Absorb the expected
   5 project_id moves via an alias table — see parked.md.
4  Convert repair_621_track and any other emitted-data patch script into
   ledger entries, then delete the script.
5  From here: periodical fetcher compares 統計至 against the index and runs
   the full pipeline only when the publication actually changed.
```

Step 1 first: without an archive there is nothing to reconcile against, and the first reconciliation would be against a single stale `source.pdf` (統計至 115-8-11, older than the data currently shipped).

## Open questions

- The city's gazette page (`uro.gov.taipei/cp.aspx?n=963B15B39CADB94E`) exposes a 資料更新 timestamp and links only the newest PDF; whether it supports conditional requests (`ETag`/`If-Modified-Since`) is untested and determines fetch cost.
- Should the ledger be a single JSONL file or per-entry files? JSONL chosen for append-only simplicity; revisit if concurrent writers appear (the single-writer rule currently covers `.link_cache` only).
- Whether re-reading archived gazettes under the current reader should also rewrite the emitted dataset, or produce a parallel "as-of" dataset. Deferred — no current requirement for historical views.