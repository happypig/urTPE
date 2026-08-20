## Context

Actors and boundaries (see proposal.md for motivation):

- **The pipeline (deterministic)**: PDF → positional parse → raw.tsv → normalization → clean.tsv → similarity merge → merged.tsv → projects.json. Pure logic and I/O adapters are separated; the pipeline itself has no side effects beyond reading the PDF and writing the five outputs.
- **The agent (judgement)**: applies the cleansing rules and the similarity model, decides borderline pairs, and populates the review/flag column. Every agent decision is recorded in the review report; nothing is guessed silently.
- **The analyst (human)**: reviews flags/review report, browses the per-project history graph in the viewer.

Domain events the design must respect: a new approval is always prepended to the list as 編號 1 (newest-first ordering); one 更新單元 accrues approvals over years (擬訂 → 變更(第N次)) across two tracks (事業計畫 / 權利變換) and optional sections (甲/A/B區段); parcels change via coverage adjustment (原N筆) and renumbering (原地號), so exact-key matching is impossible.

Exploration findings already hard-code the parseable structure: 7 columns with stable x-bands; record boundaries are standalone 編號 lines immediately followed by a 核定日期; cells wrap mid-value and must be re-joined.

## Goals / Non-Goals

**Goals:**
- Deterministic, auditable extraction (1,419 rows) from the exact 201-page source PDF.
- A pure `cleanse` and `merge` core, independent of PDF/TSV/JSON and viewer adapters.
- Append-friendly project identity: anchor by 核定日期, id from the anchor's normalized name-core — unaffected by 編號 reordering.
- Every intervention (auto-fix, flag, borderline pair) surfaced in a review report.

**Non-Goals:**
- Scheduled/online refresh — run on demand against a PDF.
- Any spatial/GIS output or parcel geometry.
- Modifying the source PDF or "fixing" ambiguous fields without a flag.
- A deployed viewer — a static page that loads projects.json is enough.

## Decisions

1. **Positional extraction, not text-flow regex.** Parse pymupdf word coordinates: assign words to columns by x-band, group by record using the 編號→日期 anchor lines, re-join wrapped cell lines by y-order. *Why:* the raw text flow already proved ambiguous (line-wrap artifacts, page furniture, truncated cells); positions are stable. *Alternative rejected:* regex over `get_text()` — fragile to spacing and wraps.

2. **Three intermediate files, not one transform.** `raw.tsv` → `clean.tsv` → `merged.tsv` are each written and independently reviewable, with a review report alongside. *Why:* auditability of an agent-in-the-loop pipeline; a bad merge must not mask a clean record. *Alternative rejected:* single in-memory chain — no checkpoints, no diff-ability.

3. **Weighted similarity + thresholds + connected components.** Features: section (exact), first-parcel (equal | alias | in 原核定 list), parcel Jaccard (aliases expanded), count bridge (原N筆), named anchor (equal); implementer is corroboration only. Score ≥ 0.7 links; 0.5–0.7 goes to the review report; below 0.5 no link. Families = connected components. *Why:* matches how the known clusters behave (中華工程 寶清段 stays 4 units despite shared section+implementer; 金華段四小段513-3 bridges 11↔13筆; 東星大樓基地 links with no parcels). *Alternatives rejected:* exact-key equality (breaks on coverage/renumbering); ML embedding similarity (no labeled corpus, overkill for 1,419 rows).

4. **Anchor by 核定日期, tie-break closest to 編號 1; `project_id` = slug of the anchor's normalized name-core** (e.g. `中正區-永昌段三小段-159地號等113筆土地`). *Why:* 編號 is volatile (new approvals prepend); the name-core is stable across revisions of one unit and append-friendly. *Alternative rejected:* `P-<recno>` ids go stale on reorder; slug of raw name collides on typos — slug of the *normalized* core avoids both.

