"""Tamil / Hindi / Malayalam without a model: deterministic planning and the localised
template. Most phrasings here are deliberately NOT in data/question_bank/bank.json — the bank
is the test set for the whole system and must not be what the vocabulary was fitted to.
No network, no model."""

from __future__ import annotations

import pytest

from marine.agents.indic import indic_plan
from marine.agents.localize import localized_template
from marine.agents.planner import Intent, detect_script, make_plan
from marine.agents.synthesis import Brief, verify
from marine.graph import ask
from marine.risk.thresholds import VesselClass
from marine.tools import ToolContext
from marine.tools.locations import find_indic_place, starts_a_word

T, M, ME = VesselClass.TRADITIONAL, VesselClass.MOTORISED, VesselClass.MECHANISED


@pytest.mark.parametrize(
    "q, intent, place, day, part, vessel, heading, speed",
    [
        # Tamil
        (
            "நாளை அதிகாலை ராமேஸ்வரத்தில் இருந்து கடலுக்குச் செல்லலாமா?",
            "safety",
            "Rameswaram",
            "tomorrow",
            "early_morning",
            None,
            None,
            None,
        ),
        (
            "இன்று இரவு சென்னை கடலில் காற்று எவ்வளவு?",
            "conditions",
            "Chennai",
            "today",
            "night",
            None,
            None,
            None,
        ),
        (
            "தூத்துக்குடிக்கு அருகே மீன் எங்கு கிடைக்கும்?",
            "pfz",
            "Thoothukudi|Tuticorin",
            "tomorrow",
            "morning",
            None,
            None,
            None,
        ),
        (
            "கன்னியாகுமரியில் இருந்து தென்மேற்கு நோக்கி 8 நாட் வேகத்தில் சென்றால் எல்லை எவ்வளவு தூரம்?",
            "boundary",
            "Kanyakumari",
            "tomorrow",
            "morning",
            None,
            225.0,
            8.0,
        ),
        (
            "விசைப்படகில் நாளை கடலூரில் இருந்து போகலாமா?",
            "safety",
            "Cuddalore",
            "tomorrow",
            "morning",
            ME,
            None,
            None,
        ),
        (
            "பாம்பனில் இருந்து மீன்பிடி மண்டலத்துக்கு வழி சொல்லுங்கள்",
            "route",
            "Pamban",
            "tomorrow",
            "morning",
            None,
            None,
            None,
        ),
        (
            "காசிமேட்டில் இருந்து நாளை மாலை வள்ளத்தில் போகலாமா?",
            "safety",
            "Kasimedu",
            "tomorrow",
            "evening",
            T,
            None,
            None,
        ),
        # Hindi
        (
            "परसों शाम ओखा से नाव ले जाना ठीक रहेगा?",
            "safety",
            "Okha",
            "day_after",
            "evening",
            None,
            None,
            None,
        ),
        (
            "मंगलौर के पास आज लहरें कितनी ऊँची हैं?",
            "conditions",
            "Mangalore",
            "today",
            "morning",
            None,
            None,
            None,
        ),
        (
            "रत्नागिरी से सबसे नज़दीकी मछली क्षेत्र का रास्ता बताओ",
            "route",
            "Ratnagiri",
            "tomorrow",
            "morning",
            None,
            None,
            None,
        ),
        (
            "क्या पोरबंदर से पश्चिम की ओर १२ नॉट पर चलने से सीमा पार होगी?",
            "boundary",
            "Porbandar",
            "tomorrow",
            "morning",
            None,
            270.0,
            12.0,
        ),
        (
            "विशाखापत्तनम के पास पानी का रंग हरा क्यों है?",
            "chlorophyll",
            "Visakhapatnam",
            "tomorrow",
            "morning",
            None,
            None,
            None,
        ),
        (
            "कल ट्रॉलर लेकर वेरावल से समुद्र में जाऊँ?",
            "safety",
            "Veraval",
            "tomorrow",
            "morning",
            ME,
            None,
            None,
        ),
        # Malayalam
        (
            "നാളെ പുലർച്ചെ നീണ്ടകരയിൽ നിന്ന് കടലിൽ പോകാമോ?",
            "safety",
            "Neendakara",
            "tomorrow",
            "early_morning",
            None,
            None,
            None,
        ),
        (
            "ഇന്ന് കൊല്ലം കടലിൽ തിരമാല എത്ര ഉയരം?",
            "conditions",
            "Quilon",
            "today",
            "morning",
            None,
            None,
            None,
        ),
    ],
)
def test_indic_questions_plan_without_a_model(q, intent, place, day, part, vessel, heading, speed):
    p = indic_plan(q)
    assert p is not None, q
    assert p.intent == intent and p.location
    assert any(name.lower() in p.location.name.lower() for name in place.split("|"))
    assert (p.day, p.part, p.vessel) == (day, part, vessel)
    assert (p.heading_deg, p.speed_kt) == (heading, speed)
    assert p.language == detect_script(q) and p.source == "fast_path"


def test_heading_in_degrees_and_speed_in_knots():
    p = indic_plan("நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?")
    assert p and p.intent == "safety" and (p.heading_deg, p.speed_kt) == (90.0, 8.0)
    p = indic_plan("पोरबंदर से २७० डिग्री पर १० नॉट से जाऊँ तो सीमा कितनी दूर?")
    assert p and (p.heading_deg, p.speed_kt) == (270.0, 10.0)


