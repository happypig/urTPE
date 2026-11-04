# -*- coding: utf-8 -*-
"""Structural regression tests for viewer/app.js field-label tables.

Pins the official label inventory captured in docs/facts_2_portals.md §12.1
(r_progress_detail.aspx DOM, 2026-08-25) so every key observed in emitted
implementation/rewards payloads renders with its portal label instead of a raw
English key, plus the construction-phase graph annotation constants
(chain slots / national provenance / implementation callout).
"""
import re
import shutil
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parents[1] / "viewer" / "app.js"

# Official labels transcribed verbatim from facts §12.1.
REWARD_INVENTORY = {
    "F1": "△F1(㎡)",
    "F2": "△F2(㎡)",
    "F4": "△F4(㎡)",
    "F6": "△F6(㎡)",
    "F4_1": "△F4-1(㎡)",
    "F4_2": "△F4-2(㎡)",
    "F4_3": "△F4-3(㎡)",
    "F5_1": "△F5-1(㎡)",
    "F5_2": "△F5-2(㎡)",
    "F5_4": "△F5-4(㎡)",
    "F5_5": "△F5-5(㎡)",
    "F5_6": "△F5-6(㎡)",
    "Park_Area": "停車獎勵(㎡)",
    "Park_Cars": "停車獎勵部數",
    "TIME_REWARD": "時程獎勵",
    "SCALE_REWARD": "規模獎勵",
    "GREENBUILD_DESIGN": "綠建築標章之建築設計",
    "SEISMIC_DESIGN": "耐震設計",
    "WISDOMBUILD_DESIGN": "智慧建築標章之建築設計",
    "ACCESSIBLE_DESIGN": "無障礙環境設計",
    "NEWTECH": "新技術之應用",
    "IMENVIRON": "改善都市環境",
    "BUILDPLANDES1": "建築規劃設計(一)",
    "BUILDPLANDES2": "建築規劃設計(二)",
    "BUILDPLANDES3": "建築規劃設計(三)",
    "BUILDPLANDES4": "建築規劃設計(四)",
    "BUILDSAFE_CONDITION": "建築物結構安全條件",
    "CHARITY_BUILD": "公益設施",
    "CULTURAL_MAINTAIN": "文資保存及維護",
    "DEVELOP_PUBFACILITY": "協助開闢公共設施用地",
    "AGREEMENT_CONSTRUCTION": "全體同意採協議合建實施",
    "PROREGENERAT1": "促進都市更新(一)",
    "PROREGENERAT2": "促進都市更新(二)",
    "VOLUME_HIGHER_REWARD": "高於法定容積部份核計之獎勵",
    "ILLEGAL_FLOORAREA_REWARD": "處理違建戶之樓地板面積獎勵",
    "name_reward_no": "獎勵上限規定",
}

# Semantic labels retained in place of △F/accounting notation.
SEMANTIC_EXCEPTIONS = {
    "F": "允建容積",
    "F0": "基準容積",
    "F3": "都市更新獎勵",
    "F5": "其他容積獎勵",
    "F5_3": "人行步道面積",
}

IMPL_DATE_FIELDS = {
    "Eng_Start_Date": "開工日期",
    "Ulic_Date": "使照核發日期",
    "Report_Date": "成果報備日期",
}

# Implementation statistics keys found unlabeled by the §3.1 corpus sweep;
# labels from the same r_progress_detail.aspx DOM (STATELAND2_OWNER is an
# upstream all-caps variant of StateLand2_Owner — same official label).
IMPL_STAT_FIELDS = {
    "Bui_Owners_Legal": "合法建物所有權人數",
    "Land_Owners_Pub": "公有土地所有權人數",
    "pc_afterUpdTotalValue": "總銷售金額",
    "Welfare_Area": "公益設施面積",
    "Road_Cost": "捐贈道路成本",
    "STATELAND2_OWNER": "國有土地管理機關2所有人",
}


