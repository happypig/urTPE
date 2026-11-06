"""Build the release-diff report: read each archived PDF, diff it, render HTML.

The adapter around :mod:`scripts.release_diff`. It reads every distinct archived
publication, merges it under the current reader, pairs the releases against
each other, and renders a self-contained HTML page.

Read-only by construction. It writes one HTML file and nothing else: no
pipeline artefact, no viewer data, no archive entry. The single-writer lock and
the ~23 MB emission diff are not touched.

    python scripts/release_diff_report.py [--out docs/release-diff.html]

The completion corpus for each release is every *other* archived publication,
so a 地號 cell the publisher truncated is completed from a sibling release
rather than reported as a missing record. That is the same rule the CLI uses
(``urtpe.cli._corpus_excluding``), and it is what makes the record counts
comparable across releases.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from release_diff import (  # noqa: E402
    ReleaseFamily,
    ReleaseRecord,
    diff_releases,
    publisher_link_for,
)
from urtpe import corpus as corpus_mod  # noqa: E402
from urtpe import cleanse as cleanse_mod  # noqa: E402
from urtpe import extract as extract_mod  # noqa: E402
from urtpe import merge as merge_mod  # noqa: E402
from urtpe import reconcile as reconcile_mod  # noqa: E402
from urtpe.ledger import normalize_land  # noqa: E402

ARCHIVE_ROOT = pathlib.Path(
    __import__("os").environ.get("URTPE_ARCHIVE_ROOT")
    or ROOT.parent / "urtpe-gazettes"
)
CORPUS_CACHE = ROOT / ".corpus_cache"

# The publisher's gazette page. Its one PDF link is the live address of the
# newest document, and it is the source of the newest release's link.
PUBLISHER_PAGE = "https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E"


def fetch_live_publisher_url(page_url: str = PUBLISHER_PAGE) -> tuple[str, str]:
    """The publisher's current PDF link and its 資料更新 stamp.

    Returns ``(url, stamp)``, both empty when the page could not be read. The
    report is generated offline and must not fail because the publisher is
    unreachable; a missing live URL costs the newest release its link, and the
    report says so.
    """
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(page_url, headers={"User-Agent": "urtpe-gazette-poller"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError):
        return "", ""

    m = re.search(r'href="([^"]*\.pdf)"', page, re.I)
    url = m.group(1) if m else ""
    if url.startswith("/"):
        url = "https://uro.gov.taipei" + url
    stamp_m = re.search(
        r"資料更新[：:]\s*</?[^>]*>?\s*([0-9]{2,4}-[0-9]{1,2}-[0-9]{1,2}[^<]*)", page)
    stamp = stamp_m.group(1).strip() if stamp_m else ""
    return url, stamp


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Release:
    """One archived publication, read under the current reader."""

    def __init__(self, gazette_id: str, path: pathlib.Path, aliases: list[str]):
        self.gazette_id = gazette_id
        self.path = path
        self.aliases = aliases
        self.sha256 = sha256(path)
        self.published_date = ""
        self.calendar = ""
        self.records_read = 0
        self.excluded = 0
        self.excluded_recnos: list[str] = []
        self.completed = 0
        self.duplicate_recnos = 0
        self.tables_found = 0
        self.families: list[ReleaseFamily] = []
        self.record_dicts: list[dict] = []
        self.tripwire_faults: list[str] = []
        self.ledger_applied = 0
        self.ledger_unmatched = 0
        # Whether the pipeline actually ingested this publication, per the
        # archive's own index. A publication that was archived but never
        # ingested is a different thing from one the dataset was built from,
        # and the report must not blur the two.
        self.ingested = False
        self.ingested_record_count = 0
        self.ingested_project_count = 0
        # The publisher URL that served this publication, when the archive
        # index records one. Empty for the publications archived before the
        # field existed — their URLs were never written down.
        self.publisher_url = ""
        self.publisher_stamp = ""

    @property
    def project_count(self) -> int:
        return len(self.families)

    @property
    def record_count(self) -> int:
        return sum(len(f.members) for f in self.families)


def discover_releases(archive_root: pathlib.Path) -> tuple[list[Release], list[tuple[str, pathlib.Path]]]:
    """Every distinct archived publication, oldest first, plus the corpus members.

    Distinct by content hash, not by filename. The city re-uploads a
    byte-identical PDF under a new name, and the archive holds both
    (``核定案件-2026-10-06.pdf`` and ``核定案件-2026-10-13.pdf`` are the same
    bytes). Counting files would report a release that was never published.

    The members are the archive's own: one per indexed publication, keyed on
    its published date. That is the same set the CLI builds, so the corpus
    cache is shared rather than rebuilt.
    """
    by_hash: dict[str, list[pathlib.Path]] = {}
    for path in sorted(archive_root.glob("核定案件-*.pdf")):
        by_hash.setdefault(sha256(path), []).append(path)

    releases: list[Release] = []
    for digest, paths in by_hash.items():
        # The publication date is the document's own 統計至 line, so it is read
        # from the bytes and not from the filename. The filename's date is the
        # publisher's upload stamp and disagrees with it (the 11-03 file is the
        # 10-28 gazette).
        published = extract_mod.find_published_date(str(paths[0])) or ""
        gazette_id = published or paths[0].stem.split("-", 1)[1]
        aliases = [p.name for p in paths]
        releases.append(Release(gazette_id, paths[0], aliases))

    releases.sort(key=lambda r: (r.gazette_id, r.path.name))

    # What the pipeline actually ingested, per the archive's own index. The
    # index is append-only, so the last ``first_ingest`` for a publication is
    # the run that produced the archived data.
    for entry in _read_index(archive_root):
        for r in releases:
            if r.gazette_id != entry["gazette_id"]:
                continue
            # The publisher URL is read from ANY entry that carries one, not
            # only from the ingest entry: a URL learned later (and verified by
            # the digest it serves) is still that publication's address.
            #
            # The stamp is read only from the entry that carries the URL, so a
            # release never inherits another release's 資料更新 date. The stamp
            # is the publisher's timestamp for the document that URL serves.
            if entry.get("publisher_url"):
                r.publisher_url = entry["publisher_url"]
                if entry.get("publisher_stamp"):
                    r.publisher_stamp = entry["publisher_stamp"]
            if entry["event"] not in ("first_ingest", "restored"):
                continue
            r.ingested = True
            r.ingested_record_count = entry["record_count"]
            r.ingested_project_count = entry["project_count"]

    # The corpus members: one per distinct publication, keyed on its published
    # date, exactly as `urtpe.cli._ingest_pdf` builds them from the index.
    members = [(r.gazette_id, r.path) for r in releases]
    return releases, members


def _read_index(archive_root: pathlib.Path) -> list[dict]:
    """The archive's append-only index, as plain dicts.

    Malformed lines are skipped, not fatal — the same rule the archive itself
    applies when it reads its own index.
    """
    path = archive_root / "index.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def build_corpus(members: list[tuple[str, pathlib.Path]]) -> list[dict]:
    """The completion corpus over every archived publication.

    Built once and filtered per release, rather than rebuilt per release. The
    candidate set is the same either way — a candidate carries the gazette it
    came from, so excluding one release's own rows is a filter — but the
    corpus cache is keyed on the member set, and a per-release build would
    miss the cache and rescan every PDF once per release.
    """
    return corpus_mod.build_corpus(members, exclude="", cache_dir=CORPUS_CACHE)


def read_release(release: Release, corpus: list[dict], ledger_path: pathlib.Path | None) -> None:
    """Read one release under the current reader and merge it.

    Mirrors the CLI's read path: the same corpus rule (every *other* archived
    publication), the same cleansing, the same merge, and the same ledger.

    The ledger matters for the count. It applies on every PDF ingest (D5,
    ledger-confirm-merge), and its ``confirm_merge`` entry unions one pair
    before scoring — so the pipeline's own count for a release is one lower
    than a merge without it. A report that skipped the ledger would disagree
    with the pipeline on every release the ledger touches.
    """
    corpus = [c for c in corpus if c.get("gazette_id") != release.gazette_id]
    records, meta = extract_mod.extract_pdf_with_meta(
        str(release.path), strict=False, corpus=corpus)
    release.record_dicts = records
    release.published_date = meta.get("published_date", "") or release.gazette_id
    release.calendar = meta.get("calendar", "")
    release.records_read = len(records)
    release.excluded = int(meta.get("excluded_count") or 0)
    release.excluded_recnos = [v for v in (meta.get("excluded_recnos") or "").split(",") if v]
    release.completed = int(meta.get("completed_count") or 0)
    release.duplicate_recnos = int(meta.get("duplicate_recnos") or 0)
    release.tables_found = int(meta.get("tables_found") or 0)

    raw = extract_mod.to_raw_records(records)
    districts = cleanse_mod.collect_districts(raw)
    clean = cleanse_mod.cleanse_all(raw, districts)

    confirmed_pairs: list[tuple[int, int]] = []
    if ledger_path is not None and ledger_path.exists():
        from urtpe import ledger as ledger_mod
        ledger = ledger_mod.CorrectionLedger(ledger_path)
        outcome = ledger.apply(clean, key_of=ledger_mod.default_key)
        confirmed_pairs = outcome.confirmed_pairs
        release.ledger_applied = len(outcome.applied)
        release.ledger_unmatched = len(outcome.unmatched)
    projects = merge_mod.merge(clean, confirmed_pairs=confirmed_pairs)
    release.families = [_to_family(p) for p in projects]

    from urtpe import tripwire as tripwire_mod
    tw = tripwire_mod.Tripwire()
    pages = _page_count(release.path)
    excluded = {int(v) for v in release.excluded_recnos if v.isdigit()}
    release.tripwire_faults = tw.check(
        records, pages=pages, tables_found=release.tables_found,
        duplicate_recnos=release.duplicate_recnos, excluded_recnos=excluded)
    release.tripwire_faults += tw.check_partition(clean, projects)


def _to_family(project) -> ReleaseFamily:
    members = tuple(
        ReleaseRecord(recno=m.recno, iso_date=m.iso_date, land=m.land,
                      name=m.name, district=m.district)
        for m in project.members)
    return ReleaseFamily(project_id=project.project_id, members=members)


def _page_count(path: pathlib.Path) -> int:
    import pymupdf
    doc = pymupdf.open(str(path))
    try:
        return len(doc)
    finally:
        doc.close()


def reconcile_pair(previous: Release, current: Release) -> reconcile_mod.ReconcileResult:
    """The record-level comparison, from the pipeline's own reconciler.

    Both sides are read without the recovery pass, so the comparison describes
    the published data and not this reader's completions.
    """
    return reconcile_mod.reconcile(
        previous.record_dicts, current.record_dicts,
        previous_id=previous.gazette_id, current_id=current.gazette_id,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _esc(text) -> str:
    return html.escape(str(text), quote=True)


def _short(land: str, limit: int = 60) -> str:
    text = " ".join(str(land or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _rec_label(rec: ReleaseRecord) -> str:
    return "%s · %s" % (rec.iso_date or "?", _short(rec.land, 44))


def _render_pdf_link(link) -> str:
    """One release's link to the document the city published for it.

    Two kinds, and the reader can tell them apart: 出版方最新檔 is the live
    link, which serves the newest document; 該版原始檔 is the version-specific
    URL that served this release. A release with neither says so — it does
    not borrow the live link, which would serve a different gazette.
    """
    e = _esc
    if not link.known:
        return '<span class="muted-cell">%s</span>' % e(link.label)
    stamp = ""
    if link.publisher_stamp:
        stamp = '<br><span class="stamp">資料更新 %s</span>' % e(link.publisher_stamp)
    return ('<a class="pdf-link" href="%s" target="_blank" rel="noopener">%s</a>%s'
            % (e(link.url), e(link.label), stamp))


def _render_pdf_link_note(live_url: str, live_stamp: str, newest: str) -> str:
    """How the 原始檔 column's URLs came about, and what is missing."""
    e = _esc
    bits = []
    if live_url:
        bits.append(
            "「出版方最新檔」指向出版方頁面上唯一的一個 PDF 連結，"
            "該連結每次發布都會改指向，所以它只對最新一版成立"
            + ("（出版方資料更新 %s）。" % e(live_stamp) if live_stamp else "。"))
    else:
        bits.append("出版方頁面本次無法讀取，所以最新一版沒有連結。")
    bits.append(
        "「該版原始檔」是該版當初被下載時的版本專屬網址；"
        "這種網址一旦知道就長期有效（實測 2026-10-15 的網址至今仍指向該版）。"
        "封存索引自本次變更起會記錄下載網址，"
        "所以之後每一版都會有屬於自己的連結；"
        "在本變更之前封存的各版沒有留下網址，該欄位顯示「未記錄」而不是指向別版。")
    return ('<p class="lead">%s</p>' % "".join(bits))


