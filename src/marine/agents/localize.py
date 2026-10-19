"""The deterministic template answer in Tamil, Hindi and Malayalam.

When the model is unreachable, the answer is built from the brief without it (CLAUDE.md rule
3). The brief's lines are produced by our own code in a small set of fixed English formats,
so each format is matched here and rewritten in the asker's language. Every number is carried
across exactly as written, so the verifier treats the result exactly as it treats the English
template: nothing new can enter. A line whose format is not recognised is kept in English —
untranslated is better than paraphrased.

The phrasing was written for this project and must be reviewed by native speakers before it
goes in front of fishermen (logged in docs/BUILD_LOG.md).
"""

from __future__ import annotations

import re

LANGS = ("ta", "hi", "ml")

COMPASS = {
    "ta": {
        "N": "வடக்கு",
        "NNE": "வடக்கு-வடகிழக்கு",
        "NE": "வடகிழக்கு",
        "ENE": "கிழக்கு-வடகிழக்கு",
        "E": "கிழக்கு",
        "ESE": "கிழக்கு-தென்கிழக்கு",
        "SE": "தென்கிழக்கு",
        "SSE": "தெற்கு-தென்கிழக்கு",
        "S": "தெற்கு",
        "SSW": "தெற்கு-தென்மேற்கு",
        "SW": "தென்மேற்கு",
        "WSW": "மேற்கு-தென்மேற்கு",
        "W": "மேற்கு",
        "WNW": "மேற்கு-வடமேற்கு",
        "NW": "வடமேற்கு",
        "NNW": "வடக்கு-வடமேற்கு",
    },
    "hi": {
        "N": "उत्तर",
        "NNE": "उत्तर-उत्तरपूर्व",
        "NE": "उत्तर-पूर्व",
        "ENE": "पूर्व-उत्तरपूर्व",
        "E": "पूर्व",
        "ESE": "पूर्व-दक्षिणपूर्व",
        "SE": "दक्षिण-पूर्व",
        "SSE": "दक्षिण-दक्षिणपूर्व",
        "S": "दक्षिण",
        "SSW": "दक्षिण-दक्षिणपश्चिम",
        "SW": "दक्षिण-पश्चिम",
        "WSW": "पश्चिम-दक्षिणपश्चिम",
        "W": "पश्चिम",
        "WNW": "पश्चिम-उत्तरपश्चिम",
        "NW": "उत्तर-पश्चिम",
        "NNW": "उत्तर-उत्तरपश्चिम",
    },
    "ml": {
        "N": "വടക്ക്",
        "NNE": "വടക്ക്-വടക്കുകിഴക്ക്",
        "NE": "വടക്കുകിഴക്ക്",
        "ENE": "കിഴക്ക്-വടക്കുകിഴക്ക്",
        "E": "കിഴക്ക്",
        "ESE": "കിഴക്ക്-തെക്കുകിഴക്ക്",
        "SE": "തെക്കുകിഴക്ക്",
        "SSE": "തെക്ക്-തെക്കുകിഴക്ക്",
        "S": "തെക്ക്",
        "SSW": "തെക്ക്-തെക്കുപടിഞ്ഞാറ്",
        "SW": "തെക്കുപടിഞ്ഞാറ്",
        "WSW": "പടിഞ്ഞാറ്-തെക്കുപടിഞ്ഞാറ്",
        "W": "പടിഞ്ഞാറ്",
        "WNW": "പടിഞ്ഞാറ്-വടക്കുപടിഞ്ഞാറ്",
        "NW": "വടക്കുപടിഞ്ഞാറ്",
        "NNW": "വടക്ക്-വടക്കുപടിഞ്ഞാറ്",
    },
}
UNITS = {
    "ta": {
        "m": "மீ",
        "km": "கி.மீ",
        "kt": "நாட்",
        "s": "வினாடி",
        "deg": "°",
        "degC": "°C",
        "min": "நிமிடம்",
    },
    "hi": {
        "m": "मी.",
        "km": "कि.मी.",
        "kt": "नॉट",
        "s": "सेकंड",
        "deg": "°",
        "degC": "°C",
        "min": "मिनट",
    },
    "ml": {
        "m": "മീ",
        "km": "കി.മീ",
        "kt": "നോട്ട്",
        "s": "സെക്കൻഡ്",
        "deg": "°",
        "degC": "°C",
        "min": "മിനിറ്റ്",
    },
}
PARAMS = {
    "ta": {
        "wave height": "அலை உயரம்",
        "wave period": "அலை இடைவெளி",
        "swell height": "நீள் அலை உயரம்",
        "swell period": "நீள் அலை இடைவெளி",
        "wind": "காற்றின் வேகம்",
        "gusts": "திடீர் காற்று",
        "wind direction": "காற்று வரும் திசை",
        "visibility": "பார்வைத் தூரம்",
        "sea temperature": "கடல் நீர் வெப்பநிலை",
        "current": "நீரோட்ட வேகம்",
        "current direction": "நீரோட்டத் திசை",
        "chlorophyll-a": "பச்சையம் (chlorophyll-a)",
        "steepness": "அலைச் செங்குத்து",
        "lightning": "மின்னல்",
        "cyclone": "புயல்",
    },
    "hi": {
        "wave height": "लहर की ऊँचाई",
        "wave period": "लहर अंतराल",
        "swell height": "स्वेल (लंबी लहर) की ऊँचाई",
        "swell period": "स्वेल अंतराल",
        "wind": "हवा की रफ़्तार",
        "gusts": "हवा के झोंके",
        "wind direction": "हवा की दिशा",
        "visibility": "दृश्यता",
        "sea temperature": "समुद्र का तापमान",
        "current": "धारा की रफ़्तार",
        "current direction": "धारा की दिशा",
        "chlorophyll-a": "क्लोरोफिल-a",
        "steepness": "लहर की ढलान",
        "lightning": "बिजली (तड़ित)",
        "cyclone": "चक्रवात",
    },
    "ml": {
        "wave height": "തിരമാലയുടെ ഉയരം",
        "wave period": "തിര ഇടവേള",
        "swell height": "ഓളത്തിര ഉയരം",
        "swell period": "ഓളത്തിര ഇടവേള",
        "wind": "കാറ്റിന്റെ വേഗം",
        "gusts": "ശക്തമായ കാറ്റ്",
        "wind direction": "കാറ്റിന്റെ ദിശ",
        "visibility": "കാഴ്ചദൂരം",
        "sea temperature": "കടൽ ജല താപനില",
        "current": "ഒഴുക്കിന്റെ വേഗം",
        "current direction": "ഒഴുക്കിന്റെ ദിശ",
        "chlorophyll-a": "ക്ലോറോഫിൽ-a",
        "steepness": "തിരയുടെ ചരിവ്",
        "lightning": "ഇടിമിന്നൽ",
        "cyclone": "ചുഴലിക്കാറ്റ്",
    },
}
# What could not be checked: gap variable names → words.
GAPS = {
    "ta": {
        "lightning": "மின்னல்",
        "cyclone": "புயல்",
        "chlorophyll": "பச்சையம்",
        "disagreement": "தரவு மூலங்களுக்கிடையே முரண்பாடு",
    },
    "hi": {
        "lightning": "बिजली (तड़ित)",
        "cyclone": "चक्रवात",
        "chlorophyll": "क्लोरोफिल",
        "disagreement": "डेटा स्रोतों में अंतर",
    },
    "ml": {
        "lightning": "ഇടിമിന്നൽ",
        "cyclone": "ചുഴലിക്കാറ്റ്",
        "chlorophyll": "ക്ലോറോഫിൽ",
        "disagreement": "ഡാറ്റ സ്രോതസ്സുകൾ തമ്മിൽ വ്യത്യാസം",
    },
}
SOURCES = {  # degraded source → what it supplies, in words
    "ta": {
        "open_meteo/marine": "அலை",
        "open_meteo/weather": "காற்று, வானிலை",
        "incois/pfz": "மீன்பிடி மண்டலம்",
        "chl": "பச்சையம்",
        "argo": "கடல் வெப்பநிலை",
    },
    "hi": {
        "open_meteo/marine": "लहरें",
        "open_meteo/weather": "हवा और मौसम",
        "incois/pfz": "मछली क्षेत्र",
        "chl": "क्लोरोफिल",
        "argo": "समुद्र का तापमान",
    },
    "ml": {
        "open_meteo/marine": "തിര",
        "open_meteo/weather": "കാറ്റ്, കാലാവസ്ഥ",
        "incois/pfz": "മത്സ്യ മേഖല",
        "chl": "ക്ലോറോഫിൽ",
        "argo": "കടൽ താപനില",
    },
}
STATES = {
    "ta": {
        "Sri Lanka": "இலங்கை",
        "Pakistan": "பாகிஸ்தான்",
        "Bangladesh": "வங்கதேசம்",
        "Myanmar": "மியான்மர்",
        "Maldives": "மாலத்தீவு",
        "Indonesia": "இந்தோனேசியா",
    },
    "hi": {
        "Sri Lanka": "श्रीलंका",
        "Pakistan": "पाकिस्तान",
        "Bangladesh": "बांग्लादेश",
        "Myanmar": "म्यांमार",
        "Maldives": "मालदीव",
        "Indonesia": "इंडोनेशिया",
    },
    "ml": {
        "Sri Lanka": "ശ്രീലങ്ക",
        "Pakistan": "പാകിസ്ഥാൻ",
        "Bangladesh": "ബംഗ്ലാദേശ്",
        "Myanmar": "മ്യാൻമർ",
        "Maldives": "മാലദ്വീപ്",
        "Indonesia": "ഇന്തോനേഷ്യ",
    },
}

