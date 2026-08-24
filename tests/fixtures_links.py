"""Fixture HTML for link discovery tests."""

from __future__ import annotations

# Sample national portal view page (view/771) with 推動歷程 and 縣市政府案件連結
VIEW_771_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="update_tab_menu">基本資料 土地使用 更新前 推動歷程 容積獎勵 規劃 財務 都更效益</div>
<div class="data_table_box">
基本資料
實施者 弘千建設股份有限公司
更新單元面積(㎡) 2,531.79
實施方式 重建區段：權利變換
權利變換送件方式 併送
更新單元範圍 大同區玉泉段二小段40、40-2、43、43-2、44、44-2、51、51-2、52、57、58、60-2、60-3、61、62-63、64、65、66、67、68、69、70、71、72、73、74、75、75-4地號
區位 西側及北側臨南京西路、東側臨玉泉段二小段39地號、南側臨甘谷街
是否位於更新地區 位於更新地區
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10110181">擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案</a>
資料更新日期 本專案資料最後更新於109.12.06 14:44
</div>
<div class="data_table_box" style="display:none">
推動歷程
項目 日期
事業計畫申請日期 101.12.28
事業計畫核定日期 109.11.17
權利變換計畫申請日期 101.12.28
權利變換計畫核定日期 109.11.17
備註
</div>
</body>
</html>
"""

# Sample national portal view page with multiple city case_ids (view/292)
VIEW_292_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="update_tab_menu">基本資料 土地使用 更新前 推動歷程 容積獎勵 規劃 財務 都更效益</div>
<div class="data_table_box">
基本資料
實施者 東綺建設
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10110211">擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案</a>
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10810271">擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新權利變換計畫案</a>
</div>
<div class="data_table_box" style="display:none">
推動歷程
項目 日期
事業計畫申請日期 101.01.15
事業計畫核定日期 108.06.20
權利變換計畫申請日期 107.03.10
權利變換計畫核定日期 108.12.05
備註
</div>
</body>
</html>
"""

# Sample national portal view page with NO city links
VIEW_NO_CITY_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="update_tab_menu">基本資料 土地使用 更新前 推動歷程 容積獎勵 規劃 財務 都更效益</div>
<div class="data_table_box">
基本資料
實施者 單一實施者
相關連結
縣市政府案件連結
<!-- No links here -->
</div>
<div class="data_table_box" style="display:none">
推動歷程
項目 日期
事業計畫申請日期 105.01.01
事業計畫核定日期 105.06.01
備註
</div>
</body>
</html>
"""

# Live portal markup (2026-08): 推動歷程 as a VISIBLE type4_table with
# 項目/日期 headers — the old display:none assumption no longer holds.
VIEW_VISIBLE_TUIDUI_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
<table class='type4_table'>
<tr><th scope="col" id="j01">項目</th><th scope="col" id="j02">日期</th></tr>
<tr><td headers="j01">事業計畫申請日期</td><td headers="j02">99.01.27</td></tr>
<tr><td headers="j01">事業計畫核定日期</td><td headers="j02">101.08.28</td></tr>
<tr><td headers="j01">權利變換計畫申請日期</td><td headers="j02">99.01.27</td></tr>
<tr><td headers="j01">第一次變更事業計畫核定日期</td><td headers="j02">105.08.24</td></tr>
<tr><td headers="j01">使用核發日期</td><td headers="j02">105.08.29</td></tr>
<tr><td headers="j01">備註</td><td headers="j02"></td></tr>
</table>
</div>
<div class="data_table_box">
<table class='type4_table'>
<tr><th scope="col" id="j11">項目</th><th scope="col" id="j12">內容</th></tr>
<tr><td headers="j11">資料更新日期</td><td headers="j12">本專案資料最後更新於112.03.17 17:40</td></tr>
</table>
</div>
<div class="data_table_box">
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=11407009">案</a>
</div>
</body>
</html>
"""

# Sample Taipei portal case page (case_id=10110211) with 階段辦理過程
TAIPEI_CASE_10110211_HTML = """
<!DOCTYPE html>
<html>
<body>
<select>
<option value="#data1">基本資料</option>
<option value="#data2">階段辦理過程</option>
</select>
<div id="data2">
計畫公聽會日期 2012/10/21
權變公聽會日期
概要公聽會日期
申請計畫日期 2012/11/08
申請權變日期
申請概要日期
公告公展日期 2014/01/15
權變公告公展日期
概要公告公展日期
公展公聽會日期 2014/02/14
權變公展公聽會日期
概要公展公聽會日期
概要審議會通過日期
申請幹事會日期 2014/03/04
權變申請幹事會日期
概要核准日期
召開幹事會日期 2014/04/29
權變召開幹事會日期
申請幹事複審日期 2015/03/05
權變申請幹事複審日期
召開幹事複審日期 2015/04/13
權變召開幹事複審日期
申請聽證日期 2015/07/24
權變申請聽證日期
召開聽證日期 2015/12/23
權變召開聽證日期
召開審議會日期 2016/03/14
權變召開審議會日期
審議通過日期 2016/03/14
權變審議通過日期
近期召開審議會日期
權變近期召開審議會日期
申請核定日期 2016/06/24
權變申請核定日期
核定日期 2017/03/21
權變核定日期
建照核發日期 2022/08/25
</div>
</body>
</html>
"""

