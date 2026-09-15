"""The risk engine is the load-bearing wall. These tests pin its behaviour."""

import time

import pytest

from marine.risk.rules import RiskInputs, evaluate
from marine.risk.thresholds import TABLES, Level, VesselClass

CALM = dict(wave_height_m=0.8, wave_period_s=9.0, wind_kt=10.0, gust_kt=14.0, visibility_km=10.0)


def verdict(**kw):
    return evaluate(RiskInputs(**{**CALM, **kw}), kw.pop("vessel", VesselClass.TRADITIONAL))


# -- the shape of the verdict -----------------------------------------------------------------


def test_calm_conditions_are_go():
    v = verdict(weather_code=1, cape_jkg=200.0)
    assert v.level == Level.GO
    assert v.status == "verdict"
    assert v.reasons == []
    assert v.label == "GO"


def test_runs_under_50ms():
    t0 = time.perf_counter()
    for _ in range(100):
        verdict()
    assert (time.perf_counter() - t0) / 100 < 0.05


def test_every_parameter_is_reported_even_when_missing():
    v = verdict()
    names = {p.parameter for p in v.parameters}
    assert {"wave_height", "wind", "steepness", "visibility", "lightning", "cyclone"} <= names
    assert any("cyclone" in g for g in v.data_gaps)
    assert any("lightning" in g for g in v.data_gaps)


# -- worst-of wins, never average ---------------------------------------------------------------


def test_one_no_go_parameter_makes_the_whole_verdict_no_go():
    # Everything benign except wind. Averaging would call this "caution" or better.
    v = verdict(wind_kt=30.0)
    assert v.level == Level.NO_GO
    assert v.reasons[0].startswith("wind 30 kt")


def test_calm_sea_with_thunderstorm_proxy_is_not_go():
    # The thunderhead case from CLAUDE.md: waves calm, convection overhead.
    v = verdict(weather_code=95)
    assert v.level >= Level.CAUTION
    lightning = next(p for p in v.parameters if p.parameter == "lightning")
    assert lightning.status == "proxy"
    assert "thunderstorm" in lightning.reason


def test_calm_sea_with_real_lightning_close_is_no_go():
    v = verdict(lightning_data_available=True, lightning_km=30.0)
    assert v.level == Level.NO_GO
    assert any("lightning 30 km" in r for r in v.reasons)


def test_lightning_between_50_and_100_is_caution():
    v = verdict(lightning_data_available=True, lightning_km=80.0, lightning_closing=True)
    assert v.level == Level.CAUTION
    assert any("closing" in r for r in v.reasons)


def test_reasons_are_sorted_worst_first():
    v = verdict(wave_height_m=2.0, wind_kt=30.0)  # caution + no-go
    assert v.reasons[0].startswith("wind")
    assert v.reasons[1].startswith("wave_height")


# -- thresholds ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hs,expected",
    [
        (1.49, Level.GO),
        (1.5, Level.CAUTION),
        (2.49, Level.CAUTION),
        (2.5, Level.NO_GO),
        (4.0, Level.NO_GO),
    ],
)
def test_wave_height_bands_traditional(hs, expected):
    v = verdict(wave_height_m=hs, wave_period_s=12.0)  # long period keeps steepness benign
    assert next(p for p in v.parameters if p.parameter == "wave_height").level == expected


@pytest.mark.parametrize(
    "kt,expected", [(18.9, Level.GO), (19.0, Level.CAUTION), (27.0, Level.NO_GO)]
)
def test_wind_bands_traditional(kt, expected):
    v = verdict(wind_kt=kt)
    assert next(p for p in v.parameters if p.parameter == "wind").level == expected


@pytest.mark.parametrize(
    "vis,expected",
    [
        (6.0, Level.GO),
        (5.0, Level.CAUTION),
        (3.0, Level.CAUTION),
        (2.0, Level.NO_GO),
        (0.5, Level.NO_GO),
    ],
)
def test_visibility_is_lower_is_worse(vis, expected):
    v = verdict(visibility_km=vis)
    assert next(p for p in v.parameters if p.parameter == "visibility").level == expected


def test_gusts_at_no_go_escalate_a_calm_sustained_wind_to_caution():
    v = verdict(wind_kt=12.0, gust_kt=28.0)
    wind = next(p for p in v.parameters if p.parameter == "wind")
    assert wind.level == Level.CAUTION
    assert "gusts to 28 kt" in wind.reason