def _js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _extract_object(js: str, name: str) -> dict[str, str]:
    m = re.search(rf"const {name}\s*=\s*\{{(.*?)\}}\s*;", js, re.S)
    assert m, f"const {name} = {{...}} not found in viewer/app.js"
    pairs = re.findall(r"(?:\"([^\"]+)\"|([A-Za-z0-9_]+))\s*:\s*\"([^\"]*)\"", m.group(1))
    return {(q or bare): v for q, bare, v in pairs}


def _extract_array(js: str, name: str) -> list[str]:
    m = re.search(rf"const {name}\s*=\s*\[(.*?)\]\s*;", js, re.S)
    assert m, f"const {name} = [...] not found in viewer/app.js"
    return re.findall(r"\"([^\"]+)\"", m.group(1))


def test_reward_labels_cover_official_inventory():
    labels = _extract_object(_js(), "REWARD_LABELS")
    missing = [k for k in REWARD_INVENTORY if not labels.get(k)]
    assert not missing, f"REWARD_LABELS missing official inventory keys: {missing}"
    wrong = {
        k: (labels.get(k), want)
        for k, want in REWARD_INVENTORY.items()
        if labels.get(k) != want
    }
    assert not wrong, f"REWARD_LABELS diverge from §12.1 official labels: {wrong}"


def test_reward_semantic_exceptions_preserved():
    labels = _extract_object(_js(), "REWARD_LABELS")
    for key, want in SEMANTIC_EXCEPTIONS.items():
        got = labels.get(key)
        assert got == want, (
            f"{key} should keep its semantic label {want!r}, got {got!r}"
        )
        assert not str(got).startswith("△"), f"{key} must not use △ notation"


def test_impl_labels_carry_construction_dates():
    labels = _extract_object(_js(), "IMPL_LABELS")
    for key, want in {**IMPL_DATE_FIELDS, **IMPL_STAT_FIELDS}.items():
        got = labels.get(key)
        assert got == want, f"IMPL_LABELS[{key}] should be {want!r}, got {got!r}"


def test_construction_chain_slots_exact():
    slots = _extract_array(_js(), "CONSTRUCTION_CHAIN_SLOTS")
    assert slots == ["建照核發日期", "開工日期", "使照核發日期"], (
        f"construction chain must have exactly the three phase slots, got {slots}"
    )


def test_national_provenance_labels():
    mapped = _extract_object(_js(), "NATIONAL_MAPPED_LABELS")
    assert "使用核發日期" in mapped.values(), (
        f"NATIONAL_MAPPED_LABELS must map the 使照 slot to national 使用核發日期, got {mapped}"
    )
    slots = _extract_array(_js(), "CONSTRUCTION_CHAIN_SLOTS")
    unknown = [k for k in mapped if k not in slots]
    assert not unknown, f"NATIONAL_MAPPED_LABELS keys outside chain slots: {unknown}"


def test_implementation_callout_fields_exact():
    fields = _extract_object(_js(), "IMPLEMENTATION_CALLOUT_FIELDS")
    assert fields == {
        "Exe_Way": "實施方式",
        "Base_Area": "基地面積",
        "Old_Doors": "原戶數",
    }, f"callout must show exactly 實施方式/基地面積/原戶數, got {fields}"


