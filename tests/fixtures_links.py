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