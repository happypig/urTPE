## Why

The Taipei City Government publishes its urban-renewal approved-cases list (臺北市都市更新核定案件一覽表) as a 201-page PDF of 1,419 approvals (2010–2026), where one 更新單元 (renewal unit) is approved many times as it progresses: 擬訂 → 變更 → 變更(第N次), across two tracks (事業計畫 / 權利變換計畫) and optional sections (甲/A/B區段). ~70% of the rows are therefore repeat approvals of the same unit, yet the file ships as flat, unlinked rows with parsing artifacts (line-wrapped cells, the 松化區 district typo, 計劃/計畫 typos) — so an analyst cannot answer "show me one project's full approval history" or "which units changed land coverage" without manually cross-referencing. This change delivers a reproducible pipeline that turns the PDF into a clean, merged dataset whose project identity is anchored on the latest approval and stays append-friendly when new approvals are prepended as 編號 1.

## What Changes

- **PDF → raw.tsv**: positional text extraction (pymupdf) of the 7 table columns, re-joining line-wrapped cells and stripping repeating page headers/footers.
- **Data cleansing (agent)**: normalization of known errors (松化區→松山區, 計劃→計畫, ㄧ→一, 權利變換案 == 權利變換計畫案), extraction of structured fields (行政區, 段X小段, 首筆地號, 地號 set + 原地號 aliases, 筆數, 原N筆, named anchor, 區段, stage, plan type, ISO date). Obvious fixes applied; ambiguous cases written to a review/flag column.
- **Similarity merge**: records linked by fuzzy similarity (section + first-parcel/alias + parcel Jaccard + count bridge + named anchor, implementer corroboration). Link ≥ 0.7, borderline 0.5–0.7 flagged. Connected components → project families.
- **Latest-anchored project_id**: the anchor of a family is the newest approval by 核定日期 (never by 編號, since new approvals are prepended). `project_id` = slug of the anchor's normalized name-core — stable across revisions and append-friendly.
- **History graph**: per-project `projects.json` (nodes = records, edges = revision chains + section branches converging on the anchor) plus a browser viewer.
- **Outputs**: `raw.tsv`, `clean.tsv`, `merged.tsv` (with project_id + is_current), `projects.json`, viewer.

## Capabilities

### New Capabilities
- `pdf-tsv-extraction`: Convert the source PDF into a raw TSV using positional extraction, correctly re-joining wrapped cells and excluding page furniture.
- `data-cleansing`: Normalize known data errors, parse structured fields (parcels, counts, aliases, sections, stages), auto-fix obvious issues and flag ambiguous ones.
- `case-merging`: Link related approvals into project families by similarity, anchor each family on its latest approval, and derive append-friendly project_id.
- `history-graph`: Emit a per-project JSON history graph and render it in a browser viewer.

### Modified Capabilities
<!-- None — no existing specs in openspec/specs/. -->

## Impact

- New Python 3 pipeline (pymupdf for extraction; pure logic for cleanse/merge; agent-assisted where judgement is required). Scripts under `tools/` or a small package; adapters (PDF/TSV/JSON I/O, viewer) kept separate from pure logic.
- Source data: the provided PDF (201 pages) plus the extracted `pdf_text.txt` used during exploration as a reference artifact.
- **POC-gated scope (provisional)**: positional parsing reliability, the 0.7/0.5–0.7 similarity thresholds, feature weights, and anchor tie-breaking are starting points validated by the initial POC against known clusters (中華工程 寶清段, 永昌段三小段159, 逸仙段二小段151, 金華段四小段513-3). Findings may adjust these.
- No external services; runs offline. Does not modify the source PDF.