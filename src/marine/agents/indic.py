"""Deterministic planning for Tamil, Hindi and Malayalam questions — no model needed.

The language model plans anything unusual, but with the network down (CLAUDE.md rule 3) a
fisherman asking in Tamil must still get an answer. This is the Indic counterpart of the
English fast path: keyword stems per intent, day and time words, boat words, a heading from a
compass word, a speed in knots, and harbour names written in Tamil, Devanagari and Malayalam
script mapped to the landing-centre names the resolver knows (`tools.locations.INDIC_NAMES`).

Matching is by substring on STEMS, because Tamil and Malayalam attach case endings to the
word: "நாகப்பட்டினத்தில்" (at Nagapattinam) contains the stem "நாகப்பட்டின". Hindi keeps
postpositions as separate words (से, के), so whole words work there.

The vocabulary was written from general fishing usage, not from the question bank; the bank
is the test set (see tests/test_indic.py for phrasings that are not in the bank). A native
speaker should review it — logged in docs/BUILD_LOG.md.
"""

from __future__ import annotations

import re

from marine.agents.planner import (
    NEEDS_LOCATION,
    Day,
    DayPart,
    Intent,
    Plan,
    detect_script,
)
from marine.risk.thresholds import VesselClass
from marine.tools import LocationQuery, ResolvedLocation, resolve_location
from marine.tools.locations import find_indic_place, starts_a_word

SUPPORTED = ("ta", "hi", "ml")

# Checked in this order — the same priority as the English fast path: a route phrase first,
# then fish-finding, then safety, boundary, productivity, conditions.
KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.ROUTE: (
        # ta: way, path, how to go/reach
        "வழி",
        "பாதை",
        "எப்படி செல்வது",
        "எப்படி போவது",
        "எப்படி அடைவது",
        # hi
        "रास्ता",
        "रास्ते",
        "मार्ग",
        "कैसे पहुँच",
        "कैसे पहुंच",
        # ml
        "വഴി",
        "റൂട്ട്",
    ),
    Intent.PFZ: (
        "மீன் எங்கே",
        "மீன் எங்கு",
        "மீன் கிடைக்கும்",
        "மீன்பிடி மண்டல",
        "மீன் மண்டல",
        "மீன்பிடி பகுதி",
        "மீன் அதிகம்",
        "मछली कहाँ",
        "मछली कहां",
        "मछली मिल",
        "मछली वाले क्षेत्र",
        "मछली पकड़ने का क्षेत्र",
        "मत्स्य क्षेत्र",
        "मछली ज़्यादा",
        "मछली ज्यादा",
        "മീൻ എവിടെ",
        "മത്സ്യ മേഖല",
        "മീൻ കിട്ടും",
        "മീൻ ലഭിക്കും",
        "pfz",
        "PFZ",
    ),
    Intent.SAFETY: (
        "போகலாமா",
        "செல்லலாமா",
        "போகலாம்",
        "பாதுகாப்பா",
        "பாதுகாப்பான",
        "ஆபத்",
        "போகக்கூடாதா",
        "போவது சரியா",
        "கடலுக்கு போக",
        "கடலுக்குச் செல்",
        "सुरक्षित",
        "खतरा",
        "ख़तरा",
        "खतरनाक",
        "जाना ठीक",
        "जा सकत",
        "जाऊं",
        "जाऊँ",
        "जाएं",
        "निकल",
        "नाव ले जा",
        "समुद्र में जा",
        "പോകാമോ",
        "പോകാൻ പറ്റുമോ",
        "സുരക്ഷിത",
        "അപകട",
    ),
    Intent.BOUNDARY: (
        "எல்லை",
        "இலங்கை",
        "கைது",
        "தாண்டு",
        "सीमा",
        "बॉर्डर",
        "पाकिस्तान",
        "श्रीलंका",
        "गिरफ्तार",
        "गिरफ़्तार",
        "पार कर",
        "അതിർത്തി",
        "ശ്രീലങ്ക",
        "അറസ്റ്റ്",
    ),
    Intent.CHLOROPHYLL: (
        "பிடிப்பு குறை",
        "குறைந்து வருகிறது",
        "மீன் குறை",
        "நீரின் நிறம்",
        "நிறம் மாறி",
        "பச்சை நிற",
        "पानी का रंग",
        "रंग बदल",
        "मछली कम",
        "कम मछली",
        "पकड़ कम",
        "हरा पानी",
        "മീൻ കുറ",
        "വെള്ളത്തിന്റെ നിറം",
        "നിറം മാറി",
    ),
    Intent.CONDITIONS: (
        "அலை ",
        "அலைக",
        "அலைய",
        "காற்று",
        "நீரோட்ட",
        "மூடுபனி",
        "பார்வை",
        "வெப்பநிலை",
        "கடல் எப்படி",
        "लहर",
        "हवा",
        "धारा",
        "कोहरा",
        "दृश्यता",
        "तापमान",
        "समुद्र कैसा",
        "मौसम कैसा",
        "തിര ",
        "തിരമാല",
        "തിരയുടെ",
        "കാറ്റ്",
        "ഒഴുക്ക്",
        "മൂടൽമഞ്ഞ്",
        "കടൽ എങ്ങനെ",
    ),
}
# Bare intent order as checked; PFZ before SAFETY because "where will I find fish" questions
# often also say "go" ("மீன் பிடிக்க எங்கே போகலாம்?").
ORDER = (
    Intent.ROUTE,
    Intent.PFZ,
    Intent.SAFETY,
    Intent.BOUNDARY,
    Intent.CHLOROPHYLL,
    Intent.CONDITIONS,
)

