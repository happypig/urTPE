"""Command-line entry point for the urban-renewal PDF pipeline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from urtpe import cleanse as cleanse_mod
from urtpe import extract as extract_mod
from urtpe import graph as graph_mod
from urtpe import io as io_mod
from urtpe import links as links_mod
from urtpe import merge as merge_mod
from urtpe import report as report_mod
from urtpe import viewer as viewer_mod
from urtpe.models import CleanRecord, Project

# Fallback mapping file path
FALLBACK_MAPPING_FILE = Path("data/taipei_case_ids.json")


def add_fallback_mapping(land_core: str, view_id: str, case_id: str) -> None:
    """Add a fallback mapping for land_core -> view_id + case_id."""
    mapping = {}
    if Path("data/taipei_case_ids.json").exists():
        try:
            mapping = json.loads(Path("data/taipei_case_ids.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if land_core not in mapping:
        mapping[land_core] = {"view_id": view_id, "case_ids": []}

    if case_id not in mapping[land_core]["case_ids"]:
        mapping[land_core]["case_ids"].append(case_id)

    mapping[land_core]["view_id"] = view_id

    Path("data/taipei_case_ids.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Write to file instead of printing to avoid encoding issues
    with open("add_mapping.log", "w", encoding="utf-8") as f:
        f.write(f"Added mapping: {land_core} -> view_id={view_id}, case_ids={mapping[land_core]['case_ids']}\n")


def _load_projects_from_js(js_path: str) -> tuple[list[Project], dict]:
    """Load projects and metadata from projects.data.js."""
    text = Path(js_path).read_text(encoding="utf-8")
    json_text = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    json_text = re.sub(r";\s*$", "", json_text)
    doc = json.loads(json_text)

    projects = []
    for pg in doc["projects"]:
        # Extract district from project_id as fallback: "{district}-{section}..."
        project_district = pg["project_id"].split("-")[0] if "-" in pg["project_id"] else ""
        members = []
        for node in pg["nodes"]:
            if (node.get("orphan") or node.get("recno", 0) < 0
                    or node.get("stage") == "孤兒節點"):
                continue
            # Fallback to project-level district if node lacks it
            node_district = node.get("district", "") or project_district
            node_district_land = node.get("district_land", "") or node_district
            
            # Derive iso_date: graph.py emits date=iso_date, so node.date may
            # already be ISO (YYYY-MM-DD). Only ROC-format strings need conversion.
            node_date = node.get("date", "")
            node_iso_date = node.get("iso_date", "")
            if not node_iso_date and node_date:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", node_date):
                    node_iso_date = node_date  # already ISO — keep as-is
                else:
                    from urtpe.cleanse import roc_to_iso
                    iso, _ = roc_to_iso(node_date)
                    node_iso_date = iso or ""
            
            rec = CleanRecord(
                recno=node["recno"],
                date=node_date,
                iso_date=node_iso_date,
                ymd=tuple(node.get("ymd", (0, 0, 0))) if "ymd" in node else (0, 0, 0),
                district=node_district,
                district_land=node_district_land,
                name=node.get("case_name", node.get("name", "")),
                name_raw=node.get("name_raw", ""),
                land=node.get("land", ""),
                section=node.get("section", ""),
                first_parcel=node.get("first_parcel", ""),
                parcels=node.get("parcels", []),
                aliases=node.get("aliases", {}),
                land_count=node.get("land_count"),
                orig_count=node.get("orig_count"),
                named_anchor=node.get("named_anchor", ""),
                area_section=node.get("area_section", ""),
                stage=node.get("stage", ""),
                stage_index=node.get("stage_index", -1),
                track=node.get("track", ""),
                implementer=node.get("implementer", ""),
                planner=node.get("planner", ""),
                auto_fixes=node.get("auto_fixes", []),
                review_flags=node.get("review_flags", []),
            )
            # Restore optional emitted state so --from-js round-trips are
            # lossless even without --links (attach overwrites when it runs)
            if node.get("implementation"):
                rec.implementation = dict(node["implementation"])
            if node.get("links"):
                rec.links = dict(node["links"])
            members.append(rec)
        project = Project(
            project_id=pg["project_id"],
            anchor_recno=pg["anchor_recno"],
            members=members,
        )
        if pg.get("implementation"):
            project.implementation = dict(pg["implementation"])
        if pg.get("rewards"):
            project.rewards = dict(pg["rewards"])
        projects.append(project)

    meta = {
        "generated_at": doc.get("generated_at", ""),
        "source": doc.get("source", ""),
        "published_date": doc.get("published_date", ""),
        "thresholds": doc.get("thresholds", {"link": merge_mod.LINK_THRESHOLD, "flag": merge_mod.FLAG_THRESHOLD}),
    }
    return projects, meta


def _run(pdf: str, outdir: str, no_tsv: bool, viewer_dir: str | None = None, links: bool = False, from_js: str | None = None, fresh: bool = False, playwright: bool = False) -> None:
    # Load projects from JS (primary) or PDF
    if from_js:
        print(f"[INFO] Loading projects from {from_js}")
        projects, meta = _load_projects_from_js(from_js)
        raw_recs = []
        clean = []
        extract_meta = {"published_date": meta.get("published_date", "")}
    else:
        recs, extract_meta = extract_mod.extract_pdf_with_meta(pdf)
        raw_recs = extract_mod.to_raw_records(recs)
        if not raw_recs:
            print("[ERROR] No records parsed", file=sys.stderr)
            sys.exit(1)

        clean = cleanse_mod.cleanse_all(raw_recs)
        projects = merge_mod.merge(clean)
        meta = {
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": pdf,
            "thresholds": {"link": merge_mod.LINK_THRESHOLD, "flag": merge_mod.FLAG_THRESHOLD},
        }
        if "published_date" in extract_meta:
            meta["published_date"] = extract_meta["published_date"]

    # Run link discovery if requested
    link_results = {}
    if links:
        from urtpe.coverage import coverage_guard

        if playwright:
            print("[INFO] Running Playwright-based link discovery (experimental)...")
            discovery = links_mod.LinksDiscovery(cache_dir=f"{outdir}/.link_cache")
            # Coverage guard (§12 #1): abort a cache-wiping job before the
            # viewer can be emitted on the regressed state.
            with coverage_guard(Path(f"{outdir}/.link_cache"), [p.project_id for p in projects]):
                link_results = discovery.run(projects, fresh=fresh, use_playwright=True)
        else:
            print("[INFO] Running link discovery with fallback JSON mapping (recommended)...")
            discovery = links_mod.LinksDiscovery(cache_dir=f"{outdir}/.link_cache")
            with coverage_guard(Path(f"{outdir}/.link_cache"), [p.project_id for p in projects]):
                link_results = discovery.run(projects, fresh=fresh)
        discovery.write_crawl_log(link_results, f"{outdir}/crawl_log.tsv")
        resolved = sum(1 for r in link_results.values() if r.status != 'unresolved')
        unresolved = sum(1 for r in link_results.values() if r.status == 'unresolved')
        errors = sum(1 for r in link_results.values() if r.status == 'error')
        print(f"  Done: {resolved} resolved, {unresolved} unresolved, {errors} errors")

    report = report_mod.review_report(
        raw_recs, clean, projects,
        link_threshold=merge_mod.LINK_THRESHOLD,
        flag_threshold=merge_mod.FLAG_THRESHOLD,
    )
    io_mod.write_text(f"{outdir}/review_report.txt", report)

    doc = graph_mod.build_graph_document(projects, meta, link_results)
    io_mod.write_json(f"{outdir}/projects.json", doc)

    if not no_tsv and not from_js:
        io_mod.write_text(f"{outdir}/raw.tsv", io_mod.raw_to_tsv(raw_recs))
        io_mod.write_text(f"{outdir}/clean.tsv", io_mod.clean_to_tsv(clean))
        io_mod.write_text(f"{outdir}/merged.tsv", io_mod.merged_to_tsv(projects))
        print(f"raw.tsv: {len(raw_recs)} records")
        print(f"clean.tsv: {len(clean)} records")
        print(f"merged.tsv: {len(clean)} records / {len(projects)} projects")

    total = sum(len(p.members) for p in projects)
    multi = [p for p in projects if len(p.members) > 1]
    print(f"Projects: {len(projects)} (multi-record {len(multi)}) / Total records {total}")
    print(f"review_report.txt, projects.json written to {outdir}")

    if viewer_dir:
        path = viewer_mod.write_projects_js(viewer_dir, doc)
        print(f"Viewer data written to {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="臺北市都市更新核定案件 PDF 管線")
    parser.add_argument("pdf", nargs="?", default="", help="來源 PDF 路徑 (不需提供若使用 --from-js)")
    parser.add_argument("-o", "--outdir", default="data", help="輸出目錄 (預設 data)")
    parser.add_argument("--no-tsv", action="store_true", help="不輸出 TSV（僅 JSON 圖）")
    parser.add_argument("--viewer", metavar="DIR", default=None,
                        help="同步輸出 viewer/projects.data.js 至指定目錄")
    parser.add_argument("--links", action="store_true", help="啟用官方連結發現 (使用 fallback JSON 映射，推薦)")
    parser.add_argument("--playwright", action="store_true", help="使用 Playwright 自動化爬取 (實驗性，需正確的源資料)")
    parser.add_argument("--fresh", action="store_true", help="強制重新爬取入口網索引與快取頁面")
    parser.add_argument("--from-js", metavar="PATH", default=None,
                        help="從既有 projects.data.js 載入專案資料 (略過 PDF 解析)")
    parser.add_argument("--add-mapping-file", metavar="PATH", default=None,
                        help="從 JSON 文件新增 fallback 映射 (包含 land_core, view_id, case_id)")
    args = parser.parse_args(argv)

    if args.add_mapping_file:
        import json
        with open(args.add_mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        add_fallback_mapping(mapping_data['land_core'], mapping_data['view_id'], mapping_data['case_id'])
        return 0

    if not args.from_js and not args.pdf:
        parser.error("需要提供 PDF 路徑或使用 --from-js 指定 projects.data.js")

    _run(args.pdf or "", args.outdir, args.no_tsv, args.viewer, args.links, args.from_js, args.fresh, args.playwright)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())