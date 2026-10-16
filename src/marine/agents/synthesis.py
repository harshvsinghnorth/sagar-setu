"""Synthesis & Verify.

`build_brief` turns everything the specialists found into one compact, deterministic
brief. That brief is both the model's entire world (it sees nothing else) and the source of
the template answer used when no model is available. The model may only restate what is in
the brief, in the user's language. It never computes, adjusts or softens the verdict.

`verify` then scans the draft: every number must be traceable to the ledger (or to a
threshold / window hour / count that the brief itself states). An unsupported number gets
one corrective retry; if it persists, the template answer ships instead. The verdict badge
the UI shows comes from the engine, never from the text, so prose cannot soften it.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from marine.agents.llm import LLM, LLMUnavailable
from marine.agents.planner import Intent, Plan
from marine.agents.specialists import AnalyticsFinding, GeoFinding, OceanFinding
from marine.ledger import EvidenceLedger
from marine.risk.rules import RiskVerdict
from marine.risk.thresholds import TABLES
from marine.tools.windows import describe_window

LANG_NAMES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "ml": "Malayalam",
    "te": "Telugu",
    "kn": "Kannada",
    "mr": "Marathi",
    "gu": "Gujarati",
    "or": "Odia",
    "bn": "Bengali",
    "pa": "Punjabi",
    "en": "English",
}


class Brief(BaseModel):
    """Everything the answer may say. Numbers here are ledger numbers or table thresholds."""

    intent: Intent
    language: str
    location: str
    window: str | None = None
    verdict: str | None = None  # "GO" | "CAUTION" | "DO NOT SAIL"
    verdict_status: str | None = None
    vessel: str | None = None
    reasons: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(
        default_factory=list
    )  # "wave height 1.02 m (open_meteo/marine, forecast for 06:00 IST, 8 km from your point)"
    pfz: list[str] = Field(default_factory=list)
    pfz_date: str | None = None
    boundary: list[str] = Field(default_factory=list)
    analytics: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    degradation: list[str] = Field(default_factory=list)
    knowledge_answer: str | None = None
    allowed_numbers: set[float] = Field(default_factory=set)  # what verify() accepts


def _fmt_obs(o, label: str) -> str:
    age = o.age()
    age_s = (
        f"{age.total_seconds() / 60:.0f} min"
        if age.total_seconds() < 7200
        else f"{age.total_seconds() / 3600:.0f} h"
    )
    # A fresh cache hit is "current" to the user; only stale cache / snapshot are degraded.
    freshness = {
        "live": "current",
        "cache": "current",
        "stale_cache": "OLDER CACHED DATA",
        "snapshot": "STORED SNAPSHOT",
    }[o.provenance]
    return f"{label} {o.value:g} {o.unit} [{o.id}; {o.source}; for {o.valid_time.astimezone().strftime('%H:%M')} local; grid {o.distance_km:g} km away; fetched {age_s} ago; {freshness}]"


def build_brief(
    plan: Plan,
    ledger: EvidenceLedger,
    ocean: OceanFinding | None,
    geo: GeoFinding | None,
    analytics: AnalyticsFinding | None,
    verdict: RiskVerdict | None,
) -> Brief:
    b = Brief(
        intent=plan.intent,
        language=plan.language,
        location=plan.location.name if plan.location else (plan.location_name or "your location"),
        knowledge_answer=plan.knowledge_answer,
    )
    nums: set[float] = set(ledger.values())
    if plan.intent == Intent.GENERAL_KNOWLEDGE:
        # "What does a 2 metre swell mean?" — the 2 is the asker's own premise, not a
        # measurement the model invented. Only for general knowledge: for a forecast question,
        # echoing the asker's number ("0.5 m tomorrow, right?") would look like confirmation.
        q = (plan.english_query or "").translate(_DIGIT_MAP)
        nums |= {float(m.group(1).replace(",", ".")) for m in _NUM.finditer(q)}
    if ocean:
        b.window = describe_window(ocean.window_start, ocean.window_end)
        nums |= {ocean.window_start.astimezone().hour, ocean.window_end.astimezone().hour}
        labels = {
            "significant_wave_height": "wave height",
            "wave_period": "wave period",
            "swell_height": "swell height",
            "swell_period": "swell period",
            "wind_speed": "wind",
            "wind_gust": "gusts",
            "wind_direction": "wind direction",
            "visibility": "visibility",
            "sea_surface_temperature": "sea temperature",
            "current_speed": "current",
            "current_direction": "current direction",
        }
        for var, label in labels.items():
            if var in ocean.summary:
                b.conditions.append(_fmt_obs(ocean.summary[var], label))
        b.degradation += [
            f"{s}: {p}" for s, p in ocean.sources.items() if p in ("stale_cache", "snapshot")
        ]
        b.gaps += ocean.missing
        b.gaps += [f"disagreement: {d}" for d in ocean.disagreements]
    if verdict:
        b.verdict, b.verdict_status, b.vessel = (
            verdict.label,
            verdict.status,
            verdict.vessel_class.value,
        )
        b.reasons = verdict.reasons
        b.gaps += verdict.data_gaps
        th = TABLES[verdict.vessel_class]
        for band in (th.wave_height_m, th.wind_kt, th.visibility_km, th.steepness):
            nums |= {band.caution, band.no_go}
        for p in verdict.parameters:
            if p.value is not None:
                nums.add(p.value)
    if geo:
        if geo.pfz:
            b.pfz_date = geo.pfz_date
            for i, z in enumerate(geo.pfz, 1):
                b.pfz.append(
                    f"PFZ #{i}: {z.distance_km:g} km {z.compass} (bearing {z.bearing_deg:g}°) from {b.location}, {z.state.title()} sector, advisory dated {z.advisory_date}"
                )
                nums |= {z.distance_km, z.bearing_deg, float(i)}
            nums.add(float(len(geo.pfz)))
        elif geo.pfz_note:
            b.pfz.append(geo.pfz_note)
        if geo.position:
            n = geo.position.nearest_imbl
            zone = {
                "eez": "inside India's EEZ",
                "land_or_port": "at an Indian harbour / on Indian land",
                "outside_india": "OUTSIDE Indian waters",
            }[geo.position.zone]
            b.boundary.append(
                f"position: {zone}"
                + (
                    f"; nearest maritime boundary: {n.name} ({n.other_state}) {n.distance_km:g} km to the {n.compass}"
                    if n
                    else ""
                )
            )
            if n:
                nums |= {n.distance_km, n.bearing_deg}
        if geo.crossing and geo.crossing.boundary:
            c = geo.crossing
            b.boundary.append(
                f"on the stated heading and speed the track reaches {c.boundary} in {c.minutes_to_crossing:g} min ({c.distance_to_crossing_km:g} km)"
                + (
                    " — WITHIN the 90 min warning horizon"
                    if c.crosses_within_horizon
                    else " — beyond the 90 min horizon"
                )
            )
            nums |= {c.minutes_to_crossing, c.distance_to_crossing_km, 90.0}
    if analytics:
        if analytics.latest:
            b.analytics.append(_fmt_obs(analytics.latest, "chlorophyll-a"))
            b.analytics.append(
                f"{analytics.baseline_days}-day baseline mean {analytics.baseline_mean:g} mg/m3 (sd {analytics.baseline_sd:g}); latest is {analytics.z_score:g} standard deviations from it; 7-day trend {analytics.trend}"
            )
            b.analytics.append(f"interpretation: {analytics.interpretation}")
            nums |= {
                analytics.baseline_days,
                analytics.baseline_mean,
                analytics.baseline_sd,
                analytics.z_score,
                7.0,
            }
        b.gaps += analytics.missing
    for m in ledger.missing:
        line = f"{m.variable}: {m.reason}"
        if line not in b.gaps and not any(m.variable in g for g in b.gaps):
            b.gaps.append(line)
    b.degradation += sorted(
        {f"{s}: {p}" for s, p in ledger.sources().items() if p in ("stale_cache", "snapshot")}
        - set(b.degradation)
    )
    # Every observation line in the brief prints its grid distance ("grid 1.8 km away"), which
    # is part of the ledger record but not its value — without this the deterministic template
    # failed its own verification whenever it quoted a chlorophyll line.
    nums |= {o.distance_km for o in ledger.observations}
    # …and its age ("fetched 14 min ago"), rounded exactly as _fmt_obs prints it.
    now = datetime.now(UTC)
    for o in ledger.observations:
        secs = o.age(now).total_seconds()
        nums |= {round(secs / 60), round(secs / 3600)}
    allowed = {float(x) for x in nums if x is not None}
    # The scanner reads "-0.62" as 0.62 (a leading hyphen is too often a dash or a range), so a
    # negative ledger value must also be accepted by its magnitude.
    b.allowed_numbers = allowed | {abs(x) for x in allowed if x < 0}
    return b


# -- template answer (no model needed) ---------------------------------------------------------


def template_answer(b: Brief) -> str:
    """Deterministic English answer, valid by construction. The floor when no LLM is available,
    and the fallback when the verifier rejects the model's draft twice."""
    lines: list[str] = []
    if b.intent == Intent.OFF_TOPIC:
        return "I can only help with sea conditions, fishing zones and maritime boundaries along the Indian coast. Ask me, for example: 'Is it safe to go out from Kochi tomorrow morning?'"
    if b.intent == Intent.GENERAL_KNOWLEDGE:
        return (
            (b.knowledge_answer or "")
            + "\n\nThis is general guidance, not today's forecast. Ask me about a specific harbour and day for live conditions."
        )
    if b.verdict:
        lines.append(
            f"{b.verdict} — {b.vessel} craft off {b.location}, {b.window}."
            + (
                " (Insufficient data for a full assessment.)"
                if b.verdict_status == "insufficient_data"
                else ""
            )
        )
        for r in b.reasons:
            lines.append(f"• {r}")
    elif b.window:
        lines.append(f"Conditions off {b.location}, {b.window}:")
    for c in b.conditions:
        lines.append(f"• {c.split(' [')[0]}")
    if b.pfz:
        lines.append(
            f"Fishing zones (INCOIS PFZ advisory {b.pfz_date or ''}):"
            if b.pfz_date
            else "Fishing zones:"
        )
        lines += [f"• {p}" for p in b.pfz]
    lines += [f"• {x}" for x in b.boundary]
    lines += [f"• {x}" for x in b.analytics]
    if b.degradation:
        lines.append("Data note: " + "; ".join(b.degradation) + ".")
    if b.gaps:
        lines.append("Not available: " + "; ".join(g.split(":")[0] for g in b.gaps) + ".")
    return "\n".join(lines)


