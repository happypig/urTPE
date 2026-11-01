/* Re-derive the TAB-1 defect numbers against TODAY's app.js + payload.
 * Loads the real viewer/app.js in a vm sandbox (top-level function declarations
 * become globals; consts stay in script scope but close over correctly) and
 * replicates the rendered row order (app.js:796-842) and the construction
 * anchoring (app.js:257-305) exactly.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const text = fs.readFileSync(path.join(ROOT, "viewer", "app.js"), "utf8");
const dataText = fs.readFileSync(path.join(ROOT, "viewer", "projects.data.js"), "utf8");
const doc = JSON.parse(dataText.slice("window.PROJECTS = ".length).replace(/;\s*$/, ""));

const sandbox = { document: { addEventListener() {} }, console };
vm.createContext(sandbox);
vm.runInContext(text, sandbox);

const effKey = sandbox.effectiveCaseKey;
const cmpMembers = sandbox.compareClusterMembers;
const chainFor = sandbox.buildConstructionChain;

function normDate(s) {
  s = String(s || "").trim();
  if (!s) return "";
  let m = s.match(/^(\d{2,3})\.(\d{1,2})\.(\d{1,2})$/);       // ROC dotted
  if (m) return `${1911 + Number(m[1])}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  m = s.match(/^(\d{2,3})\/(\d{1,2})\/(\d{1,2})$/);           // ROC slashed
  if (m && Number(m[1]) < 200) return `${1911 + Number(m[1])}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  return s.replace(/\//g, "-");
}

// ---- 1. inverted adjacent approval pairs in the RENDERED order -------------
let invPairs = 0, invProjects = 0, datedApprovals = 0, projectsWith2Dated = 0;
for (const p of doc.projects) {
  const nodes = p.nodes || [];
  const orphans = (p.links || {}).orphan_nodes || [];
  const virtualNodes = orphans
    .filter(g => g.case_name && g.stage && g.track)
    .map(g => ({
      recno: "v" + g.case_id, date: g.node_date || "", undated: !g.node_date,
      stage: g.stage, track: g.track, area: "", is_current: false, virtual: true,
      case_id: g.case_id, case_name: g.case_name, schedule: g.schedule || "",
      links: { taipei: [g.case_id], milestones_national: {}, milestones_taipei: {} },
    }));
  const allMembers = [...nodes, ...virtualNodes].slice().sort((a, b) => {
    const ka = effKey(a), kb = effKey(b);
    if (ka !== kb) return ka < kb ? -1 : 1;
    return String(a.recno).localeCompare(String(b.recno));
  });
  const dated = allMembers.filter(m => m.date);
  if (dated.length >= 2) projectsWith2Dated++;
  let inv = 0;
  for (let i = 1; i < dated.length; i++) {
    const a = normDate(dated[i - 1].date), b = normDate(dated[i].date);
    if (a > b) inv++;
  }
  invPairs += inv;
  if (inv > 0) invProjects++;
  datedApprovals += dated.length;
}
console.log("=== rendered-order date inversions (today's code + payload) ===");
console.log("projects rendered                : %d", doc.projects.length);
console.log("dated approvals rendered         : %d", datedApprovals);
console.log("adjacent date-inverted pairs     : %d", invPairs);
console.log("projects with >=1 inverted pair  : %d", invProjects);

// ---- 2. construction-chain anchoring ---------------------------------------
let totEvents = 0;
const bucket = { noProvenance: 0, sourceCaseMissing: 0, ambiguous: 0, ambiguousResolvable: 0, ambiguousUnresolved: 0, unique: 0 };
const perSlot = {};
const noRecordExamples = [], unresolvedExamples = [];
for (const p of doc.projects) {
  const nodes = p.nodes || [];
  const countFor = {};
  for (const n of nodes) for (const cid of ((n.links || {}).taipei || [])) countFor[cid] = (countFor[cid] || 0) + 1;
  const events = chainFor(p);
  for (const ev of events) {
    totEvents++;
    perSlot[ev.label] = (perSlot[ev.label] || 0) + 1;
    const evd = normDate(ev.date);
    if (!ev.case) { bucket.noProvenance++; continue; }
    const cnt = countFor[ev.case] || 0;
    if (cnt === 0) {
      bucket.sourceCaseMissing++;
      if (noRecordExamples.length < 3) noRecordExamples.push([p.project_id, ev.label, ev.date, ev.case]);
      continue;
    }
    if (cnt === 1) { bucket.unique++; continue; }
    bucket.ambiguous++;
    // candidates: records citing this case
    let best = null;
    for (const n of nodes) {
      if (!(((n.links || {}).taipei || []).includes(ev.case))) continue;
      const nd = normDate(n.date);
      if (nd && evd && nd <= evd && (!best || nd > best)) best = nd;
    }
    if (best) bucket.ambiguousResolvable++;
    else {
      bucket.ambiguousUnresolved++;
      if (unresolvedExamples.length < 3) unresolvedExamples.push([p.project_id, ev.label, ev.date, ev.case]);
    }
  }
}
console.log("\n=== construction-chain anchoring (today's code + payload) ===");
console.log("construction events total        : %d  %j", totEvents, perSlot);
console.log("no provenance (national-only etc): %d", bucket.noProvenance);
console.log("source case on NO record         : %d", bucket.sourceCaseMissing);
console.log("uniquely anchored                : %d", bucket.unique);
console.log("ambiguous (case on >1 record)    : %d", bucket.ambiguous);
console.log("  resolvable (prior approval)    : %d", bucket.ambiguousResolvable);
console.log("  unresolved (no prior approval) : %d", bucket.ambiguousUnresolved);
console.log("source-missing examples          : %j", noRecordExamples);
console.log("unresolved examples              : %j", unresolvedExamples);

// ---- 3. twur 使用核發 vs city 使照 (§6 item 1) ------------------------------
let twurUnits = 0, sameDay = 0;
for (const p of doc.projects) {
  const nat = (p.links || {}).milestones_national || {};
  const tai = (p.links || {}).milestones_taipei || {};
  const u = nat["使用核發日期"];
  if (!u) continue;
  twurUnits++;
  const city = tai["使照核發日期"] || "";
  if (city && normDate(city) === normDate(u)) sameDay++;
}
console.log("\n=== twur 使用核發 ===");
console.log("units carrying national 使用核發 : %d", twurUnits);
console.log("  same day as city 使照核發       : %d", sameDay);
