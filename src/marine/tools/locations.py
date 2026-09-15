"""Resolve a place name to coordinates: test harbours first, then INCOIS's 1223 landing
centres (static, committed). No geocoding API — one less thing to fail in a demo."""

from __future__ import annotations

import difflib
import json
import re
from functools import lru_cache

from pydantic import BaseModel, Field

from marine.config import STATIC_DIR
from marine.fixtures import HARBOURS, KNOWN_PORTS


class LocationQuery(BaseModel):
    name: str = Field(min_length=1, description="Harbour, landing centre or town, any spelling")


class ResolvedLocation(BaseModel):
    name: str
    lat: float
    lon: float
    sector_id: str | None = None  # INCOIS PFZ sector, e.g. SEC005
    sector_name: str | None = None
    district: str | None = None
    match: str  # "harbour" | "landing_centre" | "fuzzy"
    score: float  # 1.0 exact


class Candidate(BaseModel):
    name: str
    lat: float
    lon: float
    sector_id: str | None
    sector_name: str | None
    district: str | None
    kind: str


# Alternate / colloquial names → the name the data uses.
ALIASES: dict[str, str] = {
    "cochin": "kochi",
    "ernakulam": "kochi",
    "madras": "chennai",
    "bombay": "sassoon dock",
    "mumbai": "sassoon dock",
    "vizag": "visakhapatnam",
    "trivandrum": "vizhinjam",
    "thoothukudi": "tuticorin",
    "calicut": "beypore",
    "kozhikode": "beypore",
    "pondicherry": "puducherry",
    "paradeep": "paradip",
    "port blair": "port blair",
    "portblair": "port blair",
}


def _norm(s: str) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return ALIASES.get(key, key)


@lru_cache(maxsize=1)
def candidates() -> list[Candidate]:
    out = [
        Candidate(
            name=n.replace("_", " ").title(),
            lat=lat,
            lon=lon,
            sector_id=None,
            sector_name=None,
            district=None,
            kind="harbour",
        )
        for n, (lat, lon) in {**KNOWN_PORTS, **HARBOURS}.items()
    ]
    data = json.loads((STATIC_DIR / "incois_landing_centres.geojson").read_text(encoding="utf-8"))
    for f in data["features"]:
        p = f["properties"]
        out.append(
            Candidate(
                name=str(p.get("LC_NAME") or "").strip(),
                lat=float(p["LATITUDE"]),
                lon=float(p["LONGITUDE"]),
                sector_id=p.get("SECTOR_ID"),
                sector_name=(p.get("SECTOR_NAM") or "").title() or None,
                district=(p.get("DIST_NAME") or "").strip() or None,
                kind="landing_centre",
            )
        )
    # Landing centres first, harbours last: a test harbour wins a name clash.
    out = [c for c in out if c.name]
    return [c for c in out if c.kind != "harbour"] + [c for c in out if c.kind == "harbour"]


def resolve_location(q: LocationQuery) -> ResolvedLocation | None:
    key = _norm(q.name)
    if not key:
        return None
    cands = candidates()
    by_name = {_norm(c.name): c for c in cands}
    if key in by_name:
        c = by_name[key]
        return ResolvedLocation(**c.model_dump(exclude={"kind"}), match=c.kind, score=1.0)
    # Fuzzy: close spellings ("Cochin" → no; "Kochi" yes; "Vypin" → "Vypeen").
    names = list(by_name)
    best = difflib.get_close_matches(key, names, n=1, cutoff=0.7)
    # Guard: the first three letters must agree, or "Rameswaram" becomes "Kameshwaram".
    if best and best[0][:3] == key[:3]:
        c = by_name[best[0]]
        score = difflib.SequenceMatcher(None, key, best[0]).ratio()
        return ResolvedLocation(
            **c.model_dump(exclude={"kind"}), match="fuzzy", score=round(score, 2)
        )
    # Substring inside a longer landing-centre name ("Kasimedu" in "Kasimedu Fishing Harbour").
    for n, c in by_name.items():
        if key in n.split() or (len(key) >= 5 and key in n):
            return ResolvedLocation(**c.model_dump(exclude={"kind"}), match="fuzzy", score=0.7)
    return None
