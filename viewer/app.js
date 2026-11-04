"use strict";

const W = 960, PAD = 60, COL_W = 130, NODE_ROW = 64, EVENT_ROW = 32;
// Reserved callout gutter left of the leftmost track column. Width is set per
// project (from the widest callout box) up to this cap; 0 when no callouts.
const CALLOUT_GUTTER_CAP = 160;
const CALLOUT_MIN_W = 140;
const CALLOUT_PAD = 8;
const CALLOUT_GAP = 2; // px between stacked callout boxes
const KIND_COLOR = { revision: "#1d4ed8", track: "#0f766e", section: "#b45309" };
const KIND_LABEL = { revision: "版本", track: "事業種類", section: "區段" };

const TRACK_ORDER = ["事業計畫", "權利變換", "事業計畫、權利變換", "事業概要"];

// Construction-phase chain slots drawn beside the anchor record (facts §6.4/§12.1)
const CONSTRUCTION_CHAIN_SLOTS = ["建照核發日期", "開工日期", "使照核發日期"];
// Slot -> national-portal milestone label; a hit supplies the 國 badge (and the
// fallback value for the 使照 slot when 使照核發日期 is absent).
const NATIONAL_MAPPED_LABELS = { "使照核發日期": "使用核發日期" };

// §2: a national approval label carries a stage (擬訂 / 第N次變更) and a track
// (事業計畫 / 權利變換). A node gets 國 when a label binds to it by stage+track
// (date tie-break when several nodes match). Returns null for labels that name no
// stage (使用核發日期, …申請日期). Node stages render 第N次 as Chinese ordinals:
// 第一次→變更, 第二次→變更(第二次), etc.
const CHINESE_DIGIT = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };
const nationalLabelKey = label => {
  const m = String(label).match(/^(第([一二三四五六七八九十\d]+)次變更)?(事業計畫|權利變換計畫)核定日期$/);
  if (!m) return null;
  const raw = m[2] || "";
  const ordinal = raw === "" ? 0 : Number(raw) || CHINESE_DIGIT[raw] || 0;
  const stage = ordinal === 0 ? "擬訂" : ordinal === 1 ? "變更" : `變更(第${raw}次)`;
  // label track 權利變換計畫 → node track 權利變換 (label keeps 計畫 for grammar)
  const track = m[3] === "權利變換計畫" ? "權利變換" : m[3];
  return { stage, track };
};
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

// §2: 國 binds to the recno node whose stage+track match a national approval
// label (date tie-break when several nodes match). view_verified_case_ids stays
// as a second source; the current-node rule alone is removed.
function trackMatches(nodeTrack, labelTrack) {
  if (nodeTrack === labelTrack) return true;
  const combined = "事業計畫、權利變換";
  return nodeTrack === combined && (labelTrack === "事業計畫" || labelTrack === "權利變換");
}

