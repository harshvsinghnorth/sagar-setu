"""Route search on the real boundary data with synthetic sea states. No network.

The Palk Bay corner is the case that matters: the IMBL bends towards India near
9.67°N 79.38°E, so the straight line between two Indian points can cut into Sri Lankan water.
"""

from __future__ import annotations

import numpy as np
import pytest

from marine.geo.boundaries import nearest_imbl, position_status
from marine.geo.geodesy import haversine_km
from marine.geo.route import KMH_PER_KT, SeaField, plan_route
from marine.risk.thresholds import VesselClass

PALK_SOUTH, PALK_NORTH = (9.35, 79.40), (9.95, 79.45)  # both Indian; the line between is not
KACHCHATHEEVU = (9.38, 79.52)  # Sri Lankan island
OFF_KOCHI, KOCHI_OFFSHORE = (10.00, 76.15), (10.50, 75.80)  # open Arabian Sea, no IMBL near


def sea(
    south=8.5, north=10.8, west=75.4, east=80.4, *, wave=0.6, period=8.0, wind=8.0,
    current=0.0, current_to=0.0, override=None,
) -> SeaField:
    la, lo = np.meshgrid(np.arange(south, north, 0.1), np.arange(west, east, 0.1), indexing="ij")
    la, lo = la.ravel(), lo.ravel()
    n = len(la)
    w = np.full(n, wave)
    if override is not None:
        w = np.where(override(la, lo), 3.0, w)
    return SeaField(
        la, lo, w, np.full(n, period), np.full(n, 225.0), np.full(n, wind), np.full(n, 225.0),
        np.full(n, current), np.full(n, current_to),
    )


def _samples(path, every_km=0.5):
    for a, b in zip(path, path[1:], strict=False):
        k = max(int(haversine_km(*a, *b) / every_km), 2)
        for t in np.linspace(0, 1, k):
            yield a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def test_route_bends_round_the_palk_bay_corner_instead_of_crossing_the_imbl():
    r = plan_route(PALK_SOUTH, PALK_NORTH, sea(), margin_km=2.0)
    assert r.direct.crosses_border  # the straight line would enter Sri Lankan waters
    assert r.found and r.min_imbl_km >= 2.0
    assert r.distance_km > r.direct.distance_km  # the detour costs a little distance
    # Every point of the smoothed route — not just its waypoints — is Indian water,
    # at least ~2 km inside the line (allowing for the 2 km grid).
    for lat, lon in _samples(r.path):
        assert position_status(lat, lon).zone == "eez"
        assert nearest_imbl(lat, lon).distance_km >= 1.5


def test_route_refuses_a_destination_in_sri_lankan_waters():
    r = plan_route((9.29, 79.31), KACHCHATHEEVU, sea())
    assert not r.found and "outside Indian waters" in r.reason
    assert r.direct.crosses_border


def test_route_detours_round_do_not_sail_water_when_it_can():
    mid = ((OFF_KOCHI[0] + KOCHI_OFFSHORE[0]) / 2, (OFF_KOCHI[1] + KOCHI_OFFSHORE[1]) / 2)
    storm = sea(override=lambda la, lo: np.hypot(la - mid[0], lo - mid[1]) < 0.13)
    r = plan_route(OFF_KOCHI, KOCHI_OFFSHORE, storm)
    assert r.direct.max_wave_m == 3.0  # the straight line runs through the 3 m patch
    assert r.found and r.avoided_hazard
    assert r.max_wave_m < 2.5  # below the traditional-craft do-not-sail threshold


def test_route_goes_through_hazard_only_when_nothing_avoids_it():
    r = plan_route(OFF_KOCHI, KOCHI_OFFSHORE, sea(wave=3.0))
    assert r.found and r.reason == "no route avoids do-not-sail water"
    assert not r.avoided_hazard and r.max_wave_m == 3.0


def test_bigger_boat_is_not_detoured_by_water_within_its_limits():
    # 3.0 m is do-not-sail for a traditional craft but only caution for a mechanised one.
    r = plan_route(OFF_KOCHI, KOCHI_OFFSHORE, sea(wave=3.0), vessel=VesselClass.MECHANISED)
    assert r.found and r.reason is None


def test_eta_is_plain_travel_time_and_a_following_current_shortens_it():
    calm = plan_route(OFF_KOCHI, KOCHI_OFFSHORE, sea(), speed_kt=7.0)
    expected = calm.distance_km / (7.0 * KMH_PER_KT) * 60
    assert calm.eta_min == pytest.approx(expected, abs=1.0)
    # Current of 1.5 kt flowing towards the north-west — roughly along the route.
    helped = plan_route(OFF_KOCHI, KOCHI_OFFSHORE, sea(current=1.5, current_to=325.0), speed_kt=7.0)
    assert helped.eta_min < calm.eta_min


def test_a_harbour_on_land_is_snapped_to_open_water():
    r = plan_route((9.29, 79.31), (9.80, 79.30), sea())  # Rameswaram harbour → Palk Bay
    assert r.found and 0 < r.start_snap_km < 6
    assert position_status(*r.path[0]).zone == "eez"
