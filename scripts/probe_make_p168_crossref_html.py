"""Convert p168_crossref_by_parcel_report.txt into a readable HTML page."""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path("data/p168_crossref_by_parcel_report.txt")
OUT = Path("data/p168_crossref_by_parcel.html")

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines()

# ---- Parse header stats ----
stats = {}
for ln in lines[:10]:
    if "Not found by case_id:" in ln:
        stats["not_found_by_case_id"] = ln.split(":")[1].strip()
    elif "Unparseable names:" in ln:
        stats["unparseable"] = ln.split(":")[1].strip()
    elif "Matched by parcel:" in ln:
        stats["matched_by_parcel"] = ln.split(":")[1].strip()
    elif "Still unmatched:" in ln:
        stats["still_unmatched"] = ln.split(":")[1].strip()
    elif "Gazette published_date:" in ln:
        stats["gazette_date"] = ln.split(":")[1].strip()

# ---- Parse sections ----
matched_cases: list[dict] = []
unmatched_cases: list[dict] = []

current_section = None  # 'matched' | 'unmatched'

def new_case_entry(cid: str, stage: str, memo: str, name: str, in_processing: bool) -> dict:
    return {
        "cid": cid,
        "in_processing": in_processing,
        "stage": stage,
        "memo": memo,
        "parsed": "",
        "name": name,
        "gazette_matches": [],
    }

for ln in lines:
    if "MATCHED BY PARCEL" in ln:
        current_section = "matched"
        continue
    if "STILL UNMATCHED" in ln:
        current_section = "unmatched"
        continue

    # Case header line.
    # Matched format: "10010112 | - | -"   (cid | stage | memo; name comes on next "Name:" line)
    # Unmatched format: "  10112154 | 核定階段 | 2019/07/23核定公告 | 變更臺北市..."  (all 4 on one line)
    m = re.match(r"^\s*(\d+)\s*(?:\[IN-PROCESSING\]\s*)?\|\s*([^|]*)\|\s*([^|]*)(?:\|\s*(.*))?\s*$", ln)
    if m:
        cid = m.group(1)
        stage = m.group(2).strip()
        memo = m.group(3).strip()
        name = (m.group(4) or "").strip()
        in_proc = "[IN-PROCESSING]" in ln
        entry = new_case_entry(cid, stage, memo, name, in_proc)
        if current_section == "matched":
            matched_cases.append(entry)
        else:
            unmatched_cases.append(entry)
        continue

    # Parsed line: "  Parsed: section=金華段四小段, parcel=126" (matched cases only)
    m = re.match(r"\s*Parsed: section=(.*?), parcel=(.*)", ln)
    if m and matched_cases:
        matched_cases[-1]["parsed"] = f"section={m.group(1).strip()}, parcel={m.group(2).strip()}"
        continue

    # Name line: "  Name: 變更臺北市..." (matched cases only)
    m = re.match(r"\s*Name: (.*)", ln)
    if m and matched_cases:
        matched_cases[-1]["name"] = m.group(1).strip()
        # clear memo since it was just "-" on the header line
        matched_cases[-1]["memo"] = ""
        continue

    # Gazette match line: "    -> 大安區-金華段四小段-126地號等3筆 (recno=242, stage=擬訂, track=事業計畫, gazette_date=2024-05-08)"
    m = re.match(r"\s*->\s*(.*?)\s*\(recno=(\d+),\s*stage=([^,\]]+),\s*track=([^,\]]+),\s*gazette_date=([^)]+)\)", ln)
    if m and matched_cases:
        matched_cases[-1]["gazette_matches"].append({
            "project_id": m.group(1).strip(),
            "recno": m.group(2).strip(),
            "stage": m.group(3).strip(),
            "track": m.group(4).strip(),
            "gazette_date": m.group(5).strip(),
        })
        continue

