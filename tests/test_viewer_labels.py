# -*- coding: utf-8 -*-
"""Structural regression tests for viewer/app.js field-label tables.

Pins the official label inventory captured in docs/facts_2_portals.md §12.1
(r_progress_detail.aspx DOM, 2026-08-25) so every key observed in emitted
implementation/rewards payloads renders with its portal label instead of a raw
English key, plus the construction-phase graph annotation constants
(chain slots / national provenance / implementation callout).
"""
import re
from pathlib import Path

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
    # timeline-event redesign: per-event attribution edges + per-record tails
    assert "event-edge" in js, "app.js must draw source-colored attribution edges"
    assert "event-link" in js, "app.js must draw the 開工→使照 connector"
    assert "callout-tail" in js, "app.js must draw per-record callout tails"
    assert "callout-diff" in js, "app.js must red-highlight changed callout values"
    assert ".event-edge" in css and ".callout-diff" in css, (
        "app.css must style .event-edge/.callout-diff"
    )
    # superseded by the timeline redesign
    assert "chain-leader" not in js, "lane leader must be gone"
    # 相關連結 survives only as a debug toggle, hidden by default
    assert 'id="links-section" hidden' in js, (
        "link section must default to hidden"
    )
    assert "links-toggle" in js, "a toggle must control the link section"
    assert "buildRelatedLinkLabels" in js, "debug section keeps its 案名 builder"
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
    assert "ownRecno" in js, "collision set must exclude the callout's own record"
    assert "Math.min" in js, "candidate rects must clamp into the viewBox"


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
