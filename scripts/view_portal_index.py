import json

with open('data/.link_cache/portal_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Total entries:', len(data))
print()
for i, e in enumerate(data):
    print(f'{i+1:3d}. core={e["core"]} | view={e["view_id"]} | date={e["approval_date"]} | impl={e["implementer"]}')