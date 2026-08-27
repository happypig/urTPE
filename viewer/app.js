"use strict";

const W = 960, PAD = 60, COL_W = 130;
const KIND_COLOR = { revision: "#1d4ed8", track: "#0f766e", section: "#b45309" };
const KIND_LABEL = { revision: "版本", track: "事業種類", section: "區段" };

const TRACK_ORDER = ["事業計畫", "權利變換", "事業計畫、權利變換", "事業概要", "都市更新計畫", "其他"];

// Construction-phase chain slots drawn beside the anchor record (facts §6.4/§12.1)
const CONSTRUCTION_CHAIN_SLOTS = ["建照核發日期", "開工日期", "使照核發日期"];
// Slot -> national-portal milestone label; a hit supplies the 國 badge (and the
// fallback value for the 使照 slot when 使照核發日期 is absent).
const NATIONAL_MAPPED_LABELS = { "使照核發日期": "使用核發日期" };
// Implementation summary callout on the anchor record.
const IMPLEMENTATION_CALLOUT_FIELDS = {
  Exe_Way: "實施方式",
  Base_Area: "基地面積",
  Old_Doors: "原戶數",
};

// Left-list stage chip: the latest of 建照/開工/使照 (使照 falls back to the
// national 使用核發日期). Colours: 建照 orange, 開工 red, 使照 green.
function constructionStage(p) {
  const STAGE_SLOTS = [
    { label: "建照核發日期", short: "建照", color: "#f59e0b" },
    { label: "開工日期", short: "開工", color: "#dc2626" },
    { label: "使照核發日期", short: "使照", color: "#16a34a", natKey: "使用核發日期" },
  ];
  const mt = (p.links || {}).milestones_taipei || {};
  const mn = (p.links || {}).milestones_national || {};
  let best = null;
  for (const s of STAGE_SLOTS) {
    let v = mt[s.label] || "";
    if (!v && s.natKey) v = mn[s.natKey] || "";
    if (!v) continue;
    let iso = String(v).replace(/\//g, "-");
    const roc = iso.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);
    if (roc) iso = `${1911 + Number(roc[1])}-${roc[2]}-${roc[3]}`;
    if (!best || iso > best.iso) best = { short: s.short, color: s.color, iso };
  }
  return best;
}

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

// 基本面積 color/style helper: returns {color, fontWeight} or null
function getBaseAreaStyle(areaStr) {
  if (!areaStr) return null;
  const cleaned = areaStr.replace(/,/g, "");
  const val = parseFloat(cleaned);
  if (isNaN(val) || val < 0) return null;
  if (val < 500) return { color: "#8b5cf6", fontWeight: "normal" };          // purple
  if (val < 1000) return null;                                                // default
  if (val < 2000) return { color: "#f59e0b", fontWeight: "normal" };          // orange
  if (val < 3000) return { color: "#f59e0b", fontWeight: "bold" };            // orange bold
  return { color: "#ef4444", fontWeight: "bold" };                            // red bold (>=3000)
}

function byDateNodes(nodes) {
  return nodes.slice().sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? -1 : 1;
    return a.recno - b.recno;
  });
}

function getNodeMilestoneBadges(node, project) {
  // Portal links live on the nodes (相關連結 section retired): 北 → anchored
  // Taipei case page; 國 (現況 node only) → national view page. Tooltips name
  // the destination (案<case_id> / view/<id>).
  const badges = [];
  const cases = (node.links || {}).taipei || [];
  if (cases.length) {
    badges.push(`<a class="node-milestone-badge taipei badge-link" href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cases[0]}" target="_blank" rel="noopener" title="案${cases[0]}">北</a>`);
  }
  const twur = project && project.links && project.links.twur;
  if (node.is_current && twur) {
    const vm = twur.match(/view\/(\d+)/);
    const label = vm ? `view/${vm[1]}` : "國土署入口網";
    badges.push(`<a class="node-milestone-badge national badge-link" href="${escapeHtml(twur)}" target="_blank" rel="noopener" title="${escapeHtml(label)}">國</a>`);
  }
  return badges.join("");
}

