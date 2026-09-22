"""Tool belt tests. Network is stubbed: `offline` makes every request fail so the chain must
answer from the committed snapshot; `live_from_snapshot` serves snapshot payloads as if
they were live. Neither test touches the real internet."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from marine.config import SNAPSHOT_DIR
from marine.fixtures import GULF_OF_MANNAR, HARBOURS
from marine.risk.thresholds import Level, VesselClass
from marine.sources import base
from marine.tools import (
    LocationQuery,
    Point,
    RiskQuery,
    ToolContext,
    get_pfz_advisory,
    named_window,
    resolve_location,
    safety_briefing,
)

MANIFEST = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
SNAP_DAY = datetime.fromisoformat(MANIFEST["created_at"]).astimezone(UTC)


def _client_with(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2.0)


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Every request raises ConnectError; cache dir is empty → snapshot is the only way."""

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(base, "client", lambda: _client_with(handler))
    base._inflight.clear()


@pytest.fixture
def live_from_snapshot(monkeypatch, tmp_path):
    """Serve the Kochi snapshot payloads as 200s so provenance is 'live'."""

    def handler(request):
        host = request.url.host
        key = {
            "marine-api.open-meteo.com": "open_meteo_marine",
            "api.open-meteo.com": "open_meteo_weather",
            "coastwatch.noaa.gov": "noaa_viirs_chl",
        }.get(host)
        if host == "incois.gov.in":
            return httpx.Response(
                200,
                json=json.loads(
                    (SNAPSHOT_DIR / "incois_pfz_lines.json").read_text(encoding="utf-8")
                ),
            )
        if key is None:
            return httpx.Response(404)
        return httpx.Response(
            200,
            json=json.loads((SNAPSHOT_DIR / "kochi" / f"{key}.json").read_text(encoding="utf-8")),
        )

    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(base, "client", lambda: _client_with(handler))
    base._inflight.clear()


def snapshot_window():
    """A morning window the snapshot actually covers (day after the snapshot was taken)."""
    return named_window("tomorrow", "morning", now=SNAP_DAY)


# -- location resolver --------------------------------------------------------------------------


def test_resolve_harbour_exact():
    r = resolve_location(LocationQuery(name="Kochi"))
    assert r and r.match == "harbour" and (r.lat, r.lon) == HARBOURS["kochi"]


def test_resolve_landing_centre_with_sector():
    r = resolve_location(LocationQuery(name="Vypeen"))
    assert r and r.match == "landing_centre" and r.sector_id == "SEC005"


def test_resolve_fuzzy_spelling():
    r = resolve_location(LocationQuery(name="vypin"))
    assert r and r.name == "Vypeen" and r.match == "fuzzy"


def test_resolve_unknown_is_none_not_a_guess():
    assert resolve_location(LocationQuery(name="Atlantis")) is None


# -- windows ---------------------------------------------------------------------------------------


def test_named_window_tomorrow_morning_is_ist():
    now = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
    s, e = named_window("tomorrow", "morning", now=now)
    assert s == datetime(2026, 9, 15, 23, 30, tzinfo=UTC)  # 05:00 IST on the 16th
    assert e - s == timedelta(hours=7)


def test_named_window_today_rolls_forward_if_already_past():
    now = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)  # 17:30 IST
    s, _ = named_window("today", "morning", now=now)
    assert s.astimezone(UTC).day == 15 and s.hour == 23  # tomorrow's morning


# -- safety briefing offline -----------------------------------------------------------------------


async def test_offline_briefing_answers_from_snapshot_and_says_so(offline):
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = HARBOURS["kochi"]
    brief = await safety_briefing(ctx, RiskQuery(lat=lat, lon=lon, start=s, end=e))
    v = brief.verdict
    assert v.status == "verdict"
    assert v.level in (Level.GO, Level.CAUTION, Level.NO_GO)
    assert ctx.ledger.degraded()
    hs = next(p for p in v.parameters if p.parameter == "wave_height")
    obs = ctx.ledger.get(hs.evidence[0])
    assert obs.provenance == "snapshot"
    assert obs.confidence == 0.5
    assert "snapshot" in obs.note
    assert ctx.ledger.sources()["open_meteo/marine"] == "snapshot"


async def test_offline_briefing_far_from_any_snapshot_point_still_answers_and_labels_distance(
    offline,
):
    ctx = ToolContext()
    s, e = snapshot_window()
    brief = await safety_briefing(ctx, RiskQuery(lat=15.0, lon=73.5, start=s, end=e))  # off Goa
    obs = ctx.ledger.series("significant_wave_height")[0]
    assert obs.provenance == "snapshot"
    assert "snapshot point" in obs.note and "km away" in obs.note
    assert obs.distance_km > 100  # honest: the grid node is far from Goa
    assert brief.verdict.status == "verdict"