function nationalRocToIso(v) {
  const s = String(v || "");
  const m = s.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);
  if (!m) return s;
  return `${1911 + Number(m[1])}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
}

const _shiftIsoDay = (iso, days) => {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
};

// §2 / C1 (bind-national-label-once): binding is per label, decided once per
// project — not per node. Scoring each node on its own badged every candidate
// of a multi-match label (19 labels, 41 badged nodes, 16 unearned 國). Each
// label's candidates are the nodes of its stage+track; one candidate binds
// whatever the date, several resolve by exact date, then ±1 day (the
// 公告-vs-committee offset the 北 matcher allows); 0 or 2+ survivors bind
// nothing.
function bindNationalLabels(project) {
  const national = (project.links || {}).milestones_national || {};
  const nodes = (project.nodes || []).filter(n => n.recno != null);
  const out = {}; // recno -> [labels]
  for (const label of Object.keys(national)) {
    const k = nationalLabelKey(label);
    if (!k) continue; // 使用核發日期 / application dates never bind
    let candidates = nodes.filter(n => n.stage === k.stage && trackMatches(n.track, k.track));
    if (!candidates.length) continue;
    if (candidates.length > 1) {
      const iso = nationalRocToIso(national[label]);
      const near = new Set([iso, _shiftIsoDay(iso, 1), _shiftIsoDay(iso, -1)]);
      let hits = candidates.filter(n => n.date === iso);
      if (hits.length !== 1) {
        hits = candidates.filter(n => near.has(n.date));
      }
      if (hits.length !== 1) continue; // 0 or 2+ survivors: the label binds nothing
      candidates = hits;
    }
    const recno = String(candidates[0].recno);
    (out[recno] = out[recno] || []).push(label);
  }
  return out;
}

function getNodeMilestoneBadges(node, project) {
  // Portal links live on the nodes (相關連結 section retired): 北 → anchored
  // Taipei case page; 國 → national view page on the node a national label
  // binds to (per-label binding, bindNationalLabels) AND on nodes whose case
  // the view page names (view_verified_case_ids — the portal's assertion,
  // fix-row-order-tiebreak-and-view-badges D4). One 國 if both. The 現況 rule
  // (current-node rule alone) is removed.
  const badges = [];
  const cases = (node.links || {}).taipei || [];
  if (cases.length) {
    badges.push(`<a class="node-milestone-badge taipei badge-link" href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cases[0]}" target="_blank" rel="noopener" title="案${cases[0]}">北</a>`);
  }
  const twur = project && project.links && project.links.twur;
  const viewVerified = (project && project.links && project.links.view_verified_case_ids) || [];
  const anchoredViewVerified = cases.length && viewVerified.includes(cases[0]);
  const boundLabels = (twur && project.__nationalBindings) ? project.__nationalBindings[String(node.recno)] : null;
  if (twur && ((boundLabels && boundLabels.length) || anchoredViewVerified)) {
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
      <dd class="milestone-date">${escapeHtml(fmtDate(String(val)))}</dd>
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
    // D4a (inspection-batchD): the national source group is "使照 filled solely
    // from 使用核發日期" (history-graph spec). A national page hit alongside a
    // city date is corroboration (it keeps the 國 badge via natCorroborated),
    // not a source: 287 corpus events drew a wrong 現況 → 使照 green edge
    // because this flag ignored the city date.
    const natCorroborated = !!natLabel && !!national[natLabel] && !!value;
    const nationalHit = !value && !!(natLabel && national[natLabel]);
    if (nationalHit) value = national[natLabel];
    if (!value) continue;
    const natOnly = nationalHit;
    // national portal dates arrive in 民國 (110.10.25); taipei milestones in
    // slash-western (2023/04/27). Normalise BOTH to ISO at build time
    // (fix-graph-timeline-order D1): the timeline interleave compares date
    // strings, and '/'(0x2F) > '-'(0x2D) in ASCII, so slash dates sorted after
    // every ISO date of the same year — 建照/開工 landed at the newest end
    // instead of between the approvals they follow. Display converts back via
    // fmtDate at the render site.
    let dateStr = String(value);
    {
      const roc = dateStr.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);
      const slash = dateStr.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
      if (roc) {
        dateStr = `${1911 + Number(roc[1])}-${roc[2].padStart(2, "0")}-${roc[3].padStart(2, "0")}`;
      } else if (slash) {
        dateStr = `${slash[1]}-${slash[2].padStart(2, "0")}-${slash[3].padStart(2, "0")}`;
      }
    }
    // provenance (D4a rule 1): milestones_source IS the per-date provenance
    // (data2 for 建照, data3 for 開工/使照 via pick_implementation_payload C8a);
    // the implementation payload is the D5 *statistics* pick — consulted only
    // when the source map does not name the slot. Trying the payload first let
    // 潭美579's 開工 jump to a different case (recno 1052) and split the chain.
    let provCase = "";
    if (!natOnly) {
      if (sourceMap[slot] && taipei[slot] === value) provCase = sourceMap[slot];
      else {
        const implField = IMPL_SOURCE_FIELDS[slot];
        if (implCase && implField && impl[implField] === value) provCase = implCase;
      }
    }
    const ownerRecno = provCase !== "" && anchoredByCase[provCase] !== undefined
      ? anchoredByCase[provCase] : null;
    const anchored = ownerRecno !== null;
    const prov = provCase ? `案${provCase}${anchored ? `·編號${ownerRecno}` : ""}` : "";
    out.push({
      label: slot, date: dateStr, national: nationalHit, prov,
      // natCorroborated: the national portal holds this date (history-graph
      // scenario "National-mapped event shows the 國 badge") — drives the 國
      // badge even when the slot is a city event. nationalHit slots are
      // corroborated by construction.
      case: provCase, anchored, ownerRecno,
      natCorroborated: natCorroborated || nationalHit,
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
// D4c (2026-11-05): the never-approved classification is retired — a gazette
// family holds a gazette approval by construction.
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
// 施工中/自行撤回/已失效/審查中) render as badges. The city's search list writes
// an approved case as 已核准 or 已核定 (cache 2026-11-02: 739 / 14), so both
// are the default (refresh-case-status-and-drop-withdrawn-fields D6).
// 無 / NA mean the platform has no current state for the case: render them
// honestly as [無] / [NA] instead of silence (§7 viewer-UX).
const scheduleBadgeText = s => (!s || s === "已核准" || s === "已核定") ? "" : s === "無" ? " [無]" : s === "NA" ? " [NA]" : ` [${s}]`;

// D4b/c/d (inspection-batchD, user decision 2026-11-05). isDeadEnd lives in
// the D12 helper block (virtualChainPairs needs it); the dead-end badge reads
// it, and the 計畫與執行 filter uses it for the exclusive state below.

// D4d: the project's single 計畫與執行 state — construction first (the later
// fact), then the current node's own dead-end schedule, else the current
// node's exact track (事業計畫、權利變換 matches only its own option).
function execStateOf(p) {
  const st = constructionStage(p);
  if (st) return st.short;
  const cur = p.nodes.find(n => n.is_current);
  const cid = cur && cur.links && cur.links.taipei ? (cur.links.taipei[0] || "") : "";
  const sched = cid ? (((p.links || {}).case_schedules || {})[cid] || "") : "";
  if (isDeadEnd(sched)) return sched;
  return (cur || {}).track || "";
}

// (viewer-stage-chip-coverage) D4c (user decision 2026-11-05): the
// family-level chips are gone — a gazette approval proves the unit was
// approved, and an older case's state must not label the current approval.
// The list shows the dead-end state of the current node's OWN case only.
function deadEndChip(p) {
  const cur = p.nodes.find(n => n.is_current);
  const cid = ((cur || {}).links || {}).taipei ? (cur.links.taipei[0] || "") : "";
  const sched = cid ? ((p.links || {}).case_schedules || {})[cid] || "" : "";
  return isDeadEnd(sched) ? `<span class="deadend-chip">${sched}</span>` : "";
}

// (viewer-stage-chip-coverage) fmtCell: the record table renders for human
// reading — parcel lists as 、-joined prose; empty list/dict and absent values
// as an em dash. Display-time only; the payload stays verbatim.
function fmtCell(v) {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length ? v.join("、") : "—";
  if (typeof v === "object") {
    const keys = Object.keys(v);
    return keys.length ? keys.map(k => `${k}:${fmtCell(v[k])}`).join("、") : "—";
  }
  const s = String(v);
  return s === "" ? "—" : s;
}

// (fix-graph-timeline-order D2) the display form for execution dates: ISO
// internal -> the established slash-western display. Pure display-time.
function fmtDateReverse(text) {
  const m = String(text || "").match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  return m ? `${m[1]}/${m[2]}/${m[3]}` : String(text || "");
}

// (viewer-stage-chip-coverage) fmtDate: every date renders ISO at display time,
// converting the two non-ISO source forms. The ROC rule matches
// urtpe/extract.to_iso (year < 1911 ⇒ +1911). Source strings stay verbatim in
// the data; this is a render-time rule. building-permit-adapter D5: an ROC
// year above the current 民國 year is a source typo, not a far-future date —
// 橋北574-1's 291.08.02 fabricated 2202; it renders verbatim with the
// date-range-warning class instead.
function currentRocYear() {
  const now = new Date();
  return now.getFullYear() - 1911;
}
function fmtDate(text) {
  const s = String(text || "").trim();
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  m = s.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);           // Taipei slash
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  m = s.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);          // ROC dots
  if (m) {
    const y = parseInt(m[1], 10);
    if (y > currentRocYear()) return s;                      // out of range: verbatim
    return `${y < 1911 ? y + 1911 : y}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  }
  return s;                                                   // unrecognised: verbatim
}

// D12-BEGIN (add-virtual-node-ordering-and-chain — pure helpers, node-tested)
// D4b (2026-11-05): isDeadEnd lives inside the block — virtualChainPairs
// refuses any chain edge that starts at a dead-end schedule.
const isDeadEnd = s => s === "已失效" || s === "自行撤回" || s === "已駁回";
// Effective comparison key: real nodes use their ANCHORED case_id
// (links.taipei[0]); virtual nodes their own case_id; case-less real nodes
// yield "" (sorts first — "" < any case_id keeps the order strictly ascending).
// Ascending case_id == application-attempt order (YY序號), load-independent.
function effectiveCaseKey(n) {
  if (n.virtual) return n.case_id || "";
  const c = (n.links || {}).taipei || [];
  return c[0] || "";
}
// D2b (inspection-batchD, user decision 2026-11-05): the row's OWN-EVENT
// date. A 概要-track member reads 概要核准 → 申請概要 → 申請計畫; a plan-track
// member reads 核定 → 權變核定 → 申請計畫 → 申請權變 → 申請概要 — never the
// echoed 概要核准, which the city copies into every descendant case (吉林717:
// the whole triple carried the 概要's 2007/01/30). Same date or none:
// case_id ascending keeps the D12 attempt order as the tie-break.
function ownEventDate(n, project) {
  const ms = (n.virtual ? (n.milestones_taipei_case || n.milestones_national || {})
    : (((project || {}).links || {}).case_milestones || {})[effectiveCaseKey(n)]) || {};
  const first = labels => { for (const l of labels) { const v = ms[l]; if (v) return v; } return ""; };
  const outline = first(["概要核准日期", "申請概要日期", "申請計畫日期"]);
  if ((n.track || "") === "事業概要") return outline;
  const plan = first(["核定日期", "權變核定日期", "申請計畫日期", "申請權變日期", "申請概要日期"]);
  return plan || outline;
}
function _secTokenOf(m) {
  return areaTokenFromName(m.case_name) || m.area || "";
}
function compareClusterMembers(a, b) {
  if (!!a.date !== !!b.date) return a.date ? -1 : 1;   // dated members first
  const da = a.date || ownEventDate(a), db = b.date || ownEventDate(b);
  if (da !== db) return da < db ? -1 : 1;              // D2b: own-event date
  const ka = effectiveCaseKey(a), kb = effectiveCaseKey(b);
  if (ka !== kb) return ka < kb ? -1 : 1;              // D12 tie-break: attempt order
  return _secTokenOf(a).localeCompare(_secTokenOf(b), "zh-Hant");  // 區段 tie only
}
// Attempt-succession chain pairs: consecutive VIRTUAL members inside one
// cluster with matching 事業種類 (概要 vs 計畫 same-day pairs are parallel
// applications, not revisions — 吉林段676 09601260/09601262 stay unchained).
// §4 amendment (2026-11-04): virtual↔virtual only. A real↔virtual pair gains
// no chain edge — the orphan's only recno connector is the §4 dotted edge to
// its branch-off node; a chain edge would stack on it (67 pairs), flow the
// dead end onward to the row below (30, 南海段-687 393→11012301), or pick a
// wrong branch point (22), and the cluster's dated-first sort would read the
// approval as leading to the withdrawn application.
function virtualChainPairs(clusters) {
  const pairs = [];
  (clusters || []).forEach(c => {
    const ms = c.members || [];
    for (let i = 1; i < ms.length; i++) {
      const a = ms[i - 1], b = ms[i];
      if (!a.virtual || !b.virtual) continue;
      if ((a.track || "") !== (b.track || "")) continue;
      // D4b (inspection-batchD): no chain edge starts at a dead end — nothing
      // follows a closed case (已失效/自行撤回/已駁回; 36 of 48 corpus pairs).
      if (isDeadEnd(a.schedule || a.case_schedule || "")) continue;
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
  const harvested = links.candidate_names || {};
  // label-by-own-name (C7): the city's own harvested name labels the case; the
  // node's gazette 案名 is only the fallback — one node can anchor 2+ cases
  // (the area-split binding) and the gazette label cannot tell them apart
  // (吉林508's 11011241 shows without its -A區 suffix).
  for (const n of nodes) {
    const anchored = (n.links || {}).taipei || [];
    for (const cid of anchored) byCase[cid] = harvested[cid] || n.case_name || "";
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
  // label-by-own-name (C10): the 國 label is the national page's own 案名
  // (links.twur_name, the page <title>) — the portal names the project by its
  // first 擬訂 case; the current node's gazette name is only the fallback.
  const anchor = nodes.find(n => n.is_current) || nodes[nodes.length - 1] || {};
  return { byCase, anchorName: links.twur_name || anchor.case_name || "" };
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
        <dd class="milestone-date">${escapeHtml(fmtDate(date))}</dd>
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
        <dd class="milestone-date">${escapeHtml(fmtDate(date))}</dd>
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
    ` · 統計至 ${window.PROJECTS.published_date || window.PROJECTS.generated_at || ""}`;

  const sel = { district: new Set(), year: new Set(), track: new Set(), stage: new Set() };
  const districts = [...new Set(projects.map(p => p.district))].sort();
  const years = [...new Set(projects.flatMap(p => p.nodes.map(n => n.date.slice(0, 4))))]
    .sort((a, b) => (a < b ? 1 : -1));
  const DIMS = [
    { key: "district", label: "地區", options: districts },
    { key: "year", label: "年度", options: years },
    { key: "track", label: "事業種類", options: TRACK_ORDER },
    // D4d (user decision 2026-11-05): 計畫與執行 — every project matches at
    // most one state (construction > dead end > exact current-node track);
    // 其他/都市更新計畫 dropped from 事業種類 (0 nodes each).
    { key: "stage", label: "計畫與執行", options: ["建照", "開工", "使照", "已失效", "自行撤回", "已駁回", "事業概要", "事業計畫", "事業計畫、權利變換", "權利變換"] },
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
      if (!sel.stage.has(execStateOf(p))) return false;
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
        ? ` · 基地面積 <span style="color:${areaStyle.color};font-weight:${areaStyle.fontWeight}">${escapeHtml(area)}</span>`
        : area ? ` · 基地面積 ${escapeHtml(area)}` : "";
      const orphanCount = ((p.links || {}).orphan_nodes || []).length;
      el.innerHTML = `<div class="pid"><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}${stageChip(p)}${deadEndChip(p)}</div>
        <div class="cnt">${p.member_recnos.length}${orphanCount ? `(+${orphanCount})` : ""} 筆 · ${escapeHtml(p.implementer)}${areaHtml}</div>`;
      el.onclick = () => { activePid = p.project_id; renderList(); renderDetail(p); };
      list.appendChild(el);
    });
  }

  function renderDetail(p) {
    const detail = document.getElementById("detail");
    const nodes = byDateNodes(p.nodes);
    // C1 (bind-national-label-once): the per-label 國 binding is computed once
    // per project, before any node asks for its badges.
    p.__nationalBindings = bindNationalLabels(p);
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
        // D1 (inspection-batchD): the orphan's per-case dict is the Taipei
        // ashx data — renamed milestones_national → milestones_taipei_case
        // (name wrong, data right). Read the new key, fall back to the old
        // for payloads not yet re-emitted.
        links: { taipei: [g.case_id], milestones_taipei_case: g.milestones_taipei_case || g.milestones_national || {}, milestones_national: {}, milestones_taipei: {} },
        milestones_taipei_case: g.milestones_taipei_case || g.milestones_national || {},
      }));
    // §4: nameless 孤 anchors with no stage/track render no row (§4 decision 4 —
    // the 3 current nameless anchors are §8 defects removed by wave 3b).
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
    // fix-row-order-tiebreak-and-view-badges D1: two real nodes sharing one
    // case_id used to tie-break on String(recno) — and 編號 is a newest-first
    // coordinate, so the newer gazette row rendered ABOVE the older one
    // (corpus: 30 of 39 same-case groups inverted; reported on 關渡段二小段-303:
    // node 5 (2026-09-30) above node 669 (2020-07-28)). The tie-break now
    // compares node dates ascending first; the recno comparison decides only
    // between equal-or-absent dates. Cross-key order is untouched — the 603
    // pinned interleave and the 336 target never reach this layer.
    const allMembers = [...nodes, ...virtualNodes]
      .slice()
      .sort((a, b) => {
        // D2b (2026-11-05): own-event date first; case_id (D12) breaks ties
        // and orders the undated tail. Supersedes the case_id-first interleave.
        const da = a.date || ownEventDate(a, p) || "", db = b.date || ownEventDate(b, p) || "";
        if (da !== db) return da < db ? -1 : 1;
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
    // §3: an execution event that follows an approval starts ½ node row (32px)
    // under the nearest approval node directly above it; event→approval keeps the
    // full 64px clearance so badge strips do not touch.
    const rowYs = [];
    let rowAcc = PAD;
    timeline.forEach((t, i) => {
      if (i > 0) {
        const prev = timeline[i - 1];
        rowAcc += prev.kind === "approval" && t.kind === "event"
          ? NODE_ROW / 2          // §3: event starts ½ row under the approval above it
          : prev.kind === "event" && t.kind === "event"
            ? EVENT_ROW           // event→event stays 32px
            : NODE_ROW;           // event→approval keeps full 64px clearance; approval→approval 64px
      }
      rowYs[i] = rowAcc;
    });
    const contentH = rowAcc + (timeline.length ? (timeline[timeline.length - 1].kind === "approval" ? NODE_ROW : EVENT_ROW) : 0) - PAD;

    const hasEvents = events.length > 0;
    const eventColX = PAD + colKeys.length * COL_W + COL_W / 2;

    // §4: orphans take their own timeline row, interleaved with recno nodes by
    // the D12 case_id order. Named orphans are virtual nodes already in
    // `timeline`; nameless 孤 anchors with no date render no row (the 3 current
    // nameless anchors are §8 defects removed by wave 3b). "Between 2 recnos"
    // and "nearest recno" read the RENDERED ROWS, not dates: an undated orphan
    // has no date of its own (11012301 applies 2021-12-29, withdraws, renders
    // between 734@2019 and 393@2022 by case_id interleave), so a date test can
    // never fire for it (corpus: 30 orphans row-between but undated, 7 dated).
    const orphanSources = {};
    const orphanDots = []; // {from: orphanRecno, to: nearestRecno}
    // nearest recno node ROW directly above the orphan's row (its branch-off
    // point — 11012301 branches from 734, not from the later 393 it was filed
    // against), or directly under when no recno row sits above.
    const nearestRecnoRowAbove = (i) => {
      for (let j = i - 1; j >= 0; j--) {
        if (timeline[j].kind === "approval" && !timeline[j].n.virtual) return timeline[j].n;
      }
      return null;
    };
    const nearestRecnoRowUnder = (i) => {
      for (let j = i + 1; j < timeline.length; j++) {
        if (timeline[j].kind === "approval" && !timeline[j].n.virtual) return timeline[j].n;
      }
      return null;
    };
    // does the orphan's row sit between 2 recno rows in the same swimlane?
    const orphanBetweenRecnos = (v, i) => {
      const above = nearestRecnoRowAbove(i);
      if (!above) return false;
      for (let j = i + 1; j < timeline.length; j++) {
        const t = timeline[j];
        if (t.kind !== "approval" || t.n.virtual) continue;
        return colOf(t.n) === colOf(above) && colOf(t.n) === colOf(v);
      }
      return false;
    };

    const posRaw = {};
    const evPosRaw = {};
    timeline.forEach((t, i) => {
      if (t.kind === "approval") {
        let x = PAD + colOf(t.n) * COL_W + COL_W / 2;
        if (t.n.virtual && orphanBetweenRecnos(t.n, i)) x += NODE_ROW / 2; // §4: 32px right shift when its row sits between 2 recno rows of the same swimlane
        posRaw[t.n.recno] = { x, y: rowYs[i] };
        if (t.n.virtual) {
          orphanSources[t.n.case_id] = posRaw[t.n.recno];
          const to = nearestRecnoRowAbove(i)
            // D4b (user decision 2026-11-05): the under-fallback must not point
            // out of a closed case — a dead-end orphan above every recno row
            // renders with no dotted edge (160 corpus edges removed; the
            // up-edges INTO a dead end stay, 78).
            || (!isDeadEnd(t.n.schedule || t.n.case_schedule || "") ? nearestRecnoRowUnder(i) : null);
          if (to) orphanDots.push({ from: t.n.recno, to: to.recno });
        }
      } else {
        evPosRaw[t.e.label] = { x: eventColX, y: rowYs[i] };
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

    // §5.3.3 center the graph content horizontally. contentW is the graph's
    // own width; svgW keeps a minimum W so narrow graphs are not scaled up.
    // xOffset = (svgW - contentW) / 2 centers all content in the canvas.
    const contentW =
      PAD * 2 + colKeys.length * COL_W + (hasEvents ? COL_W + 250 : 0);
    const svgMinW = Math.max(W, contentW);

    // canvas width: at least W, and large enough for ghost column / callouts.
    let svgW = svgMinW;
    if (hasEvents) svgW = Math.max(svgW, eventColX + 250);
    let svgH = PAD * 2 + contentH;
    callouts.forEach(c => {
      svgH = Math.max(svgH, posRaw[c.n.recno].y + 84);
    });

    // ---------- callout box sizing (content-driven, then gutter clamp) ----------
    const cjkWidth = (s) => String(s).replace(/[一-鿿぀-ヿ〇-〿]/g, "  ").length;
    const labelRectOf = (n) => {
      const q = pos[n.recno];
      const head = `${n.virtual ? "" : n.recno + " · "}${n.date}${n.stage ? " " + n.stage : ""}`;
      const areaTxt = n.area ? `（${n.area}區段）` : "";
      const schedTxt = n.virtual
        ? ""
        : scheduleBadgeText(caseScheduleOf(p, ((n.links || {}).taipei || [])[0]));
      const w = cjkWidth(head) + areaTxt.length * 11 + schedTxt.length * 6.5 + 14 + 12;
      return { x: q.x + 14, y: q.y - 30, w, h: 50 };
    };
    const implLabelW = (label, value) => {
      const s = String(label || "");
      const v = String(value || "");
      return 8 + cjkWidth(s) * 11 + 10 + cjkWidth(v) * 11;
    };
    const implBoxW = (c) => {
      const w = Math.max(...c.rows.map(r => implLabelW(r.label, r.value)));
      return Math.max(CALLOUT_MIN_W, Math.min(w + CALLOUT_PAD, CALLOUT_GUTTER_CAP));
    };
    const implBoxH = (c) => {
      const lines = c.rows.reduce((acc, r) => acc + (String(r.value).length > 20 ? 2 : 1), 0);
      return lines * 14 + 6;
    };

    callouts.forEach(c => {
      c.boxW = implBoxW(c);
      c.boxH = implBoxH(c);
    });

    // gutter width = widest callout box (0 when no callouts)
    const gutterW = callouts.length ? Math.max(...callouts.map(c => c.boxW)) : 0;

    // canvas width: at least W, plus gutter if present, plus ghost column / callouts.
    // contentW already includes gutterW so tracks start right of the gutter.
    svgW = svgMinW + gutterW;
    if (hasEvents) svgW = Math.max(svgW, eventColX + 250);

    callouts.forEach(c => {
      svgH = Math.max(svgH, posRaw[c.n.recno].y + 84);
    });

    // apply horizontal centering once svgW is final
    const xOffset = (svgW - contentW) / 2;
    const gutterX = xOffset + PAD; // gutter starts after left padding
    const pos = {};
    const evPos = {};
    Object.entries(posRaw).forEach(([k, v]) => { pos[k] = { x: xOffset + gutterW + v.x, y: v.y }; });
    Object.entries(evPosRaw).forEach(([k, v]) => { evPos[k] = { x: xOffset + gutterW + v.x, y: v.y }; });

    // ---------- callout placement: top-to-bottom sweep in gutter ----------
    // Each box starts at its node's row; moves down only when overlapping
    // the box above (CALLOUT_GAP), never up. Leader connects box to node circle.
    let lastBoxBottom = PAD; // y of last box bottom, relative to content area
    callouts.forEach((c, ci) => {
      const np = pos[c.n.recno];
      const h = c.boxH;
      let y = np.y - h / 2; // center box on node row
      if (y < PAD) y = PAD;
      if (lastBoxBottom && y < lastBoxBottom + CALLOUT_GAP) y = lastBoxBottom + CALLOUT_GAP;
      const x = gutterX;
      c.rect = { x, y, w: c.boxW, h };
      lastBoxBottom = y + h;
      svgH = Math.max(svgH, y + h + CALLOUT_PAD);
      svgW = Math.max(svgW, gutterX + c.boxW + CALLOUT_PAD);
    });

    // layoutRects: every placed rectangle for the viewer smoke overlap guard.
    // Kept here so renderer and guard share one geometry source.
    const calloutRect = (c) => {
      const r = c.rect;
      return { id: `callout:${c.n.recno}`, x: r.x, y: r.y, w: r.w, h: r.h };
    };
    const leaderSeg = (c) => {
      const r = c.rect, np = pos[c.n.recno];
      const x1 = r.x + r.w; // right edge of gutter box
      const y1 = c.leadY != null ? c.leadY : r.y + c.boxH / 2;
      const x2 = np.x - 7;
      const y2 = y1;
      return { id: `leader:${c.n.recno}`, x1, y1, x2, y2, owns: `callout:${c.n.recno}` };
    };
    const nodeLabelRect = (n) => {
      const r = labelRectOf(n);
      return { id: `node:${n.recno}`, x: r.x, y: r.y, w: r.w, h: r.h };
    };
    const eventRect = (e) => {
      const q = evPos[e.label];
      return { id: `event:${e.label}`, x: q.x - 8, y: q.y - 12, w: 240, h: 26 };
    };
    const orphanRect = (v) => {
      const p2 = pos[v.recno];
      if (!p2) return null;
      const r = labelRectOf(v);
      return { id: `orphan:${v.recno}`, x: p2.x + 14 - 7, y: p2.y - 30 - 10, w: r.w + 14, h: r.h + 10 };
    };
    const orphanEdge = (d) => {
      const a = pos[d.from], b = pos[d.to];
      if (!a || !b) return null;
      return { id: `orphan-edge:${d.from}->${d.to}`, x1: a.x, y1: a.y, x2: b.x, y2: b.y };
    };
    window.__LAYOUT_RECTS = {
      gutterX: xOffset + PAD,
      gutterW,
      callouts: callouts.map(calloutRect),
      nodes: nodes.map(nodeLabelRect),
      events: events.map(eventRect),
      orphans: virtualNodes.filter(v => pos[v.recno]).map(orphanRect).filter(Boolean),
      leaders: callouts.map(leaderSeg),
      orphanEdges: orphanDots.map(orphanEdge).filter(Boolean),
    };

    // §2.5: stage bands and count chips removed from rendering (clash with
    // the callout gutter). Stage clustering still orders rows and tags
    // undated members as (未核定).
    const bandHtml = "";

    let s = `<h2><span class="chip" style="background:${districtColor(p.district)}"></span>${escapeHtml(p.project_id)}</h2>
      <div class="district">${escapeHtml(p.district)} · ${escapeHtml(p.section)} · ${escapeHtml(p.implementer)} · 共 ${p.member_recnos.length} 筆</div>
      <div class="legend">
        <span class="rev">版本（核定時序）</span>
        <span class="sec">區段</span>
      </div>
      <div class="graph-viewport"><div class="graph-zoom">
      <svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet">${bandHtml}`;

    // §3: track edges remain in projects.json data but are not drawn.
    p.edges.forEach(e => {
      if (e.kind === "track") return;
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

    // §4: orphan dotted edges — each orphan to the recno row directly above it
    // (its branch-off point), or the row directly under when none sits above.
    orphanDots.forEach(d => {
      const a = pos[d.from], b = pos[d.to];
      if (!a || !b) return;
      s += `<line class="edge orphan" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
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
        : scheduleBadgeText(caseScheduleOf(p, ((n.links || {}).taipei || [])[0]));
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
    // building-permit-adapter (S15): the 使照 slot's callout names the
    // building authority's permit when the project carries one.
    if (hasEvents) {
      const permit = (p.links || {}).permit || null;
      events.forEach(e => {
        const b = evPos[e.label];
        const colorCls = e.national ? "national" : "taipei";
        const href = (!e.national && !e.anchored && e.case)
          ? `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${e.case}`
          : "";
        const isUlic = e.label === "使照核發日期";
        const permitTxt = (isUlic && permit && permit.permit_no)
          ? `　執照${permit.permit_no}${permit.date ? `（${fmtDateReverse(permit.date)}）` : ""}` : "";
        const inner = `<circle r="6"></circle>
          <text class="event-label ${colorCls}" x="11" y="3">${escapeHtml(e.label)}：${escapeHtml(fmtDateReverse(e.date))}${escapeHtml(permitTxt)}</text>
          ${e.prov ? `<text class="chain-prov" x="11" y="14">${escapeHtml(e.prov)}</text>` : ""}
          ${e.natCorroborated ? `<foreignObject x="-5" y="-24" width="18" height="14"><div xmlns="http://www.w3.org/1999/xhtml"><span class="node-milestone-badge national" title="國土署里程碑">國</span></div></foreignObject>` : ""}`;
        s += `<g class="event-node" transform="translate(${b.x},${b.y})">` +
          (href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${inner}</a>` : inner) +
          `</g>`;
      });
    }

    // Per-record implementation callouts: render the pre-placed rects in the gutter.
    callouts.forEach(c => {
      const r = c.rect;
      const np = pos[c.n.recno];
      const rowsHtml = c.rows.map(row =>
        `<div class="impl-callout-row"><span>${escapeHtml(row.label)}</span><b class="${row.changed ? "callout-diff" : ""}" title="${escapeHtml(row.value)}">${escapeHtml(row.value)}</b></div>`
      ).join("");
      // Route the leader horizontally at a y that clears every neighbour node's
      // label band across the gutter span; otherwise center on the box.
      const leadX1 = r.x + r.w, leadX2 = np.x - 7;
      const leaderOverlap = (cy) => {
        for (const nn of nodes) {
          if (nn.recno === c.n.recno) continue;
          const lr = labelRectOf(nn);
          if (!lr) continue;
          const lo = lr.y, hi = lr.y + lr.h;
          if (cy > lo && cy < hi && leadX1 < lr.x + lr.w && leadX2 > lr.x) {
            return true;
          }
        }
        return false;
      };
      // try the box center, then scan ys across the box height (every 2 px);
      // fall back to placing the leader at the node's row so it enters the node
      // circle perpendicularly rather than crossing a label band horizontally.
      let leadY = r.y + c.boxH / 2;
      if (leaderOverlap(leadY)) {
        let found = false;
        for (let cy = r.y + 4; cy <= r.y + c.boxH - 4 && !found; cy += 2) {
          if (!leaderOverlap(cy)) { leadY = cy; found = true; }
        }
        if (!found) leadY = np.y + 9;
      }
      c.leadY = leadY;
      s += `<line class="callout-leader" x1="${leadX1}" y1="${leadY}" x2="${leadX2}" y2="${leadY}"></line>`;
      s += `<foreignObject x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}"><div xmlns="http://www.w3.org/1999/xhtml" class="impl-callout">${rowsHtml}</div></foreignObject>`;
    });
    s += "</svg></div></div>";

    const border = p.borderline || [];
    if (border.length) {
      s += `<p class="flag">⚠ 臨界對（相似度 0.5–0.7，未自動合併，待人工檢視）：` +
        border.map(b => `編號 ${b[0]} ↔ ${b[1]}（${b[2]}）`).join("；") + "</p>";
    }

    // Detail table with tiered columns (essential + full)
    const essentialCols = ["recno", "date", "stage", "track", "is_current", "case_name", "land", "section", "implementer", "planner", "review_flags", "auto_fixes", "recovery", "milestones"];
    const fullCols = ["parcels", "aliases", "land_count", "orig_count", "named_anchor", "area_section"];
    const allCols = [...essentialCols, ...fullCols];

    // Recovery provenance (recover-truncated-rows-via-api): a row the publisher
    // truncated and the pass re-identified via the city's APIs. The badges name
    // what the viewer must not silently gloss over: a partial list, a repaired
    // cell typo, an A/B zone attachment, a ±1-day date.
    const recoveryBadges = (rec) => {
      const r = rec.recovery;
      if (!r) return "";
      const f = r.flags || {};
      const parts = ['<span class="badge">復原</span>'];
      if (f.partial) parts.push('<span class="badge">部分清單</span>');
      if ((f.normalized || []).length) {
        parts.push('<span class="badge">修正 ' + f.normalized.map(escapeHtml).join("、") + '</span>');
      }
      if (f["ambiguous-zone"]) parts.push('<span class="badge">A/B併案</span>');
      if (f["date-pm1"]) parts.push('<span class="badge">日期±1</span>');
      if (f["similarity-band"]) parts.push('<span class="badge">相似度帶</span>');
      const cases = (r.cases || []).join("、");
      const list = r.list_source ? `<span class="muted">${escapeHtml(r.list_source)}</span>` : "";
      return parts.join(" ") + (cases ? ` 案號 ${escapeHtml(cases)}` : "") + " " + list;
    };

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
        } else if (col === "recovery") {
          val = recoveryBadges(rec);
        } else if (col === "parcels" || col === "aliases") {
          // (viewer-stage-chip-coverage) human-readable: lists as prose, empty
          // as an em dash — raw JSON literals undercut the "say what was read"
          // surface.
          val = fmtCell(rec[col]);
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
        recovery: "復原",
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
        links.taipei.forEach(cid => {
          const url = `https://gis.uro.taipei/r_progress_detail.aspx?case_id=${cid}`;
          const nm = linkLabels.byCase[cid] || "";
          const sched = schedules[cid] || "";
          // (supersede-headerless-cases-and-discover-new-ids D6) the city re-filed
          // this case under a new id and left it with no current state — name the
          // successor instead of a status badge (11211211 → 11409026).
          const succ = (links.superseded_by || {})[cid] || "";
          const schedBadge = succ ? "" : scheduleBadgeText(sched);
          const succNote = succ ? ` <span class="link-schedule">已由 ${escapeHtml(succ)} 取代</span>` : "";
          s += `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener">臺北市都市更新審議服務平台 (case_id: ${cid})</a>${nm ? ` — <span class="link-case-name">${escapeHtml(nm)}</span>` : ""}${schedBadge ? ` <span class="link-schedule">${escapeHtml(schedBadge.trim())}</span>` : ""}${succNote}</li>`;
        });
        // D4c (2026-11-05): the family "never approved" note is retired — a
        // gazette family holds a gazette approval by construction, and the 4
        // projects it named all carry an approved current node.
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

  // Exposed for the viewer smoke harness so it can recompute layout rects
  // per project without re-clicking every item.
  if (typeof window !== "undefined") window.renderDetail = renderDetail;
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