def test_annotation_leader_and_tail_present():
    js = _js()
    css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
    # timeline-event redesign: per-event attribution edges + per-record callout leaders
    assert "event-edge" in js, "app.js must draw source-colored attribution edges"
    assert "event-link" in js, "app.js must draw the 開工→使照 connector"
    assert "callout-leader" in js, "app.js must draw per-record callout leaders"
    assert "callout-diff" in js, "app.js must red-highlight changed callout values"
    assert ".event-edge" in css and ".callout-diff" in css, (
        "app.css must style .event-edge/.callout-diff"
    )
    # replaced by the gutter placement (spec §1)
    assert "callout-tail" not in js, "callout-tail polygon replaced by callout-leader"
    # replaced by the gutter placement (spec §1)
    assert "canvas-extension fallback" not in js, "dodging fallback replaced by gutter sweep"
    # superseded by the timeline redesign
    assert "chain-leader" not in js, "lane leader must be gone"
    # 相關連結 survives only as a debug toggle, hidden by default
    assert 'id="links-section" hidden' in js, (
        "link section must default to hidden"
    )
    assert "links-toggle" in js, "a toggle must control the link section"
    assert "buildRelatedLinkLabels" in js, "debug section keeps its 案名 builder"
    # fallback precedence: candidate_names (harvested) and orphan_nodes real names
    # must be consulted BEFORE the synthetic case_milestones label (里程碑 N 筆)
    i_ghost = js.index("links.orphan_nodes || []")
    i_miles = js.index("links.case_milestones && links.case_milestones[cid]")
    i_cand = js.index("links.candidate_names && links.candidate_names[cid]")
    assert i_ghost < i_miles, (
        "orphan_nodes real case names must take precedence over the "
        "case_milestones fallback label in buildRelatedLinkLabels"
    )
    assert i_cand < i_miles, (
        "candidate_names must take precedence over the case_milestones "
        "fallback label in buildRelatedLinkLabels"
    )
    # 7.2.3: schedule badge + never-approved reason (§6.14 E2)
    assert "case_schedules" in js, "相關連結 must read links.case_schedules"
    assert "link-schedule" in js, "schedule badge must render in 相關連結"
    assert "no-twur-reason" in js, "never-approved reason must surface when every case is 駁回/撤回/失效"
    assert "virtual" in js and "schedule:" in js, "virtual nodes must carry the schedule into the graph"
    # 7.2.5/7.2.6: real-node badge + left-list 未核定 chip
    assert "neverApproved" in js, "list/detail must classify never-approved projects"
    assert "never-badge" in js, "left-list cards must show the 未核定 chip"
    # D12 (add-virtual-node-ordering-and-chain): effective-case_id comparator
    # precedes the 區段 tie-break; chain edges only for virtual-involved pairs
    i_key = js.index("effectiveCaseKey(a)")
    i_sec = js.index("localeCompare(_secTokenOf(b)")
    assert i_key < i_sec, "case_id ordering must precede the 區段 tie-break"
    assert "virtualChainPairs(clusters).forEach" in js, "chain edges render from the pure helper"
    assert 'class="edge virtual"' in js, "virtual chain edges use the dashed virtual style"
    # 7.2.8: 已核准 is the default focus — its schedule badge is skipped
    assert 's === "已核准"' in js, "schedule badge must skip the default 已核准 state"
    # mockup-only annotation aids stay unrendered
    assert "phase-header" not in js, "grey grid/phase headers are mockup aids only"


def test_graph_links_live_on_nodes():
    js = _js()
    # event labels hyperlink to their portal (Taipei case / twur view)
    assert "r_progress_detail.aspx?case_id=" in js, (
        "event/approval labels must link to Taipei case pages"
    )
    # 北/國 badges wrapped as anchors
    assert re.search(r"<a[^>]+class=\"badge-link\"", js) or "<a " in js.split("getNodeMilestoneBadges")[1][:600], (
        "node badges must be hyperlinks"
    )


def test_chain_builder_carries_case_provenance():
    m = re.search(r"function buildConstructionChain\s*\([^)]*\)\s*\{[\s\S]*?\n\}", _js())
    assert m, "buildConstructionChain not found in viewer/app.js"
    body = m.group(0)
    assert "case_id" in body, (
        "builder must read implementation.case_id for carrying-case provenance"
    )
    # exact-match guard: label only when slot value equals the payload date
    assert re.search(r"(===|==)\s*(impl|p\.implementation)", body) or "===" in body, (
        "builder must exact-match the payload date before labeling provenance"
    )
    # owner record: carrying case anchors to a recno via nodes[].links.taipei
    assert "編號" in body and ".taipei" in body, (
        "provenance must name the owning record's 編號 when anchored"
    )


