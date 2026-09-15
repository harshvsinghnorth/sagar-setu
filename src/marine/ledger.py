"""The evidence ledger.

Every number that reaches the user passes through here first (CLAUDE.md rule 2). Tools
return `Observation`s, never bare floats; the synthesis step may only cite values that are
in the ledger, and the verifier strips anything else.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

Provenance = Literal["live", "cache", "stale_cache", "snapshot"]


class Observation(BaseModel):
    variable: str  # "significant_wave_height"
    value: float
    unit: str  # "m"
    source: str  # "open_meteo/marine"
    valid_time: datetime  # when the observation/forecast is FOR
    fetched_at: datetime  # when we got it
    distance_km: float  # query point → nearest grid node
    confidence: float = Field(ge=0.0, le=1.0)  # lowered when we fell down the chain
    note: str | None = None  # "served from snapshot, network unavailable"
    provenance: Provenance = "live"
    latency_ms: int | None = None
    id: str = ""  # assigned by the ledger; what the verifier matches citations against

    def age(self, now: datetime | None = None) -> timedelta:
        """How old the fetch is. Staleness is shown prominently in the UI."""
        return (now or datetime.now(UTC)) - self.fetched_at

    def lead(self, now: datetime | None = None) -> timedelta:
        """How far ahead of `now` the value is valid for (negative = past)."""
        return self.valid_time - (now or datetime.now(UTC))


class MissingObservation(BaseModel):
    """A variable we tried to get and could not. Recorded so the answer can say so."""

    variable: str
    reason: str  # "IMD API key not configured", "no grid coverage within 300 km"
    sources_tried: list[str] = Field(default_factory=list)


class EvidenceLedger(BaseModel):
    observations: list[Observation] = Field(default_factory=list)
    missing: list[MissingObservation] = Field(default_factory=list)

    # -- writing ---------------------------------------------------------------------------

    def add(self, obs: Observation) -> Observation:
        obs.id = f"obs_{len(self.observations) + 1:04d}"
        self.observations.append(obs)
        return obs

    def extend(self, observations: list[Observation]) -> list[Observation]:
        return [self.add(o) for o in observations]

    def add_missing(
        self, variable: str, reason: str, sources_tried: list[str] | None = None
    ) -> None:
        self.missing.append(
            MissingObservation(variable=variable, reason=reason, sources_tried=sources_tried or [])
        )

    # -- reading ---------------------------------------------------------------------------

    def series(
        self, variable: str, start: datetime | None = None, end: datetime | None = None
    ) -> list[Observation]:
        """All observations of one variable, sorted by valid_time, optionally windowed."""
        out = [o for o in self.observations if o.variable == variable]
        if start is not None:
            out = [o for o in out if o.valid_time >= start]
        if end is not None:
            out = [o for o in out if o.valid_time <= end]
        return sorted(out, key=lambda o: o.valid_time)

    def at(self, variable: str, when: datetime) -> Observation | None:
        """The observation of `variable` whose valid_time is nearest to `when`."""
        s = self.series(variable)
        if not s:
            return None
        return min(s, key=lambda o: abs((o.valid_time - when).total_seconds()))

    def worst(
        self, variable: str, start: datetime, end: datetime, higher_is_worse: bool = True
    ) -> Observation | None:
        """The most adverse value in a window — what the risk engine wants (worst-of wins)."""
        s = self.series(variable, start, end)
        if not s:
            return None
        return max(s, key=lambda o: o.value) if higher_is_worse else min(s, key=lambda o: o.value)

    def variables(self) -> set[str]:
        return {o.variable for o in self.observations}

    def get(self, obs_id: str) -> Observation | None:
        return next((o for o in self.observations if o.id == obs_id), None)

    def values(self) -> set[float]:
        """Every numeric value present. The verifier checks claims against this set."""
        return {o.value for o in self.observations}

    def degraded(self) -> bool:
        """True if anything is stale or from the snapshot. A fresh cache hit is not degraded."""
        return any(o.provenance in ("stale_cache", "snapshot") for o in self.observations)

    def sources(self) -> dict[str, Provenance]:
        """Worst provenance seen per source — for the 'this is cached data' banner."""
        rank = {"live": 0, "cache": 1, "stale_cache": 2, "snapshot": 3}
        out: dict[str, Provenance] = {}
        for o in self.observations:
            if o.source not in out or rank[o.provenance] > rank[out[o.source]]:
                out[o.source] = o.provenance
        return out