// Portal field labels captured from r_progress_detail.aspx DOM (id="detail_<field>")
const IMPL_LABELS = {
  Eng_Start_Date: "開工日期",
  Ulic_Date: "使照核發日期",
  Report_Date: "成果報備日期",
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
  Bui_Owners_Legal: "合法建物所有權人數",
  Land_Owners_Pub: "公有土地所有權人數",
  STATELAND2_OWNER: "國有土地管理機關2所有人",
  pc_afterUpdTotalValue: "總銷售金額",
  Welfare_Area: "公益設施面積",
  Road_Cost: "捐贈道路成本",
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
  F1: "△F1(㎡)",
  F2: "△F2(㎡)",
  F4: "△F4(㎡)",
  F6: "△F6(㎡)",
  F4_1: "△F4-1(㎡)",
  F4_2: "△F4-2(㎡)",
  F4_3: "△F4-3(㎡)",
  F5_1: "△F5-1(㎡)",
  F5_2: "△F5-2(㎡)",
  F5_4: "△F5-4(㎡)",
  F5_5: "△F5-5(㎡)",
  F5_6: "△F5-6(㎡)",
  Park_Area: "停車獎勵(㎡)",
  Park_Cars: "停車獎勵部數",
  TIME_REWARD: "時程獎勵",
  SCALE_REWARD: "規模獎勵",
  GREENBUILD_DESIGN: "綠建築標章之建築設計",
  SEISMIC_DESIGN: "耐震設計",
  WISDOMBUILD_DESIGN: "智慧建築標章之建築設計",
  ACCESSIBLE_DESIGN: "無障礙環境設計",
  NEWTECH: "新技術之應用",
  IMENVIRON: "改善都市環境",
  BUILDPLANDES1: "建築規劃設計(一)",
  BUILDPLANDES2: "建築規劃設計(二)",
  BUILDPLANDES3: "建築規劃設計(三)",
  BUILDPLANDES4: "建築規劃設計(四)",
  BUILDSAFE_CONDITION: "建築物結構安全條件",
  CHARITY_BUILD: "公益設施",
  CULTURAL_MAINTAIN: "文資保存及維護",
  DEVELOP_PUBFACILITY: "協助開闢公共設施用地",
  AGREEMENT_CONSTRUCTION: "全體同意採協議合建實施",
  PROREGENERAT1: "促進都市更新(一)",
  PROREGENERAT2: "促進都市更新(二)",
  VOLUME_HIGHER_REWARD: "高於法定容積部份核計之獎勵",
  ILLEGAL_FLOORAREA_REWARD: "處理違建戶之樓地板面積獎勵",
  name_reward_no: "獎勵上限規定",
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

// Construction-phase chain items beside the anchor record: 建照→開工→使照,
// rendered only for events that exist. 使照 falls back to the national portal's
// 使用核發日期; any national hit flags the node with the 國 badge. Construction
// events often belong to a sibling case rather than the anchor approval —
// when a slot's value exactly equals the emitted implementation payload's
// date, that payload's case_id rides along as provenance.
function buildConstructionChain(p) {
  const links = p.links || {};
  const taipei = links.milestones_taipei || {};
  const national = links.milestones_national || {};
  const sourceMap = links.milestones_source || {};
  const impl = p.implementation || {};
  const implCase = impl.case_id || "";
  const IMPL_SOURCE_FIELDS = { "開工日期": "Eng_Start_Date", "使照核發日期": "Ulic_Date" };
  const nodes = p.nodes || [];
  const anchoredByCase = {};
  for (const n of nodes) {
    for (const cid of ((n.links || {}).taipei || [])) anchoredByCase[cid] = n.recno;
  }
  const out = [];
  for (const slot of CONSTRUCTION_CHAIN_SLOTS) {
    let value = taipei[slot] || "";
    const natLabel = NATIONAL_MAPPED_LABELS[slot];
    const nationalHit = !!(natLabel && national[natLabel]);
    if (!value && nationalHit) value = national[natLabel];
    if (!value) continue;
    // national portal dates arrive in 民國 (110.10.25) — render western
    // (115 → 2026) so display and chronological sorting stay consistent.
    let dateStr = String(value);
    if (nationalHit) {
      const roc = dateStr.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);
      if (roc) {
        dateStr = `${1911 + Number(roc[1])}/${roc[2].padStart(2, "0")}/${roc[3].padStart(2, "0")}`;
      }
    }
    // provenance: implementation exact-match > milestones_source map >
    // national-only; anchored slots name their owning record.
    let provCase = "";
    if (!nationalHit) {
      const implField = IMPL_SOURCE_FIELDS[slot];
      if (implCase && implField && impl[implField] === value) provCase = implCase;
      else if (sourceMap[slot] && taipei[slot] === value) provCase = sourceMap[slot];
    }
    const ownerRecno = provCase !== "" && anchoredByCase[provCase] !== undefined
      ? anchoredByCase[provCase] : null;
    const anchored = ownerRecno !== null;
    const prov = provCase ? `案${provCase}${anchored ? `·編號${ownerRecno}` : ""}` : "";
    out.push({
      label: slot, date: dateStr, national: nationalHit, prov,
      case: provCase, anchored, ownerRecno,
    });
  }
  return out;
}