T: dict[str, dict[str, str]] = {
    "ta": {
        "GO": "கடலுக்குப் போகலாம் (GO)",
        "CAUTION": "எச்சரிக்கையுடன் மட்டும் (CAUTION)",
        "DO NOT SAIL": "கடலுக்குப் போக வேண்டாம் (DO NOT SAIL)",
        "traditional": "நாட்டுப் படகு",
        "motorised": "மோட்டார் படகு",
        "mechanised": "விசைப்படகு",
        "header": "{verdict} — {vessel}, {location}, {window}.",
        "insufficient": " (முழு மதிப்பீட்டுக்குத் தரவு போதவில்லை.)",
        "conditions_header": "{location} கடல் நிலை, {window}:",
        "no-go": "கடலுக்குப் போகக்கூடாத",
        "caution": "எச்சரிக்கை",
        "ge": "{p} {v} {u} — {k} வரம்பான {t} {u}-ஐ எட்டியுள்ளது",
        "le": "{p} {v} {u} — {k} வரம்பான {t} {u}-க்குக் குறைவு",
        "closing": ", நெருங்கி வருகிறது",
        "gust_tail": "; திடீர் காற்று {g} {kt} வரை — போகக்கூடாத வரம்பை எட்டுகிறது",
        "thunder": "மின்னல் தரவு இல்லை; வானிலை மாதிரியில் இடிமின்னல் அறிகுறி ({detail})",
        "outside": "இந்தியக் கடல் எல்லைக்கு வெளியே உள்ளது ({x})",
        "heading": "இப்போதைய திசையில் சென்றால் {m} நிமிடத்தில் {b} எல்லையைத் தாண்டுவீர்கள்",
        "heading_change": " — அதற்கு முன் திசையை மாற்றுங்கள்",
        "heading_beyond": " ({h} {min} எச்சரிக்கை நேரத்துக்கு அப்பால்)",
        "pfz_header": "மீன் கிடைக்கக்கூடிய பகுதிகள் (INCOIS PFZ அறிவிப்பு {date}):",
        "pfz_header_nodate": "மீன் கிடைக்கக்கூடிய பகுதிகள்:",
        "pfz": "PFZ #{i}: {loc}-இலிருந்து {c} திசையில் {d} {km} (திசைக்கோணம் {b}°), {state} பகுதி",
        "pfz_none": "{date} அன்று இந்த இடத்துக்கு அருகில் INCOIS மீன்பிடி மண்டல அறிவிப்பு எதுவும் வெளியிடவில்லை",
        "eez": "இந்தியப் பொருளாதாரக் கடல் மண்டலத்துக்குள் (EEZ)",
        "land_or_port": "இந்தியத் துறைமுகம் / நிலப்பகுதி",
        "outside_india": "இந்தியக் கடல் எல்லைக்கு வெளியே",
        "position": "இடம்: {zone}",
        "nearest": "; அருகிலுள்ள கடல் எல்லை: {name} ({state}) — {c} திசையில் {d} {km}",
        "crossing": "சொன்ன திசையிலும் வேகத்திலும் சென்றால் {m} நிமிடத்தில் ({d} {km}) {b} எல்லையை அடைவீர்கள் — ",
        "within": "90 நிமிட எச்சரிக்கை நேரத்துக்குள்!",
        "beyond": "90 நிமிட எச்சரிக்கை நேரத்துக்கு அப்பால்",
        "route_header": "வழி:",
        "dest": "சேருமிடம்: {dest}, நேர்கோட்டில் {c} திசையில் {d} {km}",
        "no_route": "வழி கிடைக்கவில்லை: {r}",
        "no_route_foreign": "சேருமிடம் இந்தியக் கடல் எல்லைக்கு வெளியே உள்ளது",
        "no_route_res": "இந்த வரைபடத் தெளிவில் இந்தியக் கடலுக்குள் வழி இல்லை (பாம்பன் போன்ற குறுகிய கால்வாய்கள் வரைபடத்தில் தெரியாது)",
        "no_route_sea": "வழிப் பகுதிக்கான கடல் நிலை முன்னறிவிப்பு கிடைக்கவில்லை",
        "direct_foreign": "நேர்கோடு வேறு நாட்டுக் கடலுக்குள் செல்கிறது",
        "suggested": "பரிந்துரைக்கும் வழி: {d} {km}, {s} {kt} வேகத்தில் சுமார் {h} மணி {m} நிமிடம்",
        "legs": "பகுதிகள்: {legs}",
        "leg": "{c} {d} {km}",
        "stays": "வழி கடல் எல்லையிலிருந்து குறைந்தது {x} {km} உள்ளே இருக்கும் (பாதுகாப்பு இடைவெளி {y} {km})",
        "would_cross": "நேர்கோட்டில் சென்றால் வேறு நாட்டுக் கடலுக்குள் நுழைவீர்கள்",
        "adds": "; அதைத் தவிர்க்க வழி {e} {km} கூடுதல்",
        "crosses_land": "நேர்கோடு நிலத்தின் மேல் செல்கிறது; வழி அதைச் சுற்றிச் செல்கிறது",
        "direct_ok": "நேர்கோடு இந்தியக் கடலுக்குள்ளேயே இருக்கும்; எல்லைக்கு மிக அருகில் {x} {km}",
        "worst": "வழியில் மோசமான நிலை: அலை {w} {m_} (இடைவெளி {p} {s_}), காற்று {k} {kt}",
        "detour": "இந்தப் படகுக்கு ஆபத்தான நிலையில் உள்ள கடல் பகுதியைச் சுற்றி வழி செல்கிறது",
        "no_avoid": "இந்தப் படகுக்கு ஆபத்தான கடல் பகுதியைத் தவிர்க்கும் வழி இல்லை",
        "advisory": "இது ஆலோசனை மட்டுமே: கடற்கரைக் கோடு தோராயமானது; ஆழமற்ற நீர், மணல் திட்டுகள் கணக்கில் இல்லை — இது கடல் வரைபடம் அல்ல",
        "route_note_none": "இந்தத் துறைமுகத்துக்கு அருகில் வழி காட்ட மீன்பிடி மண்டல அறிவிப்பு இல்லை",
        "baseline": "{n} நாள் சராசரி {mean} mg/m3 (திட்ட விலக்கம் {sd}); இப்போதைய அளவு அதிலிருந்து {z} திட்ட விலக்கம்; 7 நாள் போக்கு: {t}",
        "rising": "ஏறுமுகம்",
        "falling": "இறங்குமுகம்",
        "steady": "நிலையானது",
        "interp_above": "பச்சையம் வழக்கத்தை விட மிக அதிகம் — கடலின் அடியிலிருந்து ஊட்டச்சத்து மேலே வருவது அல்லது ஆற்று நீர் கலப்பதுடன் ஒத்துப்போகிறது; அதிக நுண்ணுயிர் பெரும்பாலும் நல்ல பிடிப்புக்கு முன்வரும், ஆனால் இது தொடர்பு மட்டுமே, உத்தரவாதம் அல்ல",
        "interp_below": "பச்சையம் வழக்கத்தை விட மிகக் குறைவு — ஊட்டச்சத்து குறைந்த மேல் நீருடன் ஒத்துப்போகிறது; குறைந்த உற்பத்தித்திறன் பிடிப்பு குறைவதற்கான ஒரு சாத்தியமான காரணம் மட்டுமே, நிரூபிக்கப்பட்ட காரணம் அல்ல",
        "interp_normal": "பச்சையம் வழக்கமான அளவிலேயே உள்ளது — பிடிப்பு மாற்றத்துக்கு உற்பத்தித்திறன் மாற்றம் காரணம் என்று தரவு காட்டவில்லை",
        "degraded": "தரவுக் குறிப்பு: நேரடித் தரவு கிடைக்கவில்லை — {items}.",
        "snapshot": "சேமித்த நகல்",
        "stale_cache": "பழைய தரவு",
        "route_grid": "வழிக்கான கடல் நிலைக் கட்டம் கிடைக்கவில்லை; துறைமுக முன்னறிவிப்பே முழு வழிக்கும் பயன்படுத்தப்பட்டது",
        "gaps": "சரிபார்க்க முடியாதவை: {items}.",
        "off_topic": "கடல் நிலை, மீன்பிடி மண்டலம், கடல் எல்லை பற்றி மட்டுமே என்னால் உதவ முடியும். உதாரணம்: 'நாளை காலை கொச்சியில் இருந்து கடலுக்கு போகலாமா?'",
        "general_note": "இது பொதுவான வழிகாட்டுதல், இன்றைய முன்னறிவிப்பு அல்ல. நேரடி நிலைக்கு ஒரு துறைமுகத்தையும் நாளையும் குறிப்பிட்டுக் கேளுங்கள்.",
    },
    "hi": {
        "GO": "समुद्र में जा सकते हैं (GO)",
        "CAUTION": "सावधानी के साथ ही (CAUTION)",
        "DO NOT SAIL": "समुद्र में न जाएँ (DO NOT SAIL)",
        "traditional": "पारंपरिक नाव",
        "motorised": "मोटर नाव",
        "mechanised": "मशीनी नाव (ट्रॉलर)",
        "header": "{verdict} — {vessel}, {location}, {window}।",
        "insufficient": " (पूरे आकलन के लिए डेटा काफ़ी नहीं है।)",
        "conditions_header": "{location} के पास समुद्र की स्थिति, {window}:",
        "no-go": "‘समुद्र में न जाएँ’ वाले",
        "caution": "‘सावधानी’ वाले",
        "ge": "{p} {v} {u} — यह {k} स्तर {t} {u} के बराबर या उससे ज़्यादा है",
        "le": "{p} {v} {u} — यह {k} स्तर {t} {u} के बराबर या उससे कम है",
        "closing": ", पास आ रही है",
        "gust_tail": "; झोंके {g} {kt} तक — ‘समुद्र में न जाएँ’ स्तर तक",
        "thunder": "बिजली (तड़ित) का डेटा नहीं है; मौसम मॉडल में आँधी-तूफ़ान का संकेत है ({detail})",
        "outside": "स्थिति भारतीय जल-सीमा से बाहर है ({x})",
        "heading": "मौजूदा दिशा में {m} {min} में {b} पार हो जाएगी",
        "heading_change": " — उससे पहले दिशा बदलें",
        "heading_beyond": " ({h} {min} की चेतावनी अवधि के बाद)",
        "pfz_header": "मछली मिलने के संभावित क्षेत्र (INCOIS PFZ सूचना {date}):",
        "pfz_header_nodate": "मछली मिलने के संभावित क्षेत्र:",
        "pfz": "PFZ #{i}: {loc} से {c} दिशा में {d} {km} (दिशा-कोण {b}°), {state} क्षेत्र",
        "pfz_none": "INCOIS ने {date} के लिए इस जगह के पास कोई PFZ सूचना जारी नहीं की",
        "eez": "भारत के आर्थिक समुद्री क्षेत्र (EEZ) के अंदर",
        "land_or_port": "भारतीय बंदरगाह / ज़मीन पर",
        "outside_india": "भारतीय जल-सीमा से बाहर",
        "position": "स्थिति: {zone}",
        "nearest": "; सबसे नज़दीकी समुद्री सीमा: {name} ({state}) — {c} दिशा में {d} {km}",
        "crossing": "बताई गई दिशा और रफ़्तार से {m} {min} में ({d} {km}) {b} तक पहुँच जाएँगे — ",
        "within": "90 मिनट की चेतावनी अवधि के अंदर!",
        "beyond": "90 मिनट की चेतावनी अवधि के बाद",
        "route_header": "रास्ता:",
        "dest": "मंज़िल: {dest}, सीधी रेखा में {c} दिशा में {d} {km}",
        "no_route": "रास्ता नहीं मिला: {r}",
        "no_route_foreign": "मंज़िल भारतीय जल-सीमा से बाहर है",
        "no_route_res": "इस नक्शे की बारीकी पर भारतीय जल के अंदर कोई रास्ता नहीं (पंबन जैसी संकरी नहरें नक्शे में नहीं दिखतीं)",
        "no_route_sea": "रास्ते वाले इलाके का समुद्री पूर्वानुमान नहीं मिला",
        "direct_foreign": "सीधी रेखा दूसरे देश के पानी में जाती है",
        "suggested": "सुझाया गया रास्ता: {d} {km}, {s} {kt} की रफ़्तार से लगभग {h} घंटे {m} मिनट",
        "legs": "हिस्से: {legs}",
        "leg": "{c} {d} {km}",
        "stays": "रास्ता समुद्री सीमा से कम से कम {x} {km} अंदर रहता है (सुरक्षा दूरी {y} {km})",
        "would_cross": "सीधी रेखा दूसरे देश के पानी में ले जाएगी",
        "adds": "; उससे बचने के लिए रास्ता {e} {km} लंबा है",
        "crosses_land": "सीधी रेखा ज़मीन के ऊपर से जाती है; रास्ता उसके चारों ओर से जाता है",
        "direct_ok": "सीधी रेखा भारतीय जल में ही रहती है; सीमा से सबसे कम दूरी {x} {km}",
        "worst": "रास्ते पर सबसे खराब: लहर {w} {m_} (अंतराल {p} {s_}), हवा {k} {kt}",
        "detour": "रास्ता उस पानी से बचकर जाता है जो इस नाव के लिए ख़तरनाक स्तर पर है",
        "no_avoid": "ऐसा कोई रास्ता नहीं जो इस नाव के लिए ख़तरनाक पानी से बचे",
        "advisory": "यह केवल सलाह है: तट-रेखा अनुमानित है, उथला पानी और रेत के टीले शामिल नहीं हैं — यह नौवहन चार्ट नहीं है",
        "route_note_none": "इस बंदरगाह के पास रास्ता बताने के लिए कोई मछली क्षेत्र सूचना नहीं है",
        "baseline": "{n} दिन का औसत {mean} mg/m3 (मानक विचलन {sd}); अभी का मान उससे {z} मानक विचलन दूर; 7 दिन का रुझान: {t}",
        "rising": "बढ़ रहा है",
        "falling": "घट रहा है",
        "steady": "स्थिर",
        "interp_above": "क्लोरोफिल अपने हाल के औसत से काफ़ी ऊपर है — यह नीचे से पोषक पानी ऊपर आने (अपवेलिंग) या नदी के पानी से मेल खाता है; ज़्यादा प्लवक अक्सर बेहतर पकड़ से पहले आता है, पर यह संबंध है, गारंटी नहीं",
        "interp_below": "क्लोरोफिल अपने हाल के औसत से काफ़ी नीचे है — यह पोषक-तत्वों में कम ऊपरी पानी से मेल खाता है; कम उत्पादकता पकड़ घटने का एक संभावित कारण है, साबित कारण नहीं",
        "interp_normal": "क्लोरोफिल अपनी सामान्य सीमा में है — आँकड़े पकड़ में बदलाव की वजह उत्पादकता को नहीं बताते",
        "degraded": "डेटा सूचना: लाइव डेटा नहीं मिला — {items}।",
        "snapshot": "सहेजी गई प्रति",
        "stale_cache": "पुराना डेटा",
        "route_grid": "रास्ते के लिए समुद्री पूर्वानुमान का ग्रिड नहीं मिला; बंदरगाह का पूर्वानुमान पूरे रास्ते पर लगाया गया",
        "gaps": "जाँच नहीं हो सकी: {items}।",
        "off_topic": "मैं केवल समुद्र की स्थिति, मछली क्षेत्र और समुद्री सीमा के बारे में मदद कर सकता हूँ। जैसे: 'क्या कल सुबह वेरावल से समुद्र में जाना सुरक्षित है?'",
        "general_note": "यह सामान्य जानकारी है, आज का पूर्वानुमान नहीं। लाइव स्थिति के लिए बंदरगाह और दिन बताकर पूछें।",
    },
    "ml": {
        "GO": "കടലിൽ പോകാം (GO)",
        "CAUTION": "ജാഗ്രതയോടെ മാത്രം (CAUTION)",
        "DO NOT SAIL": "കടലിൽ പോകരുത് (DO NOT SAIL)",
        "traditional": "പരമ്പരാഗത വള്ളം",
        "motorised": "മോട്ടോർ ബോട്ട്",
        "mechanised": "യന്ത്രവത്കൃത ബോട്ട്",
        "header": "{verdict} — {vessel}, {location}, {window}.",
        "insufficient": " (പൂർണ്ണ വിലയിരുത്തലിന് ഡാറ്റ പോരാ.)",
        "conditions_header": "{location} കടൽ നില, {window}:",
        "no-go": "കടലിൽ പോകരുതാത്ത",
        "caution": "ജാഗ്രതാ",
        "ge": "{p} {v} {u} — {k} പരിധിയായ {t} {u} എത്തി",
        "le": "{p} {v} {u} — {k} പരിധിയായ {t} {u}-ൽ താഴെ",
        "closing": ", അടുത്തേക്ക് വരുന്നു",
        "gust_tail": "; ശക്തമായ കാറ്റ് {g} {kt} വരെ — പോകരുതാത്ത പരിധി എത്തുന്നു",
        "thunder": "ഇടിമിന്നൽ ഡാറ്റ ഇല്ല; കാലാവസ്ഥാ മോഡലിൽ ഇടിമിന്നൽ സൂചന ({detail})",
        "outside": "സ്ഥാനം ഇന്ത്യൻ സമുദ്രാതിർത്തിക്ക് പുറത്താണ് ({x})",
        "heading": "ഇപ്പോഴത്തെ ദിശയിൽ {m} മിനിറ്റിനുള്ളിൽ {b} കടക്കും",
        "heading_change": " — അതിനു മുമ്പ് ദിശ മാറ്റുക",
        "heading_beyond": " ({h} {min} മുന്നറിയിപ്പ് സമയത്തിനപ്പുറം)",
        "pfz_header": "മത്സ്യ സാധ്യതാ മേഖലകൾ (INCOIS PFZ അറിയിപ്പ് {date}):",
        "pfz_header_nodate": "മത്സ്യ സാധ്യതാ മേഖലകൾ:",
        "pfz": "PFZ #{i}: {loc}-ൽ നിന്ന് {c} ദിശയിൽ {d} {km} (ദിശാകോൺ {b}°), {state} മേഖല",
        "pfz_none": "{date}-ന് ഈ സ്ഥലത്തിനടുത്ത് INCOIS PFZ അറിയിപ്പ് ഒന്നും നൽകിയിട്ടില്ല",
        "eez": "ഇന്ത്യയുടെ സാമ്പത്തിക സമുദ്ര മേഖലയ്ക്കുള്ളിൽ (EEZ)",
        "land_or_port": "ഇന്ത്യൻ തുറമുഖം / കര",
        "outside_india": "ഇന്ത്യൻ സമുദ്രാതിർത്തിക്ക് പുറത്ത്",
        "position": "സ്ഥാനം: {zone}",
        "nearest": "; ഏറ്റവും അടുത്ത സമുദ്രാതിർത്തി: {name} ({state}) — {c} ദിശയിൽ {d} {km}",
        "crossing": "പറഞ്ഞ ദിശയിലും വേഗത്തിലും {m} മിനിറ്റിനുള്ളിൽ ({d} {km}) {b} എത്തും — ",
        "within": "90 മിനിറ്റ് മുന്നറിയിപ്പ് സമയത്തിനുള്ളിൽ!",
        "beyond": "90 മിനിറ്റ് മുന്നറിയിപ്പ് സമയത്തിനപ്പുറം",
        "route_header": "വഴി:",
        "dest": "ലക്ഷ്യം: {dest}, നേർരേഖയിൽ {c} ദിശയിൽ {d} {km}",
        "no_route": "വഴി കണ്ടെത്താനായില്ല: {r}",
        "no_route_foreign": "ലക്ഷ്യം ഇന്ത്യൻ സമുദ്രാതിർത്തിക്ക് പുറത്താണ്",
        "no_route_res": "ഈ ഭൂപടത്തിന്റെ വ്യക്തതയിൽ ഇന്ത്യൻ കടലിനുള്ളിൽ വഴിയില്ല (പാമ്പൻ പോലുള്ള ഇടുങ്ങിയ ചാലുകൾ ഭൂപടത്തിൽ ഇല്ല)",
        "no_route_sea": "വഴിയുടെ പ്രദേശത്തെ കടൽ നില പ്രവചനം ലഭിച്ചില്ല",
        "direct_foreign": "നേർരേഖ മറ്റൊരു രാജ്യത്തിന്റെ കടലിലേക്ക് പോകുന്നു",
        "suggested": "നിർദ്ദേശിക്കുന്ന വഴി: {d} {km}, {s} {kt} വേഗത്തിൽ ഏകദേശം {h} മണിക്കൂർ {m} മിനിറ്റ്",
        "legs": "ഘട്ടങ്ങൾ: {legs}",
        "leg": "{c} {d} {km}",
        "stays": "വഴി സമുദ്രാതിർത്തിയിൽ നിന്ന് കുറഞ്ഞത് {x} {km} ഉള്ളിൽ തുടരും (സുരക്ഷാ അകലം {y} {km})",
        "would_cross": "നേർരേഖ മറ്റൊരു രാജ്യത്തിന്റെ കടലിലേക്ക് കടക്കും",
        "adds": "; അത് ഒഴിവാക്കാൻ വഴി {e} {km} കൂടുതൽ",
        "crosses_land": "നേർരേഖ കരയ്ക്കു മുകളിലൂടെയാണ്; വഴി അതിനെ ചുറ്റി പോകുന്നു",
        "direct_ok": "നേർരേഖ ഇന്ത്യൻ കടലിൽ തന്നെ; അതിർത്തിയോട് ഏറ്റവും അടുത്ത് {x} {km}",
        "worst": "വഴിയിലെ ഏറ്റവും മോശം: തിര {w} {m_} (ഇടവേള {p} {s_}), കാറ്റ് {k} {kt}",
        "detour": "ഈ ബോട്ടിന് അപകടകരമായ നിലയിലുള്ള കടൽ ഒഴിവാക്കി വഴി പോകുന്നു",
        "no_avoid": "ഈ ബോട്ടിന് അപകടകരമായ കടൽ ഒഴിവാക്കുന്ന വഴിയില്ല",
        "advisory": "ഇത് ഉപദേശം മാത്രം: തീരരേഖ ഏകദേശമാണ്, ആഴം കുറഞ്ഞ ഭാഗങ്ങളും മണൽത്തിട്ടകളും കണക്കിലില്ല — ഇത് നാവിഗേഷൻ ചാർട്ട് അല്ല",
        "route_note_none": "ഈ തുറമുഖത്തിനടുത്ത് വഴി കാണിക്കാൻ മത്സ്യ മേഖല അറിയിപ്പ് ഇല്ല",
        "baseline": "{n} ദിവസത്തെ ശരാശരി {mean} mg/m3 (SD {sd}); ഇപ്പോഴത്തെ അളവ് അതിൽ നിന്ന് {z} SD അകലെ; 7 ദിവസത്തെ പ്രവണത: {t}",
        "rising": "കൂടുന്നു",
        "falling": "കുറയുന്നു",
        "steady": "സ്ഥിരം",
        "interp_above": "ക്ലോറോഫിൽ സാധാരണയേക്കാൾ വളരെ കൂടുതലാണ് — ആഴത്തിൽ നിന്ന് പോഷകജലം ഉയരുന്നതിനോടോ പുഴവെള്ളത്തോടോ ചേരുന്നു; കൂടുതൽ പ്ലവകങ്ങൾ പലപ്പോഴും നല്ല മീൻപിടിത്തത്തിന് മുമ്പ് വരും, പക്ഷേ ഇത് ബന്ധം മാത്രം, ഉറപ്പല്ല",
        "interp_below": "ക്ലോറോഫിൽ സാധാരണയേക്കാൾ വളരെ കുറവാണ് — പോഷകം കുറഞ്ഞ മുകൾജലത്തോട് ചേരുന്നു; കുറഞ്ഞ ഉൽപ്പാദനക്ഷമത മീൻ കുറയാനുള്ള ഒരു സാധ്യതാ കാരണം മാത്രം, തെളിയിക്കപ്പെട്ടതല്ല",
        "interp_normal": "ക്ലോറോഫിൽ സാധാരണ പരിധിയിലാണ് — മീൻപിടിത്തത്തിലെ മാറ്റത്തിന് ഉൽപ്പാദനക്ഷമതാ മാറ്റമാണ് കാരണമെന്ന് ഡാറ്റ കാണിക്കുന്നില്ല",
        "degraded": "ഡാറ്റ കുറിപ്പ്: തത്സമയ ഡാറ്റ ലഭിച്ചില്ല — {items}.",
        "snapshot": "സൂക്ഷിച്ച പകർപ്പ്",
        "stale_cache": "പഴയ ഡാറ്റ",
        "route_grid": "വഴിക്കുള്ള കടൽ നില ഗ്രിഡ് ലഭിച്ചില്ല; തുറമുഖ പ്രവചനം മുഴുവൻ വഴിക്കും ഉപയോഗിച്ചു",
        "gaps": "പരിശോധിക്കാൻ കഴിയാത്തത്: {items}.",
        "off_topic": "കടൽ നില, മത്സ്യ മേഖല, സമുദ്രാതിർത്തി എന്നിവയെക്കുറിച്ച് മാത്രമേ എനിക്ക് സഹായിക്കാനാകൂ. ഉദാഹരണം: 'നാളെ രാവിലെ കൊച്ചിയിൽ നിന്ന് കടലിൽ പോകാമോ?'",
        "general_note": "ഇത് പൊതുവായ മാർഗ്ഗനിർദ്ദേശമാണ്, ഇന്നത്തെ പ്രവചനമല്ല. തത്സമയ നിലയ്ക്ക് ഒരു തുറമുഖവും ദിവസവും പറഞ്ഞ് ചോദിക്കുക.",
    },
}