# Dict order is priority: "day after tomorrow" before "tomorrow".
DAY_WORDS: dict[str, Day] = {
    "நாளை மறுநாள்": "day_after",
    "நாளைக்கு மறுநாள்": "day_after",
    "நாளை": "tomorrow",
    "இன்று": "today",
    "இன்னைக்கு": "today",
    "இப்போது": "today",
    "இப்ப": "today",
    "परसों": "day_after",
    "कल ": "tomorrow",  # also "yesterday", but a forward-looking question means tomorrow
    "आज": "today",
    "अभी": "today",
    "മറ്റന്നാൾ": "day_after",
    "നാളെ": "tomorrow",
    "ഇന്ന്": "today",
    "ഇപ്പോൾ": "today",
}
PART_WORDS: dict[str, DayPart] = {
    "அதிகாலை": "early_morning",
    "விடியற்காலை": "early_morning",
    "காலை": "morning",
    "மதியம்": "afternoon",
    "மாலை": "evening",
    "இரவு": "night",
    "तड़के": "early_morning",
    "भोर": "early_morning",
    "सुबह-सुबह": "early_morning",
    "सुबह": "morning",
    "दोपहर": "afternoon",
    "शाम": "evening",
    "रात": "night",
    "പുലർച്ചെ": "early_morning",
    "രാവിലെ": "morning",
    "ഉച്ച": "afternoon",
    "വൈകുന്നേരം": "evening",
    "രാത്രി": "night",
}
VESSEL_WORDS: dict[str, VesselClass] = {
    "கட்டுமர": VesselClass.TRADITIONAL,
    "வள்ள": VesselClass.TRADITIONAL,
    "நாட்டுப்பட": VesselClass.TRADITIONAL,
    "நாட்டுப் பட": VesselClass.TRADITIONAL,
    "பைபர் பட": VesselClass.TRADITIONAL,
    "விசைப்பட": VesselClass.MECHANISED,
    "விசைப் பட": VesselClass.MECHANISED,
    "இழுவை": VesselClass.MECHANISED,
    "डोंगी": VesselClass.TRADITIONAL,
    "छोटी नाव": VesselClass.TRADITIONAL,
    "मोटर": VesselClass.MOTORISED,
    "ट्रॉलर": VesselClass.MECHANISED,
    "ट्रालर": VesselClass.MECHANISED,
    "വള്ളം": VesselClass.TRADITIONAL,
    "ട്രോളർ": VesselClass.MECHANISED,
}
# Longest first so "வடகிழக்கு" (north-east) wins over "கிழக்கு" (east).
COMPASS: dict[str, float] = dict(
    sorted(
        {
            "வடகிழக்கு": 45,
            "தென்கிழக்கு": 135,
            "தென்மேற்கு": 225,
            "வடமேற்கு": 315,
            "வடக்கு": 0,
            "கிழக்கு": 90,
            "தெற்கு": 180,
            "மேற்கு": 270,
            "उत्तर-पूर्व": 45,
            "पूर्वोत्तर": 45,
            "दक्षिण-पूर्व": 135,
            "दक्षिण-पश्चिम": 225,
            "उत्तर-पश्चिम": 315,
            "उत्तर": 0,
            "पूर्व": 90,
            "दक्षिण": 180,
            "पश्चिम": 270,
            "വടക്കുകിഴക്ക്": 45,
            "തെക്കുകിഴക്ക്": 135,
            "തെക്കുപടിഞ്ഞാറ്": 225,
            "വടക്കുപടിഞ്ഞാറ്": 315,
            "വടക്ക്": 0,
            "കിഴക്ക്": 90,
            "തെക്ക്": 180,
            "പടിഞ്ഞാറ്": 270,
        }.items(),
        key=lambda kv: -len(kv[0]),
    )
)
_DIGITS = {
    ord(c): str(i)
    for digits in ("०१२३४५६७८९", "௦௧௨௩௪௫௬௭௮௯", "൦൧൨൩൪൫൬൭൮൯")
    for i, c in enumerate(digits)
}
_DEGREES = re.compile(r"(\d{1,3})\s*(?:டிகிரி|डिग्री|ഡിഗ്രി|°|degrees?)")
_SPEED = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:நாட்|नॉट|नाट|നോട്ട്|knots?|kt)")
_LENGTH = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:மீட்டர்|மீ\b|मीटर|മീറ്റർ|m\b)")