// Implementation summary rows for a record's callout (only populated fields).
// 4th row: non-empty 土地使用分區 values abbreviated and "/"-joined.
function buildImplCallout(impl) {
  impl = impl || {};
  const rows = [];
  for (const [key, label] of Object.entries(IMPLEMENTATION_CALLOUT_FIELDS)) {
    const v = impl[key];
    if (v !== undefined && v !== null && v !== "") rows.push({ label, value: String(v) });
  }
  const zones = [...new Set([impl.Landkind1, impl.Landkind2, impl.Landkind3]
    .filter(v => v !== undefined && v !== null && v !== "")
    .map(v => abbreviateZone(v)))];
  if (zones.length) rows.push({ label: "使用分區", value: zones.join("/") });
  return rows;
}

// Zone abbreviation: 第三種住宅區 → 住三, 第三之一種住宅區 → 住三之一,
// 第三種特定商業區 → 特商三, 住宅區(特) → 住特, 商三特(…) → 商三特,
// 道路用地 → 道路; unknown forms render verbatim.
function abbreviateZone(z) {
  let s = String(z).trim();
  const special = /\(特\)\s*$/.test(s);
  s = s.replace(/\([^)]*\)/g, "").trim();
  let m = s.match(/^第(.+?)種特定(.+?)$/);
  if (m) return "特" + zoneBase(m[2]) + m[1];
  m = s.match(/^第(.+?)種(.+?)$/);
  if (m) return zoneBase(m[2]) + m[1];
  m = s.match(/^(.+?)區$/);
  if (m) return zoneBase(m[1]) + (special ? "特" : "");
  if (s.endsWith("用地")) return s.slice(0, -2);
  return s;
}

function zoneBase(x) {
  x = String(x).replace(/區$/, "");
  return { "住宅": "住", "商業": "商", "工業": "工" }[x] || x;
}