def _signed(n: int) -> str:
    return "%+d" % n


def render_html(releases: list[Release], diffs: list, generated_at: str,
                live_url: str = "", live_stamp: str = "") -> str:
    e = _esc
    out: list[str] = []
    w = out.append

    w("<!doctype html>")
    w('<html lang="zh-Hant">')
    w("<head>")
    w('<meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width, initial-scale=1">')
    w("<title>公報發布間差異 · 專案總數變化說明</title>")
    w("""<!--
  Generated by scripts/release_diff_report.py. Do not edit by hand.
  Self-contained: no external requests, opens offline from file:// like the viewer.

  Every figure is re-derived by reading each archived PDF under the current
  reader at generation time. Nothing is copied from a previous run.
-->""")
    w("""<style>
  :root{
    --ink:#0f172a; --muted:#64748b; --line:#cbd5e1; --bg:#ffffff; --panel:#f8fafc;
    --add:#0f766e; --add-bg:#f0fdfa; --drop:#b91c1c; --drop-bg:#fef2f2;
    --warn:#b45309; --warn-bg:#fffbeb; --info:#1d4ed8; --info-bg:#eff6ff;
    --muted-bg:#f1f5f9;
  }
  @media (prefers-color-scheme: dark){
    :root{
      --ink:#e2e8f0; --muted:#94a3b8; --line:#334155; --bg:#0b1220; --panel:#111827;
      --add:#5eead4; --add-bg:#0b2b28; --drop:#fca5a5; --drop-bg:#2d1010;
      --warn:#fbbf24; --warn-bg:#2a1f06; --info:#93c5fd; --info-bg:#0c1e3d;
      --muted-bg:#1e293b;
    }
  }
  *{box-sizing:border-box}
  body{margin:0;padding:0 0 64px;background:var(--bg);color:var(--ink);
       font:15px/1.65 system-ui,-apple-system,"Segoe UI","Noto Sans TC",sans-serif}
  header{background:var(--panel);border-bottom:1px solid var(--line);padding:28px 32px}
  h1{margin:0 0 6px;font-size:22px;letter-spacing:.01em}
  .sub{color:var(--muted);font-size:13px;margin:0;max-width:92ch}
  main{max-width:1240px;margin:0 auto;padding:0 32px}
  section{margin-top:44px}
  h2{font-size:17px;margin:0 0 4px;padding-bottom:8px;border-bottom:2px solid var(--line)}
  h2 .n{color:var(--muted);font-weight:400;margin-right:10px}
  h3{font-size:14.5px;margin:22px 0 8px}
  .lead{color:var(--muted);font-size:13.5px;margin:10px 0 18px;max-width:92ch}

  table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:10px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);
        vertical-align:top}
  th{color:var(--muted);font-weight:600;font-size:12.5px;white-space:nowrap}
  td.num,th.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
  tr.total td{font-weight:650;border-top:2px solid var(--line)}
  .add{color:var(--add);font-weight:650}
  .drop{color:var(--drop);font-weight:650}
  .zero{color:var(--muted)}

  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
        padding:14px 16px;margin:12px 0}
  .card.warn{border-color:var(--warn);background:var(--warn-bg)}
  .card.stop{border-color:var(--drop);background:var(--drop-bg)}
  .card.info{border-color:var(--info);background:var(--info-bg)}
  .card.add{border-color:var(--add);background:var(--add-bg)}
  .ttl{font-weight:650;font-size:14px;margin-bottom:6px}
  .ttl small{display:block;font-weight:400;color:var(--muted);font-size:12.5px;
             margin-top:3px}
  .metric{font-variant-numeric:tabular-nums;font-weight:650}

  .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
  .kv{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:13px}
  .kv dt{color:var(--muted)}
  .kv dd{margin:0;font-variant-numeric:tabular-nums}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
       background:var(--panel);padding:1px 5px;border-radius:4px}
  .pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;
        border:1px solid currentColor}
  .p-add{color:var(--add)} .p-drop{color:var(--drop)} .p-warn{color:var(--warn)}
  .p-info{color:var(--info)}
  .pdf-link{color:var(--info);text-decoration:none;border-bottom:1px solid currentColor}
  .pdf-link:hover{color:var(--ink)}
  .stamp{display:block;color:var(--muted);font-size:11.5px;margin-top:2px}
  .muted-cell{color:var(--muted)}
  .backlink{float:right;font-size:13px;font-weight:400;color:var(--info);
            text-decoration:none;border-bottom:1px solid currentColor}
  .backlink:hover{color:var(--ink)}
  details{margin-top:8px}
  summary{cursor:pointer;font-size:13px;color:var(--info)}
  .fam{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0;
       background:var(--panel)}
  .fam .head{font-weight:650;font-size:13px}
  .fam .head .pid{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
                  font-size:12.5px}
  .fam ul{margin:6px 0 0;padding-left:18px;font-size:12.5px;color:var(--muted)}
  .fam li{margin:1px 0}
  .legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);
          margin-top:12px}
  footer{max-width:1240px;margin:56px auto 0;padding:20px 32px 0;
         border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
  @media(max-width:700px){ main,header{padding-left:16px;padding-right:16px} }
</style>""")
    w("</head>")
    w("<body>")

    # ---- header ----------------------------------------------------------
    w("<header>")
    # The back link. Relative, so the pair works from the published site, from
    # a file:// page, and from a clone alike.
    w('<a class="backlink" href="../viewer/index.html">← 回專案歷史圖</a>')
    w("<h1>公報發布間差異 — 專案總數變化說明</h1>")
    w('<p class="sub">每一版公報的核定案件重新讀取、比對，說明專案總數為何不同。'
      '所有數字於 %s 由 <code>scripts/release_diff_report.py</code> 重新產出，'
      '不抄寫前一次結果。</p>' % e(generated_at))
    w("</header>")

    w("<main>")

    # ---- §1 the releases -------------------------------------------------
    w('<section id="releases">')
    w('<h2><span class="n">1</span>各版公報</h2>')
    w('<p class="lead">以內容雜湊區分版本：同一份 PDF 被重新上傳時，'
      '檔名會變但位元組相同，那不是一次新的發布。</p>')
    w("<table><thead><tr><th>統計至</th><th>檔案</th><th>原始檔</th>"
      "<th class='num'>核定案件</th>"
      "<th class='num'>專案</th><th class='num'>排除</th><th>排除的編號</th>"
      "<th>日曆</th><th>匯入</th><th>狀態</th>"
      "</tr></thead><tbody>")
    newest = releases[-1].published_date if releases else ""
    for r in releases:
        status = "通過" if not r.tripwire_faults else "拒絕"
        cls = "" if not r.tripwire_faults else ' class="drop"'
        excluded = ", ".join(r.excluded_recnos) if r.excluded_recnos else "—"
        ingested = "是" if r.ingested else '<span class="pill p-warn">否</span>'
        link = publisher_link_for(
            r.published_date, recorded_url=r.publisher_url, live_url=live_url,
            publisher_stamp=r.publisher_stamp, live_stamp=live_stamp,
            newest_published_date=newest)
        w("<tr><td><b>%s</b></td><td><code>%s</code></td><td>%s</td>"
          "<td class='num'>%d</td><td class='num'>%d</td><td class='num'>%d</td>"
          "<td><code>%s</code></td>"
          "<td>%s</td><td>%s</td><td%s>%s</td></tr>"
          % (e(r.published_date), e(r.path.name), _render_pdf_link(link),
             r.record_count, r.project_count,
             r.excluded, e(excluded), e(r.calendar), ingested, cls, e(status)))
    w("</tbody></table>")
    w("<p class='lead'>「核定案件」是本次讀取後進入合併的筆數；「專案」是合併後的家族數。"
      "「排除」是出版方截斷地號或核定日期欄位而無法信任的筆數，該版不是該公報的忠實副本。"
      "每一版都套用同一本人工修正 ledger，"
      "所以本表的專案數與管線匯入該版時的數字一致。"
      "「匯入」為「否」者表示該版已封存但沒有成為資料集的來源。</p>")
    w(_render_pdf_link_note(live_url, live_stamp, newest))
    w("</section>")

    # ---- §2 the headline -------------------------------------------------
    w('<section id="headline">')
    w('<h2><span class="n">2</span>總數怎麼變的</h2>')
    w('<p class="lead">每一段相鄰版本之間的差異。淨變化由「新生家族」與「消失家族」'
      '組成，兩者都列在下方，數字可以自行驗算。</p>')
    w("<table><thead><tr><th>版本</th><th class='num'>核定案件</th><th class='num'>Δ案件</th>"
      "<th class='num'>專案</th><th class='num'>Δ專案</th><th class='num'>新生家族</th>"
      "<th class='num'>消失家族</th><th>新核定</th></tr></thead><tbody>")
    prev = None
    for d in diffs:
        if prev is None:
            w("<tr class='total'><td><b>%s</b></td><td class='num'>%d</td>"
              "<td class='num zero'>—</td><td class='num'>%d</td>"
              "<td class='num zero'>—</td><td class='num zero'>—</td>"
              "<td class='num zero'>—</td><td>—</td></tr>"
              % (e(d.previous_id), d.previous_records, d.previous_projects))
        else:
            net_p = d.net_projects
            cls_p = "add" if net_p > 0 else ("drop" if net_p < 0 else "zero")
            net_r = d.net_records
            cls_r = "add" if net_r > 0 else ("drop" if net_r < 0 else "zero")
            w("<tr><td><b>%s</b></td><td class='num'>%d</td>"
              "<td class='num %s'>%s</td><td class='num'>%d</td>"
              "<td class='num %s'>%s</td><td class='num'>%d</td>"
              "<td class='num'>%d</td><td>%d</td></tr>"
              % (e(d.current_id), d.current_records, cls_r, _signed(net_r),
                 d.current_projects, cls_p, _signed(net_p),
                 len(d.born), len(d.dead), d.new_approvals))
        prev = d
    w("</tbody></table>")
    w(_render_payload_note(releases))
    w("</section>")

    # ---- §3 each transition ----------------------------------------------
    w('<section id="transitions">')
    w('<h2><span class="n">3</span>逐版說明</h2>')
    for d in diffs:
        if d.previous_id == "":
            continue
        w(_render_transition(d))
    w("</section>")

    # ---- §4 method -------------------------------------------------------
    w('<section id="method">')
    w('<h2><span class="n">4</span>量法與限制</h2>')
    w("""<div class="card info">
      <div class="ttl">家族配對依據<small>成員內容，不是 project_id</small></div>
      <p style="margin:0;font-size:13.5px">同一個家族的識別鍵是
      <b>核定日期 + 案名自帶的土地核心</b>（行政區、段/小段、首筆地號、案名宣告的筆數）。
      project_id 是最新一筆核准的土地核心，會隨筆數與首筆地號變動而變
      （多筆家族約 11% 曾移動過）；若以 project_id 配對，
      每次改名都會被誤讀成一個家族消失、另一個家族新生。<br>
      地號欄位也不是穩定的：出版方在不同版本間會重印該欄位，
      有時只差一個字（實測 2026-08-27 與 2026-09-24 之間有三個單位的
      地號欄位不同）。所以配對以案名的核心為準，
      案名無法解析時才退回地號欄位。</p>
    </div>
    <div class="card">
      <div class="ttl">記錄層與專案層分開<small>兩個數字因為不同的原因移動</small></div>
      <p style="margin:0;font-size:13.5px">約七成的核定案件是同一更新單元的階段性重複核准。
      一筆新核准若落在既有家族內，記錄數 +1 而專案數不變。專案數要等家族聚類結果改變才會動。
      記錄層訊號取自管線自己的 <code>urtpe.reconcile</code>：新核定與淨變化是權威訊號，
      改期、編輯、消失是無法解析的訊號——已發布的資料無法區分「刪除」與「改寫」。</p>
    </div>
    <div class="card">
      <div class="ttl">每一版都重新讀取<small>不是沿用當時的輸出</small></div>
      <p style="margin:0;font-size:13.5px">每一份 PDF 都以目前的讀取器重新讀取並重新合併，
      因此本頁的數字描述的是「這些公報在今天被讀出什麼」，
      而不是「每一版當年被讀出什麼」。歷史的讀取器缺陷（吸收頁碼、截斷長地號欄位）
      已經修正，先前的讀取結果不再沿用。</p>
    </div>
    <div class="card warn">
      <div class="ttl">地號欄位的完成<small>跨版本借列，並非出版方所印</small></div>
      <p style="margin:0;font-size:13.5px">出版方在列印行高處截斷地號欄位時，
      該筆會從同族的其他核准補齊。每一版的完成來源是其餘所有版本。
      補齊後的筆數在統計上是完整的，但它不是該版公報原樣的內容。</p>
    </div>""")
    w("</section>")

    w("</main>")
    w("<footer>由 <code>scripts/release_diff_report.py</code> 產生，"
      "純邏輯在 <code>scripts/release_diff.py</code>。唯讀：不寫入管線產物、"
      "不動 viewer、不寫封存索引。</footer>")
    w("</body></html>")
    return "\n".join(out)


