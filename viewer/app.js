"use strict";

const W = 960, H = 560, PAD = 60, COL_W = 130;
const KIND_COLOR = { revision: "#1d4ed8", track: "#0f766e", section: "#b45309" };
const KIND_LABEL = { revision: "版本", track: "事業種類", section: "區段" };

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

  if (!window.PROJECTS || !window.PROJECTS.projects) {
    meta.textContent = "未載入資料（缺少 projects.data.js）";
    return;
  }
  const projects = window.PROJECTS.projects;
  meta.textContent =
    `${window.PROJECTS.counts.projects} 個專案 / ${window.PROJECTS.counts.records} 筆記錄` +
    ` · ${window.PROJECTS.generated_at || ""}`;

  let activePid = null;

  function renderList() {
    const q = filter.value.trim();
    const shown = projects.filter(p => {
      if (!q) return true;
      const hay = `${p.project_id} ${p.district} ${p.section} ${p.implementer} ${p.name} ${p.member_recnos.join(" ")}`;
      return hay.includes(q);
    });
    list.innerHTML = "";
    shown.forEach(p => {
      const el = document.createElement("div");
      el.className = "item" + (p.project_id === activePid ? " active" : "");
      el.innerHTML = `<div class="pid">${escapeHtml(p.project_id)}</div>
        <div class="cnt">${p.member_recnos.length} 筆 · ${p.implementer}</div>`;
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
    const svgH = Math.max(H, nodes.length * 64 + PAD * 2);
    const pos = {};
    nodes.forEach((n, i) => {
      pos[n.recno] = {
        x: PAD + colOf(n) * COL_W + COL_W / 2,
        y: PAD + i * 64,
      };
    });

    let s = `<h2>${escapeHtml(p.project_id)}</h2>
      <div class="district">${escapeHtml(p.district)} · ${escapeHtml(p.section)} · ${escapeHtml(p.implementer)} · 共 ${p.member_recnos.length} 筆</div>
      <div class="legend">
        <span class="rev">版本（核定時序）</span>
        <span class="trk">事業種類</span>
        <span class="sec">區段</span>
      </div>
      <svg width="${svgW}" height="${svgH}">`;

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
        <text class="sub" x="14" y="15">${n.track}${n.area ? "（" + n.area + "區段）" : ""}</text>
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