_NUM = r"-?\d+(?:\.\d+)?"
_REASON = re.compile(
    rf"^(?P<p>.+?) (?P<v>{_NUM}) (?P<u>\S+) (?P<cmp>[≤≥]) (?P<kind>no-go|caution) threshold "
    rf"(?P<t>{_NUM}) [^\s;,]+(?P<tail>.*)$"
)
_GUST = re.compile(rf"^; gusts to (?P<g>{_NUM}) kt reach the no-go threshold$")
_HEADING = re.compile(rf"^current heading crosses (?P<b>.+?) in (?P<m>{_NUM}) min(?P<tail>.*)$")
_BEYOND = re.compile(rf"^ \(beyond the (?P<h>{_NUM}) min horizon\)$")
_OBS = re.compile(rf"^(?P<label>[a-z][a-z -]*?) (?P<v>{_NUM}) (?P<u>\S+)$")
_PFZ = re.compile(
    rf"^PFZ #(?P<i>\d+): (?P<d>{_NUM}) km (?P<c>[NSEW]+) \(bearing (?P<b>{_NUM})°\) from "
    r"(?P<loc>.+?), (?P<state>.+?) sector, advisory dated (?P<date>.+)$"
)
_PFZ_NONE = re.compile(r"^INCOIS issued no PFZ near this point for (?P<date>.+)$")
_POSITION = re.compile(
    r"^position: (?P<zone>.+?)(?:; nearest maritime boundary: (?P<name>.+?) \((?P<state>[^)]+)\) "
    rf"(?P<d>{_NUM}) km to the (?P<c>[NSEW]+))?$"
)
_CROSSING = re.compile(
    rf"^on the stated heading and speed the track reaches (?P<b>.+?) in (?P<m>{_NUM}) min "
    rf"\((?P<d>{_NUM}) km\) — (?P<w>WITHIN|beyond)"
)
_ROUTE = [
    (
        "dest",
        re.compile(
            rf"^destination: (?P<dest>.+?), (?P<d>{_NUM}) km to the (?P<c>[NSEW]+) in a straight line$"
        ),
    ),
    ("no_route", re.compile(r"^no route: (?P<r>.+)$")),
    (
        "direct_foreign",
        re.compile(r"^the straight line to it crosses into another country's waters$"),
    ),
    (
        "suggested",
        re.compile(
            rf"^suggested route: (?P<d>{_NUM}) km, about (?P<h>\d+) h (?P<m>\d+) min at (?P<s>{_NUM}) kt$"
        ),
    ),
    ("legs", re.compile(r"^legs: (?P<legs>.+)$")),
    (
        "stays",
        re.compile(
            rf"^the route stays at least (?P<x>{_NUM}) km inside the maritime boundary "
            rf"\(safety margin (?P<y>{_NUM}) km\)$"
        ),
    ),
    (
        "would_cross",
        re.compile(
            rf"^the straight line would cross into another country's waters"
            rf"(?:; the route adds (?P<e>{_NUM}) km to stay out of them)?$"
        ),
    ),
    ("crosses_land", re.compile(r"^the straight line crosses land; the route goes round it$")),
    (
        "direct_ok",
        re.compile(
            rf"^the straight line stays in Indian waters, closest (?P<x>{_NUM}) km to the boundary$"
        ),
    ),
    (
        "worst",
        re.compile(
            rf"^worst on the route: waves (?P<w>{_NUM}) m \(period (?P<p>{_NUM}) s\), "
            rf"wind (?P<k>{_NUM}) kt$"
        ),
    ),
    ("detour", re.compile(r"^the route detours around water that is at do-not-sail level")),
    ("no_avoid", re.compile(r"^no route avoids do-not-sail water")),
    ("advisory", re.compile(r"^advisory only:")),
    ("route_note_none", re.compile(r"^no fishing-zone advisory near this harbour")),
]
_LEG = re.compile(rf"(?P<d>{_NUM}) km (?P<c>[NSEW]+)")
_BASELINE = re.compile(
    rf"^(?P<n>\d+)-day baseline mean (?P<mean>{_NUM}) mg/m3 \(sd (?P<sd>{_NUM})\); latest is "
    rf"(?P<z>{_NUM}) standard deviations from it; 7-day trend (?P<t>\w+)$"
)


