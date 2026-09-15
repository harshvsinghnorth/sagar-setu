"""Risk thresholds per vessel class.

CALIBRATION STATUS — provisional. The traditional-craft numbers are the starting values from
CLAUDE.md. They must be replaced with INCOIS's published small-craft / high-wave alert
criteria and IMD's fishermen-warning criteria as soon as someone finds the official
documents, and the citation recorded here. Until then every verdict carries
`calibration="provisional"` so the UI can say so.

Known reference points to check against when calibrating (from memory, unverified):
- IMD issues a "fishermen warning" when sustained wind is expected to reach ~45 km/h (24 kt).
- INCOIS High Wave Alert is issued for significant wave height around 3 m and above.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

CALIBRATION = (
    "provisional — CLAUDE.md starting values, not yet calibrated against INCOIS/IMD criteria"
)


class Level(IntEnum):
    """Ordered so that max() gives the worst. Worst-of wins; never average."""

    GO = 0
    CAUTION = 1
    NO_GO = 2


class VesselClass(StrEnum):
    TRADITIONAL = "traditional"  # < 12 m: canoes, catamarans, small FRP boats
    MOTORISED = "motorised"  # 12–20 m: motorised country craft
    MECHANISED = "mechanised"  # > 20 m: trawlers, gill-netters

    @classmethod
    def from_length_m(cls, length_m: float) -> VesselClass:
        if length_m < 12:
            return cls.TRADITIONAL
        if length_m <= 20:
            return cls.MOTORISED
        return cls.MECHANISED


@dataclass(frozen=True)
class Band:
    """Value < caution → GO; caution ≤ value < no_go → CAUTION; value ≥ no_go → NO_GO.
    For `lower_is_worse` parameters (visibility) the comparison is inverted."""

    caution: float
    no_go: float
    lower_is_worse: bool = False

    def level(self, value: float) -> Level:
        if self.lower_is_worse:
            if value <= self.no_go:
                return Level.NO_GO
            if value <= self.caution:
                return Level.CAUTION
            return Level.GO
        if value >= self.no_go:
            return Level.NO_GO
        if value >= self.caution:
            return Level.CAUTION
        return Level.GO


@dataclass(frozen=True)
class Thresholds:
    wave_height_m: Band
    wind_kt: Band
    # Sea steepness proxy Hs / T² (m/s²). 0.04 ≈ steep short-period chop, 0.06 ≈ breaking regime.
    steepness: Band
    visibility_km: Band
    # Nearest lightning strike distance, km. Any strike inside `no_go` is a no-go.
    lightning_km: Band
    # Hours until the cyclone cone of uncertainty intersects the area. ≤ no_go hours is no-go.
    cyclone_hours: Band


TABLES: dict[VesselClass, Thresholds] = {
    VesselClass.TRADITIONAL: Thresholds(
        wave_height_m=Band(caution=1.5, no_go=2.5),
        wind_kt=Band(caution=19.0, no_go=27.0),
        steepness=Band(caution=0.04, no_go=0.06),
        visibility_km=Band(caution=5.0, no_go=2.0, lower_is_worse=True),
        lightning_km=Band(caution=100.0, no_go=50.0, lower_is_worse=True),
        cyclone_hours=Band(caution=120.0, no_go=48.0, lower_is_worse=True),
    ),
    VesselClass.MOTORISED: Thresholds(
        wave_height_m=Band(caution=2.0, no_go=3.0),
        wind_kt=Band(caution=22.0, no_go=30.0),
        steepness=Band(caution=0.045, no_go=0.07),
        visibility_km=Band(caution=5.0, no_go=2.0, lower_is_worse=True),
        lightning_km=Band(caution=100.0, no_go=50.0, lower_is_worse=True),
        cyclone_hours=Band(caution=120.0, no_go=48.0, lower_is_worse=True),
    ),
    VesselClass.MECHANISED: Thresholds(
        wave_height_m=Band(caution=2.5, no_go=3.5),
        wind_kt=Band(caution=27.0, no_go=34.0),
        steepness=Band(caution=0.05, no_go=0.08),
        visibility_km=Band(caution=5.0, no_go=2.0, lower_is_worse=True),
        lightning_km=Band(caution=100.0, no_go=50.0, lower_is_worse=True),
        cyclone_hours=Band(caution=120.0, no_go=48.0, lower_is_worse=True),
    ),
}

# Open-Meteo WMO weather codes that mean thunderstorm — a convective proxy, NOT lightning data.
THUNDERSTORM_CODES = {95, 96, 99}
# CAPE (J/kg) above which convection is likely enough to flag caution when we have no
# lightning feed. Proxy only.
CAPE_CAUTION_JKG = 2000.0
