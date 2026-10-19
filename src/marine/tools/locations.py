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
    "thiruvananthapuram": "vizhinjam",
    # The landing-centre data spells these differently from everyday usage.
    "kollam": "quilon",  # the data's "Kollam" is a landing centre in Kozhikode district
    "quilon": "quilon",
    "alappuzha": "alleppeybeach",
    "alleppey": "alleppeybeach",
    "colachel": "kottilpadu",  # Colachel fishing harbour is at Kottilpadu
    "goa": "panaji malim",
    "panaji": "panaji malim",
    "balasore": "chandipur",
    "thondi": "tondi",
    "diu": "diu island",
    "ennore": "ennorekuppam",
    "malvan": "sindhudurg malvan",
    "mandapam": "mandapam south",
    "pamban": "pamban light house",
    "vypin": "vypeen",
    "karaikal": "karikal",
    "kodiyakkarai": "kodiyakarai",
    "vedaranyam": "vedaranniyam",
    "poompuhar": "poombuhar",
    "jafrabad": "jafarabad",
    "munambam": "munambamfh",
}


# Harbour names as written in Tamil / Devanagari / Malayalam script → the Latin name used
# above. Matched by STEM (see indic_stem) so a case ending does not matter: இராமேஸ்வரத்தில்
# ("in Rameswaram") contains the stem இராமேஸ்வர. Deterministic, so neither the demo nor the
# offline path depends on a model transliterating correctly.
INDIC_NAMES: dict[str, str] = {
    # Tamil
    "சென்னை": "chennai",
    "காசிமேடு": "kasimedu",
    "எண்ணூர்": "ennore",
    "பழவேற்காடு": "pulicat",
    "மாமல்லபுரம்": "mamallapuram",
    "கடலூர்": "cuddalore",
    "புதுச்சேரி": "puducherry",
    "பாண்டிச்சேரி": "puducherry",
    "காரைக்கால்": "karaikal",
    "பூம்புகார்": "poompuhar",
    "பழையாறு": "pazhayar",
    "நாகப்பட்டினம்": "nagapattinam",
    "நாகை": "nagapattinam",
    "வேதாரண்யம்": "vedaranyam",
    "கோடியக்கரை": "kodiyakkarai",
    "மல்லிப்பட்டினம்": "mallipattinam",
    "சேதுபாவாசத்திரம்": "sethubavachattram",
    "தொண்டி": "thondi",
    "மண்டபம்": "mandapam",
    "பாம்பன்": "pamban",
    "ராமேஸ்வரம்": "rameswaram",
    "இராமேஸ்வரம்": "rameswaram",
    "தூத்துக்குடி": "tuticorin",
    "குலசேகரப்பட்டினம்": "kulasekharapattinam",
    "கன்னியாகுமரி": "kanyakumari",
    "குளச்சல்": "colachel",
    "சின்னமுட்டம்": "chinnamuttom",
    "பாரதீப்": "paradip",
    "கொச்சி": "kochi",
    "திருவனந்தபுரம்": "thiruvananthapuram",
    "விழிஞ்ஞம்": "vizhinjam",
    # Devanagari
    "वेरावल": "veraval",
    "पोरबंदर": "porbandar",
    "ओखा": "okha",
    "मांगरोल": "mangrol",
    "जाफराबाद": "jafrabad",
    "जखौ": "jakhau",
    "मांडवी": "mandvi",
    "दीव": "diu",
    "दमन": "daman",
    "मुंबई": "mumbai",
    "बंबई": "mumbai",
    "ससून डॉक": "sassoon dock",
    "अलीबाग": "alibag",
    "रत्नागिरी": "ratnagiri",
    "मालवण": "malvan",
    "मालवन": "malvan",
    "गोवा": "goa",
    "कारवार": "karwar",
    "भटकल": "bhatkal",
    "मालपे": "malpe",
    "मंगलौर": "mangalore",
    "मंगलुरु": "mangalore",
    "मैंगलोर": "mangalore",
    "कोच्चि": "kochi",
    "कोच्ची": "kochi",
    "कोचीन": "kochi",
    "चेन्नई": "chennai",
    "रामेश्वरम": "rameswaram",
    "कन्याकुमारी": "kanyakumari",
    "तूतीकोरिन": "tuticorin",
    "थूथुकुडी": "tuticorin",
    "नागपट्टिनम": "nagapattinam",
    "विशाखापत्तनम": "visakhapatnam",
    "विशाखापट्टनम": "visakhapatnam",
    "विजाग": "visakhapatnam",
    "विज़ाग": "visakhapatnam",
    "काकीनाडा": "kakinada",
    "मछलीपट्टनम": "machilipatnam",
    "गोपालपुर": "gopalpur",
    "पारादीप": "paradip",
    "पारादिप": "paradip",
    "पाराद्वीप": "paradip",
    "पुरी": "puri",
    "बालासोर": "balasore",
    "दीघा": "digha",
    "पोर्ट ब्लेयर": "port blair",
    # Malayalam
    "കൊച്ചി": "kochi",
    "വൈപ്പിൻ": "vypin",
    "മുനമ്പം": "munambam",
    "ആലപ്പുഴ": "alappuzha",
    "നീണ്ടകര": "neendakara",
    "ശക്തികുളങ്ങര": "sakthikulangara",
    "കൊല്ലം": "kollam",
    "വിഴിഞ്ഞം": "vizhinjam",
    "തിരുവനന്തപുരം": "thiruvananthapuram",
    "പൊന്നാനി": "ponnani",
    "ബേപ്പൂർ": "beypore",
    "കോഴിക്കോട്": "kozhikode",
    "കണ്ണൂർ": "kannur",
}
_VIRAMA = ("்", "്")
_FINAL_MARKS = ("ം", "ൻ", "ർ", "ൾ", "ൽ", "ൺ")