class Localizer:
    def __init__(self, lang: str):
        self.lang, self.t = lang, T[lang]
        self.u = UNITS[lang]

    def unit(self, u: str) -> str:
        return self.u.get(u, u)

    def compass(self, c: str) -> str:
        return f"{COMPASS[self.lang].get(c, c)} ({c})"

    def param(self, name: str) -> str:
        key = name.replace("_", " ")
        return next((v for k, v in PARAMS[self.lang].items() if key == k), name)

    def state(self, s: str) -> str:
        return STATES[self.lang].get(s, s)

    def fmt(self, key: str, **kw) -> str:
        return self.t[key].format(
            km=self.unit("km"),
            kt=self.unit("kt"),
            min=self.unit("min"),
            m_=self.unit("m"),
            s_=self.unit("s"),
            **kw,
        )

    # -- line kinds ----------------------------------------------------------------------

    def reason(self, line: str) -> str:
        m = _REASON.match(line)
        if m:
            p = m["p"]
            label = (
                self.param("steepness") + p[len("steepness") :]
                if p.startswith("steepness")
                else self.param(p)
            )
            u = self.unit(m["u"])
            out = self.t["ge" if m["cmp"] == "≥" else "le"].format(
                p=label, v=m["v"], u=u, k=self.t[m["kind"]], t=m["t"]
            )
            tail = m["tail"]
            g = _GUST.match(tail)
            if g:
                out += self.fmt("gust_tail", g=g["g"])
            elif tail == ", closing":
                out += self.t["closing"]
            elif tail:
                out += tail
            return out
        if line.startswith("no lightning feed; convective proxy: "):
            return self.t["thunder"].format(detail=line.split(": ", 1)[1])
        m = re.match(r"^position is outside Indian waters \((?P<x>.+)\)$", line)
        if m:
            return self.t["outside"].format(x=m["x"])
        m = _HEADING.match(line)
        if m:
            out = self.fmt("heading", b=m["b"], m=m["m"])
            tail = m["tail"]
            if tail == " — change heading before then":
                out += self.t["heading_change"]
            elif (b := _BEYOND.match(tail)) is not None:
                out += self.fmt("heading_beyond", h=b["h"])
            return out
        return line

    def condition(self, line: str) -> str:
        m = _OBS.match(line)
        if not m:
            return line
        u = self.unit(m["u"])
        return f"{self.param(m['label'])}: {m['v']}{'' if u.startswith('°') else ' '}{u}"

    def pfz(self, line: str) -> str:
        m = _PFZ.match(line)
        if m:
            return self.fmt(
                "pfz",
                i=m["i"],
                loc=m["loc"],
                c=self.compass(m["c"]),
                d=m["d"],
                b=m["b"],
                state=m["state"],
            )
        m = _PFZ_NONE.match(line)
        if m:
            return self.t["pfz_none"].format(date=m["date"])
        return line

    def boundary(self, line: str) -> str:
        m = _POSITION.match(line)
        if m:
            zone = {
                "inside India's EEZ": "eez",
                "at an Indian harbour / on Indian land": "land_or_port",
                "OUTSIDE Indian waters": "outside_india",
            }.get(m["zone"])
            if zone is None:
                return line
            out = self.t["position"].format(zone=self.t[zone])
            if m["name"]:
                out += self.fmt(
                    "nearest",
                    name=m["name"],
                    state=self.state(m["state"]),
                    c=self.compass(m["c"]),
                    d=m["d"],
                )
            return out
        m = _CROSSING.match(line)
        if m:
            return (
                self.fmt("crossing", b=m["b"], m=m["m"], d=m["d"])
                + self.t["within" if m["w"] == "WITHIN" else "beyond"]
            )
        return line

    def route(self, line: str) -> str:
        for key, rx in _ROUTE:
            m = rx.match(line)
            if not m:
                continue
            g = {k: v for k, v in m.groupdict().items()}
            if key == "dest":
                return self.fmt(key, dest=g["dest"], c=self.compass(g["c"]), d=g["d"])
            if key == "no_route":
                r = g["r"]
                why = (
                    self.t["no_route_foreign"]
                    if r.startswith("the destination is outside")
                    else self.t["no_route_res"]
                    if r.startswith("no sea route inside")
                    else self.t["no_route_sea"]
                    if r.startswith("no sea-state forecast")
                    else r
                )
                return self.t["no_route"].format(r=why)
            if key == "legs":
                legs = [
                    self.fmt("leg", c=self.compass(x["c"]), d=x["d"])
                    for x in _LEG.finditer(g["legs"])
                ]
                return self.t["legs"].format(legs="; ".join(legs))
            if key == "would_cross":
                out = self.t["would_cross"]
                return out + (self.fmt("adds", e=g["e"]) if g.get("e") else "")
            return self.fmt(key, **{k: v for k, v in g.items() if v is not None})
        return line

    def analytics(self, line: str) -> str:
        if line.startswith("chlorophyll-a "):
            return self.condition(line.split(" [")[0])
        m = _BASELINE.match(line)
        if m:
            # specialists.analytics writes "rising" / "falling" / "flat"
            trend = self.t[m["t"]] if m["t"] in ("rising", "falling") else self.t["steady"]
            return self.t["baseline"].format(
                n=m["n"], mean=m["mean"], sd=m["sd"], z=m["z"], t=trend
            )
        if line.startswith("interpretation: chlorophyll is well above"):
            return self.t["interp_above"]
        if line.startswith("interpretation: chlorophyll is well below"):
            return self.t["interp_below"]
        if line.startswith("interpretation: chlorophyll is within"):
            return self.t["interp_normal"]
        return line

    def degradation(self, items: list[str]) -> str:
        out: list[str] = []
        for d in items:
            if d.startswith("route sea state"):
                out.append(self.t["route_grid"])
                continue
            src, _, prov = d.partition(": ")
            name = next((v for k, v in SOURCES[self.lang].items() if k in src), src)
            out.append(f"{name}: {self.t.get(prov, prov)}")
        return self.t["degraded"].format(items="; ".join(out))

    def gaps(self, gaps: list[str]) -> str:
        words: list[str] = []
        for g in gaps:
            var = g.split(":")[0]
            w = next((v for k, v in GAPS[self.lang].items() if var.startswith(k)), None)
            w = w or self.param(var)
            if w not in words:
                words.append(w)
        return self.t["gaps"].format(items=", ".join(words))


