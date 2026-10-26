# -*- coding: utf-8 -*-
"""Adapter tests for the recovery sources — task 2.8.

The two HTTP surfaces are keyed lookups only: every request is keyed by a
section+parcel from a surviving cell or an already-known identity. There is no
enumeration method to call (the exploration's getSectionList sweep stays in the
probes). Request failures degrade to residual — they must never abort the run.
"""

from __future__ import annotations

import inspect
import json

import pytest

from urtpe import recovery_pass
from urtpe import recovery_sources as RS
from tests.fixtures_recovery import FIXTURE_DIR, families, tops


class RecordingTransport:
    """Stands in for the real transport; serves recorded bodies."""

    def __init__(self):
        import urllib.parse as _up
        self.posts = []
        self.gets = []
        self._up = _up

    def post_form(self, url, params, timeout=90):
        self.posts.append((url, dict(params)))
        name = url.rsplit("/", 1)[-1]
        if name == "Get_updcase_list.ashx":
            key = f"{params['sectstr']}|{params['monobuf']}|{params['sunobuf']}"
            return families().get(key, "[]")
        if name == "get_project168_top.ashx":
            return tops().get(params["case_id"], "[]")
        raise AssertionError(f"unexpected keyed endpoint: {name}")

    def get_json(self, url, timeout=600):
        self.gets.append(url)
        decoded = self._up.unquote(url)
        if "uro-redevelop-ALL-5" in decoded:
            m = __import__("re").search(r"ID='([^']+)'", decoded)
            path = FIXTURE_DIR / f"geoserver_boundary_{m.group(1)}.json"
            if path.exists():
                with open(path, encoding="utf-8") as fh:
                    return json.load(fh)
            return {"features": []}
        raise AssertionError(f"unexpected WFS request: {url}")


# --- 2.8 ashx: keyed lookups only --------------------------------------------

def test_case_family_is_a_keyed_lookup():
    t = RecordingTransport()
    client = RS.AshxClient(transport=t)
    cands = client.case_family("美仁段二小段", "0694", "0000")
    assert len(t.posts) == 1
    url, params = t.posts[0]
    assert url.endswith("Get_updcase_list.ashx")
    assert params == {"qitem": "qland", "sectstr": "美仁段二小段",
                      "monobuf": "0694", "sunobuf": "0000"}
    assert len(cands) == 6
    # two id spaces per candidate: display case_id (GeoServer/portal key) and
    # api_case_id (parsed from details, keys get_project168_top)
    assert {c["case_id"] for c in cands} >= {"R098505"}
    assert {c["api_case_id"] for c in cands} >= {"11411014"}
    assert all(c["api_case_id"] for c in cands)


def test_case_top_is_a_keyed_lookup():
    t = RecordingTransport()
    client = RS.AshxClient(transport=t)
    top = client.case_top("11411014")
    assert len(t.posts) == 1
    url, params = t.posts[0]
    assert url.endswith("get_project168_top.ashx")
    assert params == {"case_id": "11411014"}
    assert "uro_chk_date" in top


def test_geoserver_boundary_is_keyed_by_case_id():
    import urllib.parse

    t = RecordingTransport()
    client = RS.GeoServerClient(transport=t)
    polys = client.boundary("R098505")
    assert len(t.gets) == 1
    # the cql_filter is keyed by the case id (urlencode escapes it on the wire)
    assert "ID='R098505'" in urllib.parse.unquote(t.gets[0])
    assert polys  # the recorded boundary has one polygon


def test_unit_geometry_computes_vertex_membership():
    """PIP: a square boundary; one parcel fully inside, one outside, one
    straddling the edge. Rings are closed (the last vertex repeats the first),
    so the straddler scores 3/5, not 2/4 — the same convention the calibration
    used for every parcel, which is what matters for the ≥1-vertex candidacy."""
    square = [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]]

    def parcel(land_no, coords):
        return {"properties": {"land_no": land_no},
                "geometry": {"type": "Polygon", "coordinates": [coords]}}

    inside = parcel("A", [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]])
    outside = parcel("B", [[20, 20], [21, 20], [21, 21], [20, 21], [20, 20]])
    straddle = parcel("C", [[9, 1], [11, 1], [11, 2], [9, 2], [9, 1]])

    class FakeTransport:
        def get_json(self, url, timeout=600):
            if "uro-redevelop-ALL-5" in url:
                return {"features": [{"properties": {}, "geometry":
                         {"type": "MultiPolygon", "coordinates": square}}]}
            return {"features": [inside, outside, straddle]}

    geo = RS.GeoServerClient(transport=FakeTransport())
    unit = geo.unit_geometry("R000000", "測試段一小段")
    assert set(unit.candidates) == {"A", "C"}
    assert unit.candidates["A"] == pytest.approx(5 / 5)
    assert unit.candidates["C"] == pytest.approx(3 / 5)
    assert unit.section_parcels == {"A", "B", "C"}


# --- 2.8 failures degrade, never abort ---------------------------------------

def test_transport_failure_raises_source_unavailable_after_retries():
    calls = []

    class Failing:
        def post_form(self, url, params, timeout=90):
            calls.append(1)
            raise OSError("connection reset")

    client = RS.AshxClient(transport=Failing(), backoff=0.0)
    with pytest.raises(RS.SourceUnavailable):
        client.case_family("美仁段二小段", "0694", "0000")
    assert len(calls) == RS.MAX_ATTEMPTS  # retried, then refused


def test_pass_degrades_a_source_failure_to_residuals():
    """A dead API leaves every marked row excluded and named — the run continues."""
    marked = [{"recno": "1", "date": "2026/1/14", "district": "松山區",
               "name": "變更臺北市松山區美仁段二小段694地號等74筆(原54筆)土地都市更新事業計畫及擬訂權利變換計畫案",
               "land": "臺北市松山區美仁段二小段694、695、"}]

    class DeadAshx:
        def case_family(self, *a):
            raise RS.SourceUnavailable("gis.uro unreachable")

    outcome = recovery_pass.recover_marked_rows(
        marked, ashx=DeadAshx(), geoserver=None)
    assert outcome.recovered == []
    assert [r["recno"] for r in outcome.residuals] == ["1"]
    assert outcome.audit and "1" in outcome.audit[0]


# --- 2.8 the no-enumeration guard --------------------------------------------

def test_adapters_expose_no_enumeration_surface():
    """The product never sweeps sections or parcels: every method takes a key
    derived from a row's own cells or an already-known identity. The exploration's
    getSectionList enumeration stays a probe technique."""
    source = inspect.getsource(RS)
    assert "getSectionList" not in source
    for name in ("case_family", "case_top", "boundary", "section_parcels",
                 "unit_geometry"):
        assert callable(getattr(RS.AshxClient, name, None)) or \
            callable(getattr(RS.GeoServerClient, name, None))
