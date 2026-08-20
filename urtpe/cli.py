"""Command-line entry point for the urban-renewal PDF pipeline."""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from urtpe import cleanse as cleanse_mod
from urtpe import extract as extract_mod
from urtpe import graph as graph_mod
from urtpe import io as io_mod
from urtpe import merge as merge_mod
from urtpe import report as report_mod
from urtpe import viewer as viewer_mod


def _run(pdf: str, outdir: str, no_tsv: bool, viewer_dir: str | None = None) -> None:
    raw_recs = extract_mod.to_raw_records(extract_mod.extract_pdf(pdf))
    if not raw_recs:
        print("未解析到任何記錄", file=sys.stderr)
        sys.exit(1)

    clean = cleanse_mod.cleanse_all(raw_recs)

    projects = merge_mod.merge(clean)

    report = report_mod.review_report(
        raw_recs, clean, projects,
        link_threshold=merge_mod.LINK_THRESHOLD,
        flag_threshold=merge_mod.FLAG_THRESHOLD,
    )
    io_mod.write_text(f"{outdir}/review_report.txt", report)

    meta = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": pdf,
        "thresholds": {"link": merge_mod.LINK_THRESHOLD, "flag": merge_mod.FLAG_THRESHOLD},
    }
    doc = graph_mod.build_graph_document(projects, meta)
    io_mod.write_json(f"{outdir}/projects.json", doc)

    if not no_tsv:
        io_mod.write_text(f"{outdir}/raw.tsv", io_mod.raw_to_tsv(raw_recs))
        io_mod.write_text(f"{outdir}/clean.tsv", io_mod.clean_to_tsv(clean))
        io_mod.write_text(f"{outdir}/merged.tsv", io_mod.merged_to_tsv(projects))
        print(f"raw.tsv: {len(raw_recs)} 筆")
        print(f"clean.tsv: {len(clean)} 筆")
        print(f"merged.tsv: {len(clean)} 筆 / {len(projects)} 專案")

    total = sum(len(p.members) for p in projects)
    multi = [p for p in projects if len(p.members) > 1]
    print(f"專案: {len(projects)} 個 (多筆 {len(multi)} 個) / 記錄合計 {total} 筆")
    print(f"review_report.txt, projects.json 已輸出至 {outdir}")

    if viewer_dir:
        path = viewer_mod.write_projects_js(viewer_dir, doc)
        print(f"viewer 資料已輸出至 {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="臺北市都市更新核定案件 PDF 管線")
    parser.add_argument("pdf", help="來源 PDF 路徑")
    parser.add_argument("-o", "--outdir", default="data", help="輸出目錄 (預設 data)")
    parser.add_argument("--no-tsv", action="store_true", help="不輸出 TSV（僅 JSON 圖）")
    parser.add_argument("--viewer", metavar="DIR", default=None,
                        help="同步輸出 viewer/projects.data.js 至指定目錄")
    args = parser.parse_args(argv)

    _run(args.pdf, args.outdir, args.no_tsv, args.viewer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())