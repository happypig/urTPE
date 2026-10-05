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
const DATA = path.join(ROOT, "viewer", "projects.data.js");

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

  const badgeCount = items.reduce(
    (n, el) => n + ((String(el.innerHTML).match(/stage-badge/g) || []).length), 0);
  check("left pane carries construction-stage badges", badgeCount > 0,
    `${badgeCount} badges across ${items.length} items`);

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
    firstErr ? `${firstErr.name}: ${firstErr.message}`
             : `${clicked} clicked, shortest detail ${shortest} chars`);

  console.log("");
  console.log(failures ? `${failures} check(s) FAILED` : "all checks passed");
  process.exit(failures ? 1 : 0);
}, 50);
