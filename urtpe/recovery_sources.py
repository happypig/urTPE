# -*- coding: utf-8 -*-
"""The two HTTP surfaces of truncated-row recovery (tasks 4.2 and 4.3).

Keyed lookups only — every request is keyed by a section+parcel from a row's own
surviving cells or by an already-known case id. There is no enumeration method:
the exploration's section-enumeration sweep (``probes/uro_recover67.py``) stays
a probe technique, never a product path (spec: recovery makes no enumeration
requests).

Measured behaviour baked in (poc_findings.md T5/T8/T10, design D-H/D-I):
* gis.uro shows no WAF at ~4 req/s; one transient read timeout occurred in ~300
  requests, so every call retries ``MAX_ATTEMPTS`` times with backoff and then
  raises :class:`SourceUnavailable`, which the recovery pass turns into a
  residual — a dead API never aborts the run;
* the GeoServer boundary layer (``uro-redevelop-ALL-5``) is R-form only — the
  pass never queries a numeric id, which the probes measured as 0 features on
  every probed layer;
* CQL BBOX evaluates in native TWD97 meters (the SRS trap), so the section pull
  takes the whole 段/小段 and containment is tested in-process (D-H).
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

MAX_ATTEMPTS = 4
DEFAULT_BACKOFF = 3.0
REQUEST_TIMEOUT = 90
WFS_TIMEOUT = 600
ASHX_BASE = "https://gis.uro.taipei/"
WFS_URL = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SECTION_MAX_FEATURES = 3000  # a whole 段/小段 stays under this (measured: 1076, 1033)


class SourceUnavailable(RuntimeError):
    """The city's API did not answer after the retries; the row becomes residual."""


def _post_form(url: str, params: dict, timeout: int = REQUEST_TIMEOUT) -> str:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _get_json(url: str, timeout: int = WFS_TIMEOUT) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _retry(fn, *args, backoff: float = DEFAULT_BACKOFF):
    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return fn(*args)
        except (TimeoutError, urllib.error.URLError, OSError,
                json.JSONDecodeError) as exc:  # transient city-side failures
            last = exc
            if backoff:
                time.sleep(backoff * (attempt + 1))
    raise SourceUnavailable(f"{fn.__name__} failed {MAX_ATTEMPTS}x: {last}")


def parse_family_body(body: str) -> list[dict]:
    """Get_updcase_list's body -> candidate dicts (family rows, no dates yet)."""
    rows = json.loads(body) if (body or "").strip() else []
    out = []
    for r in rows:
        m = re.search(r"case_id=(\d+)", r.get("details") or "")
        out.append({
            "case_id": str(r.get("case_id") or ""),
            "api_case_id": m.group(1) if m else "",
            "schedule": str(r.get("schedule") or ""),
            "case_name": str(r.get("case_name") or ""),
            "uro_chk_date": "",
            "uro_chk_date2": "",
        })
    return out


def parse_top_body(body: str) -> dict:
    """get_project168_top's body -> the case dict; an empty list means no data."""
    data = json.loads(body)
    return data[0] if isinstance(data, list) and data else {}


@dataclass
class UnitGeometry:
    """One unit's geometry context: membership candidates and the section cadastre."""

    candidates: dict[str, float] = field(default_factory=dict)   # land_no -> vertex fraction
    section_parcels: set[str] = field(default_factory=set)


