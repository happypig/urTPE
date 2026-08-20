#!/usr/bin/env python3
"""POC validation: run link discovery on the two known sample cases."""

import sys
sys.path.insert(0, '.')

from urtpe.links import LinksDiscovery
from urtpe.models import Project, CleanRecord
from urtpe.cleanse import cleanse
from urtpe.models import RawRecord

# Case 1: 玉泉段二小段40地號等29筆 (with 臺北市 prefix for regex matching)
raw1 = RawRecord(
    recno=1,
    date='115/8/11',
    district='大同區',
    name='擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案',
    land='大同區玉泉段二小段40、40-2、43地號等29筆',
    implementer='弘千建設股份有限公司',
    planner='某規劃'
)
p1 = Project(
    project_id='大同區-玉泉段二小段-40地號等29筆',
    anchor_recno=1,
    members=[cleanse(raw1)]
)

# Case 2: 臨沂段一小段507地號等3筆 (with 臺北市 prefix)
raw2 = RawRecord(
    recno=1,
    date='115/8/11',
    district='中正區',
    name='擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案',
    land='中正區臨沂段一小段507、508、509地號等3筆',
    implementer='東綺建設股份有限公司',
    planner='某規劃'
)
p2 = Project(
    project_id='中正區-臨沂段一小段-507地號等3筆',
    anchor_recno=1,
    members=[cleanse(raw2)]
)

# Debug: check land core keys
from urtpe.links import build_land_core_key
anchor1 = next(r for r in p1.members if r.recno == p1.anchor_recno)
anchor2 = next(r for r in p2.members if r.recno == p2.anchor_recno)
with open('data/poc_debug.txt', 'w', encoding='utf-8') as f:
    f.write(f"Case 1 land core: {build_land_core_key(anchor1)}\n")
    f.write(f"Case 2 land core: {build_land_core_key(anchor2)}\n")

discovery = LinksDiscovery(cache_dir='data/.link_cache', delay=2.0)
results = discovery.run([p1, p2], fresh=True)

with open('data/poc_results.txt', 'w', encoding='utf-8') as f:
    for pid, r in results.items():
        f.write(f'Project: {pid}\n')
        f.write(f'  Land core: {r.land_core}\n')
        f.write(f'  Status: {r.status}\n')
        f.write(f'  twur: {r.twur_url}\n')
        f.write(f'  city_case_ids: {r.city_case_ids}\n')
        f.write(f'  national milestones: {r.national_milestones}\n')
        f.write(f'  taipei milestones: {r.taipei_milestones}\n')
        f.write('\n')

discovery.write_crawl_log(results, 'data/crawl_log.tsv')
print('POC validation complete. Results written to data/poc_results.txt and data/crawl_log.tsv')