def test_national_dates_converted_to_western():
    body = re.search(
        r"function buildConstructionChain\s*\([^)]*\)\s*\{[\s\S]*?\n\}", _js()
    ).group(0)
    assert "1911" in body, (
        "national 民國 dates (e.g. 110.10.25) must convert to western for display and sorting"
    )


def test_source_group_edges_and_hyperlink_rule():
    js = _js()
    body = re.search(
        r"function buildConstructionChain\s*\([^)]*\)\s*\{[\s\S]*?\n\}", js
    ).group(0)
    assert "milestones_source" in body, (
        "builder must resolve stage slots (建照) via the milestones_source map"
    )
    assert "anchored" in body, (
        "builder must mark whether each slot's carrying case anchors to a record"
    )
    assert "event-link" in js and "dashed" in js, (
        "group transitions must render dashed connectors"
    )
    assert "event-edge" in js, "group source attachment must use event-edge"
    assert re.search(r"e\.anchored", js), (
        "event hyperlinks must be dropped when the carrying case anchors"
    )


def test_badge_tooltips_carry_ids():
    m = re.search(r"function getNodeMilestoneBadges\s*\([^)]*\)\s*\{[\s\S]*?\n\}", _js())
    assert m, "getNodeMilestoneBadges not found"
    body = m.group(0)
    assert "案" in body, "北 tooltip must name the case (案<case_id>)"
    assert "view/" in body, "國 tooltip must name the view id"


def test_callout_zone_row_and_selection():
    js = _js()
    m = re.search(r"function buildImplCallout\s*\([^)]*\)\s*\{[\s\S]*?\n\}", js)
    assert m, "buildImplCallout not found"
    assert "Landkind" in m.group(0), "callout must include the 使用分區 row"
    assert "abbreviateZone" in js, "zone abbreviator must exist"
    assert "firstCarrier" in js, "callout selection must keep the first carrier"
    assert "callout-leader" in js, "callout must render a leader to its node"
    assert "CALLOUT_GUTTER_CAP" in js, "callout gutter cap must be defined"
    assert "lastBoxBottom" in js, "gutter sweep must track last box bottom"


def test_list_stage_badge():
    js = _js()
    m = re.search(r"function constructionStage\s*\([^)]*\)\s*\{[\s\S]*?\n\}", js)
    assert m, "constructionStage derivation not found in viewer/app.js"
    body = m.group(0)
    for slot in ("建照核發日期", "開工日期", "使照核發日期"):
        assert slot in body, f"stage derivation must consider {slot}"
    assert "使用核發日期" in body, "使照 must fall back to the national 使用核發日期"
    assert "stage-badge" in js, "list items must render the stage-badge chip"
    # colours: 建照 orange, 開工 red, 使照 green
    for color in ("#f59e0b", "#dc2626", "#16a34a"):
        assert color in js, f"badge colour {color} missing"


def test_stage_filter_dimension():
    js = _js()
    m = re.search(r"const DIMS = \[[\s\S]*?\];", js)
    assert m, "DIMS not found in viewer/app.js"
    assert 'key: "stage"' in m.group(0), "DIMS must include the stage dimension"
    assert 'label: "施工階段"' in m.group(0), "stage dimension labelled 施工階段"
    for opt in ("建照", "開工", "使照"):
        assert f'"{opt}"' in m.group(0), f"stage option {opt} missing"
    i = js.find("function matches(p)")
    assert i >= 0, "matches() not found"
    seg = js[i:js.find("\n  }", i) + 3]
    assert "sel.stage" in seg, "matches() must apply the stage dimension"
    assert "constructionStage(p)" in seg, (
        "stage filter must derive via constructionStage (same as the badge)"
    )


