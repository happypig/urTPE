/* Render viewer/dashboard.js in a stub DOM against a fixture payload and print
 * what the page shows, as JSON, so tests/test_dashboard_rules.py can assert the
 * derivation rules the policy-dashboard spec states — on the rendered page,
 * not on a re-implementation of its rules (dashboard-spec, design D4).
 *
 *   node scripts/dashboard_smoke.js --payload fixture.json [--preset]
 *        [--hash "#district=萬華區&lang=en"] [--index-html index.html]
 *        [--fetch reject|404|none] [--today 2030-01-01]
 *
 * --preset sets window.PROJECTS before the page runs, so the page's own
 * dataset load is skipped — the shape scripts/viewer_smoke.js uses. Without it
 * the page runs its load path: it fetches index.html (served from
 * --index-html, or rejected / 404 / undefined per --fetch, "none" being the
 * file:// case), appends a <script> whose src this harness records, and the
 * harness then delivers the payload through that script's onload — or fires
 * onerror when no --payload was given.
 *
 * --today fixes Date.now() and `new Date()`; the page is specified to measure
 * idle time to the gazette's published_date, never to the viewing day, and a
 * test renders the same payload under two clocks to prove it.
 *
 * Chart values are read from the tooltips the page itself builds: every bar,
 * year group and review point carries a pointerenter handler whose lines are
 * the figures a reader sees on hover, so the harness fires the handler and
 * reads the tooltip. No chart geometry is inspected; text width is left at
 * the page's own 8px-per-character fallback.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const PAGE = path.join(ROOT, "viewer", "dashboard.js");

// --- arguments --------------------------------------------------------------
const argv = process.argv.slice(2);
const opt = { payload: null, preset: false, hash: "", indexHtml: null, fetch: "none", today: null };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--preset") opt.preset = true;
  else if (a === "--payload") opt.payload = argv[++i];
  else if (a === "--hash") opt.hash = argv[++i] || "";
  else if (a === "--index-html") opt.indexHtml = argv[++i];
  else if (a === "--fetch") opt.fetch = argv[++i];
  else if (a === "--today") opt.today = argv[++i];
  else { console.error("dashboard_smoke: unknown argument " + a); process.exit(2); }
}

function readPayload(file) {
  let text = fs.readFileSync(file, "utf8").trim();
  // accept the emitted projects.data.js form as well as plain JSON
  if (text.startsWith("window.PROJECTS")) {
    text = text.slice(text.indexOf("=") + 1).replace(/;\s*$/, "");
  }
  return JSON.parse(text);
}
const payload = opt.payload ? readPayload(opt.payload) : null;

// --- stub DOM ---------------------------------------------------------------
// A real tree (parent pointers, attributes, text nodes), because the harness
// reads the page back out of it; the viewer harness only needs innerHTML.
class TextNode {
  constructor(s) { this.nodeType = 3; this.data = String(s); this.parentNode = null; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}

class Element {
  constructor(tag) {
    this.nodeType = 1;
    this.tagName = String(tag).toLowerCase();
    this.attrs = {};
    this.className = "";
    this.id = "";
    this.childNodes = [];
    this.parentNode = null;
    this.style = {};
    this.dataset = {};
    this.listeners = {};
    this.hidden = false;
    this.src = "";
    this.onload = null;
    this.onerror = null;
    this.clientWidth = 0;   // the page falls back to 600
    this.offsetWidth = 0;
    this.lang = "";
  }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  _node(c) { return c && c.nodeType ? c : new TextNode(c); }
  _adopt(n) { if (n.parentNode) n.parentNode._drop(n); n.parentNode = this; return n; }
  _drop(n) { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; }
  appendChild(c) { this.childNodes.push(this._adopt(this._node(c))); return c; }
  append(...cs) { for (const c of cs) this.appendChild(c); }
  prepend(...cs) { for (const c of cs.slice().reverse()) this.childNodes.unshift(this._adopt(this._node(c))); }
  replaceChildren(...cs) { for (const n of this.childNodes.slice()) this._drop(n); this.append(...cs); }
  removeChild(c) { this._drop(c); return c; }
  remove() { if (this.parentNode) this.parentNode._drop(this); }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    if (k === "id") this.id = String(v);
    if (k === "class") this.className = String(v);
  }
  getAttribute(k) { return k === "class" ? (this.className || null) : (k in this.attrs ? this.attrs[k] : null); }
  hasAttribute(k) { return k === "class" ? !!this.className : k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  removeEventListener() {}
  get textContent() { return this.childNodes.map((n) => n.textContent).join(""); }
  set textContent(v) { this.replaceChildren(); if (v != null && v !== "") this.appendChild(new TextNode(v)); }
  getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0, right: 0, bottom: 0 }; }
  getComputedTextLength() { return 0; }
  querySelectorAll(sel) { return qsa(this, sel); }
  querySelector(sel) { return qsa(this, sel)[0] || null; }
  closest() { return null; }
  focus() {}
  blur() {}
  get classList() {
    const self = this;
    return {
      contains: (c) => cls(self).includes(c),
      add(...c) { self.className = Array.from(new Set(cls(self).concat(c))).join(" "); },
      remove(...c) { self.className = cls(self).filter((x) => !c.includes(x)).join(" "); },
    };
  }
}

function cls(e) { return String(e.className || e.attrs.class || "").split(/\s+/).filter(Boolean); }
function walk(root, pred, out) {
  out = out || [];
  for (const c of root.childNodes) {
    if (c.nodeType !== 1) continue;
    if (pred(c)) out.push(c);
    walk(c, pred, out);
  }
  return out;
}
// the selectors the page and this harness use: "tag", ".class", "tag.class", "#id"
function qsa(root, sel) {
  return String(sel).split(",").map((s) => s.trim()).flatMap((s) => {
    if (s[0] === "#") return walk(root, (e) => e.id === s.slice(1));
    const [tag, ...classes] = s.split(".");
    return walk(root, (e) => (!tag || e.tagName === tag) && classes.every((c) => cls(e).includes(c)));
  });
}

const html = new Element("html");
html.lang = "zh-Hant";
const head = new Element("head");
const body = new Element("body");
const byId = {};
function ensure(id, tag) {
  const e = new Element(tag);
  e.setAttribute("id", id);
  body.appendChild(e);
  byId[id] = e;
  return e;
}
// the elements dashboard.html carries and the page looks up by id
ensure("title", "h1");
ensure("nav-viewer", "a");
ensure("meta", "div");
ensure("nav-about", "a");
ensure("app", "main");

const scriptLog = [];
const document = {
  title: "",
  documentElement: html,
  head,
  body,
  getElementById(id) { return byId[id] || null; },
  createElement(tag) { return new Element(tag); },
  createElementNS(_ns, tag) { return new Element(tag); },
  createTextNode(s) { return new TextNode(s); },
  querySelectorAll(sel) { return qsa(body, sel); },
  querySelector(sel) { return qsa(body, sel)[0] || null; },
  addEventListener() {},
};
// The page's load path appends a <script> for the dataset; deliver the payload
// through its onload, as a browser would after the fetch, and record its src.
head.appendChild = function (s) {
  Element.prototype.appendChild.call(this, s);
  if (s.tagName === "script") {
    scriptLog.push(s.src);
    if (payload) {
      context.PROJECTS = payload;
      if (s.onload) s.onload();
    } else if (s.onerror) {
      s.onerror();
    }
  }
  return s;
};

const location = { hash: opt.hash || "", pathname: "/viewer/dashboard.html", search: "", href: "" };
const history = {
  replaceState(_state, _title, url) {
    url = String(url);
    location.hash = url.startsWith("#") ? url : "";
  },
};

let fetchImpl;
if (opt.indexHtml) {
  const text = fs.readFileSync(opt.indexHtml, "utf8");
  fetchImpl = () => Promise.resolve({ ok: true, text: () => Promise.resolve(text) });
} else if (opt.fetch === "reject") {
  fetchImpl = () => Promise.reject(new TypeError("Failed to fetch"));
} else if (opt.fetch === "404") {
  fetchImpl = () => Promise.resolve({ ok: false, text: () => Promise.resolve("") });
} else {
  fetchImpl = undefined; // no fetch at all: the page's own try/catch takes the plain path
}

let DateImpl = Date;
if (opt.today) {
  const fixed = Date.parse(opt.today + "T00:00:00Z");
  DateImpl = class extends Date {
    constructor(...a) { if (a.length) super(...a); else super(fixed); }
    static now() { return fixed; }
  };
}

const context = {
  document, location, history, console,
  setTimeout, clearTimeout, queueMicrotask, URLSearchParams, Promise,
  Math, JSON, Date: DateImpl, Object, Array, String, Number, Boolean, Set, Map, RegExp,
  Error, TypeError, parseInt, parseFloat, isNaN, isFinite,
  encodeURIComponent, decodeURIComponent,
  addEventListener() {},
  removeEventListener() {},
};
if (fetchImpl) context.fetch = fetchImpl;
if (opt.preset) context.PROJECTS = payload;
context.window = context;
context.globalThis = context;
context.self = context;
vm.createContext(context);

try {
  vm.runInContext(fs.readFileSync(PAGE, "utf8"), context, { filename: "dashboard.js" });
} catch (e) {
  console.error("dashboard.js threw while loading:\n" + (e && e.stack));
  process.exit(1);
}

// --- read the page back -----------------------------------------------------
function text(e) { return e ? e.textContent : null; }
function first(root, sel) { return root ? (qsa(root, sel)[0] || null) : null; }

// Fire the page's own hover handler and read the tooltip it filled: the
// tooltip lines are the figures a reader sees, so they are what the tests
// assert on.
function tipLines(hoverEl) {
  const fns = hoverEl.listeners.pointerenter || [];
  if (!fns.length) return null;
  fns[0]({ clientX: 0, clientY: 0 });
  let box = hoverEl;
  while (box && !cls(box).includes("chart")) box = box.parentNode;
  const tip = box && first(box, ".tip");
  return tip ? tip.children.map((d) => d.textContent) : null;
}
function kv(lines) {
  const o = {};
  for (const l of lines.slice(1)) {
    const i = l.indexOf(": ");
    if (i > 0) o[l.slice(0, i)] = l.slice(i + 2);
  }
  return o;
}
// horizontal stacked bars: one <g> per row — label text, one rect per
// segment (each with a tooltip), total text last
function barsOf(box) {
  const svg = first(box, "svg");
  if (!svg) return { rows: [], empty: text(first(box, "p.empty")) };
  return {
    rows: svg.children.filter((g) => g.tagName === "g").map((g) => {
      const texts = g.children.filter((c) => c.tagName === "text");
      const segs = {};
      for (const r of g.children.filter((c) => c.tagName === "rect")) {
        const L = tipLines(r);
        if (L) Object.assign(segs, kv(L));
      }
      return {
        label: texts.length ? texts[0].textContent : "",
        total: texts.length > 1 ? texts[texts.length - 1].textContent : "",
        segs,
        dim: g.getAttribute("opacity") != null,
      };
    }),
    empty: null,
  };
}
// year charts: every element with a hover handler is one point
function seriesOf(box) {
  const e = first(box, "p.empty");
  if (e) return { series: [], empty: e.textContent };
  const pts = walk(box, (x) => (x.listeners.pointerenter || []).length > 0).map(tipLines).filter(Boolean);
  return { series: pts.map((L) => ({ head: L[0], values: kv(L) })), empty: null };
}
function tableOf(root) {
  const tbody = first(first(root, "table"), "tbody");
  const trs = tbody ? tbody.children.filter((c) => c.tagName === "tr") : [];
  if (trs.length === 1 && trs[0].children.length === 1 && trs[0].children[0].getAttribute("colspan") != null) {
    return { rows: [], empty: trs[0].textContent };
  }
  return {
    rows: trs.map((tr) => {
      const tds = tr.children.filter((c) => c.tagName === "td");
      const a = first(tds[0], "a");
      return { cells: tds.map((td) => td.textContent), link: a ? a.getAttribute("href") : null };
    }),
    empty: null,
  };
}
function cardsOf(kpis) {
  return kpis ? kpis.children.map((c) => {
    const num = first(c, "p.kpi-num");
    const unit = num && first(num, "span.kpi-unit");
    return {
      label: text(first(c, "p.kpi-label")),
      num: num ? num.childNodes.filter((n) => n.nodeType === 3).map((n) => n.data).join("").trim() : null,
      unit: unit ? unit.textContent : "",
      sub: text(first(c, "p.sub")),
    };
  }) : [];
}

function extract() {
  const app = byId.app;
  const only = app.children.length === 1 ? app.children[0] : null;
  const failed = only && only.tagName === "p" && cls(only).includes("empty") ? only.textContent : null;
  const out = {
    lang: html.lang,
    title: document.title,
    meta: byId.meta.textContent,
    scriptSrc: scriptLog.length ? scriptLog[0] : null,
    failed,
  };
  if (failed || !app.children.length) return out;
  const take = first(app, "p.take");
  out.take = text(take);
  // the scope is the <b> that is not a number: zh leads with it, en leads with the count
  out.scope = qsa(take, "b").map(text).find((s) => !/^[\d,.]+$/.test(s)) || null;
  out.cards = cardsOf(first(app, ".kpis"));
  const sec = (id) => first(app, "#" + id);
  const stalled = sec("stalled");
  out.pipeline = barsOf(first(stalled, ".chart"));
  out.watch = tableOf(stalled);
  const review = sec("review");
  const rb = qsa(review, ".chart");
  out.approvals = seriesOf(rb[0]);
  out.review = seriesOf(rb[1]);
  out.households = barsOf(first(sec("relocation"), ".chart"));
  const housing = sec("housing");
  out.publand = barsOf(first(housing, ".chart"));
  out.public = tableOf(housing);
  out.notes = qsa(first(app, "details"), "p").map((p) => p.textContent);
  return out;
}

// the load path resolves through promises; one macrotask is enough
setTimeout(() => {
  try {
    process.stdout.write(JSON.stringify(extract(), null, 1) + "\n");
    process.exit(0);
  } catch (e) {
    console.error("dashboard_smoke: extraction failed:\n" + (e && e.stack));
    process.exit(1);
  }
}, 30);
