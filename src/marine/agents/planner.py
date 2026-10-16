"""The Planner — the only free-form LLM step. Turns a question in any language into a
typed `Plan`: language, English query, intent, location, window, vessel, heading.

Two paths:
- **fast path** (no model): English/Latin-script questions in the common shapes are parsed
  deterministically — location name, day-part words, intent keywords. ~1 ms, and most
  demo questions take it. This is how we live inside the 600 ms planner budget on a free
  tier whose round-trip is 2–3 s.
- **LLM path**: everything else (Indic scripts, vague phrasing, follow-ups). One call does
  language detection, translation and intent in a single JSON object.

The task DAG is derived from the intent by `tasks_for` — typed and explicit, so independent
fetches are marked parallel by construction rather than by prompt luck.
"""

from __future__ import annotations

import re
import time
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from marine.agents.llm import LLM, LLMUnavailable, complete_structured
from marine.risk.thresholds import VesselClass
from marine.tools.locations import LocationQuery, ResolvedLocation, resolve_location
from marine.tools.windows import Day, DayPart


class Intent(StrEnum):
    SAFETY = "safety"  # go / no-go for a trip
    PFZ = "pfz"  # where are the fish (INCOIS advisory)
    BOUNDARY = "boundary"  # distance to / crossing of IMBL / EEZ
    CONDITIONS = "conditions"  # waves, wind, visibility, currents, SST — no verdict asked
    CHLOROPHYLL = "chlorophyll"  # productivity, catch decline, anomaly
    GENERAL_KNOWLEDGE = "general_knowledge"  # marine knowledge, no live data needed
    OFF_TOPIC = "off_topic"
    CLARIFY = "clarify"  # cannot proceed without asking (no location, etc.)


NEEDS_LOCATION = {Intent.SAFETY, Intent.PFZ, Intent.BOUNDARY, Intent.CONDITIONS, Intent.CHLOROPHYLL}


class Plan(BaseModel):
    language: str = Field(
        description="ISO 639-1 code of the user's message: ta, hi, ml, te, kn, en, ..."
    )
    english_query: str = Field(description="The user's question translated to English")
    intent: Intent
    location_name: str | None = Field(
        default=None, description="Place name exactly as the user wrote it, or null"
    )
    day: Day = "tomorrow"
    part: DayPart = "morning"
    vessel: VesselClass | None = None
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    speed_kt: float | None = Field(default=None, ge=0, le=40)
    clarify_question: str | None = Field(
        default=None,
        description="If intent is clarify: the question to ask, in the user's language",
    )
    knowledge_answer: str | None = Field(
        default=None,
        description="If intent is general_knowledge: a short factual answer in the user's language, with NO specific forecast numbers",
    )
    # filled in by the planner, not the model
    location: ResolvedLocation | None = None
    source: Literal["fast_path", "llm"] = "fast_path"
    elapsed_ms: int = 0


class Task(BaseModel):
    id: str
    agent: Literal["ocean_weather", "geospatial", "analytics", "risk", "synthesis"]
    tool: str
    depends_on: list[str] = Field(default_factory=list)


def tasks_for(plan: Plan) -> list[Task]:
    """The typed DAG. Tasks with no shared dependency run in parallel."""
    i = plan.intent
    t: list[Task] = []
    # A boundary question is a safety question: the engine grades the crossing.
    if i in (Intent.SAFETY, Intent.CONDITIONS, Intent.BOUNDARY):
        t.append(Task(id="ocean", agent="ocean_weather", tool="fan_out"))
    if i in (Intent.SAFETY, Intent.PFZ, Intent.BOUNDARY):
        t.append(
            Task(
                id="geo",
                agent="geospatial",
                tool="get_pfz_advisory+check_position+predict_boundary_crossing",
            )
        )
    if i in (Intent.CHLOROPHYLL, Intent.PFZ):
        t.append(Task(id="analytics", agent="analytics", tool="get_chlorophyll+anomaly"))
    if i in (Intent.SAFETY, Intent.BOUNDARY):
        t.append(
            Task(id="risk", agent="risk", tool="assess_sailing_risk", depends_on=["ocean", "geo"])
        )
    if i not in (Intent.CLARIFY,):
        t.append(
            Task(
                id="synthesis", agent="synthesis", tool="draft+verify", depends_on=[x.id for x in t]
            )
        )
    return t


