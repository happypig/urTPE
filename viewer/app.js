"use strict";

const W = 960, PAD = 60, COL_W = 130, NODE_ROW = 64, EVENT_ROW = 32;
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
// §5.2.5 區段 token from the case_name tail: -東區/-西區/-北區/-南區, bare
// directionals (案-北), and 甲/乙區段. Empty when the name is a base case.
function areaTokenFromName(name) {
  const s = String(name || "");
  let m = s.match(/[-(（]\s*([東西南北中])區\s*[）)]?\s*$/);
  if (m) return m[1] + "區";
  m = s.match(/[-(（]\s*([東西南北中])\s*[）)]?\s*$/);
  if (m) return m[1] + "區";
  m = s.match(/([甲乙丙丁戊])區段\s*[）)]?\s*$/);
  if (m) return m[1] + "區段";
  return "";
}

// §5.3.2 four-column grid: exact track → column mapping.
const TRACK_COL1 = ["事業概要", "事業計畫", "都市更新計畫"];
const TRACK_COL2 = ["事業計畫、權利變換", "都市計畫、權利變換"];
function trackPosition(track) {
  const t = String(track).trim();
  if (TRACK_COL2.includes(t)) return 1;
  if (TRACK_COL1.includes(t)) return 0;
  return 2; // 權利變換, 其他
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

// 基地面積 color/style helper: returns {color, fontWeight} or null
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
      slot_idx: CONSTRUCTION_CHAIN_SLOTS.indexOf(slot),
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

// 相關連結 (debug toggle, default off): each city case_id resolves its display
// name via the fallback chain — anchored node's 案名 → links.case_milestones
// context ("里程碑 N 筆") → links.search_rejected stored case_name → ghost
// node case_name → raw case_id. The national link shows the anchor record's
// 案名. Primary link surface is the graph itself.
// never-approved classification: every harvested case schedule is
// 駁回/撤回/失效 and there is no national page — the unit will never appear
// on the portal (§6.14 E2/E3).
function neverApproved(p) {
  const scheds = Object.values((p.links || {}).case_schedules || {});
  return scheds.length > 0
    && scheds.every(v => v === "已駁回" || v === "自行撤回" || v === "已失效")
    && !(p.links || {}).twur;
}
const caseScheduleOf = (p, cid) => ((p.links || {}).case_schedules || {})[cid] || "";
// §10 per-track stage text: combined-track nodes whose 事業計畫/權利變換
// ordinals differ render "stage1/stage2" (事業計畫 first); uniform keeps the
// single form.
function perTrackStageText(n) {
  if ((n.track || "") !== "事業計畫、權利變換") return n.stage ? " " + n.stage : "";
  const s1 = n.stage_事業計畫 || n.stage || "";
  const s2 = n.stage_權利變換 || "";
  if (!s1 && !s2) return "";
  if (!s2 || s2 === s1) return s1 ? " " + s1 : "";
  return ` ${s1}/${s2}`;
}
// 已核准 is the default focus state — only exceptional schedules (已駁回/
// 施工中/自行撤回/已失效/審查中) render as badges.
const scheduleBadgeText = s => (!s || s === "已核准") ? "" : ` [${s}]`;

// D12-BEGIN (add-virtual-node-ordering-and-chain — pure helpers, node-tested)
// Effective comparison key: real nodes use their ANCHORED case_id
// (links.taipei[0]); virtual nodes their own case_id; case-less real nodes
// yield "" (sorts first — "" < any case_id keeps the order strictly ascending).
// Ascending case_id == application-attempt order (YY序號), load-independent.
function effectiveCaseKey(n) {
  if (n.virtual) return n.case_id || "";
  const c = (n.links || {}).taipei || [];
  return c[0] || "";
}
function _secTokenOf(m) {
  return areaTokenFromName(m.case_name) || m.area || "";
}
function compareClusterMembers(a, b) {
  if (!!a.date !== !!b.date) return a.date ? -1 : 1;   // dated members first
  const ka = effectiveCaseKey(a), kb = effectiveCaseKey(b);
  if (ka !== kb) return ka < kb ? -1 : 1;              // D12: attempt order
  return _secTokenOf(a).localeCompare(_secTokenOf(b), "zh-Hant");  // 區段 tie only
}
// Attempt-succession chain pairs: consecutive members inside one cluster where
// at least one is virtual AND the 事業種類 matches (概要 vs 計畫 same-day pairs
// are parallel applications, not revisions — 吉林段676 09601260/09601262 stay
// unchained). real↔real pairs keep graph.py's revision edges; cross-cluster
// pairs are parallel tracks, never chained.
function virtualChainPairs(clusters) {
  const pairs = [];
  (clusters || []).forEach(c => {
    const ms = c.members || [];
    for (let i = 1; i < ms.length; i++) {
      const a = ms[i - 1], b = ms[i];
      if (!a.virtual && !b.virtual) continue;
      if ((a.track || "") !== (b.track || "")) continue;
      pairs.push([a, b, c.stage]);
    }
  });
  return pairs;
}
function runScenarios(fx) {
  const out = { ordered: [], chainPairs: [] };
  (fx.clusters || []).forEach(c => out.chainPairs.push(...virtualChainPairs([c]).map(p => [{ case_id: p[0].case_id, virtual: p[0].virtual }, { case_id: p[1].case_id, virtual: p[1].virtual }, p[2]])));
  const single = fx.cluster ? [fx.cluster] : (fx.clusters || []);
  single.forEach(c => {
    const ms = (c.members || []).slice().sort(compareClusterMembers);
    out.ordered.push(ms.map(m => (m.virtual ? { case_id: m.case_id, virtual: true } : { recno: m.recno, virtual: false })));
  });
  if (!fx.clusters && fx.cluster) {
    out.chainPairs = virtualChainPairs([fx.cluster]).map(p => [{ case_id: p[0].case_id, virtual: p[0].virtual }, { case_id: p[1].case_id, virtual: p[1].virtual }, p[2]]);
  }
  return out;
}
// D12-END

function buildRelatedLinkLabels(p) {
  const links = p.links || {};
  const nodes = p.nodes || [];  const byCase = {};
  for (const n of nodes) {
    const anchored = (n.links || {}).taipei || [];
    for (const cid of anchored) byCase[cid] = n.case_name || "";
  }
  // Ghost/virtual payloads carry the harvested real case names — they must be
  // consulted before the synthetic case_milestones label (里程碑 N 筆), or the
  // generic label wins and the real name never shows.
  for (const g of (links.orphan_nodes || [])) {
    if (!byCase[g.case_id] && g.case_name) byCase[g.case_id] = g.case_name;
  }
  for (const cid of (links.taipei || [])) {
    if (byCase[cid]) continue;
    const cn = links.candidate_names && links.candidate_names[cid];
    if (cn) {
      byCase[cid] = cn;
      continue;
    }
    const cm = links.case_milestones && links.case_milestones[cid];
    if (cm) {
      byCase[cid] = `里程碑 ${Object.keys(cm).length} 筆`;
      continue;
    }
    const sr = links.search_rejected && links.search_rejected[cid];
    if (sr) {
      byCase[cid] = sr;
      continue;
    }
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
    const neverChip = p => neverApproved(p) ? `<span class="never-badge">未核定</span>` : "";
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
        ? ` · 基地面積 <span style="color:${areaStyle.color};font-weight:${areaStyle.fontWeight}">${escapeHtml(area)}</span>`
        : area ? ` · 基地面積 ${escapeHtml(area)}` : "";
      const orphanCount = ((p.links || {}).orphan_nodes || []).length;
      el.innerHTML = `<div class="pid"><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}${stageChip(p)}${neverChip(p)}</div>
        <div class="cnt">${p.member_recnos.length}${orphanCount ? `(+${orphanCount})` : ""} 筆 · ${escapeHtml(p.implementer)}${areaHtml}</div>`;
      el.onclick = () => { activePid = p.project_id; renderList(); renderDetail(p); };
      list.appendChild(el);
    });
  }

  function renderDetail(p) {
    const detail = document.getElementById("detail");
    const nodes = byDateNodes(p.nodes);
    // §5.2 virtual orphan nodes: harvested name → stage/track (+node_date when
    // the platform records an approval date). Undated named orphans join their
    // stage cluster tagged (未核定) instead of the interim column.
    const orphans = (p.links || {}).orphan_nodes || [];
    const virtualNodes = orphans
      .filter(g => g.case_name && g.stage && g.track)
      .map(g => ({
        recno: "v" + g.case_id,
        date: g.node_date || "",
        undated: !g.node_date,
        stage: g.stage,
        track: g.track,
        area: "",
        is_current: false,
        virtual: true,
        case_id: g.case_id,
        case_name: g.case_name,
        schedule: g.schedule || "",
        links: { taipei: [g.case_id], milestones_national: {}, milestones_taipei: {} },
      }));
    // Interim column holds nameless orphans only (corpus: 0 post-harvest).
    const interimOrphans = orphans.filter(g => !g.case_name);
    const columns = {};
    nodes.forEach(n => {
      const col = `${n.track}${n.area ? "（" + n.area + "區段）" : ""}`;
      columns[col] = (columns[col] || 0) + 1;
    });
    virtualNodes.forEach(v => {
      const col = v.track;
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

    // Timeline rows: §5.2.6 stage-key clusters — approvals group by 第N次
    // within the family (base real node first, splits by 區段, undated last);
    // execution events interleave by date. Cluster date = real member's date,
    // else min(dated); undated-only clusters sort to the end.
    const events = buildConstructionChain(p);
    const stageClusters = {};
    const clusterOfStage = stage => stageClusters[stage] ||
      (stageClusters[stage] = { stage, members: [] });
    nodes.forEach(n => clusterOfStage(n.stage).members.push(n));
    virtualNodes.forEach(v => clusterOfStage(v.stage).members.push(v));
    const secOf = m => areaTokenFromName(m.case_name) || m.area || "";
    const clusters = Object.values(stageClusters).map(c => {
      c.members.sort(compareClusterMembers);  // D12: case_id attempt order
      const real = c.members.find(m => !m.virtual && m.date);
      const dated = c.members.map(m => m.date).filter(Boolean).sort();
      c.clusterDate = real ? real.date : (dated[0] || "(未核定)");
      c.effDate = c.clusterDate === "(未核定)" ? "9999-12-31" : c.clusterDate;
      c.undatedCount = c.members.filter(m => !m.date).length;
      return c;
    }).sort((a, b) => (a.effDate < b.effDate ? -1 : a.effDate > b.effDate ? 1 : 0));
    // D12 Amendment 3 (603 exploration): family-wide case_id interleave —
    // all members (real + virtual) flatten into ONE row sequence by effective
    // case_id ascending, reproducing the 相關連結 order; cluster bands/chips
    // still render around each member via its stage cluster membership.
    const rowKeyOf = m => effectiveCaseKey(m) || "\uffff" + String(m.recno);
    const allMembers = [...nodes, ...virtualNodes]
      .slice()
      .sort((a, b) => {
        const ka = effectiveCaseKey(a), kb = effectiveCaseKey(b);
        if (ka !== kb) return ka < kb ? -1 : 1;
        return String(a.recno).localeCompare(String(b.recno));
      });
    const clusterOfRecno = {};
    clusters.forEach(c => c.members.forEach(m => { clusterOfRecno[m.recno] = c; }));
    const sortedEvents = events
      .map(e => ({ kind: "event", date: String(e.date).replace(/\//g, "-"), e }))
      .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
    const timeline = [];
    let ei = 0;
    for (const m of allMembers) {
      const mDate = m.date || (clusterOfRecno[m.recno] || {}).effDate || "";
      while (ei < sortedEvents.length && sortedEvents[ei].date < mDate) {
        timeline.push(sortedEvents[ei++]);
      }
      timeline.push({ kind: "approval", date: mDate, n: m, undated: !m.date });
    }
    while (ei < sortedEvents.length) timeline.push(sortedEvents[ei++]);

    // §5.3.1 content-addressed pitch: node rows 64px, execution-event rows 32px.
    const rowYs = [];
    let rowAcc = PAD;
    timeline.forEach((t, i) => {
      rowYs[i] = rowAcc;
      rowAcc += t.kind === "approval" ? NODE_ROW : EVENT_ROW;
    });
    const contentH = rowAcc - PAD;

    const hasEvents = events.length > 0;
    const eventColX = PAD + colKeys.length * COL_W + COL_W / 2;

    // Interim orphan anchors: rightmost column, nameless orphans only. Named
    // orphans became virtual nodes above; their source edges come from the
    // virtual node's own grid position.
    const hasGhosts = interimOrphans.length > 0;
    const ghostColX = eventColX + COL_W;
    const ghostPos = {};
    interimOrphans.forEach((g, i) => {
      ghostPos[`${g.case_id}::__node__`] = { x: ghostColX, y: PAD + i * NODE_ROW };
    });
    const ghostRows = interimOrphans.length;
    const orphanSources = {};
    interimOrphans.forEach(g => {
      const q = ghostPos[`${g.case_id}::__node__`];
      if (q) orphanSources[g.case_id] = q;
    });

    const pos = {};
    const evPos = {};
    timeline.forEach((t, i) => {
      if (t.kind === "approval") {
        pos[t.n.recno] = { x: PAD + colOf(t.n) * COL_W + COL_W / 2, y: rowYs[i] };
      } else {
        evPos[t.e.label] = { x: eventColX, y: rowYs[i] };
      }
    });
    virtualNodes.forEach(v => {
      if (pos[v.recno]) orphanSources[v.case_id] = pos[v.recno];
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
    let svgH = PAD * 2 + contentH;
    if (hasGhosts) {
      svgW = Math.max(svgW, ghostColX + 250);
      svgH = Math.max(svgH, PAD * 2 + Math.max(0, ghostRows - 1) * NODE_ROW + 80);
    }
    callouts.forEach(c => {
      svgH = Math.max(svgH, pos[c.n.recno].y + 84);
    });

    // Callout placement: collision-dodging spots, clamped into the viewBox.
    // Runs BEFORE the svg string is built so viewBox extensions take effect.
    const evRects = events.map(e => {
      const q = evPos[e.label];
      return { x: q.x - 8, y: q.y - 12, w: 240, h: 26 };
    });
    if (hasGhosts) {
      orphans.forEach(g => {
        const q = ghostPos[`${g.case_id}::__node__`];
        if (q) evRects.push({ x: q.x - 10, y: q.y - 16, w: 240, h: 32 });
      });
    }
    const placedBoxes = [];
    const hitsAny = (r, list) => list.some(o =>
      r.x < o.x + o.w && o.x < r.x + r.w && r.y < o.y + o.h && o.y < r.y + r.h);
    callouts.forEach(c => {
      const ownRecno = c.n.recno;
      const p2 = pos[ownRecno];
      const w = 150, h = c.rows.length * 14 + 6;
      // §5.3.6 collision boxes cover the node's full visual footprint
      // (badge strip above the label + the two text lines).
      const nodeRects = [...nodes, ...virtualNodes]
        .filter(n => n.recno !== ownRecno && pos[n.recno])
        .map(n => {
          const q = pos[n.recno];
          const headLen = (`${n.virtual ? "" : n.recno + " · "}${n.date}${n.stage ? " " + n.stage : ""}`).length;
          return { x: q.x - 10, y: q.y - 30, w: 14 + headLen * 6.5 + 40, h: 50 };
        });
      const spots = [
        { x: p2.x - 16 - w, y: p2.y + 20 },          // below-left
        { x: p2.x + 16,     y: p2.y + 20 },          // below-right
        { x: p2.x - 16 - w, y: p2.y - 10 - h },      // above-left
        { x: p2.x + 16,     y: p2.y - 10 - h },      // above-right
        { x: p2.x - 16 - w, y: p2.y + 46 },          // further below-left
        { x: p2.x + 16,     y: p2.y + 46 },          // further below-right
        { x: p2.x - 16 - w, y: p2.y + 72 },          // far below-left
        { x: p2.x + 16,     y: p2.y + 72 },          // far below-right
      ].map(s => ({
        x: Math.min(Math.max(s.x, 4), Math.max(4, svgW - w - 4)),
        y: Math.min(Math.max(s.y, 4), Math.max(4, svgH - h - 4)),
      }));
      let spot = spots.find(s => {
        const r = { x: s.x, y: s.y, w, h };
        return !hitsAny(r, nodeRects) && !hitsAny(r, evRects) && !hitsAny(r, placedBoxes);
      });
      if (!spot) {
        // §5.3.6 canvas-extension fallback: grow the canvas instead of
        // accepting an overlap.
        spot = {
          x: Math.min(Math.max(p2.x + 16, 4), Math.max(4, svgW - w - 4)),
          y: svgH + 8, w, h,
        };
        svgH = spot.y + h + 16;
      }
      spot.w = w; spot.h = h;
      placedBoxes.push(spot);
      c.rect = spot;
      svgH = Math.max(svgH, spot.y + h + 16);
      svgW = Math.max(svgW, spot.x + w + 8);
    });

    // §5.2.6 stage-cluster bands: soft band + count chip behind clusters with
    // ≥2 members. Span covers the members' full node footprint.
    const bandHtml = clusters.filter(c => c.members.length >= 2).map(c => {
      const ys = c.members.map(m => pos[m.recno]).filter(Boolean).map(q => q.y);
      if (ys.length < 2) return "";
      const top = Math.min(...ys) - 30, bottom = Math.max(...ys) + 26;
      const label = `${c.stage} · ${c.members.length} 案` +
        (c.undatedCount ? ` · ${c.undatedCount} 未核定` : "");
      return `<g class="stage-band"><rect x="${PAD - 44}" y="${top}" width="${svgW - PAD * 2 + 88}" height="${bottom - top}"></rect>` +
        `<text class="stage-band-chip" x="${PAD - 36}" y="${top + 12}">${escapeHtml(label)}</text></g>`;
    }).join("");

    let s = `<h2><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}</h2>
      <div class="district">${escapeHtml(p.district)} · ${escapeHtml(p.section)} · ${escapeHtml(p.implementer)} · 共 ${p.member_recnos.length} 筆</div>
      <div class="legend">
        <span class="rev">版本（核定時序）</span>
        <span class="trk">事業種類</span>
        <span class="sec">區段</span>
      </div>
      <div class="graph-viewport"><div class="graph-zoom">
      <svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet">${bandHtml}`;

    p.edges.forEach(e => {
      const a = pos[e.from], b = pos[e.to];
      if (!a || !b) return;
      s += `<line class="edge ${e.kind}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
    });

    // D12 chain edges: attempt-succession between consecutive virtual nodes
    // inside each cluster (row order = case_id ascending). real↔real pairs
    // keep graph.py's revision edges; cross-cluster pairs are parallel tracks.
    virtualChainPairs(clusters).forEach(([a, b]) => {
      const pa = pos[a.recno], pb = pos[b.recno];
      if (!pa || !pb) return;
      s += `<line class="edge virtual" x1="${pa.x}" y1="${pa.y}" x2="${pb.x}" y2="${pb.y}"></line>`;
    });

    // Source-group edges (final model): slanted solid source edge from the
    // owning record — or the orphan's ghost anchor — to each group's earliest
    // event; solid vertical chain within a source group; dashed vertical
    // transition between different source groups (incoming group's color).
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
          } else if (!e.national && orphanSources[e.case]) {
            const a = orphanSources[e.case];
            s += `<line class="event-edge ${colorCls}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          }
        }
        if (i > 0) {
          const a = evPos[events[i - 1].label];
          if (groupStart) {
            s += `<line class="event-link ${colorCls} dashed" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          } else {
            s += `<line class="event-link ${colorCls}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
          }
        }
      });
    }

    [...nodes, ...virtualNodes].forEach(n => {
      const p2 = pos[n.recno];
      if (!p2) return;
      const secTok = areaTokenFromName(n.case_name);
      const areaTxt = n.area ? `（${escapeHtml(n.area)}區段）` : (secTok ? `（${escapeHtml(secTok)}）` : "");
      const label = n.virtual
        ? `${n.undated ? "(未核定) " : ""}${n.stage}`
        : `${n.recno} · ${n.date}${perTrackStageText(n)}`;
      const schedTxt = n.virtual
        ? scheduleBadgeText(n.schedule)
        : scheduleBadgeText(caseScheduleOf(p, n.links.taipei[0]));
      const badges = getNodeMilestoneBadges(n, p);
      const ghost = n.track === "事業概要" ? " ghost" : "";
      const virtualCls = n.virtual ? " virtual" : "";
      // badges sit ABOVE the first line, aligned to its left edge — never
      // covering the label or the track line beneath. Virtual nodes use the
      // same badge anatomy; provenance lives in the tooltip (no 孤 badge).
      s += `<g class="node${ghost}${virtualCls} ${n.is_current ? "current" : ""}" transform="translate(${p2.x},${p2.y})">
        ${n.virtual ? `<title>孤兒案例（orphan-case-anchoring）· 案${escapeHtml(n.case_id)}</title>` : ""}
        <circle r="9"></circle>
        <text class="title" x="14" y="3">${escapeHtml(label)}${escapeHtml(schedTxt)}</text>
        <text class="sub" x="14" y="15">${escapeHtml(n.track)}${areaTxt}</text>
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

    // Interim orphan anchors (孤): rightmost column, nameless orphans only —
    // named orphans became virtual nodes in the grid. Anchors are dashed
    // circles labelled 北<case_id>; their execution dates live once in the
    // shared column, fed by slanted solid source edges from these anchors.
    if (hasGhosts) {
      interimOrphans.forEach(g => {
        const nb = ghostPos[`${g.case_id}::__node__`];
        const caseUrl = g.case_id
          ? `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${g.case_id}`
          : "";
        s += `<g class="node orphan-node" transform="translate(${nb.x},${nb.y})">
          <circle r="9"></circle>
          <foreignObject x="14" y="-27" width="90" height="15"><div xmlns="http://www.w3.org/1999/xhtml" style="display:flex;gap:2px;align-items:center;"><a class="orphan-id-link" href="${escapeHtml(caseUrl)}" target="_blank" rel="noopener"><span class="node-milestone-badge taipei">北</span>${escapeHtml(g.case_id)}</a><span class="node-milestone-badge orphan-badge" title="孤兒案例（orphan-case-anchoring）">孤</span></div></foreignObject>
          <text class="sub" x="14" y="15">PDF 未收錄 · 孤兒錨點</text>
        </g>`;
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
    s += "</svg></div></div>";

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
        const schedules = links.case_schedules || {};
        const NEVER = ["已駁回", "自行撤回", "已失效"];
        links.taipei.forEach(cid => {
          const url = `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cid}`;
          const nm = linkLabels.byCase[cid] || "";
          const sched = schedules[cid] || "";
          const schedBadge = scheduleBadgeText(sched);
          s += `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener">臺北市都市更新審議服務平台 (case_id: ${cid})</a>${nm ? ` — <span class="link-case-name">${escapeHtml(nm)}</span>` : ""}${schedBadge ? ` <span class="link-schedule">${escapeHtml(schedBadge.trim())}</span>` : ""}</li>`;
        });
        // never-approved: every case 駁回/撤回/失效 and no national page —
        // the portal will never list this unit, so the absence is explained.
        if (!links.twur && links.taipei.length) {
          const known = links.taipei.filter(cid => schedules[cid]);
          if (known.length && known.every(cid => NEVER.includes(schedules[cid]))) {
            s += `<li class="no-twur-reason">未曾核定（已駁回/自行撤回/已失效）— 無國土管理署入口網頁</li>`;
          }
        }
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

    // §5.3.3 graph viewport: pinch-zoom (2 fingers), drag-pan, ctrl-wheel zoom,
    // double-click reset. Desktop pointers get the same treatment.
    const vp = detail.querySelector(".graph-viewport");
    if (vp) attachGraphViewport(vp);

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

// §5.3.3 pinch-zoom + pan for the graph viewport. Two-finger pinch scales the
// graph (clamped, anchored at the pinch midpoint); one-finger/mouse drag pans
// via scroll; ctrl+wheel zooms; double-click resets. touch-action is disabled
// in CSS so pointer events own the gestures.
function attachGraphViewport(vp) {
  const inner = vp.querySelector(".graph-zoom");
  if (!inner) return;
  let scale = 1;
  const MIN = 0.5, MAX = 3;
  const apply = () => { inner.style.transform = `scale(${scale})`; };
  const pts = new Map();
  let lastDist = 0, panRef = null;

  vp.addEventListener("pointerdown", e => {
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 1) {
      panRef = { x: e.clientX, y: e.clientY, sl: vp.scrollLeft, st: vp.scrollTop };
    } else {
      panRef = null;
      lastDist = 0;
    }
    vp.setPointerCapture(e.pointerId);
  });
  vp.addEventListener("pointermove", e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const dist = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (lastDist > 0) {
        scale = Math.min(MAX, Math.max(MIN, scale * (dist / lastDist)));
        apply();
      }
      lastDist = dist;
      e.preventDefault();
    } else if (panRef) {
      vp.scrollLeft = panRef.sl - (e.clientX - panRef.x);
      vp.scrollTop = panRef.st - (e.clientY - panRef.y);
    }
  });
  const release = e => {
    pts.delete(e.pointerId);
    if (pts.size < 2) lastDist = 0;
    if (pts.size === 0) panRef = null;
  };
  vp.addEventListener("pointerup", release);
  vp.addEventListener("pointercancel", release);
  vp.addEventListener("wheel", e => {
    if (!e.ctrlKey) return;
    e.preventDefault();
    scale = Math.min(MAX, Math.max(MIN, scale * (e.deltaY < 0 ? 1.1 : 0.9)));
    apply();
  }, { passive: false });
  vp.addEventListener("dblclick", () => { scale = 1; apply(); });
}

function escapeHtml(t) {
  return String(t).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

document.addEventListener("DOMContentLoaded", init);