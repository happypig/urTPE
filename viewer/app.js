"use strict";

const W = 960, PAD = 60, COL_W = 130;
const KIND_COLOR = { revision: "#1d4ed8", track: "#0f766e", section: "#b45309" };
const KIND_LABEL = { revision: "版本", track: "事業種類", section: "區段" };

const TRACK_ORDER = ["事業計畫", "權利變換", "事業計畫、權利變換", "事業概要", "都市更新計畫", "其他"];
const DISTRICT_COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#06b6d4",
  "#ec4899", "#84cc16", "#f97316", "#14b8a6", "#6366f1", "#a16207",
];

function districtColor(d) {
  let h = 0;
  for (const ch of d) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return DISTRICT_COLORS[h % DISTRICT_COLORS.length];
}

function byDateNodes(nodes) {
  return nodes.slice().sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? -1 : 1;
    return a.recno - b.recno;
  });
}

function init() {
  const meta = document.getElementById("meta");
  const list = document.getElementById("list");
  const filter = document.getElementById("filter");
  const filters = document.getElementById("filters");
  const rcount = document.getElementById("rcount");

  if (!window.PROJECTS || !window.PROJECTS.projects) {
    meta.textContent = "未載入資料（缺少 projects.data.js）";
    return;
  }
  const projects = window.PROJECTS.projects;
  const total = projects.length;
  meta.textContent =
    `${window.PROJECTS.counts.projects} 個專案 / ${window.PROJECTS.counts.records} 筆記錄` +
    ` · ${window.PROJECTS.generated_at || ""}`;

  const sel = { district: new Set(), year: new Set(), track: new Set() };
  const districts = [...new Set(projects.map(p => p.district))].sort();
  const years = [...new Set(projects.flatMap(p => p.nodes.map(n => n.date.slice(0, 4))))]
    .sort((a, b) => (a < b ? 1 : -1));
  const DIMS = [
    { key: "district", label: "地區", options: districts },
    { key: "year", label: "年度", options: years },
    { key: "track", label: "事業種類", options: TRACK_ORDER },
  ];

  const dropdowns = [];
  DIMS.forEach(dim => {
    const wrap = document.createElement("div");
    wrap.className = "dd";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dd-btn";
    const panel = document.createElement("div");
    panel.className = "dd-panel";
    panel.hidden = true;

    function refreshBtn() {
      const n = sel[dim.key].size;
      btn.textContent = dim.label + (n ? `（${n}）` : "") + " ▾";
    }
    function buildOptions() {
      panel.innerHTML = "";
      const actions = document.createElement("div");
      actions.className = "dd-actions";
      const all = document.createElement("button");
      all.type = "button";
      all.textContent = "全選";
      const clear = document.createElement("button");
      clear.type = "button";
      clear.textContent = "清除";
      actions.append(all, clear);
      all.onclick = e => {
        e.stopPropagation();
        sel[dim.key] = new Set(dim.options);
        panel.querySelectorAll("input[type=checkbox]").forEach(cb => cb.checked = true);
        refreshBtn();
        renderList();
      };
      clear.onclick = e => {
        e.stopPropagation();
        sel[dim.key].clear();
        panel.querySelectorAll("input[type=checkbox]").forEach(cb => cb.checked = false);
        refreshBtn();
        renderList();
      };
      panel.appendChild(actions);
      dim.options.forEach(opt => {
        const lab = document.createElement("label");
        lab.className = "dd-opt";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.value = opt;
        cb.checked = sel[dim.key].has(opt);
        cb.onchange = () => {
          if (cb.checked) sel[dim.key].add(opt);
          else sel[dim.key].delete(opt);
          refreshBtn();
          renderList();
        };
        const span = document.createElement("span");
        span.textContent = opt;
        lab.append(cb, span);
        panel.appendChild(lab);
      });
    }
    btn.onclick = e => {
      e.stopPropagation();
      const wasHidden = panel.hidden;
      dropdowns.forEach(d => d.close());
      if (wasHidden) {
        buildOptions();
        panel.hidden = false;
      }
      refreshBtn();
    };
    wrap.append(btn, panel);
    filters.appendChild(wrap);
    dropdowns.push({ close: () => { panel.hidden = true; } });
    refreshBtn();
  });

  document.addEventListener("click", () => dropdowns.forEach(d => d.close()));

  let activePid = null;

  function matches(p) {
    if (sel.district.size && !sel.district.has(p.district)) return false;
    if (sel.year.size) {
      const yrs = new Set(p.nodes.map(n => n.date.slice(0, 4)));
      let hit = false;
      sel.year.forEach(y => { if (yrs.has(y)) hit = true; });
      if (!hit) return false;
    }
    if (sel.track.size) {
      const trs = new Set(p.nodes.map(n => n.track));
      let hit = false;
      sel.track.forEach(t => { if (trs.has(t)) hit = true; });
      if (!hit) return false;
    }
    const q = filter.value.trim();
    if (q) {
      const hay = `${p.project_id} ${p.district} ${p.section} ${p.implementer} ${p.name} ${p.member_recnos.join(" ")}`;
      if (!hay.includes(q)) return false;
    }
    return true;
  }

  function renderList() {
    const shown = projects.filter(matches);
    rcount.textContent = `顯示 ${shown.length} / ${total}`;
    list.innerHTML = "";
    if (!shown.length) {
      const empty = document.createElement("div");
      empty.className = "empty-item";
      empty.textContent = "沒有符合條件的專案";
      list.appendChild(empty);
      return;
    }
    shown.forEach(p => {
      const el = document.createElement("div");
      el.className = "item" + (p.project_id === activePid ? " active" : "");
      el.innerHTML = `<div class="pid"><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}</div>
        <div class="cnt">${p.member_recnos.length} 筆 · ${escapeHtml(p.implementer)}</div>`;
      el.onclick = () => { activePid = p.project_id; renderList(); renderDetail(p); };
      list.appendChild(el);
    });
  }

  function renderDetail(p) {
    const detail = document.getElementById("detail");
    const nodes = byDateNodes(p.nodes);
    const columns = {};
    nodes.forEach(n => {
      const col = `${n.track}${n.area ? "（" + n.area + "區段）" : ""}`;
      columns[col] = (columns[col] || 0) + 1;
    });
    const colKeys = Object.keys(columns);
    const colOf = n => {
      const c = `${n.track}${n.area ? "（" + n.area + "區段）" : ""}`;
      return colKeys.indexOf(c);
    };

    // Stable layout: row = ordinal in date order; column = track/area lane.
    const svgW = Math.max(W, colKeys.length * COL_W + PAD * 2);
    const svgH = nodes.length * 64 + PAD * 2;
    const pos = {};
    nodes.forEach((n, i) => {
      pos[n.recno] = {
        x: PAD + colOf(n) * COL_W + COL_W / 2,
        y: PAD + i * 64,
      };
    });

    let s = `<h2><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}</h2>
      <div class="district">${escapeHtml(p.district)} · ${escapeHtml(p.section)} · ${escapeHtml(p.implementer)} · 共 ${p.member_recnos.length} 筆</div>
      <div class="legend">
        <span class="rev">版本（核定時序）</span>
        <span class="trk">事業種類</span>
        <span class="sec">區段</span>
      </div>
      <svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet">`;

    p.edges.forEach(e => {
      const a = pos[e.from], b = pos[e.to];
      if (!a || !b) return;
      s += `<line class="edge ${e.kind}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
    });

    nodes.forEach(n => {
      const p2 = pos[n.recno];
      const label = `${n.recno} · ${n.date}${n.stage ? " " + n.stage : ""}`;
      s += `<g class="node ${n.is_current ? "current" : ""}" transform="translate(${p2.x},${p2.y})">
        <circle r="9"></circle>
        <text class="title" x="14" y="3">${escapeHtml(label)}</text>
        <text class="sub" x="14" y="15">${escapeHtml(n.track)}${n.area ? "（" + escapeHtml(n.area) + "區段）" : ""}</text>
      </g>`;
    });
    s += "</svg>";

    const border = p.borderline || [];
    let rows = nodes.map(n => {
      const rec = p.nodes.find(x => x.recno === n.recno);
      const isCur = rec.is_current ? ' <span class="badge">現況</span>' : "";
      return `<tr class="${rec.is_current ? "current" : ""}">
        <td>${rec.recno}</td><td>${rec.date}</td><td>${escapeHtml(rec.stage)}</td>
        <td>${escapeHtml(rec.track)}</td>${isCur}
      </tr>`;
    }).join("");
    s += `<table class="recs"><thead><tr><th>編號</th><th>核定日期</th><th>階段</th><th>事業種類</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;

    if (border.length) {
      s += `<p class="flag">⚠ 臨界對（相似度 0.5–0.7，未自動合併，待人工檢視）：` +
        border.map(b => `編號 ${b[0]} ↔ ${b[1]}（${b[2]}）`).join("；") + "</p>";
    }
    detail.innerHTML = s;
  }

  function escapeHtml(t) {
    return String(t).replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  filter.addEventListener("input", renderList);
  renderList();
}

document.addEventListener("DOMContentLoaded", init);