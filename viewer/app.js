"use strict";

const W = 960, PAD = 60, COL_W = 130;
const KIND_COLOR = { revision: "#1d4ed8", track: "#0f766e", section: "#b45309" };
const KIND_LABEL = { revision: "版本", track: "事業種類", section: "區段" };

const TRACK_ORDER = ["事業計畫", "權利變換", "事業計畫、權利變換", "事業概要", "都市更新計畫", "其他"];

// Track column positions: left, middle, right
function trackPosition(track) {
  if (track.includes("事業計畫") && !track.includes("權利變換")) return 0; // 事業計畫, 事業概要, 都市更新計畫 -> left
  if (track.includes("事業計畫") && track.includes("權利變換")) return 1; // 事業計畫、權利變換 -> middle
  return 2; // 權利變換, 其他 -> right
}
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

function getNodeMilestoneBadges(node) {
  const links = node.links || {};
  const national = links.milestones_national || {};
  const taipei = links.milestones_taipei || {};
  const badges = [];
  if (Object.keys(national).length > 0) badges.push('<span class="node-milestone-badge national" title="國土署里程碑">國</span>');
  if (Object.keys(taipei).length > 0) badges.push('<span class="node-milestone-badge taipei" title="台北市里程碑">北</span>');
  return badges.join("");
}

// Portal field labels captured from r_progress_detail.aspx DOM (id="detail_<field>")
const IMPL_LABELS = {
  Exe_Way: "實施方式",
  Base_Area: "基地面積",
  Landkind1: "土地使用分區1",
  Landkind2: "土地使用分區2",
  Landkind3: "土地使用分區3",
  Landkind1_Area: "使用分區1面積",
  Landkind2_Area: "使用分區2面積",
  Landkind3_Area: "使用分區3面積",
  Old_Doors: "原戶數",
  Settle_Old_Doors: "安置原住戶",
  Settle_Doors: "安置違建戶",
  New_Parkings: "更新後汽車停車位",
  New_Parkings2: "更新後機車停車位",
  Road_Length: "開闢道路長度",
  Road_Area: "開闢道路面積",
  Road_Eng_Fee: "開闢道路工程費用",
  Sidewalk_Length: "開闢人行道長度",
  Sidewalk_Area: "開闢人行道面積",
  Urban_Renew_Fee: "實施都市更新費用",
  Private_Area: "私有土地面積",
  State_Area: "國有土地面積",
  Muni_Area: "市有土地面積",
  Land_Owners_Pir: "私有土地所有權人數",
  StateLand1_Owner: "國有土地管理機關1所有人",
  StateLand2_Owner: "國有土地管理機關2所有人",
  StateLand3_Owner: "國有土地管理機關3所有人",
  StateLand1_Area: "國有土地管理機關1面積",
  StateLand2_Area: "國有土地管理機關2面積",
  StateLand3_Area: "國有土地管理機關3面積",
  StateLand4_Owner: "國有土地管理機關4所有人",
  StateLand5_Owner: "公有土地管理機關1所有人",
  StateLand6_Owner: "公有土地管理機關2所有人",
  StateLand4_Area: "國有土地管理機關4面積",
  StateLand5_Area: "公有土地管理機關1面積",
  StateLand6_Area: "公有土地管理機關2面積",
  VolumeTurn_Area: "容積移轉面積",
  case_id: "資料來源案件",
  review_flags: "審查標記",
};
const REWARD_LABELS = {
  F0: "基準容積",
  F: "允建容積",
  F3: "都市更新獎勵",
  F5: "其他容積獎勵",
  F5_3: "人行步道面積",
  Case_921_311_Area: "921.311震災案",
  Old_Apartment_Area: "老舊公寓獎勵",
  Radiation_Room_Area: "輻射屋獎勵",
  High_Ion_Area: "高氯離子獎勵",
  Others_Area: "其他獎勵",
  House_Use_Area: "住宅使用容積",
  Eng_Use_Area: "工業使用容積",
  Busi_Use_Area: "商業使用容積",
  Live_Houses: "住戶單元數",
  Busi_Unit: "商業單元數",
  Law_Car_Parking: "法定汽車停車位",
  Law_Moto_Parking: "法定機車停車位",
  Max_Flr_Num: "最大樓層數",
  Under_Flr_Area: "地下層樓地板面積",
  case_id: "資料來源案件",
  review_flags: "審查標記",
};