def _render_payload_note(releases: list[Release]) -> str:
    """How the report's numbers relate to the number the viewer shows.

    The report re-reads each release from its PDF. The payload was built by an
    ingest, and an ingest may do more than read a PDF: the recovery pass
    completes publisher-truncated rows from the city's APIs, and those
    completions add records and sometimes add families.

    So the two counts differ by a known amount, and this note measures the
    difference rather than asserting it. A reader who sees 679 here and 682 in
    the viewer must be able to find the 3.
    """
    e = _esc
    payload_path = ROOT / "viewer" / "projects.data.js"
    if not payload_path.exists():
        return ""
    try:
        text = payload_path.read_text(encoding="utf-8")
        doc = json.loads(re.sub(r";\s*$", "",
                                re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())))
    except (OSError, ValueError):
        return ""

    counts = doc.get("counts") or {}
    published = doc.get("published_date", "")
    by_id = {r.published_date: r for r in releases}
    emitted = by_id.get(published)
    if emitted is None:
        return ""

    # The payload's own recovery nodes: the rows the API completed.
    recovered_families: dict[str, list[str]] = {}
    recovered_rows = 0
    for p in doc.get("projects", []):
        for n in p.get("nodes", []):
            if n.get("recovery"):
                recovered_rows += 1
                recovered_families.setdefault(p["project_id"], []).append(str(n["recno"]))

    # Which of those families does the PDF-only read not have at all?
    read_keys: set[tuple[str, str]] = set()
    for fam in emitted.families:
        for m in fam.members:
            read_keys.add(m.content_key())
    novel = []
    for p in doc.get("projects", []):
        keys = set()
        recnos = []
        for n in p.get("nodes", []):
            keys.add((n.get("date", ""), normalize_land(n.get("land", ""))))
            if n.get("recovery"):
                recnos.append(str(n["recno"]))
        if not (keys & read_keys):
            novel.append((p["project_id"], sorted(recnos)))

    rows = []
    if emitted.project_count != counts.get("projects"):
        rows.append(
            "本頁重讀 %s 得到 %d 個專案 / %d 筆核定案件，"
            "viewer 顯示 %d 個專案 / %d 筆。"
            % (published, emitted.project_count, emitted.record_count,
               counts.get("projects", 0), counts.get("records", 0)))
    if recovered_rows:
        created = [pid for pid, _ in novel]
        joined = [pid for pid in recovered_families
                  if pid not in created]
        detail = ""
        if created:
            detail += "其中 %d 個家族是復原列自行成立的（%s）；" % (
                len(created), "、".join(created))
        if joined:
            detail += "另外 %d 筆復原列併入既有家族（%s）。" % (
                len(joined), "、".join(joined))
        rows.append(
            "差距的來源是復原（recovery pass）：匯入時從市政府 API 補齊了 %d 筆"
            "出版方截斷的列，本頁只讀 PDF，所以看不到這 %d 筆。%s"
            % (recovered_rows, recovered_rows, detail))
    newer = [r for r in releases if r.published_date > published]
    for r in newer:
        if r.ingested:
            continue
        rows.append(
            "%s 已封存但沒有匯入：它不在 viewer 的資料裡，"
            "但本頁把它算進去了，所以本頁的末列與 viewer 的數字本就不同。"
            % r.published_date)
    if not rows:
        return ""

    return ('<div class="card warn"><div class="ttl">與 viewer 顯示數字的差距'
            '<small>本頁只讀 PDF；viewer 的資料來自一次匯入，匯入可以多做復原</small></div>'
            '<ul style="margin:4px 0 0 18px;font-size:13.5px">%s</ul></div>'
            % "".join("<li>%s</li>" % e(r) for r in rows))


