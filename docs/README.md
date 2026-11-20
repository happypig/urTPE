# docs/ — Document catalogue

This index answers "which document?" for common questions. Every entry states the
document's status: **current**, **generated**, **historical** or **temporary**.

---

## Current — pipeline operation

| Document | Purpose | Link stability |
|---|---|---|
| `pipeline/etl_process.md` | Full PDF-to-publication runbook (§11). Keeps polling, ingestion, bounded repair, report generation, path-limited commit and deployment verification separate. | Section numbers stable; append only. |
| `pipeline/cli_flow_v2.md` | Current CLI and link-discovery flow. Line numbers are cited externally. | Append only; do not insert above. |
| `pipeline/domain_model.md` | Entity and Mermaid model in two blocks: record→graph path, and gazette cadence layer (archive, ledger, poller, change sets). | Current-payload facts carry `data-doc-field` markers; regenerate with `sync_domain_model.py`. |
| `pipeline/sync_architecture.md` | PDF-heartbeat + two-portals sync design. | Design exploration; companion to `portals/facts_2_portals.md`. |
| `pipeline/cli_enhancement.md` | Forward design for portal-discovery CLI consolidation (library-first). Retire when OpenSpec change lands. | Marked current; superseded by spec on landing. |

---

## Current — portal references

| Document | Purpose | Link stability |
|---|---|---|
| `portals/facts_2_portals.md` | Portal reference: endpoints, field maps, open issues, priorities. Points to `portals/portal_operations_log.md` for dated narratives. | Table of contents and § anchors stable. |
| `portals/portal_operations_log.md` | Append-only operational record. Anchors `§6.x` and `§16–§19` are preserved for citations. | **Append only**; new sessions append at the bottom. |
| `portals/urotpe_api.md` | `gis.uro.taipei /ashx/` API inventory: 40 endpoints, 37 live, 3 dead, 5 used by pipeline. | Inventory is a dated probe; cross-references `portals/urotpe_district_pages.md`. |
| `portals/urotpe_district_pages.md` | `uro.gov.taipei cp.aspx` district case tables: 12 pages, 3,655 rows, 3,651 IDs, four conflicting IDs, screening results. | Dated measurements; not a live contract. |
| `portals/urotpe_api_vs_pdf.md` | Comparison of API-derived data against PDF gazette records. | Dated comparison. |
| `portals/final_results_json_api.md` | Detailed JSON API endpoint documentation and merge findings. | Dated probe results. |
| `portals/gap_after_json_api.md` | Gaps between API data and pipeline needs. | Dated. |

---

## Current — viewer design

| Document | Purpose | Link stability |
|---|---|---|
| `viewer/viewer-UX.md` | Viewer improvement backlog, numbered entries (`viewer-UX §N`) with problem, design, trade-offs, spec impact. | Append; do not renumber. |
| `viewer/viewer_sort_rules.md` | Decision record for sort order and cross-row filters. | Decision record; append only. |
| `viewer/sorting_connecting_rules.md` | Sorting and graph-connection rules. | Decision record. |
| `viewer/DashboardNUXUI.md` | Dashboard NUX/UI investigation with three open items. | Investigation record. |
| `viewer/graph-tabs-decision.html` | Tab-design decision page. | Static page. |

---

## Current — findings and decisions

| Document | Purpose | Link stability |
|---|---|---|
| `inspections/inspection.md` | Master inspection board: state rows, pointers to batch documents. | Index; append state rows only. |
| `inspections/inspection-batchBC.md` | Batch B (residuals) and Batch C (post-viewer-UX gaps), integrated plan, appendices. | Fixed collection. |
| `inspections/inspection-batchD.md` | Batch D collected 2026-11-04 (orphan milestones, ghost-date echo, 國 key bug, badge bugs). | Fixed collection. |
| `inspections/inspection-batchE.md` | Batch E collected 2026-11-12 (compatibility ideographs, URL write-back, windowed list). | Fixed collection. |
| `inspections/inspection-batchF.md` | Batch F collected 2026-11-15 (membership predicate refactor, cross-route test, dependency, sibling walk, land cores, rejected-id limit, change findings, badge gaps, section labels). | Fixed collection. |
| `inspections/optimization.md` | Optimization board in three parts, in priority order: I the deterministic PDF and city-platform update cycle (U1–U8, A1–A7); II gen-1 membership measurements after D11 and S3/S5 (M1–M4); III the gen-2 viewer with one `project_uid` (O1–O7). Opens with the order, the dependencies and the decisions. | Recommendations; no change open. Item ids stay fixed. |