// 相關連結 (debug toggle, default off): each city case_id joins to its
// anchored record's 案名 via nodes[].links.taipei; the national link shows
// the anchor (現況) record's 案名. Primary link surface is the graph itself.
function buildRelatedLinkLabels(p) {
  const nodes = p.nodes || [];
  const byCase = {};
  for (const n of nodes) {
    const anchored = (n.links || {}).taipei || [];
    for (const cid of anchored) byCase[cid] = n.case_name || "";
  }
  const anchor = nodes.find(n => n.is_current) || nodes[nodes.length - 1] || {};
  return { byCase, anchorName: anchor.case_name || "" };
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

  const sel = { district: new Set(), year: new Set(), track: new Set(), stage: new Set() };
  const districts = [...new Set(projects.map(p => p.district))].sort();
  const years = [...new Set(projects.flatMap(p => p.nodes.map(n => n.date.slice(0, 4))))]
    .sort((a, b) => (a < b ? 1 : -1));
  const DIMS = [
    { key: "district", label: "地區", options: districts },
    { key: "year", label: "年度", options: years },
    { key: "track", label: "事業種類", options: TRACK_ORDER },
    { key: "stage", label: "施工階段", options: ["建照", "開工", "使照"] },
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
    if (sel.stage.size) {
      const st = constructionStage(p);
      if (!st || !sel.stage.has(st.short)) return false;
    }
    const q = filter.value.trim();
    if (q) {
      const hay = `${p.project_id} ${p.district} ${p.section} ${p.implementer} ${p.name} ${p.member_recnos.join(" ")}`;
      if (!hay.includes(q)) return false;
    }
    return true;
  }

  function renderList() {
    // Sort by the 現況 record's recno, ascending.
    const curRecno = p => {
      const cur = p.nodes.find(n => n.is_current);
      return cur ? cur.recno : Number.MAX_SAFE_INTEGER;
    };
    const shown = projects.filter(matches).sort((a, b) => curRecno(a) - curRecno(b));
    // ... each item carries a 2-char construction stage chip: the latest of
    // 建照/開工/使照 (使照 falls back to the national 使用核發日期).
    const stageChip = p => {
      const st = constructionStage(p);
      return st ? `<span class="stage-badge" style="color:${st.color}">${st.short}</span>` : "";
    };
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
      const area = p.implementation?.Base_Area;
      const areaStyle = area ? getBaseAreaStyle(area) : null;
      const areaHtml = area && areaStyle
        ? ` · 基本面積 <span style="color:${areaStyle.color};font-weight:${areaStyle.fontWeight}">${escapeHtml(area)}</span>`
        : area ? ` · 基本面積 ${escapeHtml(area)}` : "";
      el.innerHTML = `<div class="pid"><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}${stageChip(p)}</div>
        <div class="cnt">${p.member_recnos.length} 筆 · ${escapeHtml(p.implementer)}${areaHtml}</div>`;
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

    // Timeline rows: approvals + construction events share the date order.
    // Events sit in a dedicated E) 執行階段 column (rightmost); attribution
    // edges color by source portal (pink Taipei / green national).
    const events = buildConstructionChain(p);
    const timeline = nodes.map(n => ({ kind: "approval", date: n.date, n }));
    events.forEach(e => timeline.push({
      kind: "event", date: String(e.date).replace(/\//g, "-"), e,
    }));
    timeline.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 :
      (a.kind === "approval" ? -1 : 1)));

    const hasEvents = events.length > 0;
    const eventColX = PAD + colKeys.length * COL_W + COL_W / 2;

    const pos = {};
    const evPos = {};
    timeline.forEach((t, i) => {
      if (t.kind === "approval") {
        pos[t.n.recno] = { x: PAD + colOf(t.n) * COL_W + COL_W / 2, y: PAD + i * 64 };
      } else {
        evPos[t.e.label] = { x: eventColX, y: PAD + i * 64 };
      }
    });

    // Callout selection: first carrying record + diff-triggered records only.
    // 使用分區 diffs compare as a SET (order-insensitive, post-dedupe).
    const normForCompare = (label, value) =>
      label === "使用分區" ? value.split("/").sort().join("/") : value;
    const callouts = [];
    let prevVals = null;
    let firstCarrier = true;
    nodes.forEach(n => {
      if (!n.implementation) return;
      const rows = buildImplCallout(n.implementation).map(r => ({
        label: r.label,
        value: r.value,
        changed: !!(prevVals && prevVals[r.label] !== undefined &&
                    normForCompare(r.label, prevVals[r.label]) !== normForCompare(r.label, r.value)),
      }));
      const anyChanged = rows.some(r => r.changed);
      if (firstCarrier || anyChanged) callouts.push({ n, rows });
      firstCarrier = false;
      prevVals = {};
      rows.forEach(r => { prevVals[r.label] = r.value; });
    });

    let svgW = Math.max(W, (colKeys.length + (hasEvents ? 1 : 0)) * COL_W + PAD * 2);
    if (hasEvents) svgW = Math.max(svgW, eventColX + 250);
    let svgH = PAD * 2 + timeline.length * 64;
    callouts.forEach(c => {
      svgH = Math.max(svgH, pos[c.n.recno].y + 84);
    });

    // Callout placement: collision-dodging spots, clamped into the viewBox.
    // Runs BEFORE the svg string is built so viewBox extensions take effect.
    const evRects = events.map(e => {
      const q = evPos[e.label];
      return { x: q.x - 8, y: q.y - 12, w: 240, h: 26 };
    });
    const placedBoxes = [];
    const hitsAny = (r, list) => list.some(o =>
      r.x < o.x + o.w && o.x < r.x + r.w && r.y < o.y + o.h && o.y < r.y + r.h);
    callouts.forEach(c => {
      const ownRecno = c.n.recno;
      const p2 = pos[ownRecno];
      const w = 150, h = c.rows.length * 14 + 6;
      const nodeRects = nodes
        .filter(n => n.recno !== ownRecno)
        .map(n => {
          const q = pos[n.recno];
          const headLen = (`${n.recno} · ${n.date}${n.stage ? " " + n.stage : ""}`).length;
          return { x: q.x - 10, y: q.y - 14, w: 14 + headLen * 6.5 + 40, h: 34 };
        });
      const spots = [
        { x: p2.x - 16 - w, y: p2.y + 20 },          // below-left
        { x: p2.x + 16,     y: p2.y + 20 },          // below-right
        { x: p2.x - 16 - w, y: p2.y - 10 - h },      // above-left
        { x: p2.x + 16,     y: p2.y - 10 - h },      // above-right
        { x: p2.x - 16 - w, y: p2.y + 46 },          // further below-left
        { x: p2.x + 16,     y: p2.y + 46 },          // further below-right
      ].map(s => ({
        x: Math.min(Math.max(s.x, 4), Math.max(4, svgW - w - 4)),
        y: Math.min(Math.max(s.y, 4), Math.max(4, svgH - h - 4)),
      }));
      const spot = spots.find(s => {
        const r = { x: s.x, y: s.y, w, h };
        return !hitsAny(r, nodeRects) && !hitsAny(r, evRects) && !hitsAny(r, placedBoxes);
      }) || spots[spots.length - 1];
      spot.w = w; spot.h = h;
      placedBoxes.push(spot);
      c.rect = spot;
      svgH = Math.max(svgH, spot.y + h + 16);
      svgW = Math.max(svgW, spot.x + w + 8);
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

    // Source-group edges: events group by provenance (Taipei carrying case /
    // national-only). Solid edge from each group's source node to the group's
    // first event; solid chain within a group; dashed between adjacent groups
    // colored by the incoming group. No edges to non-source records.
    const sameSource = (a, b) =>
      (a.national ? "national" : "case:" + (a.case || "")) ===
      (b.national ? "national" : "case:" + (b.case || ""));
    if (hasEvents) {
      events.forEach((e, i) => {
        const b = evPos[e.label];
        const colorCls = e.national ? "national" : "taipei";
        const groupStart = i === 0 || !sameSource(e, events[i - 1]);
        if (groupStart) {
          if (!e.national && e.anchored) {
            const a = pos[e.ownerRecno];
            if (a) s += `<line class="event-edge ${colorCls}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          } else if (e.national) {
            const cur = nodes.find(n => n.is_current) || nodes[nodes.length - 1];
            const a = pos[cur.recno];
            s += `<line class="event-edge national" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          }
          if (i > 0) {
            // dashed transition into the new group (incoming group's colour)
            const a = evPos[events[i - 1].label];
            s += `<line class="event-link ${colorCls} dashed" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          }
        } else {
          const a = evPos[events[i - 1].label];
          const dashed = sameSource(e, events[i - 1]) ? "" : " dashed";
          s += `<line class="event-link ${colorCls}${dashed}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
        }
      });
    }

    nodes.forEach(n => {
      const p2 = pos[n.recno];
      const label = `${n.recno} · ${n.date}${n.stage ? " " + n.stage : ""}`;
      const badges = getNodeMilestoneBadges(n, p);
      const ghost = n.track === "事業概要" ? " ghost" : "";
      // badges sit ABOVE the first line, aligned to its left edge — never
      // covering the label or the track line beneath.
      s += `<g class="node${ghost} ${n.is_current ? "current" : ""}" transform="translate(${p2.x},${p2.y})">
        <circle r="9"></circle>
        <text class="title" x="14" y="3">${escapeHtml(label)}</text>
        <text class="sub" x="14" y="15">${escapeHtml(n.track)}${n.area ? "（" + escapeHtml(n.area) + "區段）" : ""}</text>
        ${badges ? `<foreignObject x="14" y="-27" width="34" height="15"><div xmlns="http://www.w3.org/1999/xhtml" style="display:flex;gap:2px;">${badges}</div></foreignObject>` : ""}
      </g>`;
    });

    // Construction event nodes (black dots; label hyperlinks to its portal).
    if (hasEvents) {
      events.forEach(e => {
        const b = evPos[e.label];
        const colorCls = e.national ? "national" : "taipei";
        const href = (!e.national && !e.anchored && e.case)
          ? `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${e.case}`
          : "";
        const inner = `<circle r="6"></circle>
          <text class="event-label ${colorCls}" x="11" y="3">${escapeHtml(e.label)}：${escapeHtml(e.date)}</text>
          ${e.prov ? `<text class="chain-prov" x="11" y="14">${escapeHtml(e.prov)}</text>` : ""}
          ${e.national ? `<foreignObject x="-5" y="-24" width="18" height="14"><div xmlns="http://www.w3.org/1999/xhtml"><span class="node-milestone-badge national" title="國土署里程碑">國</span></div></foreignObject>` : ""}`;
        s += `<g class="event-node" transform="translate(${b.x},${b.y})">` +
          (href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${inner}</a>` : inner) +
          `</g>`;
      });
    }

    // Per-record implementation callouts: render the pre-placed rects.
    callouts.forEach(c => {
      const r = c.rect;
      const np = pos[c.n.recno];
      const rowsHtml = c.rows.map(row =>
        `<div class="impl-callout-row"><span>${escapeHtml(row.label)}</span><b class="${row.changed ? "callout-diff" : ""}">${escapeHtml(row.value)}</b></div>`
      ).join("");
      const apex = { x: np.x - 7, y: np.y + 9 };
      let tail;
      if (r.x + r.w <= np.x) {          // box left of node → tail on right edge
        tail = `${r.x + r.w},${r.y + 4} ${apex.x},${apex.y} ${r.x + r.w},${r.y + r.h - 4}`;
      } else {                          // box right of node → tail on left edge
        tail = `${r.x},${r.y + 4} ${apex.x + 14},${apex.y} ${r.x},${r.y + r.h - 4}`;
      }
      s += `<polygon class="callout-tail" points="${tail}"></polygon>`;
      s += `<foreignObject x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}"><div xmlns="http://www.w3.org/1999/xhtml" class="impl-callout">${rowsHtml}</div></foreignObject>`;
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
          val = getNodeMilestoneBadges(rec, p);
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

    // 相關連結 (debug, default OFF): portal links live on the graph nodes;
    // this section stays available behind an explicit toggle.
    const links = p.links || {};
    if (links.twur || (links.taipei && links.taipei.length)) {
      const linkLabels = buildRelatedLinkLabels(p);
      s += `<div class="links-debug">
        <label class="links-debug-toggle"><input type="checkbox" id="links-toggle"> 相關連結（除錯）</label>
        <div id="links-section" hidden><h3>相關連結</h3><ul>`;
      if (links.twur) {
        const nm = linkLabels.anchorName;
        s += `<li><a href="${escapeHtml(links.twur)}" target="_blank" rel="noopener">都市更新入口網 (twur.nlma.gov.tw)</a>${nm ? ` — <span class="link-case-name">${escapeHtml(nm)}</span>` : ""}</li>`;
      }
      if (links.taipei && links.taipei.length) {
        links.taipei.forEach(cid => {
          const url = `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cid}`;
          const nm = linkLabels.byCase[cid] || "";
          s += `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener">臺北市都市更新審議服務平台 (case_id: ${cid})</a>${nm ? ` — <span class="link-case-name">${escapeHtml(nm)}</span>` : ""}</li>`;
        });
      }
      s += `</ul></div></div>`;
    }

    // Render milestone timelines
    s += renderMilestones(p, nodes);

    // Implementation (執行階段) / rewards (獎勵資料) cards — schema v2, render only when populated
    s += p.implementation ? renderImplementation(p) : "";
    s += p.rewards ? renderRewards(p) : "";

    detail.innerHTML = s;

    // 相關連結 debug toggle (default off)
    const linksToggle = detail.querySelector("#links-toggle");
    const linksSection = detail.querySelector("#links-section");
    if (linksToggle && linksSection) {
      linksToggle.onchange = () => { linksSection.hidden = !linksToggle.checked; };
    }

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