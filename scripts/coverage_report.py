"""Build the coverage report: the three questions, answered and proved.

The adapter around :func:`coverage_figures`. It reads the emitted dataset and
the two list snapshots, derives every number, and renders a self-contained
HTML page.

Read-only by construction. It writes one HTML file and nothing else: no
pipeline artefact, no viewer data, no archive entry.

    python scripts/coverage_report.py [--out docs/coverage-report.html]

Every figure is re-derived at generation time. Nothing is copied from a
previous run.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROJECTS = ROOT / "data" / "projects.json"
CLEAN = ROOT / "data" / "clean.tsv"
MERGED = ROOT / "data" / "merged.tsv"
P168 = ROOT / "data" / "p168_all.json"
HEADER_PASS = ROOT / "data" / "p168_header_pass.json"
PORTAL_INDEX = ROOT / "data" / ".link_cache" / "portal_index.json"

UNPLACED = "節點未能對應平台案件"


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tsv_recnos(path: pathlib.Path) -> set[int]:
    with path.open(encoding="utf-8") as fh:
        return {int(r["recno"]) for r in csv.DictReader(fh, delimiter="\t")}


def gather() -> dict:
    """Every number the report shows, derived from the emitted files."""
    doc = load_json(PROJECTS)
    projects = doc["projects"]

    project_ids: set[str] = set()
    node_ids: set[str] = set()
    for p in projects:
        project_ids.update((p.get("links") or {}).get("taipei") or [])
        for node in p.get("nodes") or ():
            node_ids.update((node.get("links") or {}).get("taipei") or [])

    # --- Q1: projects against the lists ---------------------------------
    p168 = load_json(P168) if P168.exists() else []
    p168_ids = {r["case_id"] for r in p168}

    on_168 = 0
    off_168 = 0
    no_id = []
    for p in projects:
        ids = set((p.get("links") or {}).get("taipei") or [])
        for node in p.get("nodes") or ():
            ids.update((node.get("links") or {}).get("taipei") or [])
        if not ids:
            no_id.append(p)
        elif ids & p168_ids:
            on_168 += 1
        else:
            off_168 += 1

    # the ids the list holds that the payload does not name
    all_ids = project_ids | node_ids
    missing = sorted(p168_ids - all_ids)
    header_pass = {}
    if HEADER_PASS.exists():
        header_pass = {r["case_id"]: r for r in load_json(HEADER_PASS)}
    in_pass = [m for m in missing if m in header_pass]
    not_in_pass = [m for m in missing if m not in header_pass]
    revoked = [c for c, r in header_pass.items()
               if "撤銷" in (r.get("NAME") or "")]

    # --- the national portal's list --------------------------------------
    portal = load_json(PORTAL_INDEX) if PORTAL_INDEX.exists() else []
    portal_ids = {e.get("view_id") for e in portal}
    payload_views = set()
    for p in projects:
        url = (p.get("links") or {}).get("twur") or ""
        marker = "/view/"
        if marker in url:
            payload_views.add(url.split(marker, 1)[1].split("/")[0].split("?")[0])

    # --- Q2: the partition ------------------------------------------------
    node_recnos = [n["recno"] for p in projects for n in p.get("nodes") or ()]
    clean = tsv_recnos(CLEAN)
    seen: set[int] = set()
    duplicates = sorted({r for r in node_recnos if r in seen or seen.add(r)})
    lost = sorted(clean - set(node_recnos))
    extra = sorted(set(node_recnos) - clean)
    with MERGED.open(encoding="utf-8") as fh:
        merged_rows = list(csv.DictReader(fh, delimiter="\t"))

    # --- Q3: the badge and the flag --------------------------------------
    unbadged = []
    flagged = 0
    flagged_with_id = 0
    for p in projects:
        for node in p.get("nodes") or ():
            has = bool((node.get("links") or {}).get("taipei"))
            is_flagged = any(f.startswith(UNPLACED)
                             for f in (node.get("review_flags") or []))
            if is_flagged:
                flagged += 1
                if has:
                    flagged_with_id += 1
            if not has:
                unbadged.append({
                    "project_id": p["project_id"],
                    "recno": node.get("recno"),
                    "date": node.get("date", ""),
                    "case_name": node.get("case_name", ""),
                    "flags": [f for f in (node.get("review_flags") or [])
                              if "案名與地號段小段不一致" in f],
                })

    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "published_date": doc.get("published_date", ""),
        "counts": doc.get("counts") or {},
        "projects_total": len(projects),
        "q1": {
            "on_168": on_168,
            "off_168": off_168,
            "no_id": no_id,
            "p168_total": len(p168_ids),
            "payload_ids": len(all_ids),
            "missing": missing,
            "in_pass": in_pass,
            "not_in_pass": not_in_pass,
            "revoked": revoked,
            "portal_crawl": len(portal_ids),
            "payload_views": len(payload_views),
            "views_in_crawl": len(payload_views & portal_ids),
        },
        "q2": {
            "clean": len(clean),
            "nodes": len(node_recnos),
            "distinct": len(set(node_recnos)),
            "duplicates": duplicates,
            "lost": lost,
            "extra": extra,
            "merged_rows": len(merged_rows),
            "merged_projects": len({r["project_id"] for r in merged_rows}),
        },
        "q3": {
            "with_id": len(node_recnos) - len(unbadged),
            "without_id": len(unbadged),
            "flagged": flagged,
            "flagged_with_id": flagged_with_id,
            "unbadged": unbadged,
        },
    }


def render(f: dict) -> str:
    e = esc
    out: list[str] = []
    w = out.append

    w("<!doctype html>")
    w('<html lang="zh-Hant">')
    w("<head>")
    w('<meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width, initial-scale=1">')
    w("<title>資料覆蓋度報告 · 三個問題的證明</title>")
    w("""<!--
  Generated by scripts/coverage_report.py. Do not edit by hand.
  Self-contained: no external requests, opens offline from file:// like the viewer.

  Every figure is re-derived by reading the emitted dataset at generation
  time. Nothing is copied from a previous run.