---

## Current — dataset audits

| Document | Purpose | Link stability |
|---|---|---|
| `audits/dataset_completeness_audit.md` | 2026-10-26 post-recovery audit: per-gazette binding, 718→709→694 viewer-count history, record churn. | Dated audit. |
| `audits/gazette-churn.md` | Generated project-count churn between gazettes. | Generated; do not hand-edit. |
| `audits/stranded-cache-dirs.md` | Generated orphan cache directory report. | Generated; do not hand-edit. |

---

## Generated HTML — keep exact paths

These paths are used by GitHub Pages, the Viewer and generation scripts. Do not move
them without updating all references.

| Path | Generator | Published to |
|---|---|---|
| `domain-model.html` | `sync_domain_model.py` | `https://happypig.github.io/urTPE/domain-model.html` |
| `etl_process.html` | `sync_etl_process.py` | `https://happypig.github.io/urTPE/etl_process.html` |
| `release-diff.html` | `scripts/release_diff_report.py` | `https://happypig.github.io/urTPE/release-diff.html` |
| `coverage-report.html` | `scripts/coverage_report.py` | `https://happypig.github.io/urTPE/coverage-report.html` |

All links are relative, so the chain also works from `file://`.

---

## Historical — moved after link audit

| Document | Origin | Why historical |
|---|---|---|
| `history/cli_flow.archive.md` | v1 CLI flow diagram, replaced by `pipeline/cli_flow_v2.md` | Dead; archived. |
| `history/facts_2_portals.archive.md` | v1 portal reference, superseded by `portals/facts_2_portals.md` | Closed. |
| `history/ingest_0924_review_report.txt` | One-shot ingestion review | Dated output. |
| `history/ingest_1001_rereview_report.txt` | One-shot re-review | Dated output. |
| `history/信義區永吉段四小段44地號等26筆.md` | Case-specific investigation | Dated output. |
| `portals/gap_after_json_api.md` | Gaps after JSON API discovery | Superseded by portal docs. |
| `portals/final_results_json_api.md` | Detailed endpoint docs | Partially superseded; some findings still relevant. |

---

## Temporary — local paste pads

| Document | Purpose |
|---|---|
| `temp.md` | Untracked scratchpad. |
| `temp.live_cluster_req.md` | Untracked scratchpad. |
| `temp_unjoined_projects.md` | Untracked scratchpad. |

**Do not commit** these files. Extract durable findings into a named document
instead.

---

## External state — documented by reference

| Resource | Location | Notes |
|---|---|---|
| Gazette archive, index, ledger, change sets | `D:\project\urtpe-gazettes\` | Shared by every process that imports `urtpe`. Override with `URTPE_ARCHIVE_ROOT` / `URTPE_LEDGER`. |
| `.link_cache` per-project caches | `data/.link_cache/` | Durable middle layer, not a disposable cache. Five backups exist. |
| Dashboard artifact | `https://claude.ai/artifact/3Xk8sdtJ1CqEhhy8B5Vbge` | Holds Venn diagram, field comparison, amendments, ID conflicts. External state; open for region ID lists under 100. |

---

## Link maintenance

- `pipeline/cli_flow_v2.md` line numbers are cited from outside (`openspec/changes/archive/2026-10-05-no-silent-data-loss/proposal.md` pins line 83). Do not reorganize it without updating external citations.
- `portals/portal_operations_log.md` section anchors (`§6.x`, `§16–§19`) are durable citations. Preserve them on any edit.
- Inspection batches use fixed identifiers (F1–F9, O1–O7). Do not renumber.
- Generated HTML files must keep their current paths for GitHub Pages and the Viewer.
- `inspections/inspection.md` is the master pointer. Update it when a batch is added.

---

## Adding a document

1. Choose the correct section above.
2. Add one row with purpose and link stability.
3. If the document is current, add its path to the table.
4. If the document is generated, add its generator and published URL.
5. Do not add temporary files.

---

## Versioning

This document uses no version number. Its date is the date of the last edit.

**Last updated:** 2026-11-20