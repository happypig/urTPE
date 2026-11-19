"""Synchronise current-payload regions of docs/domain-model.html.

Usage: python scripts/sync_domain_model.py [--check]
The current figures come from the whole payload and the real viewer chain.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.doc_measurements import (DocSyncError, load_payload, measure_viewer,
                                      replace_fields, write_or_check)
from scripts.probe_tab2_numbers import measure_payload


def _row(en: str, zh: str, value) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return (f'      <tr><td><span class="en">{en}</span><span class="zh">{zh}</span></td>'
            f'<td class="num">{value}</td></tr>')


def _fact_rows(m: dict, v: dict) -> str:
    p = m["projects"]
    rows = [
        ("approvals / units", "核定 / 單元", f"{m['records']:,} / {m['projects']}"),
        ("records per unit, median", "每單元紀錄數中位數", m["median_records"]),
        ("units with ≤2 records", "≤2 筆紀錄的單元", f"{m['units_le2']} ({round(100*m['units_le2']/p)}%)"),
        ("units with ≥3 records", "≥3 筆紀錄的單元", f"{m['units_ge3']} ({round(100*m['units_ge3']/p)}%)"),
        ("case→record bindings", "案→紀錄 綁定數", f"{m['bindings']:,}"),
        ("distinct cases on ≥1 record", "掛在 ≥1 筆紀錄上的不同案", f"{m['distinct_real_cases']:,}"),
        ("cases covering >1 record", "涵蓋 >1 筆紀錄的案", m["cases_multiple_records"]),
        ("— most records on one case", "— 單一案最多紀錄數", m["max_records_per_case"]),
        ("records naming >1 case", "掛在不只一個案上的紀錄", m["records_multiple_cases"]),
        ("recovered nodes", "復原的節點", m["recovered_nodes"]),
        ("distinct virtual cases", "不同的虛擬案", m["distinct_virtual_cases"]),
        ("— dated / undated", "— 有日期 / 無日期", f"{m['virtual_dated']} / {m['virtual_undated']}"),
        ("virtual cases listed >once", "被列出不只一次的虛擬案", m["virtual_duplicates"]),
        ("cases both virtual and real", "同時是虛擬與真實的案", m["cases_virtual_and_real"]),
        ("total distinct real and virtual cases", "真實與虛擬案的不同總數", f"{m['total_distinct_cases']:,}"),
        ("construction events rendered", "渲染的施工事件", f"{v['construction_events']:,}"),
        ("progress markers ambiguously anchored", "錨定有歧義的進度標記", v["ambiguous_markers"]),
        ("markers whose source case is on no record", "源案不在任何紀錄上的標記", v["source_case_missing"]),
        ("rendered row pairs date-inverted", "渲染列 日期倒置", f"{v['inverted_pairs']} ({v['inverted_projects']} 單元)"),
    ]
    return "\n".join(_row(en, zh, value) for en, zh, value in rows)


def fields_for(doc: dict, viewer: dict | None = None) -> dict[str, str]:
    m = measure_payload(doc)
    v = measure_viewer() if viewer is None else viewer
    date = dt.date.today().isoformat()
    published = m["published_date"]
    return {
        "record-cases": (
            f'<span class="en">the record\'s own cases, via links.taipei; '
            f'{m["records_multiple_cases"]} records name more than one</span>'
            f'<span class="zh">該筆自身的案，經 links.taipei；'
            f'{m["records_multiple_cases"]} 筆紀錄掛在不只一個案上</span>'),
        "case-binding": (
            f'<span class="en">every bound case sits on one record ({m["bindings"]:,} bindings, '
            f'{m["distinct_real_cases"]:,} cases; measured {date} — 344 cases covered more than one '
            f'on the 2026-10-15 payload)</span>'
            f'<span class="zh">每個已綁定的案只掛在一筆紀錄上（{m["bindings"]:,} 個綁定、'
            f'{m["distinct_real_cases"]:,} 個案；{date} 量測 — 在 2026-10-15 payload 上曾有 344 個案涵蓋不只一筆）</span>'),
        "asymmetry-current": (
            f'<span class="en">Drawing a virtual case is reading one object; drawing a real case is joining four. '
            f'That asymmetry is why the viewer handles them differently. It cost 342 ambiguously anchored '
            f'progress markers on the 2026-10-15 payload. Measured {date} on the {published} payload, '
            f'{v["ambiguous_markers"]} markers are ambiguous; {v["source_case_missing"]} name a source case on no record.</span>'
            f'<span class="zh">畫一個虛擬案是讀一個物件，畫一個真實案要 join 四處。這個不對稱正是 viewer 對兩者處理方式不同的原因。'
            f'在 2026-10-15 payload 上，它造成 342 個進度標記錨定有歧義。{date} 以 {published} payload 量測：'
            f'{v["ambiguous_markers"]} 個標記有歧義；另有 {v["source_case_missing"]} 個所指的源案不在任何紀錄上。</span>'),
        "virtual-integrity-current": (
            f'<span class="en">On the 2026-10-15 payload <b>20</b> virtual cases were listed more than once '
            f'and <b>9</b> case ids appeared <i>both</i> as virtual and as real. Measured {date} on the '
            f'{published} payload: <b>{m["virtual_duplicates"]}</b> are listed more than once '
            f'({m["virtual_entries"]} entries, {m["distinct_virtual_cases"]} distinct ids) and '
            f'<b>{m["cases_virtual_and_real"]}</b> appear on both sides. The total distinct set is '
            f'{m["total_distinct_cases"]:,}. The shape still hides either problem because the virtual set is a flat list.</span>'
            f'<span class="zh">在 2026-10-15 payload 上，<b>20</b> 個虛擬案被重複列出，另有 <b>9</b> 個案同時出現在虛擬與真實兩邊。'
            f'{date} 以 {published} payload 量測：<b>{m["virtual_duplicates"]}</b> 個被重複列出'
            f'（{m["virtual_entries"]} 筆、{m["distinct_virtual_cases"]} 個不同 id），'
            f'<b>{m["cases_virtual_and_real"]}</b> 個同時出現在兩邊。不同案總數為 {m["total_distinct_cases"]:,}。'
            f'這個形狀仍會藏起問題，因為虛擬集合是一個沒有鍵的扁平清單。</span>'),
        "invariant-current": (
            f'<span class="en">Measured {date}: {m["bindings"]:,} bindings via <code>links.taipei</code> '
            f'on {m["distinct_real_cases"]:,} cases; {m["cases_multiple_records"]} cover more than one record; '
            f'<b>{m["records_multiple_cases"]}</b> records name more than one case. The relation is many-to-many '
            f'by design: <code>recovery.cases</code> may select a subset of the discovery candidates, and the landed '
            f'<code>case-record-join</code> spec fixes recovery-wins precedence with <code>ambiguous-zone</code> provenance.</span>'
            f'<span class="zh">{date} 量測：經 <code>links.taipei</code> 計 {m["bindings"]:,} 個綁定、'
            f'{m["distinct_real_cases"]:,} 個案；{m["cases_multiple_records"]} 個案涵蓋不只一筆紀錄；'
            f'<b>{m["records_multiple_cases"]}</b> 筆紀錄掛在不只一個案上。這個關係依設計是多對多：'
            f'<code>recovery.cases</code> 可以只選發現候選的子集，而已落地的 <code>case-record-join</code> '
            f'規格明定以 recovery 綁定為準，並攜帶 <code>ambiguous-zone</code> 來源標記。</span>'),
        "anchor-resolution": (
            f'<span class="en">{v["ambiguous_markers"]} ambiguous markers on the {published} payload '
            f'(measured {date}); 342 on the 2026-10-15 payload, where 320 resolved and 22 had no prior approval. '
            f'{v["source_case_missing"]} markers name a source case on no record</span>'
            f'<span class="zh">{published} payload 上有 {v["ambiguous_markers"]} 個錨定有歧義的標記'
            f'（{date} 量測）；2026-10-15 payload 上有 342 個，其中 320 可解、22 沒有更早的核定。'
            f'另有 {v["source_case_missing"]} 個所指的源案不在任何紀錄上</span>'),
        "undated-current": (
            f'<span class="en">{m["virtual_undated"]} of {m["distinct_virtual_cases"]} distinct virtual cases '
            f'carry no date at all (measured {date}). They are retained today because <code>orphan_nodes</code> '
            f'holds them, but a class with no position on the time axis needs a stated home — a gutter column, '
            f'or listed beneath the graph. That is a decision, not a default.</span>'
            f'<span class="zh">{m["distinct_virtual_cases"]} 個不同虛擬案中有 {m["virtual_undated"]} 個完全沒有日期'
            f'（{date} 量測）。它們今天被保留下來是因為 <code>orphan_nodes</code> 留著它們，'
            f'但一個在時間軸上沒有位置的類別需要一個明確的歸屬 — 一個側欄欄位，或是列在圖的下方。這是一個決定，不是一個預設值。</span>'),
        "measurement-source": (
            f'<span class="en">One measurement pass over the {published} payload '
            f'(<code>viewer/projects.data.js</code>, {m["projects"]} units; measured {date} with '
            f'<code>scripts/probe_tab2_numbers.py</code> and <code>scripts/probe_tab1_numbers.js</code>, '
            f'the second running the real <code>buildConstructionChain</code> of <code>viewer/app.js</code>). '
            f'The previous pass — 2026-11-01, the 2026-10-15 payload, 694 units — is in git history at <code>83b7b2e</code>.</span>'
            f'<span class="zh">對 {published} payload（<code>viewer/projects.data.js</code>，{m["projects"]} 個單元）'
            f'做一次量測（{date}；以 <code>scripts/probe_tab2_numbers.py</code> 與 '
            f'<code>scripts/probe_tab1_numbers.js</code> 量測，後者執行 <code>viewer/app.js</code> 真實的 '
            f'<code>buildConstructionChain</code>）。前一次量測（2026-11-01，2026-10-15 payload，694 個單元）'
            f'留在 git 歷史的 <code>83b7b2e</code>。</span>'),
        "current-facts": _fact_rows(m, v),
    }


def render_current(doc: dict, root: Path = ROOT):
    return replace_fields((root / "docs" / "domain-model.html").read_text(encoding="utf-8"),
                          fields_for(doc))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        doc = load_payload(ROOT / "viewer" / "projects.data.js")
        changed = write_or_check(ROOT / "docs" / "domain-model.html",
                                 fields_for(doc), args.check)
    except (DocSyncError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if args.check and changed:
        return 1
    print(f"[OK] domain-model.html: {doc['published_date']}; "
          f"{'stale' if changed else 'current' if args.check else 'updated' if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