def test_app_js_parses():
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node not available")
    r = subprocess.run([node, "--check", str(APP_JS)], capture_output=True, text=True)
    assert r.returncode == 0, f"viewer/app.js has a syntax error: {r.stderr[:400]}"
class TestConstructionEdgeSemantics:
    """Final edge model (design D3 third amendment, 2026-08-27):
    R1 slanted solid pink/green source edge from record OR ghost anchor to the
       group's earliest event (national-fallback groups attach to 現況);
    R2 vertical solid connector between adjacent same-source events;
    R3 vertical dashed connector between different-source events (incoming color);
    single-render: ghost columns hold anchor nodes only — execution dates never
    duplicate; compact ROW pitch (32px); dotted chain styling retired."""

    def _js(self):
        return APP_JS.read_text(encoding="utf-8")

    def test_rule1_source_edge_slants_from_record_to_first_event(self):
        js = self._js()
        assert 'line class="event-edge ${colorCls}"' in js
        assert 'line class="event-edge national"' in js
        assert "pos[e.ownerRecno]" in js
        assert "nodes.find(n => n.is_current)" in js

    def test_rule1b_orphan_ghost_acts_as_source(self):
        js = self._js()
        assert "orphanSources" in js, (
            "ghost anchors must be wired as slanted solid sources for their events")
        assert "orphanSources[e.case]" in js

    def test_rule2_same_source_connects_solid(self):
        js = self._js()
        assert re.search(
            r"else \{\s*s \+= `<line class=\"event-link \$\{colorCls\}\" x1", js), (
            "same-source neighbors must fall through to a solid event-link")

    def test_rule3_cross_source_transition_dashed(self):
        js = self._js()
        assert 'class="event-link ${colorCls} dashed"' in js

    def test_dashed_has_css_rule(self):
        css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        assert ".event-link.dashed" in css, (
            "cross-source dashed transitions need an actual dash pattern")

    def test_dotted_chain_styling_retired(self):
        js = self._js()
        assert "event-link ${colorCls} dotted" not in js
        css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        assert ".event-link.dotted" not in css

    def test_execution_dates_render_once_no_ghost_events(self):
        js = self._js()
        assert "orphan-event" not in js, (
            "ghost columns hold anchor nodes only; events must not duplicate")
        assert "ghostChains" not in js

    def test_content_addressed_pitch(self):
        js = self._js()
        assert "NODE_ROW = 64" in js and "EVENT_ROW = 32" in js
        # §3: an event after an approval starts ½ row (NODE_ROW/2) under it
        assert "NODE_ROW / 2" in js, (
            "execution events must start ½ node row under the approval above them (§3)")
        assert "EVENT_ROW" in js, "event-to-event pitch must use EVENT_ROW"
        assert "* 64" not in js, "row math must use NODE_ROW/EVENT_ROW, not literal 64"

    def test_orphan_shift_and_edge_target_are_row_based(self):
        # §4: "between 2 consecutive recnos" and "nearest recno" mean RENDERED
        # ROWS in the timeline, not dates. An undated orphan (11012301:
        # applies 2021-12-29, withdraws, renders between 734@2019 and
        # 393@2022 by case_id interleave) has no date of its own, so a
        # date-based test can never fire for it (corpus: 30 undated vs 7 dated).
        js = self._js()
        assert "nearestRecnoRowAbove" in js and "nearestRecnoRowUnder" in js, (
            "orphan edge target must come from timeline rows, not date scan")
        assert "allRecnosByDate" not in js and "recnosByTrack" not in js, (
            "date-based placement helpers must be gone")
        # branch-off point: the recno row directly above the orphan's row wins
        assert re.search(r"nearestRecnoRowAbove\(i\)\s*\|\|\s*nearestRecnoRowUnder\(i\)", js), (
            "dotted edge must target the recno row directly above the orphan's row, "
            "falling to the row under only when none sits above (11012301 -> 734)")

    def test_four_column_grid_mapping(self):
        js = self._js()
        assert '"事業概要", "事業計畫", "都市更新計畫"' in js
        assert '"事業計畫、權利變換", "都市計畫、權利變換"' in js

    def test_virtual_nodes_present(self):
        js = self._js()
        assert "virtualNodes" in js
        assert "node virtual" in js or 'virtualCls' in js
        css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        assert ".node.virtual circle" in css

    def test_graph_viewport_zoom_pan(self):
        js = self._js()
        assert "graph-viewport" in js and "attachGraphViewport" in js
        assert "pointerdown" in js and "ctrlKey" in js
        css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        assert ".graph-viewport" in css

    def test_rwd_list_cap(self):
        css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        assert "max-width: 767px" in css and "max-height: 32vh" in css

    def test_callout_gutter_present(self):
        js = self._js()
        assert "callout-leader" in js, "callout leaders replace dodging fallback"
        assert re.search(r"y: q\.y - 30", js), "node boxes must cover the badge strip"