def test_steep_short_period_sea_is_flagged_even_when_height_is_within_limits():
    # 1.4 m at 5 s: below the 1.5 m wave band, but Hs/T² = 0.056 — a nasty chop for a canoe.
    v = verdict(wave_height_m=1.4, wave_period_s=5.0)
    steep = next(p for p in v.parameters if p.parameter == "steepness")
    assert steep.level == Level.CAUTION
    assert v.level == Level.CAUTION


def test_breaking_sea_regime_is_no_go():
    v = verdict(wave_height_m=2.4, wave_period_s=6.0)  # 0.067
    assert next(p for p in v.parameters if p.parameter == "steepness").level == Level.NO_GO
    assert v.level == Level.NO_GO


# -- vessel classes --------------------------------------------------------------------------


def test_same_sea_is_worse_for_a_smaller_boat():
    hs = 2.2
    trad = evaluate(
        RiskInputs(**{**CALM, "wave_height_m": hs, "wave_period_s": 12.0}), VesselClass.TRADITIONAL
    )
    mech = evaluate(
        RiskInputs(**{**CALM, "wave_height_m": hs, "wave_period_s": 12.0}), VesselClass.MECHANISED
    )
    assert trad.level == Level.CAUTION
    assert mech.level == Level.GO


def test_vessel_class_from_length():
    assert VesselClass.from_length_m(8) == VesselClass.TRADITIONAL
    assert VesselClass.from_length_m(12) == VesselClass.MOTORISED
    assert VesselClass.from_length_m(20) == VesselClass.MOTORISED
    assert VesselClass.from_length_m(20.1) == VesselClass.MECHANISED


def test_threshold_tables_are_monotonic_across_classes():
    t, m, x = (
        TABLES[c] for c in (VesselClass.TRADITIONAL, VesselClass.MOTORISED, VesselClass.MECHANISED)
    )
    assert t.wave_height_m.no_go < m.wave_height_m.no_go < x.wave_height_m.no_go
    assert t.wind_kt.no_go < m.wind_kt.no_go < x.wind_kt.no_go


# -- missing data can never produce GO ---------------------------------------------------------


def test_missing_wave_height_is_insufficient_data_not_go():
    v = evaluate(RiskInputs(wind_kt=5.0, visibility_km=10.0))
    assert v.status == "insufficient_data"
    assert v.level >= Level.CAUTION


def test_missing_wind_is_insufficient_data_not_go():
    v = evaluate(RiskInputs(wave_height_m=0.5, wave_period_s=10.0, visibility_km=10.0))
    assert v.status == "insufficient_data"
    assert v.level >= Level.CAUTION


def test_missing_critical_data_does_not_hide_a_no_go():
    v = evaluate(RiskInputs(wind_kt=35.0))
    assert v.status == "insufficient_data"
    assert v.level == Level.NO_GO


def test_no_inputs_at_all_is_caution_with_gaps_not_a_crash():
    v = evaluate(RiskInputs())
    assert v.status == "insufficient_data"
    assert v.level == Level.CAUTION
    assert len(v.data_gaps) >= 5


# -- cyclone and boundary ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "hours,expected",
    [
        (None, Level.GO),
        (150.0, Level.GO),
        (100.0, Level.CAUTION),
        (48.0, Level.NO_GO),
        (6.0, Level.NO_GO),
    ],
)
def test_cyclone_cone_hours(hours, expected):
    v = verdict(cyclone_data_available=True, cyclone_hours=hours)
    assert next(p for p in v.parameters if p.parameter == "cyclone").level == expected


def test_boundary_crossing_within_horizon_is_no_go():
    v = verdict(boundary_crossing_min=40.0, boundary_name="Sri Lanka - India")
    assert v.level == Level.NO_GO
    assert any("Sri Lanka - India" in r and "40 min" in r for r in v.reasons)


def test_boundary_crossing_beyond_horizon_is_reported_but_go():
    v = verdict(boundary_crossing_min=180.0)
    b = next(p for p in v.parameters if p.parameter == "boundary")
    assert b.level == Level.GO
    assert "beyond the 90 min horizon" in b.reason


def test_outside_indian_waters_is_no_go():
    v = verdict(outside_indian_waters=True, boundary_name="Sri Lanka - India")
    assert v.level == Level.NO_GO


# -- evidence linkage --------------------------------------------------------------------------


def test_parameter_verdicts_carry_ledger_evidence_ids():
    v = verdict(evidence={"wave_height": ["obs_0001", "obs_0002"], "wind": ["obs_0003"]})
    assert next(p for p in v.parameters if p.parameter == "wave_height").evidence == [
        "obs_0001",
        "obs_0002",
    ]
    assert next(p for p in v.parameters if p.parameter == "wind").evidence == ["obs_0003"]