# -- fast path ---------------------------------------------------------------------------------

SCRIPTS = {
    "ta": (0x0B80, 0x0BFF),
    "hi": (0x0900, 0x097F),  # Devanagari: hi / mr — the LLM path disambiguates
    "ml": (0x0D00, 0x0D7F),
    "te": (0x0C00, 0x0C7F),
    "kn": (0x0C80, 0x0CFF),
    "gu": (0x0A80, 0x0AFF),
    "or": (0x0B00, 0x0B7F),
    "bn": (0x0980, 0x09FF),
    "pa": (0x0A00, 0x0A7F),
}


def detect_script(text: str) -> str:
    """Language by Unicode block; 'en' if Latin. Cheap, and right for the scripts we serve."""
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for lang, (lo, hi) in SCRIPTS.items():
            if lo <= cp <= hi:
                counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=counts.get) if counts else "en"


KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.SAFETY: (
        "safe",
        "safety",
        "go out",
        "go to sea",
        "sail",
        "venture",
        "risk",
        "dangerous",
        "ok to go",
        "can i go",
        "should i go",
        "go fishing",
    ),
    Intent.PFZ: (
        "pfz",
        "fishing zone",
        "where are the fish",
        "where is the fish",
        "fish today",
        "potential fishing",
        "catch today",
        "where to fish",
        "good fishing",
    ),
    Intent.BOUNDARY: (
        "border",
        "boundary",
        "sri lanka",
        "imbl",
        "eez",
        "cross",
        "international",
        "maritime line",
        "detain",
        "arrest",
        "pakistan",
    ),
    Intent.CHLOROPHYLL: (
        "chlorophyll",
        "plankton",
        "productivity",
        "catch declining",
        "less fish",
        "fewer fish",
        "catch dropped",
        "green water",
        "upwelling",
    ),
    Intent.CONDITIONS: (
        "wave",
        "swell",
        "wind",
        "visibility",
        "fog",
        "current",
        "temperature",
        "sst",
        "sea state",
        "how rough",
        "how high",
    ),
}
# Matched as whole words (see _day): a substring test read "know" as "now" → today.
# Dict order is priority: "day after tomorrow" must be day_after, not tomorrow.
DAY_WORDS: dict[str, Day] = {
    "day after": "day_after",
    "parso": "day_after",  # Hindi in Latin script
    "tomorrow": "tomorrow",
    "tmrw": "tomorrow",
    "tmr": "tomorrow",
    "kal": "tomorrow",  # Hindi "kal" — tomorrow in a forward-looking question
    "this morning": "today",
    "this afternoon": "today",
    "this evening": "today",
    "tonight": "today",
    "today": "today",
    "aaj": "today",
    "now": "today",
}
PART_WORDS: dict[str, DayPart] = {
    "early morning": "early_morning",
    "before dawn": "early_morning",
    "dawn": "early_morning",
    "morning": "morning",
    "subah": "morning",
    "afternoon": "afternoon",
    "dopahar": "afternoon",
    "evening": "evening",
    "shaam": "evening",
    "night": "night",
    "tonight": "night",
    "raat": "night",
    "all day": "all_day",
    "whole day": "all_day",
}
# "Which direction should I go to find fish?" asks about fishing zones even though it also
# contains a safety phrase ("should I go"). Checked before the keyword table.
FISH_FINDING = re.compile(
    r"\b(find|locate|catch|get)\b[^.?!]*\bfish\b|\bwhere\b[^.?!]*\bfish\b|\bdirection\b[^.?!]*\bfish\b"
)
# Hindi typed in Latin letters ("Kal subah Porbandar se boat nikalna safe hai kya?"). Two or
# more of these words → answer in Hindi. Deterministic, so it needs no model call.
HINGLISH = frozenset(
    "kal aaj parso subah shaam raat dopahar hai hain kya kaisa kaise kitna kitni kitne nahi "
    "mein se ko jana jaana jaun nikalna nikal machli machhli samundar samudra mausam hoga "
    "hogi rahega chahiye sakta sakte".split()
)