def find_place(text: str) -> tuple[str, ResolvedLocation] | None:
    """The harbour named in the text (longest stem in the shared table), resolved."""
    latin = find_indic_place(text)
    r = resolve_location(LocationQuery(name=latin)) if latin else None
    return (r.name, r) if r else None


def detect_intent(text: str) -> Intent | None:
    return next((i for i in ORDER if any(starts_a_word(text, k) for k in KEYWORDS[i])), None)


def _first(table: dict, text: str):
    return next((v for k, v in table.items() if starts_a_word(text, k)), None)


def indic_plan(query: str) -> Plan | None:
    """A Plan for a Tamil / Hindi / Malayalam question in the common shapes, else None (the
    model, if reachable, plans the rest)."""
    lang = detect_script(query)
    if lang not in SUPPORTED:
        return None
    q = query.translate(_DIGITS)
    intent = detect_intent(q)
    if intent is None:
        return None
    loc = find_place(q)
    if intent in NEEDS_LOCATION and loc is None:
        return None
    vessel = _first(VESSEL_WORDS, q)
    m = _LENGTH.search(q)
    if vessel is None and m:
        vessel = VesselClass.from_length_m(float(m.group(1)))
    sm = _SPEED.search(q)
    hm = _DEGREES.search(q)
    heading = (
        float(hm.group(1)) % 360
        if hm
        else _first(COMPASS, q)
        if (sm or intent == Intent.BOUNDARY)
        else None
    )
    return Plan(
        language=lang,
        english_query=query,
        intent=intent,
        location_name=loc[0] if loc else None,
        location=loc[1] if loc else None,
        day=_first(DAY_WORDS, q) or "tomorrow",
        part=_first(PART_WORDS, q) or "morning",
        vessel=vessel,
        heading_deg=float(heading) if heading is not None and sm else None,
        speed_kt=float(sm.group(1)) if sm else None,
        source="fast_path",
    )


# -- what to say when the model is needed but unreachable ----------------------------------

