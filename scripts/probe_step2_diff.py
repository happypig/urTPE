"""D9g step 2: the re-emit's project diff. Read-only.

Compares the emitted payload before and after the cache pass, and reports:
  - how many projects changed, and how many did not
  - for each changed project, WHICH top-level fields changed
  - the node-level counts: how many nodes gained or lost a milestone label, a
    link, an implementation snapshot, or a review flag
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    before = load(ROOT / "data" / "_projects_before_step2.json")
    after = load(ROOT / "data" / "projects.json")

    b_by = {p["project_id"]: p for p in before["projects"]}
    a_by = {p["project_id"]: p for p in after["projects"]}

    print("projects before:", len(b_by), " after:", len(a_by))
    only_b = sorted(set(b_by) - set(a_by))
    only_a = sorted(set(a_by) - set(b_by))
    print("projects only before:", len(only_b), only_b[:10])
    print("projects only after:", len(only_a), only_a[:10])

    changed = []
    field_counts = {}
    node_label_gain = node_label_loss = 0
    node_link_change = 0
    impl_change = 0
    flag_change = 0
    for pid, b in b_by.items():
        a = a_by.get(pid)
        if a is None:
            continue
        if b == a:
            continue
        changed.append(pid)
        for k in set(b) | set(a):
            if b.get(k) != a.get(k):
                field_counts[k] = field_counts.get(k, 0) + 1
        bn = {n["recno"]: n for n in b.get("nodes", [])}
        an = {n["recno"]: n for n in a.get("nodes", [])}
        for recno in set(bn) & set(an):
            x, y = bn[recno], an[recno]
            for k in set(x) | set(y):
                if x.get(k) == y.get(k):
                    continue
                if k == "links":
                    node_link_change += 1
                elif k == "implementation":
                    impl_change += 1
                elif k == "review_flags":
                    flag_change += 1
                elif k == "milestones_taipei":
                    old = x.get(k) or {}
                    new = y.get(k) or {}
                    node_label_gain += len(set(new) - set(old))
                    node_label_loss += len(set(old) - set(new))
                else:
                    field_counts.setdefault("node." + k, 0)
                    field_counts["node." + k] += 1

    print()
    print("projects changed:", len(changed))
    print("projects unchanged:", len(b_by) - len(changed))
    print()
    print("changed project fields:")
    for k, v in sorted(field_counts.items(), key=lambda x: -x[1]):
        print("   %-32s %d" % (k, v))
    print()
    print("node milestones_taipei labels gained:", node_label_gain)
    print("node milestones_taipei labels lost:  ", node_label_loss)
    print("node links changed:", node_link_change)
    print("node implementation changed:", impl_change)
    print("node review_flags changed:", flag_change)
    print()
    print("the changed projects:")
    for pid in changed:
        print("   ", pid)


if __name__ == "__main__":
    main()