def test_list_shows_orphan_count_after_records():
    js = APP_JS.read_text(encoding="utf-8")
    assert re.search(r"\(\+\$\{orphanCount\}\)", js), (
        "left list must append (+N) after the record count when orphan nodes exist")
    assert "orphan_nodes" in js


def test_section_token_extraction_wiring():
    js = APP_JS.read_text(encoding="utf-8")
    assert "function areaTokenFromName" in js
    assert "areaTokenFromName(n.case_name)" in js
    assert "（西區）" not in js  # label is built from the token, not hard-coded


def test_stage_key_cluster_order_kept_bands_removed():
    # clustering still orders rows & tags undated; stage-band rendering removed (spec §2.5)
    js = APP_JS.read_text(encoding="utf-8")
    assert "stageClusters" in js
    assert "clusterDate" in js
    assert "未核定" in js
    assert "stage-band" not in js, "stage bands removed from rendering per spec §2.5"
    css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
    assert ".stage-band" not in css


def test_national_label_key_binds_stage_and_track():
    # §2: nationalLabelKey maps a national approval label to {stage, track}; application
    # dates and 使用核發日期 bind nothing.
    import subprocess, json
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"(const CHINESE_DIGIT = \{[\s\S]*?\};\nconst nationalLabelKey = label => \{[\s\S]*?\n\};)", js)
    assert m, "nationalLabelKey must exist in app.js"
    cases = [["事業計畫核定日期", "擬訂", "事業計畫"],
             ["權利變換計畫核定日期", "擬訂", "權利變換"],
             ["第一次變更事業計畫核定日期", "變更", "事業計畫"],
             ["第一次變更權利變換計畫核定日期", "變更", "權利變換"],
             # D3a (inspection-batchD): second-or-later 變更 ordinals. The shipped
             # code built 變更(二次) while every payload node spells 變更(第二次),
             # so 223 such labels bound 0 nodes (吉林717 node 762 shape).
             ["第二次變更權利變換計畫核定日期", "變更(第二次)", "權利變換"],
             ["第三次變更事業計畫核定日期", "變更(第三次)", "事業計畫"],
             ["第4次變更事業計畫核定日期", "變更(第4次)", "事業計畫"],
             ["第十次變更權利變換計畫核定日期", "變更(第十次)", "權利變換"],
             ["使用核發日期", None, None],
             ["申請計畫日期", None, None]]
    arg = json.dumps(cases, ensure_ascii=False)
    prog = (m.group(0) + "\nconst cases = " + arg + ";\n" +
            "console.log(JSON.stringify(cases.map(([label, stage, track]) => {\n" +
            "  const k = nationalLabelKey(label);\n" +
            "  const ok = k == null ? stage == null && track == null\n" +
            "             : k.stage === stage && k.track === track;\n" +
            "  return [label, ok];\n" +
            "})));\n")
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    results = json.loads(r.stdout)
    assert all(ok for _, ok in results), f"nationalLabelKey mismatches: {results}"


