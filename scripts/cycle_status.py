#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the cycle status page: the recent PDF-cycle runs on one local page.

openspec change a4-pdf-cycle-coordinator, capability `cycle-status-page`. This is the optional
part of the change: delete `specs/cycle-status-page/` and this file, and the coordinator does
not notice (`run_cycle.py` imports it best effort).

It reads `cycle_log.jsonl` in the archive root and writes ONE file, `cycle_status.html`, beside
it. That is outside the repository on purpose: GitHub Pages serves the repository, and an
operational log must not be committed or published by accident. A path inside the repository
is refused.

A stopped schedule writes no new page, so a warning computed only at generation time would
never appear. The newest record's time is embedded, and a small inline script compares it with
the clock when the page is OPENED. The page is self-contained (no script, stylesheet or font
from anywhere else), light-only, with the project's cream tokens.

    python scripts/cycle_status.py [--archive-root PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import html as _html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cycle  # noqa: E402

PAGE_NAME = "cycle_status.html"
LOG_NAME = "cycle_log.jsonl"
STALE_HOURS = 36
SHOW_RUNS = 60

#: outcome word -> (style, label). Four styles, so a stopped run is not mistaken for a quiet
#: one: finished, quiet (nothing to do), stopped (needs a person), waiting (a busy moment).
STYLE = {
    "ingested": ("finished", "已匯入"),
    "nothing_new": ("quiet", "沒有新公報"),
    "already_done": ("quiet", "已完成過"),
    "refused": ("stopped", "被拒絕"),
    "stopped": ("stopped", "已停止"),
    "awaiting_diagnosis": ("stopped", "等待診斷"),
    "locked": ("waiting", "鎖被占用"),
    "dirty_tree": ("waiting", "工作樹未提交"),
    "another_cycle": ("waiting", "另一個週期在跑"),
    "publish_failed": ("stopped", "發布失敗"),
}


def default_output_path(archive_root: Path | str) -> Path:
    return Path(archive_root) / PAGE_NAME


def assert_outside_repo(path: Path | str) -> None:
    """Refuse any path inside the repository: Pages serves it, and git would commit it."""
    p = Path(path).resolve()
    r = ROOT.resolve()
    if p == r or r in p.parents:
        raise ValueError("refusing to write the status page inside the repository: %s" % p)


def _read_records(archive_root: Path) -> list[dict]:
    log = Path(archive_root) / LOG_NAME
    if not log.is_file():
        return []
    out = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


_CSS = """
:root{--bg:#fff8f4;--panel:#ffffff;--ink:#211d1d;--muted:#686362;--line:#f3d9bf;--accent:#ad4d2a;
      --tint:#fff1e8;--sun:#fde272;--ok:#3fae74;--ok-bg:#f0fdf4;--gate:#8e2626;--gate-bg:#fdf0ef;
      --mrg:#8a5a00;--mrg-bg:#fdf3dc}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--ink);
     font:15px/1.6 "Instrument Sans","Microsoft JhengHei","PingFang TC",system-ui,sans-serif}
main{max-width:1100px;margin:0 auto}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin:0 0 16px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;background:var(--tint);
     padding:1px 5px;border-radius:4px}
.warn{display:none;border:1px solid var(--gate);background:var(--gate-bg);color:var(--gate);
      border-radius:10px;padding:10px 14px;margin:0 0 14px;font-weight:600}
.warn.show{display:block}
.newest{margin:0 0 12px;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:13.5px;background:var(--panel);
      border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12.5px;background:var(--tint);white-space:nowrap}
td.nowrap{white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.run.finished td.out{color:var(--ok);font-weight:700}
tr.run.quiet td.out{color:var(--muted)}
tr.run.stopped{background:var(--gate-bg)}
tr.run.stopped td.out{color:var(--gate);font-weight:700}
tr.run.waiting{background:var(--mrg-bg)}
tr.run.waiting td.out{color:var(--mrg);font-weight:700}
.wrap{overflow-x:auto}
"""

_SCRIPT = """
(function () {
  var n = document.getElementById('newest');
  var s = document.getElementById('stale');
  if (!n || !s) return;
  var t = Date.parse(n.getAttribute('data-newest'));
  if (isNaN(t) || (Date.now() - t) / 3600000 > %d) s.classList.add('show');
})();
""" % STALE_HOURS


def render(records: list[dict], now_iso: str) -> str:
    """The page as one HTML string. Pure: records and a clock in, text out."""
    esc = _html.escape
    ordered = sorted(records, key=lambda r: r.get("time", ""), reverse=True)
    newest = ordered[0]["time"] if ordered else ""
    age = cycle.newest_record_age_hours(records, now_iso)
    stale_now = age is None or age > STALE_HOURS

    rows = []
    for r in ordered[:SHOW_RUNS]:
        outcome = str(r.get("outcome", ""))
        klass, label = STYLE.get(outcome, ("stopped", outcome))
        rows.append(
            '<tr class="run %s" data-outcome="%s">'
            '<td class="nowrap">%s</td><td class="out">%s <code>%s</code></td><td>%s</td><td>%s</td>'
            '<td class="num">%s</td><td class="nowrap">%s</td><td>%s</td></tr>' % (
                klass, esc(outcome), esc(str(r.get("time", ""))), esc(label), esc(outcome),
                esc(str(r.get("last_stage", ""))), esc(str(r.get("failed_stage", ""))),
                esc(str(r.get("exit_code", ""))), esc(str(r.get("gazette_id", ""))),
                esc(str(r.get("reason", "")))))
    body_rows = "\n".join(rows) if rows else '<tr><td colspan="7">沒有任何執行紀錄。</td></tr>'
    newest_text = esc(newest) if newest else "沒有任何執行紀錄"
    return """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>週期執行狀態</title>
<style>%(css)s</style>
</head>
<body>
<main>
<h1>週期執行狀態</h1>
<p class="sub">PDF cycle 的最近執行紀錄。資料來自 <code>cycle_log.jsonl</code>；本頁唯讀、只在本機，不發布。</p>
<div id="stale" class="warn%(show)s">超過 %(hours)d 小時沒有新的執行紀錄，排程可能已停止。</div>
<p class="newest">最新紀錄：<span id="newest" data-newest="%(newest)s">%(newest_text)s</span></p>
<div class="wrap">
<table>
<thead><tr><th>時間</th><th>結果</th><th>最後階段</th><th>失敗階段</th><th>結束碼</th><th>公報</th><th>說明</th></tr></thead>
<tbody>
%(rows)s
</tbody>
</table>
</div>
<script>%(script)s</script>
</main>
</body>
</html>
""" % {"css": _CSS, "show": " show" if stale_now else "", "hours": STALE_HOURS,
       "newest": esc(newest), "newest_text": newest_text, "rows": body_rows, "script": _SCRIPT}


def write_page(archive_root: Path | str, now_iso: str | None = None,
               out: Path | str | None = None) -> Path:
    """Read the record, write the page. The only file written is the page itself."""
    root = Path(archive_root)
    target = Path(out) if out else default_output_path(root)
    assert_outside_repo(target)
    now_iso = now_iso or datetime.now().astimezone().isoformat(timespec="seconds")
    page = render(_read_records(root), now_iso)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(page, encoding="utf-8")
    os.replace(tmp, target)
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--archive-root", default=None,
                    help="archive directory (default: the configured archive root)")
    ap.add_argument("--out", default=None, help="page path (default: beside the record)")
    args = ap.parse_args(argv)
    if args.archive_root:
        root = Path(args.archive_root)
    else:
        from urtpe.archive import DEFAULT_ARCHIVE_ROOT
        root = Path(DEFAULT_ARCHIVE_ROOT)
    try:
        path = write_page(root, out=args.out)
    except ValueError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
