"""D15: the flag-order effect on the live payload. Read-only.

Loads the emitted payload through the real --from-js loader, re-emits it, and
reports the nodes whose review_flags order changed — and proves that no flag
text changed, no flag was added and none was lost.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cli  # noqa: E402
from urtpe.graph import build_project_graph  # noqa: E402

FLAG_CASE_RE = re.compile(r"案(\d+)")


def key_of(flag: str):
    m = FLAG_CASE_RE.search(flag)
    return (m.group(1) if m else "", flag)


def main():
    doc = json.loads((ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8")
                     .replace("window.PROJECTS = ", "").rstrip().rstrip(";"))
    before = {}
    for p in doc["projects"]:
        for n in p["nodes"]:
            before[n["recno"]] = list(n.get("review_flags") or [])

    projects, _meta = cli._load_projects_from_js(str(ROOT / "viewer" / "projects.data.js"))
    after = {}
    for p in projects:
        g = build_project_graph(p, implementer="", name="")
        for n in g["nodes"]:
            after[n["recno"]] = list(n.get("review_flags") or [])

    changed = [r for r in before if before[r] != after.get(r)]
    print("nodes:", len(before))
    print("nodes whose flag ORDER changes under the stable sort:", len(changed))
    set_diff = [r for r in before if set(before[r]) != set(after.get(r, []))]
    print("nodes whose flag SET changes:", len(set_diff), set_diff)
    count_diff = [r for r in before if len(before[r]) != len(after.get(r, []))]
    print("nodes whose flag COUNT changes:", len(count_diff), count_diff)
    print()
    for r in changed[:8]:
        print("recno", r)
        print("   before:", before[r])
        print("   after: ", after[r])
        print()
    if len(changed) > 8:
        print("... and %d more" % (len(changed) - 8))


if __name__ == "__main__":
    main()