CLARIFY_PLACE = {
    "en": "Which harbour or landing centre are you going from? For example: 'Is it safe off "
    "Kochi tomorrow morning?'",
    "ta": "எந்தத் துறைமுகத்தில் இருந்து போகிறீர்கள்? உதாரணம்: 'நாளை காலை கொச்சியில் இருந்து கடலுக்கு போகலாமா?'",
    "hi": "आप किस बंदरगाह या घाट से जा रहे हैं? जैसे: 'क्या कल सुबह वेरावल से समुद्र में जाना सुरक्षित है?'",
    "ml": "ഏത് തുറമുഖത്തു നിന്നാണ് പോകുന്നത്? ഉദാഹരണം: 'നാളെ രാവിലെ കൊച്ചിയിൽ നിന്ന് കടലിൽ പോകാമോ?'",
}
MODEL_DOWN = {
    "en": "The language model is unavailable ({why}), so I can only answer the common "
    "questions right now: safety, waves and wind, fishing zones, the border and routes, for a "
    "named harbour. For example: 'Is it safe off Kochi tomorrow morning?'",
    "ta": "மொழி மாதிரி இப்போது கிடைக்கவில்லை ({why}). இப்போது ஒரு துறைமுகத்தின் பெயருடன் "
    "கேட்கும் கேள்விகளுக்கு மட்டும் பதில் தர முடியும்: பாதுகாப்பு, அலை, காற்று, மீன் "
    "கிடைக்கும் பகுதி, எல்லை, வழி. உதாரணம்: 'நாளை காலை கொச்சியில் இருந்து கடலுக்கு போகலாமா?'",
    "hi": "भाषा मॉडल अभी उपलब्ध नहीं है ({why})। अभी मैं किसी बंदरगाह के नाम के साथ पूछे गए "
    "आम सवालों का ही जवाब दे सकता हूँ: सुरक्षा, लहर, हवा, मछली क्षेत्र, सीमा और रास्ता। जैसे: "
    "'क्या कल सुबह वेरावल से समुद्र में जाना सुरक्षित है?'",
    "ml": "ഭാഷാ മോഡൽ ഇപ്പോൾ ലഭ്യമല്ല ({why}). ഒരു തുറമുഖത്തിന്റെ പേരോടെ ചോദിക്കുന്ന "
    "സാധാരണ ചോദ്യങ്ങൾക്ക് മാത്രമേ ഇപ്പോൾ ഉത്തരം നൽകാനാകൂ: സുരക്ഷ, തിര, കാറ്റ്, മത്സ്യ മേഖല, "
    "അതിർത്തി, വഴി. ഉദാഹരണം: 'നാളെ രാവിലെ കൊച്ചിയിൽ നിന്ന് കടലിൽ പോകാമോ?'",
}


# "What is …" / "what does … mean" — asks for an explanation, not a place's forecast.
EXPLAIN = (
    "what is",
    "what are",
    "what does",
    "what do",
    "meaning of",
    "explain",
    "why is",
    "why do",
    "why does",
    "என்றால் என்ன",
    "என்ன அர்த்தம்",
    "ஏன்",
    "क्या होता है",
    "क्या है",
    "मतलब",
    "क्यों",
    "എന്താണ്",
    "എന്ന് പറഞ്ഞാൽ",
    "എന്തുകൊണ്ട്",
)


def offline_clarify(query: str, why: str) -> Plan:
    """The reply when the deterministic paths could not plan the question and the model is
    unreachable — in the asker's language. If the question clearly asks for live data but
    names no place, ask for the harbour; otherwise (an explanation, small talk, anything
    unrecognised) say what can be answered without the model."""
    lang = detect_script(query)
    q = query.lower().translate(_DIGITS)
    if lang == "en":
        from marine.agents.planner import KEYWORDS as EN_KEYWORDS

        intent = next((i for i, ws in EN_KEYWORDS.items() if any(w in q for w in ws)), None)
    else:
        intent = detect_intent(q)
    explaining = any(e in q for e in EXPLAIN)
    needs_place = intent is not None and intent in NEEDS_LOCATION and not explaining
    table = CLARIFY_PLACE if needs_place else MODEL_DOWN
    short = why.split(" (")[0]  # "gemini: host unreachable", not the breaker's timings
    text = table.get(lang, table["en"]).format(why=short)
    return Plan(language=lang, english_query=query, intent=Intent.CLARIFY, clarify_question=text)
