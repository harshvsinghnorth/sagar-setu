"""Cyclone (GDACS) and official lightning-warning (NDMA SACHET) checks, on real responses saved
on 2026-11-04 (tests/fixtures, trimmed but unchanged in structure). No network.

Murasu-26 was a 157 km/h storm that came ashore on the Andhra coast on 3 November 2026; the
SACHET file holds the lightning warnings in force that morning over the Godavari delta."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from marine.agents.localize import localized_template
from marine.agents.planner import Intent, detect_script
from marine.agents.synthesis import Brief, verify
from marine.geo.hazards import cyclone_threat, nearest_lightning_warning
from marine.risk.rules import RiskInputs, evaluate
from marine.risk.thresholds import Level
from marine.sources import gdacs, sachet
from marine.sources.base import FetchOutcome, SourceUnavailable
from marine.tools import RiskQuery, ToolContext, assess_sailing_risk
from marine.tools.hazards import HazardQuery, check_hazards

FIX = Path(__file__).parent / "fixtures"
NIZAMPATNAM, MACHILIPATNAM, KOCHI = (15.90, 80.67), (16.14, 81.20), (9.97, 76.28)
KAKINADA, VISAKHAPATNAM = (16.94, 82.26), (17.69, 83.29)
DURING_MURASU = datetime(2026, 11, 4, 2, tzinfo=UTC)
DAWN_2_NOV = datetime(2026, 11, 1, 23, 30, tzinfo=UTC)  # 05:00 IST, 2 November
IST = sachet.IST


def _json(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def murasu(advisory: int) -> gdacs.Storm:
    props = gdacs.active_in_basin(_json("gdacs_tc_list_2026-11-04.json"), DURING_MURASU)[0]
    return gdacs.parse_storm(
        {**props, "episodeid": advisory}, _json(f"gdacs_murasu_advisory_{advisory}.json")
    )


def warnings() -> list[sachet.Warning]:
    return sachet.parse_alerts(_json("sachet_alerts_2026-11-04.json"))


def _outcome(prov="live") -> FetchOutcome:
    return FetchOutcome(payload={}, provenance=prov, fetched_at=datetime.now(UTC), latency_ms=5)


# -- GDACS parsing -------------------------------------------------------------------------------


def test_only_current_storms_in_the_north_indian_ocean_are_active():
    listing = _json("gdacs_tc_list_2026-11-04.json")
    # In-fa (west Pacific) and Vance (east Pacific) are outside the basin; Arnab had ended.
    assert [p["eventname"] for p in gdacs.active_in_basin(listing, DURING_MURASU)] == ["MURASU-26"]
    # GDACS still lists Murasu as "current" a week later; 48 h without an advisory = ended.
    assert gdacs.active_in_basin(listing, datetime(2026, 11, 12, tzinfo=UTC)) == []


def test_advisory_is_parsed_into_cone_wind_field_and_timed_track():
    s = murasu(3)
    assert s.agency == "JTWC" and s.episode_id == 3
    assert s.issued == datetime(2026, 11, 1, 12, tzinfo=UTC)
    assert s.cone is not None and s.swath is not None and len(s.radii) == 6
    # Track times come from the labels ("02/11 12:00 UTC"), not polygondate (= advisory time).
    assert [p.time.day for p in s.track] == [1, 1, 1, 2, 2, 3, 3, 4]
    assert s.track[3].time == datetime(2026, 11, 2, 0, tzinfo=UTC)


def test_label_time_crosses_the_year_boundary():
    near = datetime(2027, 1, 1, 6, tzinfo=UTC)
    assert gdacs._label_time("31/12 18:00 UTC", near) == datetime(2026, 12, 31, 18, tzinfo=UTC)


# -- cyclone geometry ----------------------------------------------------------------------------


def test_harbour_inside_the_forecast_wind_field_is_threatened_with_the_arrival_time():
    t = cyclone_threat(murasu(3), *NIZAMPATNAM, DAWN_2_NOV)
    assert t.affected and t.via == "wind field" and t.hours == 0.5
    # A later advisory moved the landfall north: the winds now arrive on 3 November.
    later = cyclone_threat(murasu(10), *NIZAMPATNAM, DAWN_2_NOV)
    assert later.affected and later.hours == 30.5
    assert later.arrives == datetime(2026, 11, 3, 6, tzinfo=UTC)


def test_harbour_outside_cone_and_wind_field_is_not_threatened_but_distance_is_given():
    t = cyclone_threat(murasu(10), *MACHILIPATNAM, DAWN_2_NOV)
    assert not t.affected and t.track_km == pytest.approx(113.3, abs=0.1)
    k = cyclone_threat(murasu(10), *KOCHI, DAWN_2_NOV)
    assert not k.affected and k.track_km > 600


def test_a_storm_that_has_passed_no_longer_threatens():
    t = cyclone_threat(murasu(10), *NIZAMPATNAM, datetime(2026, 11, 6, 23, 30, tzinfo=UTC))
    assert not t.affected and t.passed


@pytest.mark.parametrize(
    "hours, level", [(0.5, Level.NO_GO), (30.5, Level.NO_GO), (100, Level.CAUTION), (130, Level.GO)]
)
def test_cyclone_hours_follow_the_specification_bands(hours, level):
    v = evaluate(
        RiskInputs(
            wave_height_m=0.5,
            wind_kt=5,
            cyclone_data_available=True,
            cyclone_hours=hours,
            cyclone_name="MURASU-26",
        )
    )
    p = next(p for p in v.parameters if p.parameter == "cyclone")
    assert p.level == level and "MURASU-26" in p.reason


# -- lightning warnings --------------------------------------------------------------------------


def test_sachet_times_and_alerts_are_parsed():
    assert sachet.parse_when("Wed Nov 04 09:40:00 IST 2026") == datetime(
        2026, 11, 4, 9, 40, tzinfo=IST
    )
    assert sachet.parse_when("04/11/2026 09:40") is None
    ws = warnings()
    assert len(ws) == 11  # 15 alerts in force; the 4 rain-only ones are not lightning
    assert all(w.radius_km and w.radius_km > 0 for w in ws)


def test_warning_covering_the_harbour_and_one_nearby_are_told_apart():
    s, e = datetime(2026, 11, 4, 8, tzinfo=IST), datetime(2026, 11, 4, 10, tzinfo=IST)
    hit, n = nearest_lightning_warning(warnings(), *KAKINADA, s, e)
    assert n == 11 and hit.covered and hit.distance_km == 0.0
    hit, _ = nearest_lightning_warning(warnings(), *VISAKHAPATNAM, s, e)
    assert not hit.covered and hit.distance_km == pytest.approx(82.9, abs=0.1)


def test_a_warning_that_names_the_district_covers_it_even_outside_the_circle():
    s, e = datetime(2026, 11, 4, 8, tzinfo=IST), datetime(2026, 11, 4, 10, tzinfo=IST)
    hit, _ = nearest_lightning_warning(warnings(), 25.0, 80.0, s, e, district="South 24 Parganas")
    assert hit.covered and hit.named


def test_warnings_do_not_reach_into_tomorrow():
    s, e = datetime(2026, 11, 5, 5, tzinfo=IST), datetime(2026, 11, 5, 12, tzinfo=IST)
    assert nearest_lightning_warning(warnings(), *KAKINADA, s, e) == (None, 0)


@pytest.mark.parametrize(
    "km, level, words",
    [(0.0, Level.NO_GO, "covers this area"), (30.0, Level.CAUTION, "30 km away")],
)
def test_lightning_warning_rule(km, level, words):
    v = evaluate(
        RiskInputs(
            wave_height_m=0.5,
            wind_kt=5,
            weather_code=3,
            cape_jkg=100,
            lightning_warnings_checked=True,
            lightning_warning_km=km,
            lightning_warning_text="Lightning, IMD Chennai",
        )
    )
    p = next(p for p in v.parameters if p.parameter == "lightning")
    assert p.level == level and words in p.reason and "IMD Chennai" in p.reason
    assert v.level == level  # worst-of: calm sea does not soften it


def test_a_warning_beyond_50_km_leaves_the_weather_model_signal_in_charge():
    v = evaluate(
        RiskInputs(
            wave_height_m=0.5,
            wind_kt=5,
            weather_code=95,
            lightning_warnings_checked=True,
            lightning_warning_km=80.0,
        )
    )
    p = next(p for p in v.parameters if p.parameter == "lightning")
    assert p.level == Level.CAUTION and p.status == "proxy"
    assert p.reason.startswith("no official lightning warning near this area")


# -- the tool: fetch, ledger, verdict ------------------------------------------------------------


@pytest.fixture
def murasu_morning(monkeypatch):
    """Both feeds answer with what they said around landfall, without the network."""

    async def storms(now=None):
        return gdacs.CycloneFeed(storms=[murasu(10)], outcome=_outcome())

    async def alerts(now=None):
        return sachet.WarningFeed(warnings=warnings(), outcome=_outcome())

    monkeypatch.setattr(gdacs, "fetch_active_storms", storms)
    monkeypatch.setattr(sachet, "fetch_lightning_warnings", alerts)


async def test_cyclone_threat_reaches_the_verdict_through_the_ledger(murasu_morning):
    ctx = ToolContext()
    s, e = DAWN_2_NOV, DAWN_2_NOV + timedelta(hours=7)
    res = await check_hazards(
        ctx, HazardQuery(lat=NIZAMPATNAM[0], lon=NIZAMPATNAM[1], start=s, end=e)
    )
    assert res.cyclone_checked and res.lightning_checked
    assert any("MURASU-26 is forecast to affect this area in about 30.5 h" in x for x in res.lines)
    hours = ctx.ledger.series("cyclone_cone_hours")[0]
    assert hours.value == 30.5 and hours.source == "gdacs/tc" and "JTWC" in hours.note
    v = assess_sailing_risk(ctx, RiskQuery(lat=NIZAMPATNAM[0], lon=NIZAMPATNAM[1], start=s, end=e))
    cyc = next(p for p in v.parameters if p.parameter == "cyclone")
    assert v.level == Level.NO_GO and cyc.evidence == [hours.id]


async def test_lightning_warning_reaches_the_verdict_through_the_ledger(murasu_morning):
    ctx = ToolContext()
    s, e = datetime(2026, 11, 4, 8, tzinfo=IST), datetime(2026, 11, 4, 10, tzinfo=IST)
    res = await check_hazards(ctx, HazardQuery(lat=KAKINADA[0], lon=KAKINADA[1], start=s, end=e))
    assert any("covers this area until" in x for x in res.lines)
    v = assess_sailing_risk(ctx, RiskQuery(lat=KAKINADA[0], lon=KAKINADA[1], start=s, end=e))
    lit = next(p for p in v.parameters if p.parameter == "lightning")
    assert lit.level == Level.NO_GO and lit.evidence
    # Strike locations are still not available, and the answer must keep saying so.
    assert any(m.variable == "lightning_strikes" for m in ctx.ledger.missing)


async def test_a_feed_that_fails_is_never_read_as_no_threat(monkeypatch):
    async def down(now=None):
        raise SourceUnavailable("gdacs/tc: ConnectError; no copy newer than 6 h")

    monkeypatch.setattr(gdacs, "fetch_active_storms", down)
    monkeypatch.setattr(sachet, "fetch_lightning_warnings", down)
    ctx = ToolContext()
    s = datetime.now(UTC)
    res = await check_hazards(
        ctx, HazardQuery(lat=KOCHI[0], lon=KOCHI[1], start=s, end=s + timedelta(hours=3))
    )
    assert not res.cyclone_checked and not res.lightning_checked
    v = assess_sailing_risk(
        ctx, RiskQuery(lat=KOCHI[0], lon=KOCHI[1], start=s, end=s + timedelta(hours=3))
    )
    cyc = next(p for p in v.parameters if p.parameter == "cyclone")
    assert cyc.status == "missing" and cyc.level is None
    assert {m.variable for m in ctx.ledger.missing} >= {"cyclone", "lightning_warnings"}


async def test_an_active_storm_without_a_forecast_makes_the_check_incomplete(monkeypatch):
    async def partial(now=None):
        return gdacs.CycloneFeed(
            storms=[], outcome=_outcome(), unresolved=[("MURASU-26", 15.8, 80.2)]
        )

    monkeypatch.setattr(gdacs, "fetch_active_storms", partial)
    ctx = ToolContext()
    s = DAWN_2_NOV
    res = await check_hazards(
        ctx,
        HazardQuery(lat=NIZAMPATNAM[0], lon=NIZAMPATNAM[1], start=s, end=s + timedelta(hours=3)),
    )
    assert not res.cyclone_checked
    assert any("could not be loaded" in x for x in res.lines)
    v = assess_sailing_risk(
        ctx, RiskQuery(lat=NIZAMPATNAM[0], lon=NIZAMPATNAM[1], start=s, end=s + timedelta(hours=3))
    )
    assert next(p for p in v.parameters if p.parameter == "cyclone").status == "missing"


async def test_nothing_is_ever_served_from_the_frozen_snapshot(monkeypatch, tmp_path):
    """A cyclone or warning answer from an old copy would be a confident falsehood."""
    from marine.sources import base

    async def offline(url, ttl, timeout_s=None):
        return "ConnectError"

    monkeypatch.setattr(gdacs, "try_live", offline)
    monkeypatch.setattr(sachet, "try_live", offline)
    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    with pytest.raises(SourceUnavailable):
        await gdacs.fetch_active_storms()
    with pytest.raises(SourceUnavailable):
        await sachet.fetch_lightning_warnings()


# -- the answer ----------------------------------------------------------------------------------

HAZARD_LINES = [
    "cyclone check: MURASU-26 is forecast to affect this area in about 30.5 h; "
    "its forecast track passes 51.3 km away",
    "lightning check: official Lightning warning from Andhra Pradesh SDMA is 82.9 km away, "
    "in force until 11:40 IST",
]


@pytest.mark.parametrize("lang", ["ta", "hi", "ml"])
def test_hazard_lines_are_translated_with_every_number_kept(lang):
    b = Brief(
        intent=Intent.SAFETY,
        language=lang,
        location="Nizampatnam",
        window="Mon 02 Nov 05:00–12:00 IST",
        verdict="DO NOT SAIL",
        verdict_status="verdict",
        vessel="traditional",
        reasons=[
            "storm MURASU-26 is forecast to reach this area in 30.5 h, inside the 48 h no-go limit"
        ],
        hazards=HAZARD_LINES,
        allowed_numbers={30.5, 48.0, 51.3, 82.9, 26.0, 2.0, 5.0, 12.0},
    )
    text = localized_template(b)
    assert detect_script(text) == lang
    assert (
        "cyclone check" not in text and "lightning check" not in text and "no-go limit" not in text
    )
    for n in ("30.5", "51.3", "82.9", "48"):
        assert n in text
    assert verify(text, b).ok


# -- an old fishing-zone advisory is said to be old ----------------------------------------------


def test_an_old_pfz_advisory_is_flagged_in_the_answer_with_its_age():
    from marine.agents.localize import Localizer
    from marine.agents.planner import Plan
    from marine.agents.specialists import GeoFinding
    from marine.agents.synthesis import build_brief, pfz_age_days
    from marine.ledger import EvidenceLedger

    assert pfz_age_days("2026-09-04", today=datetime(2026, 11, 13).date()) == 70
    assert pfz_age_days(None) is None
    plan = Plan(language="en", english_query="where are the fish", intent=Intent.PFZ)
    b = build_brief(plan, EvidenceLedger(), None, GeoFinding(pfz_date="2026-01-01"), None, None)
    note = next(d for d in b.degradation if d.startswith("incois/pfz: advisory dated 2026-01-01"))
    age = int(note.split(" is ")[1].split()[0])
    assert age > 300 and float(age) in b.allowed_numbers
    ta = Localizer("ta").degradation([note])
    assert str(age) in ta and "days old" not in ta
