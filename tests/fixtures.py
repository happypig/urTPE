"""Fixture helpers: a tiny sample PDF containing known records."""

from __future__ import annotations

import pymupdf

# Header words inserted as individual words so the extractor's furniture
# filter removes them, mirroring the real document. x positions align with
# the column bands below (日期 shares the date band, 單位 the planner band).
HEADER_WORDS = ["編號", "本府核定", "日期", "行政區", "案名", "地號", "實施者", "更新規劃", "單位"]
HEADER_XS = [25.0, 100.0, 110.0, 160.0, 240.0, 460.0, 675.0, 780.0, 790.0]


def build_sample_pdf(path: str, rows: list[tuple[int, str, str, str, str, str, str]]) -> None:
    """Write a PDF with the same column layout as the real document."""
    doc = pymupdf.open()
    page = doc.new_page(width=842, height=595)
    fontsize = 7
    page.insert_font(fontname="china-s")

    # Column x-bands mirroring BANDS in urtpe.extract. Tokens start inside
    # their band and stay within it at fontsize 7 (no cross-band overflow).
    xs = {"recno": 25.0, "date": 100.0, "district": 160.0,
          "name": 200.0, "land": 330.0, "implementer": 675.0, "planner": 780.0}

    y = 40.0
    page.insert_text((30.0, 30.0), "臺北市都市更新核定案件一覽表", fontsize=fontsize, fontname="china-s")
    page.insert_text((30.0, y), "統計至115/8/11止共1,419筆", fontsize=fontsize, fontname="china-s")
    y += 16.0
    for i, token in enumerate(HEADER_WORDS):
        page.insert_text((HEADER_XS[i], y), token, fontsize=fontsize, fontname="china-s")

    for (recno, date, district, name, land, imp, planner) in rows:
        y += 20.0
        for i, token in enumerate([str(recno), date, district, name, land, imp, planner]):
            page.insert_text((list(xs.values())[i], y), token, fontsize=fontsize, fontname="china-s")

    # Page furniture: footer page number bottom-right.
    page.insert_text((600.0, 580.0), "115", fontsize=fontsize, fontname="china-s")

    doc.save(path)
    doc.close()


SAMPLE_ROWS = [
    (1, "115/8/11", "中正區", "擬訂中正永昌159地號等113筆",
     "臺北市中正區永昌段三小段159、161、162地號等113筆", "○○公司", "○○規劃公司"),
    (2, "115/7/1", "中正區", "變更中正永昌159地號等113筆",
     "臺北市中正區永昌段三小段159、161、162地號等113筆", "○○公司", "○○規劃公司"),
    (3, "115/6/1", "中正區", "變更(第二次)中正永昌159地號等113筆",
     "臺北市中正區永昌段三小段159、161、162地號等113筆", "○○公司", "○○規劃公司"),
]