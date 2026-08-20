## 1. POC: Validate extraction and calibrate similarity

- [x] 1.1 Write a probe that extracts word coordinates from the source PDF and verifies positional parsing: 1,419 records, 7 column bands, wrapped cells re-joined (嘉興發股份有限公司), page headers/footers excluded
- [x] 1.2 Assemble a ground-truth fixture of known clusters from exploration: 中華工程 寶清段 (4 units), 永昌段三小段159 (6 records), 逸仙段二小段151 (A/B sections), 金華段四小段513-3 (11↔13筆 bridge), 立農段五小段329, 東星大樓基地 (2 records)
- [x] 1.3 Calibrate feature weights and the 0.7 / 0.5–0.7 thresholds against the ground-truth fixture; record findings in the change and update design.md thresholds if POC invalidates them

## 2. Test-writing

- [x] 2.1 Write domain unit tests for cleansing: 松化區→松山區, 計劃→計畫, ㄧ→一, 權利變換案 normalization, ROC→ISO date, parcel/count/alias/anchor/區段/stage/track derivation, ambiguous-review flagging
- [x] 2.2 Write domain unit tests for merging: stage-approval links, section-split merge, coverage-change bridge, renumbering-alias bridge, named-anchor link, borderline (0.5–0.7) flagged not linked, singletons separate
- [x] 2.3 Write domain unit tests for anchoring: newest-by-核定日期 anchor, deterministic tie-break, project_id slug stability across revisions, coverage-change re-anchoring, independence from 編號
- [x] 2.4 Write domain unit tests for the graph: node/edge validity, one node per record in exactly one project, edges converge on the anchor, section branches represented, projects.json is schema-valid
- [x] 2.5 Write adapter unit tests for extraction: 1,419 rows, header/footer exclusion, wrapped-cell rejoin, parse-error marker for non-conforming records
- [x] 2.6 Write acceptance/E2E tests for each user-visible requirement: full PDF → raw/clean/merged TSV + review report + projects.json; report completeness; viewer renders the dataset

## 3. Adapter: PDF extraction to raw.tsv

- [x] 3.1 Implement positional extraction adapter (pymupdf words → column x-bands → records anchored on 編號→日期 lines → wrapped-cell rejoin)
- [x] 3.2 Implement raw.tsv writer: page furniture stripped, parse-error marker column, verbatim cell values
- [x] 3.3 Implement the extraction report listing non-conforming records with 編號 and reason

## 4. Domain: cleansing

- [x] 4.1 Implement normalization rules (district/variant/date corrections) and field derivation (行政區, 段X小段, first parcel, parcel set, 原地號 aliases, 筆數, 原N筆, named anchor, 區段, stage, track)
- [x] 4.2 Implement auto-fix-vs-flag classification producing the review/flag column with reasons; no silent overwrite of ambiguous fields
- [x] 4.3 Implement the review report writer (auto-fixes + flagged records, traceable by 編號) and clean.tsv emission

## 5. Domain: similarity merge

- [x] 5.1 Implement feature extraction and weighted similarity scoring with threshold bands (link ≥ 0.7, flag 0.5–0.7), corroboration-only implementer
- [x] 5.2 Implement clustering into families (connected components) and borderline-pair collection for the review report
- [x] 5.3 Implement anchor selection (newest 核定日期, tie-break closest to 編號 1) and project_id slugging from the anchor's normalized name-core
- [x] 5.4 Implement merged.tsv emission: project_id, unit fields, is_current flag, review flags, source 編號 preserved

## 6. Domain: history graph and viewer

- [x] 6.1 Implement graph construction: nodes (編號, ISO date, stage, track, 區段, is_current) and edges (revision chains, section branches, tracks) converging on the anchor; emit projects.json against the declared schema
- [x] 6.2 Implement the static browser viewer (HTML/JS) loading projects.json: per-project timeline, anchor highlighted, tracks visually distinct, 區段 annotations, browse/search across families
- [x] 6.3 Implement the CLI orchestrator that runs all stages end-to-end and produces raw/clean/merged TSV, review report, and projects.json

## 7. Acceptance and verification

- [x] 7.1 Run the full pipeline on the source PDF and verify outputs against specs: 1,419 rows, ground-truth clusters merge correctly, anchors correct, graph converges
- [x] 7.2 Run the test suite green and confirm the test gate: every task in group 2 checked before implementation tasks complete
- [x] 7.3 Sanity-check the review report (松化區 fix present, record-500 district mismatch flagged) and viewer rendering on the full dataset
