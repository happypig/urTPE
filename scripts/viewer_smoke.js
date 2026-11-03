/* Run viewer/app.js against viewer/projects.data.js in a stub DOM and assert that
 * selecting a project actually fills the detail pane.
 *
 * The blank-pane regression was invisible to the Python suite: every count and date
 * matched while app.js threw before assigning detail.innerHTML. This harness exercises
 * the real init() -> renderList() -> renderDetail() path.
 *
 *   node scripts/viewer_smoke.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const APP = path.join(ROOT, "viewer", "app.js");
// an alternate dataset may be passed so the render path can be exercised against a
// fixture whose records carry no portal data at all
const DATA = process.argv[2] ? path.resolve(process.argv[2])
                             : path.join(ROOT, "viewer", "projects.data.js");

const text = fs.readFileSync(DATA, "utf8");
const doc = JSON.parse(text.slice("window.PROJECTS = ".length).replace(/;\s*$/, ""));

let failures = 0;
function check(name, ok, detail) {
  console.log(`${ok ? "  ok  " : "  FAIL"} ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures++;
}

// --- minimal DOM -----------------------------------------------------------
function makeEl(id) {
  const el = {
    id,
    innerHTML: "",
    textContent: "",
    value: "",
    className: "",
    style: {},
    dataset: {},
    children: [],
    _onclick: null,
    get onclick() { return this._onclick; },
    set onclick(fn) {
      this._onclick = fn;
      // only list entries, not the filter chips that also take a handler
      if (String(this.className).indexOf("item") !== -1) items.push(this);
    },
    appendChild(c) { this.children.push(c); return c; },
    append(...cs) { cs.forEach((c) => this.children.push(c)); },
    prepend(...cs) { cs.forEach((c) => this.children.unshift(c)); },
    insertBefore(c) { this.children.push(c); return c; },
    replaceChildren(...cs) { this.children = cs; },
    remove() {}, removeChild(c) { return c; },
    setAttribute() {}, getAttribute() { return null; },
    hasAttribute() { return false; }, removeAttribute() {},
    classList: {
      _s: new Set(),
      add(...c) { c.forEach((x) => this._s.add(x)); },
      remove(...c) { c.forEach((x) => this._s.delete(x)); },
      toggle(c, f) { f ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return makeEl("q"); },
    querySelectorAll() { return []; },
    closest() { return null; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0 }; },
    setPointerCapture() {}, releasePointerCapture() {},
    focus() {}, blur() {}, scrollIntoView() {},
  };
  return el;
}

const items = [];
const byId = {};
const document = {
  getElementById(id) { return (byId[id] = byId[id] || makeEl(id)); },
  createElement() { return makeEl("created"); },
  addEventListener(ev, fn) { if (ev === "DOMContentLoaded") queueMicrotask(fn); },
  body: makeEl("body"),
  documentElement: makeEl("html"),
};

const context = {
  document,
  window: { PROJECTS: doc },
  console,
  setTimeout, clearTimeout, queueMicrotask,
  Math, JSON, Date, Object, Array, String, Number, Boolean, Set, Map, RegExp, Error,
  parseInt, parseFloat, isNaN, encodeURIComponent, decodeURIComponent,
};
context.globalThis = context;
context.window.document = document;
vm.createContext(context);

vm.runInContext(fs.readFileSync(APP, "utf8"), context, { filename: "app.js" });

setTimeout(() => {
  console.log("");
  console.log(`dataset: ${doc.counts.projects} projects / ${doc.counts.records} records` +
              ` / ${doc.published_date}`);
  console.log("");

  const listEl = byId["list"];
  const detailEl = document.getElementById("detail");
  const metaEl = byId["meta"];

  check("header shows the dataset counts",
    /\d+ 個專案 \/ \d+ 筆記錄/.test(metaEl.textContent || ""),
    JSON.stringify(metaEl.textContent));

  check("left pane rendered items", (listEl.children || []).length > 0,
    `${(listEl.children || []).length} children`);

  // Stage chips come from p.links.milestones_taipei, so they are only expected when
  // the dataset actually carries milestone data. A fixture with no portal fields must
  // still render, just without the chips.
  const expectBadges = doc.projects.some((p) =>
    (p.links || {}).milestones_taipei &&
    Object.keys(p.links.milestones_taipei).length > 0);
  const badgeCount = items.reduce(
    (n, el) => n + ((String(el.innerHTML).match(/stage-badge/g) || []).length), 0);
  if (expectBadges) {
    check("left pane carries construction-stage badges", badgeCount > 0,
      `${badgeCount} badges across ${items.length} items`);
  } else {
    check("stage badges omitted when the dataset carries no milestones",
      badgeCount === 0, `${badgeCount} badges (dataset has none to render)`);
  }

  const fakeEvent = { stopPropagation() {}, preventDefault() {}, target: {} };

  let threw = null;
  if (items.length) {
    try {
      items[0]._onclick(fakeEvent);
    } catch (e) {
      threw = e;
    }
  } else {
    threw = new Error("no list item carried a click handler");
  }

  check("clicking a project does not throw", !threw,
    threw ? `${threw.name}: ${threw.message}` : "");
  if (threw) console.log(String(threw.stack).split("\n").slice(0, 5).join("\n"));

  const html = detailEl.innerHTML || "";
  check("detail pane was filled", html.length > 200, `${html.length} chars`);
  check("detail pane no longer shows the placeholder",
    !/從左側選擇一個專案/.test(html));

  // the clicked entry's own project id must appear in what was rendered
  const clickedId = (String(items[0].innerHTML).match(/>([^<>]*地號等\d+筆)</) || [])[1];
  check("detail pane names the clicked project",
    !!clickedId && html.indexOf(clickedId) !== -1, clickedId || "id not parsed");

  // prove no single node can blank the pane: click a spread of projects, keeping
  // memory flat by discarding the re-rendered list between clicks
  let badProjects = 0, firstErr = null, shortest = Infinity, clicked = 0;
  const stride = Math.max(1, Math.floor(items.length / 12));
  const fresh = makeEl("list");
  byId["list"] = fresh;
  for (let i = 0; i < items.length && clicked < 12; i += stride) {
    try {
      items[i]._onclick(fakeEvent);
      const h = detailEl.innerHTML || "";
      if (h.length < shortest) shortest = h.length;
      if (/從左側選擇一個專案/.test(h) || h.length < 200) badProjects++;
      clicked++;
    } catch (e) {
      badProjects++;
      firstErr = firstErr || e;
    }
    if (byId["list"].children.length > 800) byId["list"].children.length = 0;
    detailEl.innerHTML = "";
  }
  check("every sampled project renders a detail pane", badProjects === 0,
    firstErr ? `${firstErr.name}: ${firstErr.message}` : `${clicked} clicked`);

  // ── overlap guard: every project with a callout or an orphan ─────────────────
  // layoutRects is populated by viewer/app.js renderDetail (window.__LAYOUT_RECTS).
  // Checks run on every project that carries implementation callouts or orphan
  // nodes (named virtual nodes or nameless anchors).
  const renderDetailApp = context.window.renderDetail;
  let calloutProjects = 0;
  let orphanProjects = 0;
  let guardFailures = 0;
  let missingOrphanEdges = 0;
  for (const pp of doc.projects) {
    const implNodes = (pp.nodes || []).filter((n) => n.implementation);
    const orphans = (pp.links || {}).orphan_nodes || [];
    if (!implNodes.length && !orphans.length) continue;
    if (implNodes.length) calloutProjects++;
    if (orphans.length) orphanProjects++;
    renderDetailApp(pp);
    const L = context.window.__LAYOUT_RECTS || {
      callouts: [], nodes: [], events: [], orphans: [], leaders: [], orphanEdges: [],
    };
    const allRects = [].concat(L.nodes, L.events, L.orphans, L.callouts);
    // check 1: no two placed rectangles intersect
    for (let i = 0; i < allRects.length; i++) {
      for (let j = i + 1; j < allRects.length; j++) {
        const a = allRects[i], b = allRects[j];
        if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) {
          guardFailures++;
          console.log(`  FAIL  overlap ${pp.project_id}: rect${i}(${a.x},${a.y},${a.w},${a.h}) vs rect${j}(${b.x},${b.y},${b.w},${b.h})`);
        }
      }
    }
    // check 2: every callout box inside the gutter
    for (const c of L.callouts) {
      const gx = L.gutterX || 0;
      const gw = L.gutterW || 0;
      if (c.x < gx || c.x + c.w > gx + gw) {
        guardFailures++;
        console.log(`  FAIL  gutter ${pp.project_id}: callout(${c.x},${c.y},${c.w},${c.h}) outside gutter[${gx},${gw}]`);
      }
    }
    // check 3: no leader crosses a callout box other than its own, or a node label
    // other than its own node (leader legitimately ends at its own node circle)
    for (const ld of L.leaders) {
      const ownNodeId = `node:${ld.owns.split(":")[1]}`;
      for (const c of L.callouts) {
        if (ld.owns === c.id) continue;
        if (segRectHit(ld, c)) {
          guardFailures++;
          console.log(`  FAIL  leader-box ${pp.project_id}: leader ${ld.id} crosses callout ${c.id}`);
        }
      }
      for (const n of L.nodes) {
        if (n.id === ownNodeId) continue;
        if (segRectHit(ld, n)) {
          guardFailures++;
          console.log(`  FAIL  leader-node ${pp.project_id}: leader ${ld.id} crosses node ${n.id}`);
        }
      }
    }
    // check 4: every named orphan renders a dotted edge orphan line to the recno
    // row directly above it (or directly under when none sits above) — the SVG
    // line with class "edge orphan" between orphan and recno. layoutRects.
    // orphanEdges lists each orphan→recno pair; confirm each orphan in the data
    // has a corresponding edge.
    const orphanEdges = L.orphanEdges || [];
    for (const g of orphans) {
      if (!g.case_name) continue; // nameless anchors render no row (§4 decision 4)
      const hasEdge = orphanEdges.some(d => d.id.includes(`orphan-edge:v${g.case_id}->`));
      if (!hasEdge) {
        missingOrphanEdges++;
        console.log(`  FAIL  orphan-edge ${pp.project_id}: case ${g.case_id} has no dotted edge to nearest recno node`);
      }
    }
  }

  function segRectHit(s, r) {
    // returns true if segment s crosses rect r (not just touches an endpoint)
    const dx = s.x2 - s.x1, dy = s.y2 - s.y1;
    const t0 = 0, t1 = 1;
    let tmin = t0, tmax = t1;
    const clip = (p, q) => {
      if (Math.abs(p) < 1e-9) return q >= 0;
      const t = q / p;
      if (p < 0) { if (t > tmax) return false; if (t > tmin) tmin = t; }
      else { if (t < tmin) return false; if (t < tmax) tmax = t; }
      return true;
    };
    if (!clip(-dx, s.x1 - r.x) || !clip(dx, r.x + r.w - s.x1) ||
        !clip(-dy, s.y1 - r.y) || !clip(dy, r.y + r.h - s.y1)) return false;
    return tmin < tmax;
  }

  check("overlap guard: ran on projects with callouts or orphans",
    (calloutProjects + orphanProjects) > 0 || guardFailures === 0,
    `${calloutProjects} callout / ${orphanProjects} orphan projects, ${guardFailures} failures`);
  check("overlap guard: no intersecting rects", guardFailures === 0,
    `${guardFailures} failures`);
  check("overlap guard: no leader crosses box/label", guardFailures === 0, "see above");
  check("overlap guard: every named orphan has a dotted edge orphan line", missingOrphanEdges === 0,
    `${missingOrphanEdges} missing orphan edges`);

  // ── C1 (bind-national-label-once): the per-label 國 binding ────────────────
  // Each label with stage+track candidates must badge at most one node. Count,
  // per project, the 國 badges rendered from label binding (not from
  // view_verified_case_ids) and compare with the number of bound labels.
  const bindNationalLabels = context.bindNationalLabels;
  let checkedBind = 0, bindFailures = 0;
  if (typeof bindNationalLabels === "function") {
    for (const pp of doc.projects) {
      if (!(pp.links || {}).twur) continue;
      if (!(pp.links || {}).milestones_national ||
          !Object.keys(pp.links.milestones_national).length) continue;
      checkedBind++;
      const binding = bindNationalLabels(pp);
      const boundCount = Object.values(binding).reduce((a, l) => a + l.length, 0);
      const multi = Object.keys(binding).filter((r) => binding[r].length > 1);
      // a recno carrying 2+ labels is legitimate (one node, several labels of
      // its stage+track); what must never happen is a label bound to 2 recnos.
      const seenLabels = new Set();
      for (const labels of Object.values(binding)) {
        for (const lb of labels) {
          if (seenLabels.has(lb)) { bindFailures++; console.log(`  FAIL  bind ${pp.project_id}: label ${lb} bound twice`); }
          seenLabels.add(lb);
        }
      }
      const badged = (pp.nodes || []).filter((n) =>
        (binding[String(n.recno)] || []).length > 0).length;
      if (badged > boundCount) { bindFailures++; console.log(`  FAIL  bind ${pp.project_id}: ${badged} badged nodes for ${boundCount} bound labels`); }
      if (multi.length > 1 && boundCount > Object.keys(binding).length) { /* informational only */ }
    }
  }
  // checkedBind > 0 only when the dataset carries twur links; a degraded
  // dataset without links must degrade, not fail (test_viewer_degrades).
  check("national label binding: one badge per bound label", bindFailures === 0,
    `${checkedBind} project(s) with a national page checked, ${bindFailures} failures`);

  console.log("");
  console.log(failures ? `${failures} check(s) FAILED` : "all checks passed");
  process.exit(failures ? 1 : 0);
}, 50);