def test_words_inside_other_words_do_not_match():
    # रात (night) inside गुजरात, कल (tomorrow) inside निकलना — whole-word / word-start only.
    p = indic_plan("गुजरात के पोरबंदर से आज निकलना ठीक है?")
    assert p and p.intent == "safety" and (p.day, p.part) == ("today", "morning")
    # തിര (wave) begins തിരുവനന്തപുരം: a safety question from there is not about waves.
    p = indic_plan("തിരുവനന്തപുരത്ത് നിന്ന് നാളെ കടലിൽ പോകാമോ?")
    assert p and p.intent == "safety"
    assert not starts_a_word("कलकत्ता", "कल ")


def test_inflected_place_names_are_found_by_stem():
    assert find_indic_place("நாகப்பட்டினத்தில்") == "nagapattinam"
    assert find_indic_place("காசிமேட்டில்") == "kasimedu"
    assert find_indic_place("കൊല്ലത്ത്") == "kollam"
    assert find_indic_place("വിഴിഞ്ഞത്ത്") == "vizhinjam"
    assert find_indic_place("அலைபேசி") is None


def test_unknown_shapes_are_left_to_the_model():
    assert indic_plan("அலை உயரம் என்றால் என்ன?") is None  # general knowledge, no place
    assert indic_plan("मेरे फोन का रिचार्ज कैसे करूँ?") is None
    assert indic_plan("Is it safe off Kochi?") is None  # English has its own fast path


async def test_model_down_tamil_without_place_asks_for_the_harbour_in_tamil():
    p = await make_plan("நாளைக்கு கடல் எப்படி இருக்கும்?", None)
    assert p.intent == Intent.CLARIFY and p.model_unavailable
    assert detect_script(p.clarify_question) == "ta"


@pytest.mark.parametrize(
    "q", ["What is a potential fishing zone?", "அலை உயரம் என்றால் என்ன?", "PFZ क्या होता है?"]
)
async def test_model_down_explanations_are_not_answered_with_which_harbour(q):
    p = await make_plan(q, None)
    assert p.intent == Intent.CLARIFY and p.model_unavailable
    asks_for_place = ("Which harbour", "துறைமுகத்தில் இருந்து போகிறீர்கள்", "किस बंदरगाह")
    assert not any(a in p.clarify_question for a in asks_for_place)


async def test_model_down_off_topic_hindi_says_so_in_hindi():
    p = await make_plan("मेरे फोन का रिचार्ज कैसे करूँ?", None)
    assert p.intent == Intent.CLARIFY and p.model_unavailable
    assert detect_script(p.clarify_question) == "hi"


# -- end to end, network down, no model ------------------------------------------------------


@pytest.mark.parametrize(
    "q, lang",
    [
        ("நாளை காலை கொச்சியில் இருந்து கடலுக்குச் செல்லலாமா?", "ta"),
        ("क्या कल सुबह कोच्चि से समुद्र में जाना सुरक्षित है?", "hi"),
        ("നാളെ രാവിലെ കൊച്ചിയിൽ നിന്ന് കടലിൽ പോകാമോ?", "ml"),
    ],
)
async def test_offline_safety_answer_in_the_askers_language(network_down, q, lang):
    out = await ask(q, llm=None, ctx=ToolContext())
    ans = out["answer"]
    assert out["plan"].model_unavailable and out["verdict"] is not None
    assert ans.language == lang and detect_script(ans.text) == lang
    assert ans.verification.ok, ans.verification.unsupported
    assert ans.degradation  # rule 3: the answer says it is from the snapshot
    # The fixed English formats were all translated.
    for english in ("threshold", "Data note", "Not available", "craft off"):
        assert english not in ans.text, english


async def test_offline_hindi_route_answer_is_translated_and_verified(network_down):
    out = await ask("कोच्चि से मछली क्षेत्र तक का रास्ता बताओ", llm=None, ctx=ToolContext())
    ans = out["answer"]
    assert out["geo"].route and out["geo"].route.found
    assert ans.verification.ok and detect_script(ans.text) == "hi"
    for english in ("suggested route", "legs:", "navigation chart", "straight line"):
        assert english not in ans.text, english


async def test_offline_tamil_chlorophyll_answer_is_translated_and_verified(network_down):
    out = await ask("கொச்சி அருகே மீன் பிடிப்பு ஏன் குறைந்து வருகிறது?", llm=None, ctx=ToolContext())
    ans = out["answer"]
    assert out["plan"].intent == Intent.CHLOROPHYLL
    assert ans.verification.ok, ans.verification.unsupported
    assert "baseline" not in ans.text and "interpretation" not in ans.text


def test_localised_lines_keep_every_number():
    b = Brief(
        intent=Intent.SAFETY,
        language="ta",
        location="Rameswaram",
        window="Tue 20 Oct 05:00–12:00 IST",
        verdict="DO NOT SAIL",
        verdict_status="verdict",
        vessel="traditional",
        reasons=[
            "wind 28.5 kt ≥ no-go threshold 27 kt; gusts to 33.1 kt reach the no-go threshold",
            "visibility 1.4 km ≤ no-go threshold 2 km",
            "current heading crosses Sri Lanka - India in 42 min",
        ],
        conditions=["wave height 1.12 m [obs_1; x]"],
        boundary=[
            "position: inside India's EEZ; nearest maritime boundary: Sri Lanka - India "
            "(Sri Lanka) 14.6 km to the ESE"
        ],
        allowed_numbers={28.5, 27, 33.1, 1.4, 2, 42, 1.12, 14.6, 5, 12, 20},
    )
    text = localized_template(b)
    assert verify(text, b).ok
    for n in ("28.5", "27", "33.1", "1.4", "42", "1.12", "14.6"):
        assert n in text
    assert "threshold" not in text and "nearest maritime boundary" not in text