class AshxClient:
    """``gis.uro.taipei/ashx/`` keyed lookups (task 4.2)."""

    def __init__(self, base_url: str = ASHX_BASE, transport=None,
                 backoff: float = DEFAULT_BACKOFF):
        self._base = base_url
        # transport: test seam with post_form(url, params, timeout) -> str
        self._transport = transport
        self._backoff = backoff

    def _post(self, name: str, params: dict) -> str:
        url = self._base + "ashx/" + name
        if self._transport is not None:
            # the transport seam retries like the real path, so a test double
            # exercises the same degradation the live client has
            return _retry(self._transport.post_form, url, params, REQUEST_TIMEOUT,
                          backoff=self._backoff)
        return _retry(_post_form, url, params, backoff=self._backoff)

    def case_family(self, sectstr: str, mono: str, suno: str) -> list[dict]:
        """The case family touching one parcel — the row's own land core (D-B)."""
        body = self._post("Get_updcase_list.ashx",
                          {"qitem": "qland", "sectstr": sectstr,
                           "monobuf": mono, "sunobuf": suno})
        return parse_family_body(body)

    def case_top(self, case_id: str) -> dict:
        """One case's header: the approval dates live in uro_chk_date/uro_chk_date2."""
        return parse_top_body(self._post("get_project168_top.ashx",
                                         {"case_id": case_id}))


def _geom_polys(geometry: dict) -> list:
    coords = geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return coords
    return [coords]


def _pip(x: float, y: float, polys: list) -> bool:
    """Even-odd point-in-polygon over every ring of every polygon part."""
    inside = False
    for poly in polys:
        for ring in poly:
            n = len(ring)
            j = n - 1
            crossing = False
            for i in range(n):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    crossing = not crossing
                j = i
            if crossing:
                inside = not inside
    return inside


def _vertex_fraction(geometry: dict, polys: list) -> float:
    """The share of a parcel's ring vertices strictly inside the boundary.

    ≥1 vertex inside makes the parcel a candidate (T8); centroid-in is NOT a
    containment signal — 17 far parcels measure centroid-in with zero vertices
    inside, all boundary artifacts (poc_findings.md T8).
    """
    n_in = n_tot = 0
    for poly in _geom_polys(geometry):
        for ring in poly:
            for x, y in ring:
                n_tot += 1
                if _pip(x, y, polys):
                    n_in += 1
    return (n_in / n_tot) if n_tot else 0.0


class GeoServerClient:
    """UDD GeoServer WFS keyed lookups (task 4.3, design D-H)."""

    def __init__(self, wfs_url: str = WFS_URL, transport=None,
                 backoff: float = DEFAULT_BACKOFF):
        self._wfs = wfs_url
        self._transport = transport
        self._backoff = backoff

    def _get(self, params: dict) -> dict:
        query = dict(service="WFS", request="GetFeature", version="1.1.0",
                     outputFormat="json", srsName="EPSG:4326", **params)
        url = f"{self._wfs}?{urllib.parse.urlencode(query)}"
        if self._transport is not None:
            return _retry(self._transport.get_json, url, WFS_TIMEOUT,
                          backoff=self._backoff)
        return _retry(_get_json, url, backoff=self._backoff)

    def boundary(self, case_id: str) -> list:
        """Every polygon carried under ``ID='<case>'`` (R089305 returns two)."""
        data = self._get({"typename": "Taipei:uro-redevelop-ALL-5",
                          "cql_filter": f"ID='{case_id}'"})
        polys: list = []
        for feat in data.get("features", []):
            polys.extend(_geom_polys(feat["geometry"]))
        return polys

    def section_parcels(self, sect_name: str) -> list[dict]:
        """The whole 段/小段 from LAND-ALL-TWD97 — never a bbox filter (D-H)."""
        data = self._get({"typename": "Taipei:LAND-ALL-TWD97",
                          "maxFeatures": str(SECTION_MAX_FEATURES),
                          "cql_filter": f"sect_name='{sect_name}'"})
        return data.get("features", [])

    def unit_geometry(self, case_id: str, sect_name: str) -> UnitGeometry:
        """Candidates (≥1 vertex inside, union over returned features) + cadastre."""
        polys = self.boundary(case_id)
        feats = self.section_parcels(sect_name)
        candidates: dict[str, float] = {}
        parcels: set[str] = set()
        for feat in feats:
            land = str(feat["properties"]["land_no"])
            parcels.add(land)
            frac = _vertex_fraction(feat["geometry"], polys)
            if frac > 0:
                candidates[land] = frac
        return UnitGeometry(candidates=candidates, section_parcels=parcels)