def _day(q: str) -> Day:
    return next((d for w, d in DAY_WORDS.items() if re.search(rf"\b{re.escape(w)}\b", q)), "tomorrow")


def _is_hinglish(q: str) -> bool:
    return sum(w in HINGLISH for w in re.findall(r"[a-z]+", q)) >= 2
VESSEL_WORDS: dict[str, VesselClass] = {
    "canoe": VesselClass.TRADITIONAL,
    "catamaran": VesselClass.TRADITIONAL,
    "vallam": VesselClass.TRADITIONAL,
    "fibre": VesselClass.TRADITIONAL,
    "fiber": VesselClass.TRADITIONAL,
    "small boat": VesselClass.TRADITIONAL,
    "motor": VesselClass.MOTORISED,
    "motorised": VesselClass.MOTORISED,
    "motorized": VesselClass.MOTORISED,
    "trawler": VesselClass.MECHANISED,
    "mechanised": VesselClass.MECHANISED,
    "mechanized": VesselClass.MECHANISED,
}
STOP = {
    "is",
    "it",
    "the",
    "a",
    "to",
    "off",
    "near",
    "from",
    "at",
    "in",
    "of",
    "for",
    "go",
    "out",
    "and",
    "tomorrow",
    "today",
    "morning",
    "safe",
    "sea",
    "fish",
    "fishing",
    "can",
    "i",
    "we",
    "my",
    "boat",
    "should",
    "what",
    "how",
    "where",
    "are",
    "will",
    "be",
    "there",
}


def _find_location(text: str) -> tuple[str, ResolvedLocation] | None:
    """Try 1–3 word spans against the resolver and keep the BEST match, not the first: a weak
    fuzzy hit on an early span ("i have a 15 m boat") must not beat an exact place name later
    in the sentence ("…at Veraval"). An exact match is returned at once (longest spans first)."""
    words = re.findall(r"[a-z]+", text.lower())
    best: tuple[tuple[float, int], str, ResolvedLocation] | None = None
    for n in (3, 2, 1):
        for k in range(len(words) - n + 1):
            span = words[k : k + n]
            if all(w in STOP for w in span) or len(span[-1]) < 4:
                continue
            r = resolve_location(LocationQuery(name=" ".join(span)))
            if not r or not (r.score >= 0.85 or n > 1):
                continue
            if r.score >= 1.0:
                return " ".join(span), r
            if best is None or (r.score, n) > best[0]:
                best = ((r.score, n), " ".join(span), r)
    return (best[1], best[2]) if best else None


def fast_plan(query: str) -> Plan | None:
    """Deterministic plan for Latin-script questions in the common shapes, else None."""
    if detect_script(query) != "en":
        return None
    q = query.lower()
    intent: Intent | None = Intent.PFZ if FISH_FINDING.search(q) else None
    for cand, words in KEYWORDS.items():  # dict order = priority: safety first
        if intent is not None:
            break
        if any(w in q for w in words):
            intent = cand
    if intent is None:
        return None
    loc = _find_location(q)
    day: Day = _day(q)
    part: DayPart = next((p for w, p in PART_WORDS.items() if w in q), "morning")
    vessel = next((v for w, v in VESSEL_WORDS.items() if w in q), None)
    m = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:m|metre|meter)\b", q)
    if vessel is None and m:
        vessel = VesselClass.from_length_m(float(m.group(1)))
    hm = re.search(r"(?:head(?:ing)?|course|bearing)\s*(?:of\s*)?(\d{1,3})", q)
    sm = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:kt|knots?)", q)
    # Explanatory phrasing with no place is general knowledge or clarify — the model decides.
    if intent in NEEDS_LOCATION and loc is None:
        return None
    return Plan(
        language="hi" if _is_hinglish(q) else "en",
        english_query=query,
        intent=intent,
        location_name=loc[0] if loc else None,
        location=loc[1] if loc else None,
        day=day,
        part=part,
        vessel=vessel,
        heading_deg=float(hm.group(1)) if hm else None,
        speed_kt=float(sm.group(1)) if sm else None,
        source="fast_path",
    )


