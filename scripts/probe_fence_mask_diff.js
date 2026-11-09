/**
 * Differential check: the Python probes' fence mask against the archive's own.
 *
 * The archive masks fenced code-block lines before it counts scenarios
 * (`buildCodeFenceMask` in the installed package's
 * `dist/core/parsers/code-fence.js`). The Python probes re-implement that
 * rule so they can answer the same question the archive does.
 *
 * A hand-written mask that is merely READ from the JS can be wrong in ways
 * nobody thought of. So this imports the real function, asks the REAL Python
 * probe for its mask over the same line lists, and compares the two. It does
 * not transliterate the Python — a transliteration would be a third
 * implementation, and the thing under test would not be the thing that ships.
 *
 *   node scripts/probe_fence_mask_diff.js
 *
 * Reads the installed package and the Python probes. Writes nothing, reaches
 * no network.
 */
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const PKG = "C:/Users/jeffw/AppData/Roaming/npm/node_modules/@fission-ai/openspec";
const { buildCodeFenceMask } = require(PKG + "/dist/core/parsers/code-fence.js");

const CASES = [
  ["no fence", ["a", "b"]],
  ["a plain backtick fence", ["```", "x", "```", "y"]],
  ["a plain tilde fence", ["~~~", "x", "~~~", "y"]],
  ["a fence with an info string", ["```markdown", "x", "```", "y"]],
  ["a four-backtick fence", ["````", "x", "````", "y"]],
  ["a tilde inside a backtick block", ["```", "~~~", "x", "```", "y"]],
  ["a backtick inside a tilde block", ["~~~", "```", "x", "~~~", "y"]],
  ["a shorter close does not close", ["~~~~", "~~~", "x", "~~~~", "y"]],
  ["a longer close does close", ["~~~", "````", "x", "~~~", "y"]],
  ["an indented fence", ["   ```", "x", "   ```", "y"]],
  ["an unclosed fence runs to the end", ["```", "x", "y", "z"]],
  ["two fences in a row", ["```", "a", "```", "```", "b", "```"]],
  ["a fence marker inside prose", ["text ``` more", "x"]],
  ["a lone backtick is not a fence", ["`", "x", "`"]],
  ["a tilde run of two is not a fence", ["~~", "x", "~~"]],
  ["a fence with a trailing space", ["``` ", "x", "```", "y"]],
  ["a close with trailing spaces", ["```", "x", "```  ", "y"]],
  ["an empty line inside a fence", ["```", "", "x", "```", "y"]],
];

// ask the REAL Python probes for their masks
const work = mkdtempSync(join(tmpdir(), "fence-diff-"));
const script = join(work, "masks.py");
writeFileSync(
  script,
  `import json, sys, importlib.util, pathlib
ROOT = pathlib.Path(${JSON.stringify(process.cwd())})
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
pas = load("probe_archive_scenarios")
psu = load("probe_spec_unprotected")
cases = json.loads(sys.stdin.read())
out = []
for name, lines in cases:
    a = pas._mask_fences(lines)
    b = psu.fence_mask(lines)
    out.append({"name": name, "scenario_probe": a, "unprotected_probe": b})
print(json.dumps(out))
`,
  "utf-8"
);

let py;
try {
  py = JSON.parse(
    execFileSync("C:/Python314/python.exe", [script], {
      input: JSON.stringify(CASES),
      encoding: "utf-8",
    })
  );
} finally {
  rmSync(work, { recursive: true, force: true });
}

let mismatches = 0;
for (let i = 0; i < CASES.length; i += 1) {
  const [name, lines] = CASES[i];
  const real = buildCodeFenceMask(lines);
  const mine = py[i].scenario_probe;
  const other = py[i].unprotected_probe;
  const same = JSON.stringify(real) === JSON.stringify(mine);
  const sameBoth = JSON.stringify(mine) === JSON.stringify(other);
  if (!same || !sameBoth) mismatches += 1;
  console.log(
    `${same && sameBoth ? "ok  " : "DIFF"}  ${name.padEnd(38)} archive=[${real}] ` +
      `scenario_probe=[${mine}] unprotected_probe=[${other}]`
  );
}
console.log();
console.log(`${CASES.length} adversarial cases, ${mismatches} mismatches.`);
process.exit(mismatches === 0 ? 0 : 1);