def test_is_current_branch_removed_from_國_badge():
    # §2: the 現況 rule no longer grants 國 alone.
    js = APP_JS.read_text(encoding="utf-8")
    assert "node.is_current" not in js, "國 badge must not be granted by is_current alone"


def test_per_track_stage_helpers_present():
    """§10: per-track stage text + combined-track append (viewer change specs)."""
    js = (APP_JS.parent / "app.js").read_text(encoding="utf-8")
    assert "perTrackStageText" in js, "chain/filter helpers present"
    assert "scheduleBadgeText" in js, "已核准 default-state filter present"


def test_national_label_binding_is_per_label():
    """C1/S4: a national label binds at most one node, decided per label.
    Scoring per node badged every candidate of a multi-match label (16 unearned
    國 on 19 multi-candidate labels)."""
    import subprocess, json
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"(const CHINESE_DIGIT = \{[\s\S]*?\};\nconst nationalLabelKey = label => \{[\s\S]*?\n\};)", js)
    assert m, "nationalLabelKey must exist in app.js"
    if "bindNationalLabels" not in js:
        pytest.fail("bindNationalLabels not implemented yet (S4 test-first)")
    jsn = js.replace("\r\n", "\n")
    m2 = re.search(r"(function trackMatches[\s\S]*?\n\}\n)(function bindNationalLabels[\s\S]*?\n\}\n)", jsn)
    if not m2:
        # trackMatches and bindNationalLabels are separated by the two date
        # helpers this test does not need; extract the spans directly.
        i1 = jsn.index("function trackMatches")
        i2 = jsn.index("function bindNationalLabels")
        end = jsn.index("\n}\n", i2) + 3
        m2 = type("M", (), {"group": lambda self, k: jsn[i1:i2] if k == 1 else jsn[i2:end]})()
    assert m2, "trackMatches + bindNationalLabels must exist in app.js"
    prog = (m.group(0).replace("\r\n", "\n") + "\n" + m2.group(1) + "\n" + m2.group(2) + "\n"
        + """
const projects = [
  { // single candidate binds whatever the date
    nodes: [{recno: 1, stage: "擬訂", track: "事業計畫", date: "2009-06-04"}],
    national: {"事業計畫核定日期": "98.06.04"}
  },
  { // multi-candidate: exact date decides
    nodes: [{recno: 3, stage: "擬訂", track: "事業計畫", date: "2022-08-02"},
            {recno: 370, stage: "變更", track: "事業計畫", date: "2023-03-21"}],
    national: {"第一次變更事業計畫核定日期": "112.03.21"}
  },
  { // ±1 day decides
    nodes: [{recno: 5, stage: "擬訂", track: "事業計畫", date: "2023-03-20"},
            {recno: 6, stage: "擬訂", track: "事業計畫", date: "2023-09-01"}],
    national: {"事業計畫核定日期": "112.03.21"}
  },
  { // a tie ±1 day cannot break binds nothing
    nodes: [{recno: 7, stage: "擬訂", track: "事業計畫", date: "2023-03-20"},
            {recno: 8, stage: "擬訂", track: "事業計畫", date: "2023-03-20"}],
    national: {"事業計畫核定日期": "112.03.21"}
  },
  { // 使用核發日期 and application dates bind nothing
    nodes: [{recno: 9, stage: "擬訂", track: "事業計畫", date: "2020-01-01"}],
    national: {"使用核發日期": "109.10.25", "事業計畫申請日期": "109.01.01"}
  }
];
const out = projects.map(p => bindNationalLabels({nodes: p.nodes, links: {milestones_national: p.national}}));
console.log(JSON.stringify(out));
""")
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "1" in out[0], "single candidate binds its node"
    assert list(out[1]) == ["370"], f"exact date decides: {out[1]}"
    assert list(out[2]) == ["5"], f"±1 day decides: {out[2]}"
    assert out[3] == {}, f"a tie the window cannot break binds nothing: {out[3]}"
    assert out[4] == {}, f"execution/application labels bind nothing: {out[4]}"