async def test_offline_pfz_from_snapshot(offline):
    ctx = ToolContext()
    lat, lon = HARBOURS["kochi"]
    r = await get_pfz_advisory(ctx, Point(lat=lat, lon=lon))
    assert r.source_status == "snapshot"
    assert r.zones and r.zones[0].state == "KERALA"
    d = next(o for o in r.observations if o.variable == "pfz_distance_km")
    assert d.confidence == 0.5 and d.provenance == "snapshot"


# -- safety briefing 'live' ------------------------------------------------------------------------


async def test_live_briefing_has_full_ledger_and_evidence_links(live_from_snapshot):
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = HARBOURS["kochi"]
    brief = await safety_briefing(ctx, RiskQuery(lat=lat, lon=lon, start=s, end=e))
    v = brief.verdict
    assert not ctx.ledger.degraded()
    assert {
        "significant_wave_height",
        "wave_period",
        "wind_speed",
        "wind_gust",
        "visibility",
        "cape",
        "weather_code",
    } <= ctx.ledger.variables()
    for p in v.parameters:
        for oid in p.evidence:
            assert ctx.ledger.get(oid) is not None
    # every evaluated value is a ledger value (what the verifier will enforce later)
    for p in v.parameters:
        if p.status == "evaluated" and p.parameter in ("wave_height", "wind", "visibility"):
            assert p.value in ctx.ledger.values()
    assert any("cyclone" in g for g in v.data_gaps)
    assert brief.elapsed_ms < 1000


async def test_live_briefing_uses_worst_value_in_window(live_from_snapshot):
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = HARBOURS["kochi"]
    brief = await safety_briefing(ctx, RiskQuery(lat=lat, lon=lon, start=s, end=e))
    hs = next(p for p in brief.verdict.parameters if p.parameter == "wave_height")
    assert hs.value == max(o.value for o in ctx.ledger.series("significant_wave_height", s, e))
    vis = next(p for p in brief.verdict.parameters if p.parameter == "visibility")
    assert vis.value == min(o.value for o in ctx.ledger.series("visibility", s, e))


async def test_gulf_of_mannar_heading_east_is_no_go_regardless_of_sea_state(live_from_snapshot):
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = GULF_OF_MANNAR
    brief = await safety_briefing(
        ctx,
        RiskQuery(
            lat=lat,
            lon=lon,
            start=s,
            end=e,
            heading_deg=90,
            speed_kt=8,
            vessel=VesselClass.MECHANISED,
        ),
    )
    v = brief.verdict
    assert v.level == Level.NO_GO
    b = next(p for p in v.parameters if p.parameter == "boundary")
    assert "Sri Lanka - India" in b.reason and b.level == Level.NO_GO
    assert ctx.ledger.series("boundary_crossing_min")[0].value == b.value


async def test_gulf_of_mannar_heading_west_boundary_is_go(live_from_snapshot):
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = GULF_OF_MANNAR
    brief = await safety_briefing(
        ctx, RiskQuery(lat=lat, lon=lon, start=s, end=e, heading_deg=270, speed_kt=8)
    )
    b = next(p for p in brief.verdict.parameters if p.parameter == "boundary")
    assert b.level == Level.GO


async def test_concurrent_same_url_fetches_share_one_request(live_from_snapshot, monkeypatch):
    calls = {"n": 0}
    real = base._network

    async def counting(url, now, timeout_s=None):
        calls["n"] += 1
        return await real(url, now, timeout_s)

    monkeypatch.setattr(base, "_network", counting)
    ctx = ToolContext()
    s, e = snapshot_window()
    lat, lon = HARBOURS["kochi"]
    await safety_briefing(ctx, RiskQuery(lat=lat, lon=lon, start=s, end=e))
    assert calls["n"] == 2  # one marine, one weather — not four


@pytest.mark.parametrize(
    "name,expected",
    [
        ("இராமேஸ்வரத்தில்", "Rameswaram"),  # Tamil, locative suffix
        ("கொச்சியில் இருந்து", "Kochi"),
        ("वेरावल से", "Veraval"),  # Hindi, "from Veraval"
        ("पारादीप", "Paradip"),
        ("കൊച്ചി", "Kochi"),  # Malayalam
    ],
)
def test_resolve_indic_script_names_deterministically(name, expected):
    r = resolve_location(LocationQuery(name=name))
    assert r is not None and r.name == expected