def _render_transition(d) -> str:
    e = _esc
    o: list[str] = []
    w = o.append
    net_p = d.net_projects
    cls_p = "add" if net_p > 0 else ("drop" if net_p < 0 else "zero")

    w('<h3 id="t-%s">%s → %s</h3>' % (e(d.current_id), e(d.previous_id), e(d.current_id)))

    # The headline: what moved and why, in one card.
    w('<div class="card %s">' % ("add" if net_p > 0 else ("stop" if net_p < 0 else "info")))
    w('<div class="ttl">專案數 %s → %s（%s）'
      '<small>家族新生 %d、消失 %d、擴張 %d、縮小 %d</small></div>'
      % (d.previous_projects, d.current_projects, _signed(net_p),
         len(d.born), len(d.dead), len(d.grew), len(d.shrank)))
    w('<dl class="kv">')
    w("<dt>核定案件</dt><dd>%d → %d（%s）</dd>"
      % (d.previous_records, d.current_records, _signed(d.net_records)))
    w("<dt>新核定</dt><dd>%d 筆</dd>" % d.new_approvals)
    if d.calendar_previous != d.calendar_current:
        w("<dt>日曆</dt><dd>%s → %s <span class='pill p-warn'>已變更</span></dd>"
          % (e(d.calendar_previous or "—"), e(d.calendar_current or "—")))
    else:
        w("<dt>日曆</dt><dd>%s（未變）</dd>" % e(d.calendar_current or "—"))
    if d.redated or d.edited or d.vanished:
        w("<dt>歷史列變動</dt><dd>改期 %d、編輯 %d、消失 %d</dd>"
          % (d.redated, d.edited, d.vanished))
    if d.recovered:
        w("<dt>本讀取器補齊</dt><dd>%d 筆</dd>" % d.recovered)
    w("<dt>僅改名</dt><dd>%d 個家族（成員未變，project_id 改變）</dd>" % d.renamed)
    w("</dl>")
    if d.blocking:
        w('<div class="card stop" style="margin-top:12px">')
        w('<div class="ttl">管線會拒絕這一次匯入</div><ul style="margin:4px 0 0 18px;font-size:13px">')
        for b in d.blocking:
            w("<li>%s</li>" % e(b))
        w("</ul></div>")
    w("</div>")

    # The identity of the movement, in named families.
    if d.born or d.dead:
        w('<div class="cols">')
        if d.dead:
            w('<div class="card"><div class="ttl">消失的家族（%d）'
              '<small>這一版沒有任何成員留下</small></div>' % len(d.dead))
            for fam in d.dead:
                w('<details><summary>%s</summary>' % e(fam.project_id))
                w("<ul>")
                for m in fam.members:
                    w("<li>%s</li>" % e(_rec_label(m)))
                w("</ul></details>")
            w("</div>")
        if d.born:
            w('<div class="card"><div class="ttl">新生的家族（%d）'
              '<small>這一版所有成員都是新的</small></div>' % len(d.born))
            for fam in d.born:
                w('<details><summary>%s</summary>' % e(fam.project_id))
                w("<ul>")
                for m in fam.members:
                    w("<li>%s</li>" % e(_rec_label(m)))
                w("</ul></details>")
            w("</div>")
        w("</div>")
    else:
        w('<div class="card"><div class="ttl">沒有家族消失，也沒有家族新生'
          '<small>淨變化 %s 全部來自既有家族的擴張或縮小</small></div></div>'
          % _signed(net_p))

    if d.grew or d.shrank:
        w('<h3>既有家族的變動</h3>')
        for change in d.grew:
            w('<div class="fam"><div class="head"><span class="pid">%s</span></div>'
              % e(change.current.project_id if change.current else ""))
            if change.added:
                w('<div style="font-size:12.5px;color:var(--add)">+%d 筆</div>' % len(change.added))
                w("<ul>")
                for m in change.added:
                    w("<li>%s</li>" % e(_rec_label(m)))
                w("</ul>")
            if change.removed:
                w('<div style="font-size:12.5px;color:var(--drop)">−%d 筆</div>'
                  % len(change.removed))
                w("<ul>")
                for m in change.removed:
                    w("<li>%s</li>" % e(_rec_label(m)))
                w("</ul>")
            w("</div>")
        for change in d.shrank:
            if change in d.grew:
                continue
            w('<div class="fam"><div class="head"><span class="pid">%s</span></div>'
              % e(change.previous.project_id if change.previous else ""))
            if change.removed:
                w('<div style="font-size:12.5px;color:var(--drop)">−%d 筆</div>'
                  % len(change.removed))
                w("<ul>")
                for m in change.removed:
                    w("<li>%s</li>" % e(_rec_label(m)))
                w("</ul>")
            w("</div>")
    return "\n".join(o)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "release-diff.html"))
    ap.add_argument("--archive-root", default=str(ARCHIVE_ROOT))
    ap.add_argument("--no-live-url", action="store_true",
                    help="do not fetch the publisher's current PDF link "
                         "(the newest release then carries no link)")
    args = ap.parse_args(argv)

    archive_root = pathlib.Path(args.archive_root)
    if not archive_root.exists():
        print("[ERROR] archive root not found: %s" % archive_root, file=sys.stderr)
        return 2

    releases, members = discover_releases(archive_root)
    if not releases:
        print("[ERROR] no archived publications found in %s" % archive_root, file=sys.stderr)
        return 2

    # The publisher's live PDF link, for the newest release. A failure here
    # costs that release its link and nothing else: the report says the URL
    # is unknown rather than failing the run.
    live_url = live_stamp = ""
    if not args.no_live_url:
        live_url, live_stamp = fetch_live_publisher_url()
        print("[INFO] publisher link: %s" % (live_url or "(unavailable)"),
              file=sys.stderr)

    print("[INFO] building the completion corpus over %d publication(s)"
          % len(members), file=sys.stderr)
    corpus = build_corpus(members)
    ledger_path = pathlib.Path(
        __import__("os").environ.get("URTPE_LEDGER")
        or (archive_root / "corrections.jsonl"))
    for r in releases:
        print("[INFO] reading %s (%s)" % (r.gazette_id, r.path.name), file=sys.stderr)
        read_release(r, corpus, ledger_path)

    diffs = []
    for i, r in enumerate(releases):
        if i == 0:
            diffs.append(diff_releases("", r.gazette_id, [], r.families))
            continue
        prev = releases[i - 1]
        rec = reconcile_pair(prev, r)
        diffs.append(diff_releases(prev.gazette_id, r.gazette_id,
                                   prev.families, r.families, reconciliation=rec))

    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    html_text = render_html(releases, diffs, generated_at,
                            live_url=live_url, live_stamp=live_stamp)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print("[INFO] written %s (%d releases, %d transitions)"
          % (out_path, len(releases), len(diffs) - 1), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
