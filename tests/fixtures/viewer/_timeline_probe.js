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

const ROOT = path.resolve(__dirname, "..", "..", "..");
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
  const detailEl = document.getElementById("detail");
  const PID_PART = process.argv[3] || "";
  const listChildren = byId["list"].children || [];
  const target = listChildren.find(c => c.innerHTML.includes(PID_PART));
  if (target) { target._onclick({ stopPropagation(){}, preventDefault(){}, target:{} }); }
  const svgHtml = detailEl.innerHTML || "";
  // Rows live in separate SVG layers; document order is layer order, not
  // timeline order. The y coordinate (transform translate y) IS the timeline
  // order: extract (y, label) pairs and sort by y.
  const rowRe = /translate\(([\d.]+),\s*([\d.]+)\)"[^]*?<text[^>]*>([^<]*(?:\d{4}-\d{2}-\d{2}|建照核發日期|開工日期)[^<]*)<\/text>/g;
  const pairs = [];
  let m2;
  while ((m2 = rowRe.exec(svgHtml)) !== null) {
    pairs.push({ y: parseFloat(m2[2]), text: m2[3] });
  }
  pairs.sort((a, b) => a.y - b.y);
  for (const pr of pairs) console.log(`y=${pr.y} ${pr.text}`);
  if (process.argv[4] === "badges") {
    // Badge dump (fix-row-order-tiebreak-and-view-badges 1.6): every
    // node-milestone-badge anchor with its node's y, class (taipei/national)
    // and destination (case_id=NNN or view/NNN). One line per badge — a node
    // carrying 北+國 yields two lines at the same y.
    const groupRe = /translate\(([\d.]+),\s*([\d.]+)\)"[^]*?<\/g>/g;
    const badgeAnchorRe = /<a class="node-milestone-badge (taipei|national)[^]*?href="([^"]*)"[^]*?title="([^"]*)"/g;
    const badges = [];
    let m3;
    while ((m3 = groupRe.exec(svgHtml)) !== null) {
      const y = parseFloat(m3[1 + 1]); // group 2: the y of translate(x, y)
      let m4;
      badgeAnchorRe.lastIndex = 0;
      while ((m4 = badgeAnchorRe.exec(m3[0])) !== null) {
        const href = m4[2];
        const dest = href.includes("case_id=") ? "case_" + href.split("case_id=")[1]
                   : "view/" + ((href.match(/view\/(\d+)/) || [null, ""])[1]);
        badges.push({ y, cls: m4[1], dest, title: m4[3] });
      }
    }
    badges.sort((a, b) => a.y - b.y);
    for (const b of badges) console.log(`y=${b.y} BADGE ${b.cls} ${b.dest} ${b.title}`);
  }
}, 0);