# -- model draft -------------------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """You write the reply of a marine safety assistant for small-craft fishermen on the Indian coast. You will receive a BRIEF containing a verdict computed by a deterministic safety engine and the evidence behind it.

Absolute rules:
1. If the BRIEF has a VERDICT line, that verdict (GO / CAUTION / DO NOT SAIL) is final: state it first, plainly, and never soften it, hedge it, or add your own judgement about safety. If the BRIEF has NO VERDICT line, no safety assessment was made: do not write GO, CAUTION, DO NOT SAIL, safe, or unsafe anywhere in the reply — report the facts only.
2. Use ONLY numbers that appear in the BRIEF. Do not compute, convert, round differently, or estimate any number. If a value is not in the BRIEF, do not mention one.
3. If the BRIEF has a "degradation" section, one sentence of your reply MUST say that some data is old or from a stored copy (name which: wind/weather or waves) because the live source did not answer. If it lists "data gaps", say in one short sentence what could not be checked. The user must know what we could not check.
4. Write in {language}. Simple spoken register, as to a working fisherman, not a scientist. Short sentences. No markdown headers, no bullet symbols, at most 6 sentences unless the BRIEF has many findings.
5. Give the practical bearing and distance for fishing zones as a fisherman would use them (compass point and km).
6. Do not add safety tips, disclaimers or advice beyond what the BRIEF supports.
7. Do not mention the evidence ids like obs_0012, the source names, or the word BRIEF.
8. Keep each number with the unit the BRIEF gives it, translated correctly: kt = knots (a SPEED — wind, gusts, boat speed; never seconds), s = seconds (wave period), m = metres, km = kilometres, mg/m3 = milligrams per cubic metre. Knots in Tamil is நாட், in Hindi नॉट, in Malayalam നോട്ട്."""


def brief_text(b: Brief) -> str:
    parts = [f"intent: {b.intent}", f"location: {b.location}"]
    if b.window:
        parts.append(f"window: {b.window}")
    if b.verdict:
        parts.append(f"VERDICT: {b.verdict} (status {b.verdict_status}) for a {b.vessel} craft")
        parts.append(
            "reasons:\n"
            + ("\n".join(f"- {r}" for r in b.reasons) or "- none; all parameters within limits")
        )
    if b.conditions:
        parts.append("conditions (worst in window):\n" + "\n".join(f"- {c}" for c in b.conditions))
    if b.pfz:
        parts.append("fishing zones:\n" + "\n".join(f"- {p}" for p in b.pfz))
    if b.boundary:
        parts.append("boundary:\n" + "\n".join(f"- {x}" for x in b.boundary))
    if b.analytics:
        parts.append("analytics:\n" + "\n".join(f"- {x}" for x in b.analytics))
    if b.degradation:
        parts.append("degradation:\n" + "\n".join(f"- {d}" for d in b.degradation))
    if b.gaps:
        parts.append("data gaps:\n" + "\n".join(f"- {g}" for g in b.gaps))
    if b.knowledge_answer:
        parts.append(f"knowledge answer to convey: {b.knowledge_answer}")
    return "\n".join(parts)


async def draft(llm: LLM, b: Brief, *, correction: str | None = None) -> AsyncIterator[str]:
    system = SYNTHESIS_SYSTEM.format(language=LANG_NAMES.get(b.language, b.language))
    user = "BRIEF:\n" + brief_text(b)
    if correction:
        user += f"\n\nYour previous draft was rejected: {correction}\nWrite it again following the rules."
    async for chunk in llm.stream(system, user, max_tokens=700):
        yield chunk


# -- verifier ----------------------------------------------------------------------------------------

_DIGIT_MAP = {
    ord(c): str(i)
    for digits in (
        "०१२३४५६७८९",
        "௦௧௨௓௔௕௖ௗ௘௙",
        "൦൧൨൩൪൫൬൭൮൯",
        "౦౧౨౩౪౫౬౭౮౯",
        "೦೧೨೩೪೫೬೭೮೯",
        "૦૧૨૩૪૫૬૭૮૯",
        "০১২৩৪৫৬৭৮৯",
        "୦୧୨୩୪୫୬୭୮୯",
    )
    for i, c in enumerate(digits)
}
_NUM = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)(?![\w.]*\d)")
_UNIT_AFTER = re.compile(
    r"^\s*(?:m\b|km\b|kt\b|knots?\b|metres?\b|meters?\b|°|deg|nm\b|mg|h\b|hours?\b|min)",
    re.IGNORECASE,
)
_CONTRADICT = ("safe to go", "you can go", "it is safe", "go ahead", "fine to sail", "ok to go")
_VERDICT_WORDS = re.compile(r"\b(GO|CAUTION|DO NOT SAIL|NO[- ]GO)\b|(?i:\b(un)?safe\b)")


class Verification(BaseModel):
    ok: bool
    numbers_found: list[float] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)
    contradiction: str | None = None


def _close(x: float, allowed: set[float]) -> bool:
    for a in allowed:
        if (
            x == a
            or abs(x - a) <= 0.011
            or (a != 0 and abs(x - round(a)) < 1e-9)
            or (a != 0 and abs(x - round(a, 1)) < 1e-9)
        ):
            return True
    return False


_DATE_TIME = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"  # 2026-09-15
    r"|\b\d{1,2}:\d{2}\b"  # 05:00
    r"|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b"  # 17 Sep
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}\b"  # Sep 17
    r"|\b(?:19|20)\d{2}\b",  # a bare year
    re.IGNORECASE,
)


def verify(text: str, b: Brief) -> Verification:
    """Every number in the draft must be in the brief. Dates and clock times are not
    measurements and are removed before scanning."""
    t = _DATE_TIME.sub(" ", text.translate(_DIGIT_MAP))
    found: list[float] = []
    bad: list[str] = []
    for m in _NUM.finditer(t):
        raw = m.group(1).replace(",", ".")
        try:
            x = float(raw)
        except ValueError:
            continue
        found.append(x)
        if _close(x, b.allowed_numbers):
            continue
        # bare small integers not followed by a unit (e.g. "3 things") are tolerated
        if x.is_integer() and 0 <= x <= 3 and not _UNIT_AFTER.match(t[m.end() : m.end() + 8]):
            continue
        bad.append(m.group(0))
    contradiction = None
    if b.verdict == "DO NOT SAIL" and b.language == "en":
        low = t.lower()
        hit = next((c for c in _CONTRADICT if c in low), None)
        if hit:
            contradiction = f"verdict is DO NOT SAIL but the draft says '{hit}'"
    if b.verdict is None and b.intent not in (Intent.GENERAL_KNOWLEDGE, Intent.OFF_TOPIC):
        # No engine verdict exists, so the prose may not supply one (rule 1).
        m = _VERDICT_WORDS.search(t)
        if m:
            contradiction = f"no safety verdict was computed but the draft says '{m.group(0)}'"
    return Verification(
        ok=not bad and contradiction is None,
        numbers_found=found,
        unsupported=bad,
        contradiction=contradiction,
    )


# Sentinel passed to on_chunk when a draft was rejected and a fresh one begins.
RESET = "\x00RESET\x00"


class Answer(BaseModel):
    text: str
    language: str
    verdict: str | None
    source: str  # "llm" | "llm_retry" | "template" | "template_fallback"
    verification: Verification
    brief: Brief
    elapsed_ms: int = 0

    @property
    def degradation(self) -> list[str]:
        """For the UI banner: shown from the ledger, never dependent on the prose."""
        return self.brief.degradation

    @property
    def gaps(self) -> list[str]:
        return self.brief.gaps


async def synthesize(llm: LLM | None, b: Brief, *, on_chunk=None) -> Answer:
    """Draft with the model (streaming chunks to `on_chunk`), verify, retry once, else template."""
    t0 = datetime.now(UTC)
    if b.intent == Intent.CLARIFY:
        raise ValueError("clarify plans are answered by the graph, not synthesised")
    if llm is None:
        text = template_answer(b)
        return Answer(
            text=text,
            language="en",
            verdict=b.verdict,
            source="template",
            verification=verify(text, b),
            brief=b,
        )
    correction = None
    for attempt in ("llm", "llm_retry"):
        try:
            chunks: list[str] = []
            if attempt == "llm_retry" and on_chunk:
                await on_chunk(RESET)  # the rejected draft must vanish from the screen
            async for ch in draft(llm, b, correction=correction):
                chunks.append(ch)
                if on_chunk:
                    await on_chunk(ch)
            text = "".join(chunks).strip()
        except LLMUnavailable:
            break
        v = verify(text, b)
        if v.ok and text:
            return Answer(
                text=text,
                language=b.language,
                verdict=b.verdict,
                source=attempt,
                verification=v,
                brief=b,
                elapsed_ms=int((datetime.now(UTC) - t0).total_seconds() * 1000),
            )
        correction = (
            f"it contained numbers not in the BRIEF: {', '.join(v.unsupported)}"
            if v.unsupported
            else ""
        ) + (f"; {v.contradiction}" if v.contradiction else "")
    text = template_answer(b)
    return Answer(
        text=text,
        language="en",
        verdict=b.verdict,
        source="template_fallback",
        verification=verify(text, b),
        brief=b,
        elapsed_ms=int((datetime.now(UTC) - t0).total_seconds() * 1000),
    )
