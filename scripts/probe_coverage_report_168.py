"""Break down the 88 ids the 168 list holds and the payload does not. Read-only."""
import json
import pathlib

doc = json.loads(pathlib.Path("data/projects.json").read_text(encoding="utf-8"))
ids = set()
for p in doc["projects"]:
    L = p.get("links") or {}
    ids |= set(L.get("taipei") or [])
    for nd in p["nodes"]:
        ids |= set((nd.get("links") or {}).get("taipei") or [])

p168 = {r["case_id"] for r in
        json.loads(pathlib.Path("data/p168_all.json").read_text(encoding="utf-8"))}
missing = sorted(p168 - ids)
print("missing from the payload: %d" % len(missing))

hp = {r["case_id"]: r for r in
      json.loads(pathlib.Path("data/p168_header_pass.json").read_text(encoding="utf-8"))}
not_checked = [m for m in missing if m not in hp]
print("not in the header pass (%d): %s" % (len(not_checked), not_checked))
for m in not_checked:
    print("   %s  168 row: %s" % (
        m,
        next((r for r in json.loads(
            pathlib.Path("data/p168_all.json").read_text(encoding="utf-8"))
            if r["case_id"] == m), {}).get("MEMO")))

print()
states = {}
for m in missing:
    r = hp.get(m)
    key = "header pass" if r else "not checked"
    if r:
        name = r.get("NAME") or ""
        if "撤銷" in name:
            key = "header pass — revoked"
        elif r.get("state") == "approved":
            key = "header pass — approved"
        else:
            key = "header pass — not approved"
    states.setdefault(key, []).append(m)
for k, v in sorted(states.items()):
    print("   %-28s %d" % (k, len(v)))

# the D9a named cases
for cid in ("10112154", "10702271", "10904071", "11410026",
            "10708311", "11412011", "11104211"):
    print("   %-10s in the payload: %-5s  in the header pass: %s"
          % (cid, cid in ids, cid in hp))