def indic_stem(name: str) -> str:
    """Drop a final vowel-less consonant so inflected forms still contain the stem:
    கடலூர் → கடலூ (matches கடலூரில்), വിഴിഞ്ഞം → വിഴിഞ്ഞ (matches വിഴിഞ്ഞത്ത്). Hindi keeps
    postpositions as separate words (वेरावल से), so Devanagari names are used whole."""
    if any(0x0900 <= ord(c) <= 0x097F for c in name) or len(name) <= 4:
        return name
    if name.endswith(("டு", "று")):  # காசிமேடு → காசிமேட்டில், பழையாறு → பழையாற்றில்
        return name[:-2]
    if name.endswith(_VIRAMA):
        return name[:-2]
    if name.endswith(_FINAL_MARKS):
        return name[:-1]
    return name


INDIC_STEMS: list[tuple[str, str]] = sorted(
    {(indic_stem(k), v) for k, v in INDIC_NAMES.items()}, key=lambda kv: -len(kv[0])
)


_TOKEN_SPLIT = re.compile(r"[\s,.;:!?।॥\"'()\-]+")


def starts_a_word(text: str, key: str) -> bool:
    """`key` begins some word of `text` (a phrase must begin at a word). Indic case endings
    attach to the END of a word, so a prefix match finds இராமேஸ்வரத்தில் from இராமேஸ்வர
    without letting रात (night) match inside गुजरात, or कल (tomorrow) inside निकलना. A key
    ending in a space must be a whole word ("कल " does not match कलकत्ता)."""
    joined = " " + " ".join(t for t in _TOKEN_SPLIT.split(text) if t) + " "
    return (" " + key) in joined


def find_indic_place(text: str) -> str | None:
    """Latin name of the longest harbour stem found in Indic-script text, or None."""
    return next((latin for stem, latin in INDIC_STEMS if starts_a_word(text, stem)), None)


def _plain(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _norm(s: str) -> str:
    raw = s.strip()
    if re.search(r"[^\x00-\x7f]", raw):
        raw = find_indic_place(raw) or raw
    key = _plain(raw)
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
    # A data name taken literally beats an alias applied to another data name: "quilon" must
    # find the landing centre called Quilon, not the one called "Kollam" that the alias maps.
    by_name.update({_plain(c.name): c for c in cands})
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
    # Inside a longer landing-centre name ("Kasimedu" in "Kasimedu Fishing Harbour"), on word
    # boundaries only: a raw substring let "i have" match "vash[i have]li" (Vashi(Haveli)).
    single = " " not in key
    for n, c in by_name.items():
        words = n.split()
        if key in words or (
            len(key) >= 5
            and (f" {key} " in f" {n} " or (single and any(w.startswith(key) for w in words)))
        ):
            return ResolvedLocation(**c.model_dump(exclude={"kind"}), match="fuzzy", score=0.7)
    return None