# ---- Build HTML ----
html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P_project168 Cross-Reference (by parcel)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 20px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
  .stats {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; font-size: 0.95rem; }}
  .stat {{ font-weight: 600; }}
  .stat .val {{ font-size: 1.1rem; color: #0969da; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; font-size: 0.88rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f6f8fa; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafbfc; }}
  .in-proc {{ background: #ffeef5 !important; }}
  .badge-inproc {{ background: #d6336c; color: #fff; font-size: 0.7rem; padding: 1px 6px; border-radius: 8px; font-weight: 600; }}
  .badge-approved {{ background: #198754; color: #fff; font-size: 0.7rem; padding: 1px 6px; border-radius: 8px; font-weight: 600; }}
  .gmatch {{ margin: 4px 0; padding: 6px; background: #f1f8ff; border-radius: 4px; border-left: 3px solid #0969da; }}
  .gmatch b {{ color: #0969da; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.82rem; }}
  .unmatched-list {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.82rem; line-height: 1.5; }}
  .unmatched-list div {{ margin: 2px 0; }}
  .note {{ font-size: 0.85rem; color: #57606a; margin-top: 0.5rem; }}
  .search-box {{ margin-bottom: 1rem; }}
  .search-box input {{ width: 100%; padding: 8px; font-size: 0.9rem; border: 1px solid #d0d7de; border-radius: 4px; }}
  .section-intro {{ font-size: 0.9rem; color: #57606a; margin-bottom: 0.75rem; }}
</style>
</head>
<body>

<h1>P_project168 Cross-Reference (by parcel)</h1>

<div class="stats">
  <div><span class="stat">Gazette date:</span> <span class="val">{stats.get('gazette_date','')}</span></div>
  <div><span class="stat">P_project168 total:</span> <span class="val">466</span></div>
  <div><span class="stat">Not found by case_id:</span> <span class="val">{stats.get('not_found_by_case_id','')}</span></div>
  <div><span class="stat">Matched by parcel:</span> <span class="val">{stats.get('matched_by_parcel','')}</span></div>
  <div><span class="stat">Still unmatched:</span> <span class="val">{stats.get('still_unmatched','')}</span></div>
</div>

<h2>1. Matched by parcel ({len(matched_cases)} cases)</h2>
<p class="section-intro">These platform cases were not found by case_id but matched a gazette project by section + first parcel.</p>
<div class="search-box">
  <input type="text" id="matchedSearch" placeholder="Filter matched cases by case ID, stage, or name...">
</div>
<table id="matchedTable">
  <thead>
    <tr>
      <th style="width:70px">Case ID</th>
      <th style="width:110px">Platform stage</th>
      <th style="width:200px">Parsed section / parcel</th>
      <th style="width:340px">Platform case name</th>
      <th>Gazette match(es)</th>
    </tr>
  </thead>
  <tbody>
"""

for c in matched_cases:
    badge = '<span class="badge-inproc">IN-PROCESSING</span>' if c["in_processing"] else '<span class="badge-approved">已核定</span>'
    gmatches = ""
    for gm in c["gazette_matches"]:
        gmatches += (
            f'<div class="gmatch">'
            f'<b>{gm["project_id"]}</b> '
            f'(recno={gm["recno"]}, stage={gm["stage"]}, track={gm["track"]}, '
            f'gazette_date={gm["gazette_date"]})'
            f'</div>'
        )
    html += f"""
    <tr class="{'in-proc' if c['in_processing'] else ''}">
      <td class="mono">{c['cid']}</td>
      <td class="mono">{c['stage']} {badge}</td>
      <td class="mono">{c['parsed']}</td>
      <td>{c['name']}</td>
      <td>{gmatches if gmatches else '—'}</td>
    </tr>
    """

html += f"""
  </tbody>
</table>

<h2>2. Still unmatched ({len(unmatched_cases)} cases)</h2>
<p class="section-intro">Platform cases not found by case_id and not matched by parcel either. Mostly <i>擬訂</i> cases from 2023–2026 that may not yet be in any gazette.</p>
<div class="search-box">
  <input type="text" id="unmatchedSearch" placeholder="Filter unmatched cases...">
</div>
<div class="unmatched-list" id="unmatchedList">
"""

for c in unmatched_cases:
    html += f'<div><span class="mono">{c["cid"]}</span> | {c["stage"]} | {c["memo"]} | {c["name"]}</div>\n'

html += f"""
</div>

<p class="note">
Generated from <code>data/p168_crossref_by_parcel_report.txt</code>.<br>
IN-PROCESSING rows are cases on the Taipei platform whose stage is not <i>核定階段</i> (not yet approved).
</p>

<script>
function setupSearch(inputId, tableIdOrListId, isTable) {{
  const input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener("input", function () {{
    const term = this.value.toLowerCase();
    if (isTable) {{
      const rows = document.querySelectorAll("#" + tableIdOrListId + " tbody tr");
      rows.forEach(row => {{
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? "" : "none";
      }});
    }} else {{
      const items = document.querySelectorAll("#" + tableIdOrListId + " div");
      items.forEach(item => {{
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(term) ? "" : "none";
      }});
    }}
  }});
}}
setupSearch("matchedSearch", "matchedTable", true);
setupSearch("unmatchedSearch", "unmatchedList", false);
</script>

</body>
</html>"""

OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT} ({len(matched_cases)} matched, {len(unmatched_cases)} unmatched)")