# Sample search results page for a core query (unique hit)
SEARCH_UNIQUE_HIT_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
<tr><td>臺北市</td><td>109.11.17</td><td><a href="/zh/urban/rebuild/view/771">擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案</a></td><td>弘千建設股份有限公司</td><td>重建區段：權利變換</td></tr>
</table>
</body>
</html>
"""

# Sample search results page for a core query (no hits)
SEARCH_NO_HIT_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
</table>
</body>
</html>
"""

# Sample search results page for a core query (multiple hits - should be flagged)
SEARCH_MULTI_HIT_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
<tr><td>臺北市</td><td>109.11.17</td><td><a href="/zh/urban/rebuild/view/771">擬訂...玉泉段二小段40地號等29筆...</a></td><td>弘千建設</td><td>重建區段：權利變換</td></tr>
<tr><td>臺北市</td><td>108.05.01</td><td><a href="/zh/urban/rebuild/view/888">擬訂...玉泉段二小段40地號等29筆...另一案</a></td><td>其他建設</td><td>重建區段：權利變換</td></tr>
</table>
</body>
</html>
"""

# Land-identity cores for test projects
TEST_CORES = {
    "yuquan": "玉泉段二小段40地號等29筆",
    "linyi": "臨沂段一小段507地號等3筆",
}

# Sample Get_project168_third.ashx payload — completed case (facts §10.5, case 141 values)
THIRD_CASE_COMPLETED_JSON = """
[
  {
    "Eng_Start_Date": "2013/09/10",
    "Ulic_Date": "2016/08/29",
    "Report_Date": "",
    "Exe_Way": "權利變換",
    "Base_Area": "1,604.00",
    "Landkind1": "第四種商業區(特)(原商三)",
    "Landkind1_Area": "1,604.00",
    "Landkind2": "",
    "Landkind2_Area": "0.00",
    "Old_Doors": "50",
    "Settle_Old_Doors": "0",
    "Settle_Doors": "0",
    "New_Parkings": "103",
    "New_Parkings2": "85",
    "Sidewalk_Length": "60",
    "Sidewalk_Area": "230.81",
    "Urban_Renew_Fee": "1242782140",
    "Land_Owners_Pir": "54"
  }
]
"""

# Sample Get_project168_third.ashx payload — revision case (all empty)
THIRD_CASE_EMPTY_JSON = """
[
  {
    "Eng_Start_Date": "",
    "Ulic_Date": "",
    "Report_Date": "",
    "Exe_Way": "",
    "Base_Area": ""
  }
]
"""

# Sample Get_project168_fourth.ashx payload — completed case (facts §10.5 values)
FOURTH_CASE_JSON = """
[
  {
    "F0": "8,982.01",
    "F": "10,829.58",
    "F3": "538.92",
    "F5": "1,308.65",
    "F5_3": "230.81"
  }
]
"""

# Sample Get_project168_fourth.ashx payload — all empty
FOURTH_CASE_EMPTY_JSON = """
[
  {
    "F0": "",
    "F": "",
    "F3": ""
  }
]
"""

# Sample national portal list page (page 1) with multiple cases
LIST_PAGE_1_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
<tr><td>臺北市</td><td>109.11.17</td><td><a href="/zh/urban/rebuild/view/771">擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案</a></td><td>弘千建設股份有限公司</td><td>重建區段：權利變換</td></tr>
<tr><td>臺北市</td><td>108.06.20</td><td><a href="/zh/urban/rebuild/view/292">擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案</a></td><td>東綺建設</td><td>重建區段：權利變換</td></tr>
<tr><td>臺北市</td><td>107.12.05</td><td><a href="/zh/urban/rebuild/view/888">擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫案另一案</a></td><td>其他建設</td><td>重建區段：權利變換</td></tr>
</table>
<a href="?city_id=2&page=2">下一頁</a>
</body>
</html>
"""

# Sample national portal list page (page 2) - last page
LIST_PAGE_2_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
<tr><td>臺北市</td><td>106.03.15</td><td><a href="/zh/urban/rebuild/view/999">擬訂臺北市信義區松仁段100地號等5筆土地都市更新事業計畫案</a></td><td>信義建設</td><td>重建區段：事業計畫</td></tr>
</table>
<!-- No next page link = last page -->
</body>
</html>
"""

# Sample list page with empty table (end of pagination)
LIST_PAGE_EMPTY_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
<tr><th>縣市</th><th>核定年期</th><th>案件名稱</th><th>實施者</th><th>實施方式</th></tr>
</table>
</body>
</html>
"""