function renderObjectCard(title, badgeClass, badgeText, obj, labels) {
  const entries = Object.entries(obj || {}).filter(([, v]) => v !== "" && v !== null && v !== undefined);
  if (entries.length === 0) return "";
  let html = `<details class="milestone-card" open>
    <summary class="milestone-summary">
      <span class="milestone-title">${escapeHtml(title)}</span>
      <span class="milestone-badge ${badgeClass}">${escapeHtml(badgeText)}</span>
    </summary>
    <dl class="milestone-list">`;
  for (const [key, val] of entries) {
    const label = labels[key] || key;
    html += `<div class="milestone-row">
      <dt class="milestone-label">${escapeHtml(label)}</dt>
      <dd class="milestone-date">${escapeHtml(String(val))}</dd>
    </div>`;
  }
  html += `</dl></details>`;
  return html;
}

function renderImplementation(project) {
  if (!project.implementation || Object.keys(project.implementation).length === 0) return "";
  return renderObjectCard("執行階段", "taipei", "北", project.implementation, IMPL_LABELS);
}

function renderRewards(project) {
  if (!project.rewards || Object.keys(project.rewards).length === 0) return "";
  return renderObjectCard("獎勵資料", "taipei", "北", project.rewards, REWARD_LABELS);
}

function renderMilestones(project, nodes) {
  const links = project.links || {};
  const national = links.milestones_national || {};
  const taipei = links.milestones_taipei || {};
  const twurUrl = links.twur || "";

  let html = "";

  // National portal milestones (推動歷程)
  if (Object.keys(national).length > 0) {
    html += `<details class="milestone-card" open>
      <summary class="milestone-summary">
        <span class="milestone-title">推動歷程 (國土署)</span>
        <span class="milestone-badge national">國</span>
      </summary>
      <dl class="milestone-list">`;
    for (const [label, date] of Object.entries(national)) {
      html += `<div class="milestone-row">
        <dt class="milestone-label">${escapeHtml(label)}</dt>
        <dd class="milestone-date">${escapeHtml(date)}</dd>
        <span class="milestone-badge national">國</span>
      </div>`;
    }
    html += `</dl></details>`;
  }

  // Taipei platform milestones (階段辦理過程)
  if (Object.keys(taipei).length > 0) {
    html += `<details class="milestone-card" open>
      <summary class="milestone-summary">
        <span class="milestone-title">階段辦理過程 (台北市)</span>
        <span class="milestone-badge taipei">北</span>
      </summary>
      <dl class="milestone-list">`;
    for (const [label, date] of Object.entries(taipei)) {
      html += `<div class="milestone-row">
        <dt class="milestone-label">${escapeHtml(label)}</dt>
        <dd class="milestone-date">${escapeHtml(date)}</dd>
        <span class="milestone-badge taipei">北</span>
      </div>`;
    }
    html += `</dl></details>`;
  } else if (twurUrl) {
    // Progressive loading placeholder for Taipei data
    html += `<details class="milestone-card milestone-placeholder">
      <summary class="milestone-summary">
        <span class="milestone-title">階段辦理過程 (台北市)</span>
        <span class="milestone-badge taipei">北</span>
      </summary>
      <div class="milestone-placeholder-content">
        資料未取得 · <a href="${escapeHtml(twurUrl)}" target="_blank" rel="noopener">前往入口網查看</a>
      </div>
    </details>`;
  }

  return html;
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
    ` · ${window.PROJECTS.published_date || window.PROJECTS.generated_at || ""}`;

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
    const shown = projects.filter(matches).sort((a, b) => {
      // Sort by earliest date (ascending)
      const dateA = a.nodes.reduce((min, n) => n.date < min ? n.date : min, "9999-12-31");
      const dateB = b.nodes.reduce((min, n) => n.date < min ? n.date : min, "9999-12-31");
      return dateA.localeCompare(dateB);
    });
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
    // Sort columns by track position (left -> middle -> right), then by area
    const colKeys = Object.keys(columns).sort((a, b) => {
      const trackA = a.split("（")[0];
      const trackB = b.split("（")[0];
      const posDiff = trackPosition(trackA) - trackPosition(trackB);
      if (posDiff !== 0) return posDiff;
      return a.localeCompare(b);
    });
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
      const badges = getNodeMilestoneBadges(n);
      s += `<g class="node ${n.is_current ? "current" : ""}" transform="translate(${p2.x},${p2.y})">
        <circle r="9"></circle>
        <text class="title" x="14" y="3">${escapeHtml(label)}</text>
        <text class="sub" x="14" y="15">${escapeHtml(n.track)}${n.area ? "（" + escapeHtml(n.area) + "區段）" : ""}</text>
        ${badges ? `<foreignObject x="18" y="-12" width="32" height="16"><div xmlns="http://www.w3.org/1999/xhtml" style="display:flex;gap:2px;">${badges}</div></foreignObject>` : ""}
      </g>`;
    });
    s += "</svg>";

    const border = p.borderline || [];
    if (border.length) {
      s += `<p class="flag">⚠ 臨界對（相似度 0.5–0.7，未自動合併，待人工檢視）：` +
        border.map(b => `編號 ${b[0]} ↔ ${b[1]}（${b[2]}）`).join("；") + "</p>";
    }

    // Detail table with tiered columns (essential + full)
    const essentialCols = ["recno", "date", "stage", "track", "is_current", "case_name", "land", "section", "implementer", "planner", "review_flags", "auto_fixes", "milestones"];
    const fullCols = ["parcels", "aliases", "land_count", "orig_count", "named_anchor", "area_section"];
    const allCols = [...essentialCols, ...fullCols];

    let rows = nodes.map(n => {
      const rec = p.nodes.find(x => x.recno === n.recno);
      const isCur = rec.is_current ? ' <span class="badge">現況</span>' : "";
      const cells = allCols.map(col => {
        let val = "";
        if (col === "is_current") {
          val = rec.is_current ? '<span class="badge">現況</span>' : "";
        } else if (col === "review_flags") {
          val = (rec.review_flags || []).join("、");
        } else if (col === "auto_fixes") {
          val = (rec.auto_fixes || []).join("、");
        } else if (col === "parcels" || col === "aliases") {
          val = JSON.stringify(rec[col] || []);
        } else if (col === "milestones") {
          val = getNodeMilestoneBadges(rec);
        } else {
          val = rec[col] !== undefined ? escapeHtml(String(rec[col])) : "";
        }
        const tier = essentialCols.includes(col) ? "essential" : "full";
        return `<td data-tier="${tier}">${val}</td>`;
      }).join("");
      return `<tr class="${rec.is_current ? "current" : ""}">${cells}</tr>`;
    }).join("");

    const headerCells = allCols.map(col => {
      const tier = essentialCols.includes(col) ? "essential" : "full";
      const label = {
        recno: "編號", date: "核定日期", stage: "階段", track: "事業種類",
        is_current: "現況", case_name: "案名", land: "地號", section: "區段",
        implementer: "實施者", planner: "更新規劃單位",
        review_flags: "審查標記", auto_fixes: "自動修正",
        milestones: "里程碑",
        parcels: "地號清單", aliases: "地號別名", land_count: "地號數",
        orig_count: "原地號數", named_anchor: "命名錨點", area_section: "行政區段"
      }[col] || col;
      return `<th data-tier="${tier}">${label}</th>`;
    }).join("");

    s += `<div class="table-wrap"><table class="recs"><thead><tr>${headerCells}</tr></thead><tbody>${rows}</tbody></table></div>
    <button id="expand-toggle" class="expand-btn" data-expanded="false">展開全部</button>`;

    // Render 相關連結 section
    const links = p.links || {};
    if (links.twur || (links.taipei && links.taipei.length)) {
      s += `<div class="related-links"><h3>相關連結</h3><ul>`;
      if (links.twur) {
        s += `<li><a href="${escapeHtml(links.twur)}" target="_blank" rel="noopener">都市更新入口網 (twur.nlma.gov.tw)</a></li>`;
      }
      if (links.taipei && links.taipei.length) {
        links.taipei.forEach(cid => {
          const url = `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cid}`;
          s += `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener">臺北市都市更新審議服務平台 (case_id: ${cid})</a></li>`;
        });
      }
      s += `</ul></div>`;
    }

    // Render milestone timelines
    s += renderMilestones(p, nodes);

    // Implementation (執行階段) / rewards (獎勵資料) cards — schema v2, render only when populated
    s += p.implementation ? renderImplementation(p) : "";
    s += p.rewards ? renderRewards(p) : "";

    detail.innerHTML = s;

    // Toggle for full columns
    const toggleBtn = detail.querySelector("#expand-toggle");
    if (toggleBtn) {
      toggleBtn.onclick = () => {
        const expanded = toggleBtn.dataset.expanded === "true";
        toggleBtn.dataset.expanded = expanded ? "false" : "true";
        toggleBtn.textContent = expanded ? "展開全部" : "收起";
        const displayValue = expanded ? "none" : "table-cell";
        detail.querySelectorAll("td[data-tier='full'], th[data-tier='full']").forEach(el => {
          el.style.display = displayValue;
        });
      };
    }
  }

  filter.addEventListener("input", renderList);
  renderList();
}

function escapeHtml(t) {
  return String(t).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

document.addEventListener("DOMContentLoaded", init);