def localized_template(b) -> str | None:
    """The template answer in b.language, or None if that language is not supported."""
    from marine.agents.planner import Intent

    if b.language not in LANGS:
        return None
    L = Localizer(b.language)
    t = L.t
    if b.intent == Intent.OFF_TOPIC:
        return t["off_topic"]
    if b.intent == Intent.GENERAL_KNOWLEDGE:
        return (b.knowledge_answer or "") + "\n\n" + t["general_note"]
    lines: list[str] = []
    if b.verdict:
        lines.append(
            t["header"].format(
                verdict=t.get(b.verdict, b.verdict),
                vessel=t.get(b.vessel, b.vessel),
                location=b.location,
                window=b.window,
            )
            + (t["insufficient"] if b.verdict_status == "insufficient_data" else "")
        )
        lines += [f"• {L.reason(r)}" for r in b.reasons]
    elif b.window:
        lines.append(t["conditions_header"].format(location=b.location, window=b.window))
    lines += [f"• {L.condition(c.split(' [')[0])}" for c in b.conditions]
    if b.pfz:
        lines.append(
            t["pfz_header"].format(date=b.pfz_date) if b.pfz_date else t["pfz_header_nodate"]
        )
        lines += [f"• {L.pfz(p)}" for p in b.pfz]
    lines += [f"• {L.boundary(x)}" for x in b.boundary]
    if b.route:
        lines.append(t["route_header"])
        lines += [f"• {L.route(x)}" for x in b.route]
    lines += [f"• {L.analytics(x)}" for x in b.analytics]
    if b.degradation:
        lines.append(L.degradation(b.degradation))
    if b.gaps:
        lines.append(L.gaps(b.gaps))
    return "\n".join(lines)