def test_related_link_labels_use_the_city_name():
    """C7/S9: an anchored case is labelled by its own city name; the 國 anchor
    label is the national page's own name (twur_name, C10)."""
    import subprocess, json
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8").replace("\r\n", "\n")
    if "twur_name" not in js:
        pytest.fail("twur_name not implemented yet (S9 test-first)")
    m = re.search(r"(function buildRelatedLinkLabels[\s\S]*?\n\}\n)", js)
    assert m, "buildRelatedLinkLabels must exist in app.js"
    prog = (m.group(1) + "\n"
        + """
const p = {
  nodes: [
    {recno: 1376, is_current: false, case_name: "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案",
     links: {taipei: ["09307102"]}},
    {recno: 1311, is_current: true, case_name: "變更臺北市中山區吉林段四小段705地號等47筆土地都市更新權利變換計畫(含釐正圖冊)案",
     links: {taipei: ["09307100", "09307101"]}}
  ],
  links: {
    twur: "https://twur.nlma.gov.tw/zh/urban/rebuild/view/57",
    twur_name: "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案",
    candidate_names: {
      "09307100": "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業概要案",
      "09307101": "變更臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫及擬訂權利變換計畫案"
    }
  }
};
const r = buildRelatedLinkLabels(p);
console.log(JSON.stringify({byCase: r.byCase, anchorName: r.anchorName}));
""")
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["byCase"]["09307100"] == "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業概要案", out["byCase"]
    assert out["byCase"]["09307101"] == "變更臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫及擬訂權利變換計畫案", out["byCase"]
    assert out["anchorName"] == "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案", out["anchorName"]


def test_fmt_date_rejects_an_out_of_range_roc_year():
    """S15 D5: 橋北574-1's 291.08.02 rendered 2202 — an ROC year above the
    current 民國 year is a source typo; it renders verbatim. A normal ROC
    year still converts."""
    import subprocess, json
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.search(r"(function currentRocYear\(\) \{[\s\S]*?\n\}\n)(function fmtDate\(text\) \{[\s\S]*?\n\}\n)", js)
    assert m, "fmtDate + currentRocYear must exist in app.js"
    prog = (m.group(1) + "\n" + m.group(2) + "\n"
        + """
console.log(JSON.stringify([
  fmtDate("291.08.02"),          // out-of-range ROC year: verbatim
  fmtDate("111.08.02"),          // a normal ROC year converts
  fmtDate("115.09.24"),          // the current 民國 year converts
  fmtDate("2022/08/02"),         // slash-western converts
]));
""")
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out[0] == "291.08.02", f"out-of-range renders verbatim: {out[0]}"
    assert out[1] == "2022-08-02", f"a normal ROC year converts: {out[1]}"
    assert out[2] == "2026-09-24", f"the current year converts: {out[2]}"
    assert out[3] == "2022-08-02", f"slash-western converts: {out[3]}"


def test_the_permit_witness_reaches_the_event_label():
    """S15: the 使照 event's label names the building authority's permit when
    the project carries links.permit."""
    import subprocess, json
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8").replace("\r\n", "\n")
    if "執照${permit.permit_no" not in js and "執照" not in js:
        pytest.fail("the permit witness not implemented yet (S15 test-first)")
    # structural: the render path reads links.permit beside the 使照 slot
    assert "}).permit || null" in js, "the render path must read links.permit"
    i = js.index("}).permit || null")
    span = js[max(0, i - 600):i + 600]
    assert "使照核發日期" in span, "the witness rides the 使照 slot"
    assert "permit_no" in span and "permit.date" in span, "the label carries the permit number and date"