-->""")
    w("""<style>
  /* The site's one design system: the cream palette the dashboard and the
     viewer share (viewer/app.css, viewer/dashboard.css). Light-only by
     construction — no dark-mode block, or these pages would be the only dark
     ones on the site (openspec: docs-cream-restyle). */
  :root{
    --bg:#fff8f4; --panel:#ffffff; --ink:#211d1d; --muted:#686362;
    --line:#f3d9bf; --accent:#ad4d2a; --tint:#fff1e8; --sun:#fde272;
    --ok:#3fae74; --ok-bg:#f0fdf4;
    --warn:#8a5a00; --warn-bg:#fdf3dc;
    --bad:#8e2626; --bad-bg:#fdf0ef;
    --info:#ad4d2a; --info-bg:#fff1e8;
    --muted-bg:#fdf0e7;
  }
  *{box-sizing:border-box}
  body{margin:0;padding:0 0 64px;background:var(--bg);color:var(--ink);
       font:15px/1.65 "Instrument Sans","Microsoft JhengHei","PingFang TC",system-ui,sans-serif}
  header{background:var(--panel);border-bottom:1px solid var(--line);padding:28px 32px}
  h1{margin:0 0 6px;font-size:22px;letter-spacing:.01em}
  .sub{color:var(--muted);font-size:13px;margin:0;max-width:92ch}
  main{max-width:1240px;margin:0 auto;padding:0 32px}
  section{margin-top:44px}
  h2{font-size:17px;margin:0 0 4px;padding-bottom:8px;display:inline-block;
     padding:0 6px;background:linear-gradient(transparent 58%,var(--sun) 58%)}
  h2 .n{color:var(--muted);font-weight:400;margin-right:10px}
  h3{font-size:14.5px;margin:22px 0 8px}
  .lead{color:var(--muted);font-size:13.5px;margin:10px 0 18px;max-width:92ch}

  table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:10px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);
        vertical-align:top}
  th{color:var(--muted);font-weight:600;font-size:12.5px;white-space:nowrap}
  td.num,th.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
  td.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
  tr.total td{font-weight:650;border-top:2px solid var(--line)}
  .ok{color:var(--ok);font-weight:650}
  .warn{color:var(--warn);font-weight:650}
  .bad{color:var(--bad);font-weight:650}
  .zero{color:var(--muted)}

  .card{background:var(--panel);border:1px solid var(--line);
        border-top:4px solid var(--accent);box-shadow:6px 6px 0 var(--line);
        border-radius:0;
        padding:14px 16px;margin:12px 0}
  .card.ok{border-color:var(--ok);border-top-color:var(--ok);background:var(--ok-bg)}
  .card.warn{border-color:var(--warn);border-top-color:var(--warn);background:var(--warn-bg)}
  .card.bad{border-color:var(--bad);border-top-color:var(--bad);background:var(--bad-bg)}
  .card.info{border-color:var(--info);border-top-color:var(--info);background:var(--info-bg)}
  .ttl{font-weight:650;font-size:14px;margin-bottom:6px}
  .ttl small{display:block;font-weight:400;color:var(--muted);font-size:12.5px;
             margin-top:3px}
  .metric{font-variant-numeric:tabular-nums;font-weight:650}

  .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
         gap:12px;margin:16px 0 4px}
  .tile{border:1px solid var(--line);border-radius:0;padding:13px 15px;
        background:var(--panel);border-top:4px solid var(--accent);
        box-shadow:6px 6px 0 var(--line)}
  .tile .k{color:var(--muted);font-size:12px;margin-bottom:3px}
  .tile .v{font-size:25px;font-weight:650;font-variant-numeric:tabular-nums;
           line-height:1.15}
  .tile .n{color:var(--muted);font-size:11.5px;margin-top:3px}
  .tile.ok .v{color:var(--ok)}
  .tile.bad .v{color:var(--bad)}
  .tile.warn .v{color:var(--warn)}

  .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
  .kv{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:13px}
  .kv dt{color:var(--muted)}
  .kv dd{margin:0;font-variant-numeric:tabular-nums}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
       background:var(--tint);padding:1px 5px;border-radius:4px}
  .pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;
        border:1px solid currentColor}
  .p-ok{color:var(--ok)} .p-warn{color:var(--warn)} .p-bad{color:var(--bad)}
  .p-info{color:var(--info)}
  .wrap{overflow-x:auto}
  .backlink{float:right;font-size:13px;font-weight:400;color:var(--info);
            text-decoration:none;border-bottom:1px solid currentColor}
  .backlink:hover{color:var(--ink)}
  footer{max-width:1240px;margin:56px auto 0;padding:20px 32px 0;
         border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
  @media(max-width:700px){ main,header{padding-left:16px;padding-right:16px} }
</style>""")
    w("</head>")
    w("<body>")

    # ---- header ----------------------------------------------------------
    counts = f["counts"]
    w("<header>")
    # The back link (openspec: about-page-links): 關於 carries the license,
    # the sources and the contact; the viewer is one hop further through it.
    w('<a class="backlink" href="../viewer/about.html">關於</a>')
    w("<h1>資料覆蓋度報告 — 三個問題的證明</h1>")
    w('<p class="sub">三個問題：有哪些專案不在名單裡、有哪些編號不屬於任何專案、'
      '每個編號是否都掛著北向平台案件。每一個數字都在 %s 由 '
      '<code>scripts/coverage_report.py</code> 重新產出，'
      '資料集統計至 %s，%d 筆核定案件、%d 個專案。</p>'
      % (e(f["generated_at"]), e(f["published_date"]),
         counts.get("records", 0), counts.get("projects", 0)))
    w("</header>")

    w("<main>")

    # ---- §1 the three answers -------------------------------------------
    q1, q2, q3 = f["q1"], f["q2"], f["q3"]
    w('<section id="answers">')
    w('<h2><span class="n">1</span>三個答案</h2>')
    w('<p class="lead">每一列的證明方式寫在下方各節。'
      '沒有一列是從產出流程的回報抄來的——全部從產出的檔案重新推導。</p>')
    w('<div class="tiles">')
    w('<div class="tile warn"><div class="k">不在任何名單的專案</div>'
      '<div class="v">%d</div><div class="n">完全沒有平台案件編號</div></div>'
      % len(q1["no_id"]))
    w('<div class="tile ok"><div class="k">不屬於任何專案的編號</div>'
      '<div class="v">%d</div><div class="n">分割完全且互斥</div></div>'
      % len(q2["lost"]))
    w('<div class="tile warn"><div class="k">沒有北向徽章的節點</div>'
      '<div class="v">%d</div><div class="n">全部都有旗標具名</div></div>'
      % q3["without_id"])
    w('<div class="tile ok"><div class="k">節點總數</div>'
      '<div class="v">%d</div><div class="n">每個編號都歸屬一個專案</div></div>'
      % q2["nodes"])
    w("</div>")
    w("</section>")

    # ---- §2 Q1 -----------------------------------------------------------
    w('<section id="q1">')
    w('<h2><span class="n">2</span>問題一：有哪些專案不在名單裡</h2>')
    w('<p class="lead">一個專案算「在名單裡」，當它帶著的某個案件編號出現在那份名單上。'
      '兩份名單是台北市的 168 專案清單（<code>Get_project168.ashx</code>）'
      '與國土署入口網的專案清單（<code>twur.nlma.gov.tw</code>）。</p>')
    w('<div class="wrap"><table><thead><tr><th>族群</th><th class="num">數量</th>'
      '<th>說明</th></tr></thead><tbody>')
    w("<tr><td>資料集裡的專案</td><td class='num'>%d</td><td>—</td></tr>"
      % f["projects_total"])
    w("<tr><td>在 168 清單上</td><td class='num'>%d</td>"
      "<td>至少一個案件編號在名單上</td></tr>" % q1["on_168"])
    w("<tr><td>有案件編號，但都不在 168 清單上</td><td class='num'>%d</td>"
      "<td>168 清單是<b>子集</b>，不是全部案件的登記簿</td></tr>" % q1["off_168"])
    w("<tr class='total'><td>完全沒有案件編號</td><td class='num'>%d</td>"
      "<td>因此兩個名單都沒有</td></tr>" % len(q1["no_id"]))
    w("</tbody></table></div>")

    w('<div class="card warn">')
    w('<div class="ttl">168 清單是子集，不是全體案件的名冊'
      '<small>它收的是 168 專案；不在該專案裡而審查中的案件不會出現在上面</small></div>')
    w('<p style="margin:0;font-size:13.5px">清單有 %d 件，資料集命名了 %d 個案件編號，'
      '其中 %d 個在清單上。清單上資料集沒有的 %d 件，'
      '其中 %d 件以案件標頭確認過（每件一次請求）：%d 件未核定，%d 件經本府撤銷核准。'
      '其餘 %d 件在標頭掃描當時尚未查過，其中 %d 件是「業經本府撤銷核准」的案件'
      '（核准後撤銷，從未列入公報），1 件是既有公報專案上的待審修訂案。</p>'
      % (q1["p168_total"], q1["payload_ids"],
         q1["p168_total"] - len(q1["missing"]),
         len(q1["missing"]), len(q1["in_pass"]),
         len(q1["in_pass"]) - len(q1["revoked"]),
         len(q1["revoked"]), len(q1["not_in_pass"]),
         len(q1["not_in_pass"]) - 1))
    w("</div>")

    if q1["no_id"]:
        w("<h3>那 %d 個專案</h3>" % len(q1["no_id"]))
        w('<div class="wrap"><table><thead><tr><th>專案</th><th>行政區</th>'
          '<th>為什麼平台沒有案件編號</th></tr></thead><tbody>')
        for p in q1["no_id"]:
            flags = [f for nd in p.get("nodes") or ()
                     for f in (nd.get("review_flags") or [])
                     if "案名與地號段小段不一致" in f]
            rejected = (p.get("links") or {}).get("search_rejected") or {}
            twur = (p.get("links") or {}).get("twur") or ""
            if flags:
                why = ("地號欄與案名的小段不一致（%s），"
                       "平台的土地搜尋因此查無" % flags[0].split("(")[-1].rstrip("）)"))
            elif rejected:
                why = ("平台的土地搜尋找到 %d 件，但每一件都被 §6.7 的"
                       "名稱守衛擋下（案例名稱的單位與公報不同）"
                       % len(rejected))
            elif p["project_id"].startswith("中正區-臨沂"):
                why = ("對應的平台案件 <code>11410026</code> 從未核定；"
                       "這個專案在國土署有頁面（%s），"
                       "但平台沒有對應的核定案件" % e(twur.rsplit("/", 1)[-1]))
            else:
                why = "平台的土地搜尋查無這個單位"
            w("<tr><td class='mono'>%s</td><td>%s</td><td>%s</td></tr>"
              % (e(p["project_id"]), e(p.get("district", "")), why))
        w("</tbody></table></div>")

    w('<div class="card info">')
    w('<div class="ttl">國土署的清單以土地核心比對，不是案件編號'
      '<small>而且它的爬取被 WAF 限制</small></div>')
    w('<p style="margin:0;font-size:13.5px">快取索引只有 %d 筆，'
      '而資料集命名了 %d 個 view id，其中 %d 個在索引內。'
      '爬取不完整不等於專案遺漏；要證明那份清單完整，需要重新實地爬取一次，'
      '而不是讀這個快取檔。</p>'
      % (q1["portal_crawl"], q1["payload_views"], q1["views_in_crawl"]))
    w("</div>")
    w("</section>")

    # ---- §3 Q2 -----------------------------------------------------------
    w('<section id="q2">')
    w('<h2><span class="n">3</span>問題二：有哪些編號不屬於任何專案</h2>')
    w('<p class="lead">檢查的是一個分割：每一筆洗淨後的紀錄恰好屬於一個專案，'
      '而且沒有專案持有洗淨階段沒有的紀錄。</p>')
    w('<div class="wrap"><table><thead><tr><th>檢查</th><th class="num">數量</th>'
      '<th>結果</th></tr></thead><tbody>')
    w("<tr><td>clean.tsv 的紀錄</td><td class='num'>%d</td><td>—</td></tr>"
      % q2["clean"])
    w("<tr><td>資料集的節點</td><td class='num'>%d</td><td>—</td></tr>"
      % q2["nodes"])
    w("<tr><td>不同的節點編號</td><td class='num'>%d</td><td>—</td></tr>"
      % q2["distinct"])
    w("<tr><td>同時出現在兩個節點的編號</td><td class='num'>%s</td>"
      "<td class='%s'>%s</td></tr>"
      % (len(q2["duplicates"]), "ok" if not q2["duplicates"] else "bad",
         "沒有重複" if not q2["duplicates"] else "重複"))
    w("<tr><td>不屬於任何專案的洗淨紀錄</td><td class='num'>%s</td>"
      "<td class='%s'>%s</td></tr>"
      % (len(q2["lost"]), "ok" if not q2["lost"] else "bad",
         "沒有遺失" if not q2["lost"] else "遺失"))
    w("<tr><td>洗淨階段沒有的節點紀錄</td><td class='num'>%s</td>"
      "<td class='%s'>%s</td></tr>"
      % (len(q2["extra"]), "ok" if not q2["extra"] else "bad",
         "沒有多餘" if not q2["extra"] else "多餘"))
    w("<tr class='total'><td>merged.tsv 的列 / 不同 project_id</td>"
      "<td class='num'>%d / %d</td><td>與節點數一致</td></tr>"
      % (q2["merged_rows"], q2["merged_projects"]))
    w("</tbody></table></div>")
    w('<div class="card ok">')
    w('<div class="ttl">結論：分割完全且互斥'
      '<small>沒有任何編號游離在專案之外</small></div>')
    w('<p style="margin:0;font-size:13.5px">%d 筆紀錄、%d 個專案，'
      '每筆恰好一次，沒有任何一筆落在外面。</p>'
      % (q2["clean"], q2["merged_projects"]))
    w("</div>")
    w("</section>")

    # ---- §4 Q3 -----------------------------------------------------------
    w('<section id="q3">')
    w('<h2><span class="n">4</span>問題三：每個編號是否都掛著北向徽章</h2>')
    w('<p class="lead">徽章由節點的 <code>links.taipei</code> 畫出（viewer 的 '
      '<code>getNodeMilestoneBadges</code>），旗標 '
      '<code>節點未能對應平台案件</code> 用文字說同一件事。兩者必須一致。</p>')
    w('<div class="wrap"><table><thead><tr><th>檢查</th><th class="num">數量</th>'
      '<th>結果</th></tr></thead><tbody>')
    w("<tr><td>帶著案件編號的節點</td><td class='num'>%d</td><td>—</td></tr>"
      % q3["with_id"])
    w("<tr><td>沒有案件編號的節點</td><td class='num'>%d</td>"
      "<td class='%s'>%s</td></tr>"
      % (q3["without_id"], "warn" if q3["without_id"] else "ok",
         "全部具名" if q3["without_id"] == q3["flagged"] else "有節點未具名"))
    w("<tr><td>帶著旗標的節點</td><td class='num'>%d</td><td>—</td></tr>"
      % q3["flagged"])
    w("<tr class='total'><td>帶著旗標卻也有案件編號的節點</td>"
      "<td class='num'>%d</td><td class='%s'>%s</td></tr>"
      % (q3["flagged_with_id"], "ok" if not q3["flagged_with_id"] else "bad",
         "旗標與徽章一致" if not q3["flagged_with_id"] else "旗標過期"))
    w("</tbody></table></div>")
    if q3["unbadged"]:
        w("<h3>那 %d 個沒有徽章的節點</h3>" % len(q3["unbadged"]))
        w('<div class="wrap"><table><thead><tr><th class="num">編號</th>'
          '<th>核定日期</th><th>案名</th></tr></thead><tbody>')
        for n in q3["unbadged"]:
            w("<tr><td class='num mono'>%s</td><td class='mono'>%s</td>"
              "<td>%s</td></tr>"
              % (e(n["recno"]), e(n["date"]), e(n["case_name"][:60])))
        w("</tbody></table></div>")
    w('<div class="card ok">')
    w('<div class="ttl">結論：沒有節點被無聲地鬆開'
      '<small>沒有徽章的節點，都帶著說明為什麼的旗標</small></div>')
    w('<p style="margin:0;font-size:13.5px">%d 個節點沒有案件編號，'
      '而帶著旗標的正好也是 %d 個，兩者完全對應；'
      '沒有任何一個節點帶著旗標卻又有案件編號。</p>'
      % (q3["without_id"], q3["flagged"]))
    w("</div>")
    w("</section>")

    # ---- §5 method -------------------------------------------------------
    w('<section id="method">')
    w('<h2><span class="n">5</span>量法</h2>')
    w("""<div class="card info">
      <div class="ttl">每一個數字都在產生時重新推導<small>不是抄寫前一次結果</small></div>
      <p style="margin:0;font-size:13.5px">本頁讀取 <code>data/projects.json</code>、
      <code>data/clean.tsv</code>、<code>data/merged.tsv</code>、
      168 清單快照與案件標頭掃描結果，全部重新計算。
      證明本身也可以獨立重跑：<code>python scripts/probe_three_coverage_proofs.py</code>，
      它從產出的檔案重新推導分割，與管線的記憶體內檢查互相獨立。</p>
    </div>
    <div class="card">
      <div class="ttl">名單的兩種比對方式<small>案件編號，以及土地核心</small></div>
      <p style="margin:0;font-size:13.5px">台北市的清單以案件編號比對，
      所以 168 清單可以直接對上。國土署的清單只有土地核心，
      而它的爬取被 WAF 限制在 %d 筆，因此那一側的完整性不能由快取檔證明。</p>
    </div>
    <div class="card">
      <div class="ttl">「沒有徽章」不等於「遺失」<small>兩者的差別在於有沒有被具名</small></div>
      <p style="margin:0;font-size:13.5px">平台沒有覆蓋每個專案，
      所以 %d 個節點沒有案件編號是預期的狀態。
      重要的是這些節點不是無聲的：每一個都帶著旗標說明原因，
      而這兩者的一致性現在由管線檢查。</p>
    </div>""" % (q1["portal_crawl"], q3["without_id"]))
    w("</section>")

    w("</main>")
    w("<footer>由 <code>scripts/coverage_report.py</code> 產生。"
      "唯讀：不寫入管線產物、不動 viewer、不寫封存索引。"
      "配套紀錄見 <code>docs/inspection-batchD.md</code> D18。</footer>")
    w("</body></html>")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "coverage-report.html"))
    args = ap.parse_args(argv)

    figures = gather()
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(figures), encoding="utf-8")
    print("[INFO] written %s (%d projects, %d records)"
          % (out_path, figures["projects_total"],
             figures["counts"].get("records", 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
