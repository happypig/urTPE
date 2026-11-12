/* Policy dashboard for the urTPE viewer.
 *
 * Reads the same window.PROJECTS payload as app.js and derives everything in
 * the browser: one flat row per project (stage, idle time, durations,
 * households, public land), then per-district aggregates. No build step, no
 * dependency, no network beyond this directory.
 *
 * State lives in the URL hash (#district=萬華區&lang=en) so a view can be linked.
 */
(function () {
  "use strict";

  const ALL = "全市";
  const STAGES = ["已核定未領建照", "已領建照未開工", "施工中", "已完工"];
  const IDLE5 = "停滯5年以上";
  const IDLE3 = "停滯3至5年";
  const DAY = 86400000;

  // ---------------------------------------------------------------- text
  // [English, 中文]
  const L = {
    title: ["Taipei urban renewal approved cases · Policy dashboard", "臺北市都市更新核定案件 · 政策儀表板"],
    navViewer: ["Project history", "專案歷史圖"],
    navAbout: ["About", "關於"],
    loadFail: ["Could not load projects.data.js.", "無法載入 projects.data.js。"],
    city: ["Taipei City", "臺北市"],
    allDistricts: ["All districts", "全部行政區"],
    district: ["District", "行政區"],
    kProjects: ["Approved projects", "已核定專案"],
    kStalled: ["Unfinished, idle 5+ years", "未完工且停滯五年以上"],
    kReview: ["Median review time", "審議時間中位數"],
    kHouseholds: ["Households in unfinished projects", "未完工專案內的原住戶"],
    kPublic: ["Public land in unfinished projects", "未完工專案內的公有地"],
    kWelfare: ["Public-benefit floor area", "公益設施面積"],
    years: ["years", "年"],
    householdsUnit: ["", "戶"],
    sStalled: ["Stalled cases", "停滯案件"],
    sStalledLede: [
      "A project is idle when none of its recorded milestones, approvals or permits moved in the stated period, measured to the latest gazette.",
      "「停滯」是指專案的里程碑、核定與執照紀錄在該期間內都沒有新進度，計算至最新一期公報。",
    ],
    cPipeline: ["Where approved projects stand", "已核定專案的進度分布"],
    cPipelineCap: [
      "Projects by furthest milestone reached, split by time since last recorded progress.",
      "依已達到的最後階段分類，並依距上次進度紀錄的時間區分。",
    ],
    moving: ["Completed or moving", "已完工或推進中"],
    idle3: ["Idle 3 to 5 years", "停滯三至五年"],
    idle5: ["Idle 5+ years", "停滯五年以上"],
    tWatch: ["Watchlist: unfinished projects idle three years or more", "觀察名單：停滯三年以上的未完工專案"],
    tWatchCap: [
      "Longest idle first. Project names open the project\u2019s history graph.",
      "停滯最久者在前。點選專案名稱可開啟該專案的歷史圖。",
    ],
    thProject: ["Project", "專案"],
    thStage: ["Stage", "階段"],
    thLast: ["Last progress", "最後進度"],
    thIdle: ["Idle years", "停滯年數"],
    thHouseholds: ["Households", "原住戶"],
    thImplementer: ["Implementer", "實施者"],
    thPublic: ["Public land ㎡", "公有地 ㎡"],
    thPublicPct: ["% of site", "占基地 %"],
    noWatch: ["No unfinished project here has been idle for three years.", "此範圍內沒有停滯三年以上的未完工專案。"],
    noPublic: ["No unfinished project here includes public land.", "此範圍內沒有含公有地的未完工專案。"],
    sReview: ["Review workload and speed", "審議量能與時程"],
    sReviewLede: [
      "How many approvals the review bodies issue each year, and how long a first approval takes.",
      "審議單位每年核定多少案，以及首次核定要花多久。",
    ],
    cApprovals: ["Approvals issued each year", "每年核定件數"],
    cApprovalsCap: [
      "New plans (擬訂) against changes to plans already approved (變更). The latest year is partial.",
      "新擬訂計畫與已核定計畫的變更。最近一年尚未滿一年。",
    ],
    newPlans: ["New plans", "擬訂"],
    changes: ["Changes", "變更"],
    cReview: ["Median review years, by year of first approval", "審議年數中位數，依首次核定年度"],
    cReviewCap: [
      "Each project is measured from the plan application on its first approval's own city case. Years with few projects move a lot.",
      "每件專案自其首次核定案件的計畫申請日起算。專案數少的年度波動較大。",
    ],
    review1: ["Application to first approval", "自申請至首次核定"],
    review2: ["Application to the approval before the building permit", "自申請至建照核發前之核定"],
    median: ["Median", "中位數"],
    projectsN: ["Projects", "專案數"],
    noApprovals: ["No approvals recorded.", "沒有核定紀錄。"],
    noReview: ["No review times recorded.", "沒有審議時間紀錄。"],
    sReloc: ["Relocation demand", "安置需求"],
    sRelocLede: [
      "Existing units in projects that are approved but have no use permit yet: the households already displaced or waiting.",
      "已核定但尚未取得使用執照的專案內既有戶數，也就是已搬遷或等待中的住戶。",
    ],
    cHouseholds: ["Households in unfinished projects, by district", "各行政區未完工專案內的原住戶"],
    cHouseholdsCap: ["Existing units, split by whether construction has started.", "既有戶數，依是否已開工區分。"],
    building: ["Under construction", "施工中"],
    waiting: ["Not yet started", "尚未開工"],
    sHousing: ["Public land in the pipeline", "公有地與公有分回"],
    sHousingLede: [
      "State and city land inside unfinished projects shows where the public share of renewed floor area will come from.",
      "未完工專案內的國有與市有土地，顯示公有分回可能來自哪裡。",
    ],
    cPubland: ["Public land in unfinished projects, by district", "各行政區未完工專案內的公有地"],
    cPublandCap: ["Square metres of state and city land.", "國有與市有土地面積（㎡）。"],
    publicArea: ["Public land ㎡", "公有地 ㎡"],
    tPublic: ["Largest public land holdings in unfinished projects", "未完工專案中公有地面積最大者"],
    tPublicCap: ["Top 12 by public land area.", "依公有地面積取前 12 名。"],
    notes: ["Definitions and limits", "定義與限制"],
  };
  const STAGE_EN = {
    已核定未領建照: "Approved, no building permit",
    已領建照未開工: "Permit issued, not started",
    施工中: "Under construction",
    已完工: "Completed",
  };
  const NOTES = {
    en: [
      ["Stage.", "已完工: a use permit date is recorded. 施工中: a construction start date but no use permit. 已領建照未開工: a building permit but no start. 已核定未領建照: approved, no building permit recorded."],
      ["Idle years.", "Years between the latest recorded milestone, approval or permit of a project and the latest gazette. The 3 and 5 year cut-offs are a convention of this page, not a legal definition, and a quiet record can also mean missing data."],
      ["Review time.", "Measured on the city case of a project's first approval (its earliest 擬訂 plan or rights-transfer approval; outline approvals never count): years from that case's plan application to its approval, and to the last approval before the building permit — or the latest approval when no permit is recorded. Projects with only an outline approval are left out and counted in the chart caption."],
      ["Coverage.", "Only approved cases appear here; projects stuck before approval are not in the gazette. Households, land areas and public-benefit area are the figures filed with each plan and may differ from built results."],
    ],
    zh: [
      ["階段。", "已完工：有使用執照日期。施工中：有開工日期但無使用執照。已領建照未開工：有建造執照但未開工。已核定未領建照：已核定，但無建造執照紀錄。"],
      ["停滯年數。", "專案最近一筆里程碑、核定或執照紀錄，距最新一期公報的年數。三年與五年的門檻是本頁的慣例，並非法定定義；沒有紀錄也可能只是資料缺漏。"],
      ["審議時間。", "以專案首次核定案件（最早的擬訂事業計畫或權利變換計畫，不含事業概要）為準：自該案的計畫申請日，至該案核定日的年數，以及至建照核發前最後一次核定的年數；無建照紀錄者量至最近一次核定。僅有事業概要核定的專案不計入，件數標示於圖表說明。"],
      ["涵蓋範圍。", "這裡只有已核定案件；核定前就卡住的案件不在公報內。戶數、土地面積與公益設施面積為計畫書所載數字，可能與實際興建結果不同。"],
    ],
  };

  // --------------------------------------------------------------- state
  const state = { district: "", lang: "zh" };
  function readHash() {
    const q = new URLSearchParams(location.hash.replace(/^#/, ""));
    state.district = q.get("district") || "";
    state.lang = q.get("lang") === "en" ? "en" : "zh";
  }
  function writeHash() {
    const q = new URLSearchParams();
    if (state.district) q.set("district", state.district);
    if (state.lang === "en") q.set("lang", "en");
    const h = q.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }
  const t = (k) => L[k][state.lang === "zh" ? 1 : 0];
  const stageLabel = (s) => (state.lang === "zh" ? s : STAGE_EN[s] || s);
  const f0 = (n) => Math.round(n).toLocaleString("en-US");
  const f1 = (n) => Number(n).toFixed(1);

  // ----------------------------------------------------------------- dom
  function el(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) {
      const v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "class") e.className = v;
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v);
    }
    for (const c of kids.flat()) {
      if (c == null || c === false) continue;
      e.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return e;
  }
  const NS = "http://www.w3.org/2000/svg";
  function sv(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  const b = (v) => el("b", null, v);

  // ------------------------------------------------------------- flatten
  function flatten(payload) {
    const asof = Date.parse(payload.published_date + "T00:00:00Z");
    function pd(s) {
      if (!s) return null;
      s = String(s).trim();
      let y, mo, d;
      let m = /^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})/.exec(s);
      if (m) { y = +m[1]; mo = +m[2]; d = +m[3]; }
      else {
        m = /^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/.exec(s); // ROC date, 107.02.08
        if (!m) return null;
        y = +m[1] + 1911; mo = +m[2]; d = +m[3];
      }
      const ms = Date.UTC(y, mo - 1, d);
      const dt = new Date(ms);
      if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
      if (y < 1995 || ms > asof) return null;
      return ms;
    }
    const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };
    const int = (v) => (v == null ? null : Math.round(v));
    const yrs = (a, c) => (a != null && c != null && c >= a ? Math.round(((c - a) / DAY / 365.25) * 100) / 100 : null);
    const iso = (ms) => (ms == null ? "" : new Date(ms).toISOString().slice(0, 10));
    const min = (a) => (a.length ? Math.min.apply(null, a) : null);
    const max = (a) => (a.length ? Math.max.apply(null, a) : null);
    const keep = (a) => a.filter((x) => x != null);

    const rows = [];
    const approvals = [];
    for (const p of payload.projects) {
      const l = p.links || {};
      const im = p.implementation || {};
      const cm = Object.values(l.case_milestones || {});
      const mn = l.milestones_national || {};
      const nodes = p.nodes || [];
      const nd = keep(nodes.map((n) => pd(n.date))).sort((a, c) => a - c);
      const allOf = (key) => keep(cm.map((c) => pd(c[key])));

      // Review time is anchored on the first approval node and read from that
      // node's own city case (policy-dashboard, dashboard-review-time): the
      // 概要 application is an outline, not the plan under review, and the
      // national date is a second copy of the city's. 事業概要 rows never count.
      const cmById = l.case_milestones || {};
      const eligible = nodes
        .map((n) => ({ n, ms: pd(n.date) }))
        .filter((x) => x.ms != null && String(x.n.track || "") !== "事業概要")
        .sort((a, c) => a.ms - c.ms);
      const casesOf = (n) => {
        const found = ((n.links && n.links.taipei) || []).map((id) => cmById[id]).filter(Boolean);
        if (found.length) return found;
        return n.links && n.links.milestones_taipei ? [n.links.milestones_taipei] : [];
      };
      const dateOf = (cases, keys) => min(keep(cases.flatMap((c) => keys.map((k) => pd(c[k])))));
      const approvalOf = (x) => { const d = dateOf(casesOf(x.n), ["核定日期", "權變核定日期"]); return d != null ? d : x.ms; };
      // the 擬訂 node first, else the earliest eligible node (design D2)
      const firstX = eligible.find((x) => String(x.n.stage || "").indexOf("擬訂") === 0) || eligible[0] || null;
      const apply = firstX ? dateOf(casesOf(firstX.n), ["申請計畫日期", "申請權變日期"]) : null;
      const first = firstX ? approvalOf(firstX) : null;
      const permit = min(allOf("建照核發日期"));
      // line 2 ends on the latest eligible node before the permit, or the
      // latest node when no permit is recorded; absent when the permit
      // precedes every node (design D3)
      let endX = null;
      if (permit != null) { const before = eligible.filter((x) => x.ms < permit); endX = before.length ? before[before.length - 1] : null; }
      else endX = eligible.length ? eligible[eligible.length - 1] : null;
      const reviewEnd = endX ? approvalOf(endX) : null;
      const onlyOutline = !eligible.length && nodes.length > 0;
      const starts = allOf("開工日期").concat(keep([pd(im.Eng_Start_Date)]));
      const start = min(starts);
      const comps = allOf("使照核發日期").concat(
        keep([pd(im.Ulic_Date), pd(mn["使用核發日期"]), pd((l.permit || {}).date)]));
      const comp = max(comps);
      const everything = nd.concat(
        keep(cm.flatMap((c) => Object.values(c).map(pd))),
        keep(Object.values(mn).map(pd)), comps, starts);
      const last = max(everything);

      const status = comp != null ? "已完工" : start != null ? "施工中" : permit != null ? "已領建照未開工" : "已核定未領建照";
      const idle = yrs(last, asof);
      const flag = status === "已完工" ? "" : idle != null && idle >= 5 ? IDLE5 : idle != null && idle >= 3 ? IDLE3 : "推進中";
      const base = num(im.Base_Area);
      const pub = (num(im.State_Area) || 0) + (num(im.Muni_Area) || 0);

      rows.push({
        project_id: p.project_id,
        district: p.district,
        implementer: p.implementer || "",
        status, flag,
        first_approval: iso(first),
        last_activity: iso(last),
        idle_years: idle,
        review_years: yrs(apply, first),
        review2_years: yrs(apply, reviewEnd),
        only_outline: onlyOutline,
        total_years: yrs(apply, comp),
        old_doors: int(num(im.Old_Doors)),
        welfare_area: int(num(im.Welfare_Area)),
        public_area: int(pub),
        public_pct: base ? Math.round(Math.min(pub / base, 1) * 1000) / 10 : null,
      });
      for (const n of nodes) {
        const ms = pd(n.date);
        if (ms == null) continue;
        approvals.push({
          district: p.district,
          year: new Date(ms).getUTCFullYear(),
          change: String(n.stage || "").indexOf("變更") === 0,
        });
      }
    }
    return { rows, approvals };
  }

  // ----------------------------------------------------------- aggregate
  function median(a) {
    const s = a.filter((v) => v != null).sort((x, y) => x - y);
    if (!s.length) return null;
    const h = s.length >> 1;
    return Math.round((s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2) * 10) / 10;
  }
  const sum = (a, k) => a.reduce((n, r) => n + (r[k] || 0), 0);

  function kpiOf(district, g) {
    const open = g.filter((p) => p.status !== "已完工");
    const building = open.filter((p) => p.status === "施工中");
    const done = g.length - open.length;
    return {
      district,
      projects: g.length,
      completed: done,
      completed_pct: g.length ? Math.round((done / g.length) * 1000) / 10 : null,
      stalled5: open.filter((p) => p.flag === IDLE5).length,
      stalled3: open.filter((p) => p.flag === IDLE3).length,
      median_review: median(g.map((p) => p.review2_years)),   // the card: to the approval before the permit
      median_review1: median(g.map((p) => p.review_years)),   // to first approval
      median_total: median(g.map((p) => p.total_years)),
      outline_only: g.filter((p) => p.only_outline).length,
      open_households: sum(open, "old_doors"),
      households_building: sum(building, "old_doors"),
      households_waiting: sum(open, "old_doors") - sum(building, "old_doors"),
      open_public_area: sum(open, "public_area"),
      open_public_projects: open.filter((p) => p.public_area > 0).length,
      welfare_area: sum(g, "welfare_area"),
      welfare_projects: g.filter((p) => p.welfare_area > 0).length,
    };
  }

  function aggregate(flat) {
    const districts = [...new Set(flat.rows.map((p) => p.district))];
    const kpi = new Map([[ALL, kpiOf(ALL, flat.rows)]]);
    for (const d of districts) kpi.set(d, kpiOf(d, flat.rows.filter((p) => p.district === d)));
    return { districts, kpi };
  }

  function pipelineOf(rows) {
    return STAGES.map((status) => {
      const s = rows.filter((p) => p.status === status);
      const i5 = s.filter((p) => p.flag === IDLE5).length;
      const i3 = s.filter((p) => p.flag === IDLE3).length;
      return { status, moving: s.length - i5 - i3, idle3: i3, idle5: i5 };
    });
  }
  function approvalsOf(list) {
    const m = new Map();
    for (const a of list) {
      if (!m.has(a.year)) m.set(a.year, { year: a.year, newPlans: 0, changes: 0 });
      m.get(a.year)[a.change ? "changes" : "newPlans"] += 1;
    }
    return [...m.values()].sort((x, y) => x.year - y.year);
  }
  function reviewOf(rows) {
    // both intervals keyed by the year of the first approval's date
    const series = (key) => {
      const m = new Map();
      for (const p of rows) {
        if (p[key] == null || !p.first_approval) continue;
        const y = +p.first_approval.slice(0, 4);
        if (!m.has(y)) m.set(y, []);
        m.get(y).push(p[key]);
      }
      return [...m.entries()].sort((x, y) => x[0] - y[0])
        .map(([year, v]) => ({ year, projects: v.length, median: median(v) }));
    };
    return { first: series("review_years"), pre: series("review2_years") };
  }

  // -------------------------------------------------------------- charts
  const COLOR = { ok: "var(--fill)", alt: "var(--alt)", warn: "var(--warn)", bad: "var(--current)" };

  function frame(box, h, label) {
    box.replaceChildren();
    const w = Math.max(260, box.clientWidth || 600);
    const svg = sv("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: h, role: "img", "aria-label": label });
    const tip = el("div", { class: "tip", hidden: "" });
    box.append(svg, tip);
    function show(ev, lines) {
      tip.hidden = false;
      tip.replaceChildren(...lines.map((s) => el("div", null, s)));
      const r = box.getBoundingClientRect();
      let x = ev.clientX - r.left + 12;
      if (x + tip.offsetWidth > r.width) x = Math.max(0, ev.clientX - r.left - tip.offsetWidth - 12);
      tip.style.left = x + "px";
      tip.style.top = ev.clientY - r.top + 14 + "px";
    }
    const hide = () => { tip.hidden = true; };
    return { svg, w, show, hide };
  }
  function textW(svg, strs) {
    const tx = sv("text");
    svg.append(tx);
    let m = 0;
    for (const s of strs) {
      tx.textContent = s;
      m = Math.max(m, tx.getComputedTextLength() || String(s).length * 8);
    }
    tx.remove();
    return m;
  }
  function hover(node, show, hide, lines) {
    node.addEventListener("pointerenter", (ev) => show(ev, lines));
    node.addEventListener("pointermove", (ev) => show(ev, lines));
    node.addEventListener("pointerleave", hide);
    node.addEventListener("click", (ev) => show(ev, lines));
  }
  function niceTicks(maxV, n) {
    if (!(maxV > 0)) return [0, 1];
    const raw = maxV / n;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 5, 10].map((k) => k * p).find((s) => s >= raw);
    const out = [];
    for (let v = 0; v < maxV + step - 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6);
    return out;
  }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);

  // Horizontal stacked bars, one row per item, total printed at the end.
  function hbars(box, o) {
    const bh = 26;
    const { svg, w, show, hide } = frame(box, o.rows.length * bh + 4, o.aria);
    const totals = o.rows.map((r) => o.segs.reduce((n, s) => n + (r[s.k] || 0), 0));
    const lw = Math.min(textW(svg, o.rows.map(o.label)), w * 0.5);
    const vw = textW(svg, totals.map(f0));
    const x = lin(0, Math.max.apply(null, totals.concat(1)), lw + 8, Math.max(lw + 40, w - vw - 10));
    o.rows.forEach((r, i) => {
      const y = i * bh + 4;
      const g = sv("g", o.dim && o.dim(r) ? { opacity: 0.4 } : {});
      g.append(sv("text", { x: lw, y: y + 13, "text-anchor": "end" }, o.label(r)));
      let acc = 0;
      for (const s of o.segs) {
        const v = r[s.k] || 0;
        if (!v) continue;
        const rect = sv("rect", { x: x(acc), y, height: 18, width: Math.max(1, x(acc + v) - x(acc)), rx: 2, style: "fill:" + s.color });
        hover(rect, show, hide, [o.label(r), s.name + ": " + f0(v)]);
        g.append(rect);
        acc += v;
      }
      g.append(sv("text", { class: "val", x: x(acc) + 5, y: y + 13 }, f0(totals[i])));
      svg.append(g);
    });
  }

  function yAxis(svg, y, ticks, x0, x1, fmt) {
    for (const v of ticks) {
      svg.append(sv("line", { class: "gridline", x1: x0, x2: x1, y1: y(v), y2: y(v) }));
      svg.append(sv("text", { x: x0 - 6, y: y(v) + 4, "text-anchor": "end" }, fmt(v)));
    }
  }

  function approvalsChart(box, rows, scopeName) {
    if (!rows.length) { box.replaceChildren(el("p", { class: "empty" }, t("noApprovals"))); return; }
    const h = 240;
    const { svg, w, show, hide } = frame(box, h, scopeName + " · " + t("cApprovals"));
    const by = new Map(rows.map((r) => [r.year, r]));
    const y0 = rows[0].year, y1 = rows[rows.length - 1].year;
    const n = y1 - y0 + 1;
    const ticks = niceTicks(Math.max.apply(null, rows.map((r) => r.newPlans + r.changes)), 4).filter(Number.isInteger);
    const top = ticks[ticks.length - 1];
    const y = lin(0, top, h - 22, 8);
    const ml = textW(svg, ticks.map(f0)) + 10;
    const half = textW(svg, [String(y1)]) / 2;
    const left = ml + half / 2, right = w - 2 - half;
    const band = (right - left) / n;
    const bw = band * 0.82;
    const xOf = (yr) => left + (yr - y0) * band + (band - bw) / 2;
    yAxis(svg, y, ticks, ml, w - 2, f0);
    const step = Math.max(1, Math.ceil(n / Math.max(1, (w - ml) / 44)));
    for (let yr = y1; yr >= y0; yr -= step) {
      svg.append(sv("text", { x: xOf(yr) + bw / 2, y: h - 6, "text-anchor": "middle" }, yr));
    }
    for (let yr = y0; yr <= y1; yr++) {
      const r = by.get(yr);
      if (!r) continue;
      const g = sv("g");
      g.append(sv("rect", { x: xOf(yr), width: bw, y: y(r.newPlans), height: y(0) - y(r.newPlans), style: "fill:" + COLOR.ok }));
      g.append(sv("rect", { x: xOf(yr), width: bw, y: y(r.newPlans + r.changes), height: y(r.newPlans) - y(r.newPlans + r.changes), style: "fill:" + COLOR.alt }));
      hover(g, show, hide, [String(yr), t("newPlans") + ": " + f0(r.newPlans), t("changes") + ": " + f0(r.changes)]);
      svg.append(g);
    }
  }

  function reviewChart(box, data, scopeName) {
    // two series on one frame: to first approval, and to the approval before
    // the building permit (dashboard-review-time); each point names its own
    // interval and its own project count
    const series = [
      { rows: data.first, name: t("review1"), color: COLOR.ok },
      { rows: data.pre, name: t("review2"), color: COLOR.alt },
    ].filter((s) => s.rows.length);
    if (!series.length) { box.replaceChildren(el("p", { class: "empty" }, t("noReview"))); return; }
    const h = 240;
    const { svg, w, show, hide } = frame(box, h, scopeName + " · " + t("cReview"));
    const all = series.flatMap((s) => s.rows);
    const ticks = niceTicks(Math.max.apply(null, all.map((r) => r.median)), 4);
    const y = lin(0, ticks[ticks.length - 1], h - 22, 8);
    const ml = textW(svg, ticks.map(f1)) + 10;
    let y0 = Math.min.apply(null, all.map((r) => r.year)), y1 = Math.max.apply(null, all.map((r) => r.year));
    if (y0 === y1) { y0 -= 1; y1 += 1; }
    const x = lin(y0, y1, ml + 6 + textW(svg, [String(y0)]) / 2, w - 6 - textW(svg, [String(y1)]) / 2);
    yAxis(svg, y, ticks, ml, w - 2, f1);
    const step = Math.max(1, Math.ceil((y1 - y0 + 1) / Math.max(1, (w - ml) / 48)));
    for (let yr = y1; yr >= y0; yr -= step) {
      svg.append(sv("text", { x: x(yr), y: h - 6, "text-anchor": "middle" }, yr));
    }
    series.forEach((s, si) => {
      const rows = s.rows;
      // Point to point: a curve would suggest values the data lacks.
      svg.append(sv("path", {
        d: rows.map((r, i) => (i ? "L" : "M") + x(r.year) + "," + y(r.median)).join(""),
        style: "fill:none;stroke-width:2;stroke:" + s.color,
      }));
      for (const r of rows) {
        svg.append(sv("circle", { cx: x(r.year), cy: y(r.median), r: 4, style: "fill:" + s.color }));
        const hit = sv("circle", { cx: x(r.year), cy: y(r.median), r: 11, style: "fill:transparent" });
        hover(hit, show, hide, [String(r.year), s.name + ": " + f1(r.median) + " " + t("years"), t("projectsN") + ": " + f0(r.projects)]);
        svg.append(hit);
      }
      const last = rows[rows.length - 1];
      // the first series labels above its last point, the second below, so the two never overprint
      const ly = si ? Math.min(h - 24, y(last.median) + 16) : Math.max(12, y(last.median) - 9);
      svg.append(sv("text", { class: "val", x: x(last.year), y: ly, "text-anchor": "end" }, f1(last.median)));
    });
  }

  // -------------------------------------------------------------- render
  let flat = null;
  let agg = null;
  const app = document.getElementById("app");

  function legend(items) {
    return el("ul", { class: "legend" }, items.map(([c, k]) =>
      el("li", null, el("span", { class: "sw", style: "background:" + COLOR[c] }), t(k))));
  }
  function card(labelKey, value, unit, sub) {
    return el("div", { class: "card" },
      el("p", { class: "kpi-label" }, t(labelKey)),
      el("p", { class: "kpi-num" }, value == null ? "—" : value, unit ? [" ", el("span", { class: "kpi-unit" }, unit)] : null),
      el("p", { class: "sub" }, sub));
  }
  function chartCard(titleKey, capKey, leg, box, capText) {
    return el("div", { class: "card" },
      el("h3", null, t(titleKey)), el("p", { class: "cap" }, capText || t(capKey)), leg, box);
  }
  function projectCell(p) {
    // Opens the project's history graph in the viewer (index.html reads #project=).
    return el("td", null, el("a", { href: "index.html#project=" + encodeURIComponent(p.project_id) }, p.project_id));
  }
  function table(heads, rows, emptyKey, rowOf) {
    return el("div", { class: "scroll" }, el("table", null,
      el("thead", null, el("tr", null, heads.map(([k, numeric]) => el("th", { class: numeric ? "num" : null }, t(k))))),
      el("tbody", null, rows.length
        ? rows.map(rowOf)
        : el("tr", null, el("td", { colspan: heads.length }, t(emptyKey))))));
  }
  const cell = (v, cls) => el("td", { class: cls }, v == null || v === "" ? "—" : v);

  function render() {
    const zh = state.lang === "zh";
    document.documentElement.lang = zh ? "zh-Hant" : "en";
    document.title = t("title");
    document.getElementById("title").textContent = t("title");
    document.getElementById("nav-viewer").textContent = t("navViewer");
    const navAbout = document.getElementById("nav-about");
    if (navAbout) navAbout.textContent = t("navAbout");
    document.querySelectorAll(".lang").forEach((btn) =>
      btn.setAttribute("aria-pressed", String(btn.dataset.lang === state.lang)));

    if (!flat) return;
    if (state.district && !agg.kpi.has(state.district)) state.district = "";
    const scope = state.district || ALL;
    const scopeName = state.district || t("city");
    const k = agg.kpi.get(scope);
    const rows = state.district ? flat.rows.filter((p) => p.district === state.district) : flat.rows;
    const apprs = state.district ? flat.approvals.filter((a) => a.district === state.district) : flat.approvals;

    const take = zh
      ? [b(scopeName), "共有 ", b(f0(k.projects)), " 件已核定都更專案，其中 ", b(f0(k.completed)), " 件已完工。未完工專案中，",
         b(f0(k.stalled5)), " 件已五年以上沒有進度紀錄，", b(f0(k.stalled3)), " 件為三至五年。"]
      : ["Of ", b(f0(k.projects)), " approved renewal projects in ", b(scopeName), ", ", b(f0(k.completed)),
         " are complete. Among the unfinished ones, ", b(f0(k.stalled5)), " show no recorded progress for five years or more and ",
         b(f0(k.stalled3)), " for three to five years."];

    const select = el("select", { "aria-label": t("district"), onchange: (ev) => { state.district = ev.target.value; writeHash(); render(); } },
      el("option", { value: "" }, t("allDistricts")),
      agg.districts.map((d) => el("option", { value: d, selected: d === state.district ? "" : null }, d)));

    const pct = k.completed_pct == null ? "—" : f1(k.completed_pct);
    const med = (v) => (v == null ? "—" : f1(v));
    const kpis = el("div", { class: "kpis" },
      card("kProjects", f0(k.projects), "", zh ? [b(pct), "% 已取得使用執照"] : [b(pct), "% have a use permit"]),
      card("kStalled", f0(k.stalled5), "", zh ? ["另有 ", b(f0(k.stalled3)), " 件停滯三至五年"] : ["Plus ", b(f0(k.stalled3)), " idle for three to five years"]),
      card("kReview", med(k.median_review), t("years"), zh
        ? ["自申請至建照核發前之核定。自申請至首次核定為 ", b(med(k.median_review1)), " 年；已完工專案自申請至使用執照為 ", b(med(k.median_total)), " 年。"]
        : ["Application to the approval before the building permit. ", b(med(k.median_review1)), " years to first approval; ",
           b(med(k.median_total)), " years from application to use permit for completed projects."]),
      card("kHouseholds", f0(k.open_households), t("householdsUnit"), zh
        ? ["施工中 ", b(f0(k.households_building)), " 戶，尚未開工 ", b(f0(k.households_waiting)), " 戶"]
        : [b(f0(k.households_building)), " under construction, ", b(f0(k.households_waiting)), " not yet started"]),
      card("kPublic", f0(k.open_public_area), "㎡", zh
        ? ["共 ", b(f0(k.open_public_projects)), " 件專案含國有或市有土地"]
        : ["State and city land across ", b(f0(k.open_public_projects)), " projects"]),
      card("kWelfare", f0(k.welfare_area), "㎡", zh
        ? ["共 ", b(f0(k.welfare_projects)), " 件專案提供，含各階段"]
        : ["Provided by ", b(f0(k.welfare_projects)), " projects, all stages"]));

    const boxes = {
      pipeline: el("div", { class: "chart" }),
      approvals: el("div", { class: "chart" }),
      review: el("div", { class: "chart" }),
      households: el("div", { class: "chart" }),
      publand: el("div", { class: "chart" }),
    };

    const watch = rows.filter((p) => p.flag === IDLE5 || p.flag === IDLE3).sort((a, c) => c.idle_years - a.idle_years);
    const pubs = rows.filter((p) => p.status !== "已完工" && p.public_area > 0)
      .sort((a, c) => c.public_area - a.public_area).slice(0, 12);

    app.replaceChildren(
      el("div", null, el("p", { class: "take" }, take),
        el("div", { class: "controls" }, el("label", null, t("district"), select))),
      kpis,
      el("section", { id: "stalled" },
        el("h2", null, t("sStalled")), el("p", { class: "lede" }, t("sStalledLede")),
        chartCard("cPipeline", "cPipelineCap", legend([["ok", "moving"], ["warn", "idle3"], ["bad", "idle5"]]), boxes.pipeline),
        el("div", { class: "card" }, el("h3", null, t("tWatch")), el("p", { class: "cap" }, t("tWatchCap")),
          table([["thProject"], ["thStage"], ["thLast"], ["thIdle", 1], ["thHouseholds", 1], ["thImplementer"]], watch, "noWatch",
            (p) => el("tr", null, projectCell(p), cell(stageLabel(p.status), "nowrap"), cell(p.last_activity, "nowrap"),
              cell(p.idle_years.toFixed(2), "num " + (p.flag === IDLE5 ? "flag5" : "flag3")),
              cell(p.old_doors == null ? null : f0(p.old_doors), "num"), cell(p.implementer))))),
      el("section", { id: "review" },
        el("h2", null, t("sReview")), el("p", { class: "lede" }, t("sReviewLede")),
        el("div", { class: "grid" },
          chartCard("cApprovals", "cApprovalsCap", legend([["ok", "newPlans"], ["alt", "changes"]]), boxes.approvals),
          chartCard("cReview", "cReviewCap", legend([["ok", "review1"], ["alt", "review2"]]), boxes.review,
            // the 概要-only notice: these projects count in the project card but in neither interval
            t("cReviewCap") + (k.outline_only
              ? (zh ? ` 不含 ${f0(k.outline_only)} 件僅有事業概要核定的專案。`
                    : ` Excludes ${f0(k.outline_only)} projects with only an outline (事業概要) approval.`)
              : "")))),
      el("section", { id: "relocation" },
        el("h2", null, t("sReloc")), el("p", { class: "lede" }, t("sRelocLede")),
        chartCard("cHouseholds", "cHouseholdsCap", legend([["ok", "building"], ["alt", "waiting"]]), boxes.households)),
      el("section", { id: "housing" },
        el("h2", null, t("sHousing")), el("p", { class: "lede" }, t("sHousingLede")),
        el("div", { class: "grid" },
          chartCard("cPubland", "cPublandCap", null, boxes.publand),
          el("div", { class: "card" }, el("h3", null, t("tPublic")), el("p", { class: "cap" }, t("tPublicCap")),
            table([["thProject"], ["thStage"], ["thPublic", 1], ["thPublicPct", 1], ["thHouseholds", 1]], pubs, "noPublic",
              (p) => el("tr", null, projectCell(p), cell(stageLabel(p.status), "nowrap"), cell(f0(p.public_area), "num"),
                cell(p.public_pct == null ? null : f1(p.public_pct), "num"), cell(p.old_doors == null ? null : f0(p.old_doors), "num")))))),
      el("details", null, el("summary", null, t("notes")),
        NOTES[state.lang].map(([h, body]) => el("p", null, b(h), " ", body))));

    // Charts measure text and width, so they draw after the boxes are in the page.
    const drawCharts = () => {
      hbars(boxes.pipeline, {
        rows: pipelineOf(rows), label: (r) => stageLabel(r.status), aria: scopeName + " · " + t("cPipeline"),
        segs: [{ k: "moving", name: t("moving"), color: COLOR.ok }, { k: "idle3", name: t("idle3"), color: COLOR.warn }, { k: "idle5", name: t("idle5"), color: COLOR.bad }],
      });
      approvalsChart(boxes.approvals, approvalsOf(apprs), scopeName);
      reviewChart(boxes.review, reviewOf(rows), scopeName);
      const byDistrict = agg.districts.map((d) => agg.kpi.get(d));
      const dim = (r) => !!state.district && r.district !== state.district;
      hbars(boxes.households, {
        rows: byDistrict.slice().sort((a, c) => c.open_households - a.open_households), label: (r) => r.district, dim, aria: t("cHouseholds"),
        segs: [{ k: "households_building", name: t("building"), color: COLOR.ok }, { k: "households_waiting", name: t("waiting"), color: COLOR.alt }],
      });
      hbars(boxes.publand, {
        rows: byDistrict.slice().sort((a, c) => c.open_public_area - a.open_public_area), label: (r) => r.district, dim, aria: t("cPubland"),
        segs: [{ k: "open_public_area", name: t("publicArea"), color: COLOR.ok }],
      });
    };
    drawCharts();
    redraw = drawCharts;
  }

  let redraw = null;
  let timer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(timer);
    timer = setTimeout(() => { if (redraw) redraw(); }, 120);
  });
  window.addEventListener("hashchange", () => { readHash(); render(); });
  document.querySelectorAll(".lang").forEach((btn) => btn.addEventListener("click", () => {
    state.lang = btn.dataset.lang === "en" ? "en" : "zh";
    writeHash();
    render();
  }));

  // ---------------------------------------------------------------- load
  function start() {
    const payload = window.PROJECTS;
    if (!payload || !Array.isArray(payload.projects)) { fail(); return; }
    flat = flatten(payload);
    agg = aggregate(flat);
    const c = payload.counts || {};
    document.getElementById("meta").textContent =
      `${c.projects != null ? c.projects : flat.rows.length} 個專案 / ${c.records != null ? c.records : flat.approvals.length} 筆記錄` +
      ` · 統計至 ${payload.published_date || payload.generated_at || ""}`;
    render();
  }
  function fail() {
    app.replaceChildren(el("p", { class: "empty" }, t("loadFail")));
  }
  function loadData() {
    if (window.PROJECTS) { start(); return; }
    const add = (v) => {
      const s = document.createElement("script");
      s.src = "projects.data.js" + (v ? "?v=" + v : "");
      s.onload = start;
      s.onerror = fail;
      document.head.appendChild(s);
    };
    // Borrow the dataset version index.html names, so both pages share one
    // cached copy. Opened from disk (file://) the fetch fails and the plain
    // path is used.
    let asked = null;
    try { asked = fetch("index.html", { cache: "no-cache" }); } catch (e) { asked = null; }
    if (!asked) { add(""); return; }
    asked.then((r) => (r.ok ? r.text() : ""))
      .then((html) => { const m = /projects\.data\.js\?v=([0-9a-zA-Z]+)/.exec(html); add(m ? m[1] : ""); })
      .catch(() => add(""));
  }

  readHash();
  render();
  loadData();
})();
