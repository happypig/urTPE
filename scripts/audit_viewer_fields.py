"""Audit which fields app.js reads that the rebuilt dataset no longer carries."""
import json
import pathlib
import re

ROOT = pathlib.Path(".")
app = (ROOT / "viewer" / "app.js").read_text(encoding="utf-8")
lines = app.split("\n")


def fn_body(name, limit=400):
    """Source lines of a top-level-ish function, to the next line at column 0."""
    start = next((i for i, l in enumerate(lines)
                  if re.match(r"\s*(function %s\b|const %s\s*=|%s\s*=\s*\()" % (name, name, name), l)), None)
    if start is None:
        return None, None
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        l = lines[end]
        if l.strip() and (len(l) - len(l.lstrip())) <= indent and not l.strip().startswith("//"):
            break
        end += 1
    return start + 1, "\n".join(lines[start:end])


def fn_at(start_line, limit=600):
    indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
    end = start_line
    while end < len(lines) and end < start_line + limit:
        l = lines[end]
        if l.strip() and (len(l) - len(l.lstrip())) <= indent and not l.strip().startswith("//"):
            break
        end += 1
    return "\n".join(lines[start_line - 1:end])


data = json.loads((ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8")
                  [len("window.PROJECTS = "):].rstrip().rstrip(";"))
proj = data["projects"][0]
node = proj["nodes"][0]
multi = max(data["projects"], key=lambda p: len(p["nodes"]))

print("project keys :", sorted(proj.keys()))
print("node keys    :", sorted(node.keys()))
print("multi-node project has %d nodes" % len(multi["nodes"]))
print()

# constructionStage and its inputs
cs, cs_src = fn_body("constructionStage")
print("=" * 78)
print("constructionStage (drives the left-pane chip) — line", cs)
print("=" * 78)
print(cs_src[:700] if cs_src else "  not found")
print()

# every member access on p / n / node / cur in renderDetail
start = next(i for i, l in enumerate(lines) if l.strip().startswith("function renderDetail(p)"))
body = fn_at(start + 1)
print("=" * 78)
print("renderDetail: lines %d-%d, %d chars" % (start + 1, start + 1 + body.count("\n"), len(body)))
print("=" * 78)

access = re.findall(r"\b(p|n|node|cur|proj)\.([A-Za-z_][A-Za-z0-9_]*)", body)
missing_p, missing_n = set(), set()
for var, prop in access:
    src = {"p": proj, "proj": proj, "n": node, "node": node, "cur": node}.get(var)
    if src is None:
        continue
    if prop not in src:
        (missing_p if var in ("p", "proj") else missing_n).add(prop)
print("fields read off a project that are ABSENT :", sorted(missing_p) or "none")
print("fields read off a node    that are ABSENT :", sorted(missing_n) or "none")

# unguarded uses: prop followed by . or ( without ?.
unguarded = []
for m in re.finditer(r"\b(p|n|node|cur)\.([A-Za-z_][A-Za-z0-9_]*)(\??\.\w+|\s*\()", body):
    var, prop, tail = m.group(1), m.group(2), m.group(3)
    if tail.startswith("?."):
        continue
    src = {"p": proj, "n": node, "node": node, "cur": node}[var]
    if prop not in src:
        unguarded.append("%s.%s%s" % (var, prop, tail))
print()
print("UNGUARDED accesses to absent fields:", unguarded or "none")