# -- LLM path -------------------------------------------------------------------------------------

PLANNER_SYSTEM = """You are the planner for a marine safety assistant used by small-craft fishermen on the Indian coast. You NEVER answer questions about sea conditions yourself — you only classify the question and extract fields so deterministic tools can fetch real data.

Classify `intent`:
- safety: asking whether it is safe / OK to go to sea or fish (go / no-go).
- pfz: asking where the fish are, fishing zones, INCOIS PFZ advisory.
- boundary: distance to or crossing of the maritime boundary (Sri Lanka, Pakistan, EEZ), detention risk.
- conditions: asking about waves, wind, swell, visibility, currents, sea temperature — without asking for a verdict.
- chlorophyll: productivity, plankton, why the catch is declining, unusual water colour.
- general_knowledge: a marine/fishing question that needs no live data (what is a PFZ, what does 2 m swell mean, why is the sea rough in monsoon). Put a short factual answer in `knowledge_answer`, in the user's language, with NO specific forecast numbers for any place or date. NOT general_knowledge if the question names a specific harbour or place and asks what is happening there or why (e.g. "why is the catch falling near Chennai?" is chlorophyll; "how high are the waves at Kochi?" is conditions) — those need live data for that place.
- off_topic: not about the sea, weather, fishing, boats or the coast.
- clarify: the request needs live data but the location is missing and cannot be inferred. Put the question to ask in `clarify_question`, in the user's language.

Rules:
- `language`: ISO 639-1 of the user's message (ta, hi, ml, te, kn, mr, gu, or, bn, en).
- `english_query`: faithful English translation.
- `location_name`: the place name in LATIN SCRIPT (English spelling, e.g. "Rameswaram", "Kochi", "Veraval"), with any case suffix removed — never Tamil/Devanagari/Malayalam script — or null.
- `day` / `part`: default tomorrow / morning when not stated. Fishermen leave before dawn: "early morning" = 03:00–08:00.
- `vessel`: traditional (canoe, catamaran, vallam, fibre boat, < 12 m), motorised (12–20 m), mechanised (trawler, > 20 m), or null.
- `heading_deg` / `speed_kt` only if stated."""


async def llm_plan(llm: LLM, query: str) -> Plan:
    plan = await complete_structured(llm, PLANNER_SYSTEM, query, Plan, max_tokens=600)
    plan.source = "llm"
    if plan.location_name:
        plan.location = resolve_location(LocationQuery(name=plan.location_name))
    if plan.intent in NEEDS_LOCATION and plan.location is None:
        plan.intent = Intent.CLARIFY
        if not plan.clarify_question:
            plan.clarify_question = (
                f"I could not find '{plan.location_name}'. Which harbour or landing centre do you mean?"
                if plan.location_name
                else "Which harbour or landing centre are you asking about?"
            )
    return plan


async def make_plan(query: str, llm: LLM | None, *, force_llm: bool = False) -> Plan:
    """Fast path first; LLM only when needed. With no LLM at all, non-fast-path questions
    become a clarify plan in English — the system still answers, honestly."""
    t0 = time.perf_counter()
    plan = None if force_llm else fast_plan(query)
    if plan is None:
        if llm is None:
            plan = Plan(
                language=detect_script(query),
                english_query=query,
                intent=Intent.CLARIFY,
                clarify_question="I could not understand the question without the language model. Please ask in English, e.g. 'Is it safe off Kochi tomorrow morning?'",
            )
        else:
            try:
                plan = await llm_plan(llm, query)
            except LLMUnavailable as e:
                plan = Plan(
                    language=detect_script(query),
                    english_query=query,
                    intent=Intent.CLARIFY,
                    clarify_question=f"The language model is unavailable ({e}). Please ask in English, e.g. 'Is it safe off Kochi tomorrow morning?'",
                )
    plan.elapsed_ms = round((time.perf_counter() - t0) * 1000)
    return plan