5. **Port/adapter split (minimal).** Adapters: `pymupdf` extraction, TSV/JSON read/write, static viewer. Pure core: normalization rules, field derivation (parcels/aliases/counts/anchor/區段/stage/track), similarity scoring, clustering, anchor selection, slugging, graph edge construction. *Why:* per config practice — testable pure logic without touching adapters. Not full Clean Architecture: no repositories, no CQRS, batch-only.

6. **Agent-in-the-loop with a review column.** The agent decides borderline links and ambiguous normalizations; the machine enforces deterministic rules; every agent decision lands in the review report. *Why:* the merge is judgement-based by requirement, but must stay auditable.

7. **Graph = JSON schema + static HTML/JS viewer.** `projects.json` holds nodes (編號, ISO date, stage, track, 區段, is_current) and edges (revision chains + section branches) converging on the anchor. Viewer is a single static page loading the JSON. *Why:* programmatic use (user chose JSON); no server. *Alternative rejected:* Mermaid — render-only, not a data format.

8. **POC first, thresholds provisional.** Before the full build, validate positional parsing against real pages and calibrate the 0.7/0.5–0.7 thresholds and feature weights on the known clusters (寶清段, 永昌段三小段159, 逸仙段二小段151, 金華段四小段513-3, 立農段五小段329). Findings may change thresholds — they are starting points, not contracts (see proposal).

## POC Findings (implemented)

Validation on the real 201-page PDF confirmed the plan with three refinements:

1. **案名 carries the stable case identity; the 地號 cell does not always.** Wrapped 地號 cells can start mid-list (e.g. `37、37-1、38…`) with the 段小段 prefix on a different row; the 案名 always contains `臺北市{區}{段}{N}地號等N筆`. The pipeline now derives section/first-parcel/count from the 案名 first and falls back to the 地號 cell, so continuation cells inherit the right identity and still get a 缺少段小段 review flag. 區段 (甲/A/B) and parcel enumeration still come from the 地號 cell.
2. **Section shapes vary: `段N小段` (永昌段三小段), `N小段` (吳興一小段), bare `段` (民生段).** One shared token regex covers all three; 小段 is not required.
3. **The name-core slug is not unique.** Two distinct units can share `區-段-N地號等N筆` (e.g. two 中山段二小段-125 projects by different implementers). After clustering, colliding slugs get a deterministic `-2`, `-3`, … suffix ordered by anchor 編號, keeping every project_id unique while preserving the anchor name-core form.

Thresholds held: link ≥ 0.7, flag 0.5–0.7, weights unchanged. All known clusters merge correctly (中華工程 stays 4 units; 永昌段三小段159, 逸仙段二小段151, 金華段四小段513-3 bridge; 東星大樓基地 links without parcels).

## Risks / Trade-offs

- [Threshold miscalibration → over- or under-merge] → POC calibration on known clusters; 0.5–0.7 flag band routes uncertain pairs to the review report instead of silent decisions.
- [A future PDF layout change breaks positional bands] → extraction is isolated in the adapter; parse-error markers and the extraction report surface non-conforming records instead of silently dropping them.
- [Same section + implementer spans several real units] → parcel identity and alias matching are primary; implementer is corroboration only, never a trigger.
- [Ambiguous records (e.g. 案名 district ≠ 地號 district)] → flagged with reason, never guessed; review report carries them to the analyst.
- [New approvals reorder 編號] → anchoring and ids never depend on 編號; 編號 remains as source traceability only.
- [Agent judgement is hard to reproduce] → the review report and merged.tsv record every agent decision (link, flag, reason) so runs are explainable.

## Migration Plan

- Run on demand against the provided PDF; all outputs are regenerated from the source, so rollback is simply re-running the previous pipeline version. No schema migration — this is a greenfield batch tool with no existing consumers.

## Open Questions

- Output directory conventions (repo `data/` vs root) and whether `raw.tsv`/`pdf_text.txt` are committed — implementation detail, no spec impact.
- Viewer implementation detail (vanilla JS vs a tiny framework) — deferrable to implementation.
- Whether a second anchor tie-break (same date) should prefer the record with the lower 編號 or the one listed later on that page — resolved deterministically by the chosen rule (closest to 編號 1); confirmed during POC.