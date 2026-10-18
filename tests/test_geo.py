"""Geofencing and PFZ geometry against the real static data in data/static/."""

import json
import time

import pytest

from marine.config import SNAPSHOT_DIR
from marine.fixtures import GULF_OF_MANNAR, HARBOURS
from marine.geo.boundaries import nearest_imbl, position_status, predict_crossing
from marine.geo.geodesy import compass_point, destination, haversine_km, initial_bearing_deg
from marine.geo.pfz import nearest_zones
from marine.sources.incois_pfz import parse_zones

# -- geodesy -----------------------------------------------------------------------------------


def test_haversine_kochi_to_chennai():
    d = haversine_km(*HARBOURS["kochi"], *HARBOURS["chennai"])
    assert 550 < d < 570  # ~560 km great-circle


def test_bearing_and_destination_round_trip():
    lat, lon = HARBOURS["kochi"]
    lat2, lon2 = destination(lat, lon, 250.0, 40.0)
    assert abs(haversine_km(lat, lon, lat2, lon2) - 40.0) < 0.01
    assert abs(initial_bearing_deg(lat, lon, lat2, lon2) - 250.0) < 0.05


@pytest.mark.parametrize("brg,name", [(0, "N"), (44, "NE"), (90, "E"), (247, "WSW"), (359, "N")])
def test_compass_points(brg, name):
    assert compass_point(brg) == name


# -- position / IMBL --------------------------------------------------------------------------


@pytest.mark.parametrize("harbour", list(HARBOURS))
def test_every_harbour_is_on_indian_land_or_port(harbour):
    s = position_status(*HARBOURS[harbour])
    assert s.zone == "land_or_port"
    assert s.nearest_imbl is not None


def test_gulf_of_mannar_is_in_eez_near_the_sri_lanka_line():
    s = position_status(*GULF_OF_MANNAR)
    assert s.zone == "eez"
    assert s.nearest_imbl.name == "Sri Lanka - India"
    assert s.nearest_imbl.other_state == "Sri Lanka"
    assert 10 < s.nearest_imbl.distance_km < 20


def test_point_across_the_sri_lanka_line_is_outside_india():
    s = position_status(9.0, 79.6)
    assert s.zone == "outside_india"
    assert s.nearest_imbl.name == "Sri Lanka - India"
    assert s.nearest_imbl.distance_km < 15


def test_open_ocean_far_south_is_outside_india():
    assert position_status(5.0, 70.0).zone == "outside_india"


def test_position_status_is_fast_after_warmup():
    position_status(*GULF_OF_MANNAR)
    t0 = time.perf_counter()
    for _ in range(20):
        position_status(*GULF_OF_MANNAR)
    assert (time.perf_counter() - t0) / 20 < 0.05


# -- predictive geofence ------------------------------------------------------------------------


def test_heading_east_from_gulf_of_mannar_crosses_the_line_within_90_min():
    c = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=8)
    assert c.crosses_within_horizon
    assert c.boundary == "Sri Lanka - India"
    assert c.other_state == "Sri Lanka"
    assert 0 < c.minutes_to_crossing <= 90
    assert 10 < c.distance_to_crossing_km < 25


def test_heading_west_from_gulf_of_mannar_does_not_cross_within_90_min():
    c = predict_crossing(*GULF_OF_MANNAR, heading_deg=270, speed_kt=8)
    assert not c.crosses_within_horizon


def test_slower_boat_takes_longer_to_reach_the_line():
    fast = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=12)
    slow = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=4)
    assert fast.distance_to_crossing_km == pytest.approx(slow.distance_to_crossing_km, abs=0.2)
    assert slow.minutes_to_crossing > fast.minutes_to_crossing * 2.5


def test_crossing_beyond_horizon_is_still_reported():
    c = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=2)  # ~4 h away
    assert not c.crosses_within_horizon
    assert c.boundary == "Sri Lanka - India"
    assert c.minutes_to_crossing > 90


def test_stationary_vessel_never_crosses():
    c = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=0)
    assert not c.crosses_within_horizon and c.boundary is None


def test_track_samples_are_every_5_minutes():
    c = predict_crossing(*GULF_OF_MANNAR, heading_deg=90, speed_kt=8, horizon_min=90)
    assert len(c.track) == 19  # t = 0, 5, …, 90


def test_nearest_imbl_bearing_points_at_the_closest_point():
    n = nearest_imbl(*GULF_OF_MANNAR)
    d = haversine_km(*GULF_OF_MANNAR, n.closest_lat, n.closest_lon)
    assert d == pytest.approx(n.distance_km, abs=0.5)


# -- PFZ geometry ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def zones():
    payload = json.loads((SNAPSHOT_DIR / "incois_pfz_lines.json").read_text(encoding="utf-8"))
    z = parse_zones(payload)
    assert len(z) > 0
    return z


def test_pfz_parse_reads_state_and_date(zones):
    z = zones[0]
    assert z.state and z.advisory_date.year >= 2026
    assert z.length_km > 0
    assert z.coordinates and len(z.coordinates[0]) >= 2


def test_nearest_pfz_from_kochi_is_kerala_and_offshore(zones):
    hits = nearest_zones(*HARBOURS["kochi"], zones)
    assert hits and hits[0].state == "KERALA"
    assert hits[0].distance_km < 100
    assert hits[0].compass in {"W", "WSW", "SW", "SSW", "WNW", "NW", "S", "SSE"}  # seaward of Kochi
    d = haversine_km(*HARBOURS["kochi"], hits[0].nearest_lat, hits[0].nearest_lon)
    assert d == pytest.approx(hits[0].distance_km, abs=0.5)


def test_no_pfz_within_range_returns_empty_not_a_guess(zones):
    # When a sector has no advisory nearby, the right answer is "none", not a number. Built
    # from the data rather than assumed: drop every Gujarat zone, and Veraval has nothing
    # within range. (The first version asserted the September snapshot had no Gujarat
    # advisory — true that day, false on the next refresh.)
    others = [z for z in zones if z.state != "GUJARAT"]
    assert nearest_zones(*HARBOURS["veraval"], others) == []


def test_nearest_zones_are_sorted_and_capped(zones):
    hits = nearest_zones(*HARBOURS["paradip"], zones, k=2)
    assert len(hits) == 2
    assert hits[0].distance_km <= hits[1].distance_km
