"""Per-request tool context: the ledger every tool writes to, and the source chains."""

from __future__ import annotations

from dataclasses import dataclass, field

from marine.ledger import EvidenceLedger
from marine.sources.base import SourceChain
from marine.sources.incois_erddap import IncoisArgoTemperature
from marine.sources.noaa_chl import NoaaViirsChlorophyll
from marine.sources.open_meteo import OpenMeteoMarine, OpenMeteoWeather


def default_chains() -> dict[str, SourceChain]:
    """Open-Meteo is the floor of every chain (CLAUDE.md). When Copernicus / INCOIS live
    products are wired in they go *in front* of it, never instead of it."""
    return {
        "marine": SourceChain(OpenMeteoMarine()),
        "weather": SourceChain(OpenMeteoWeather()),
        "chlorophyll": SourceChain(NoaaViirsChlorophyll()),
        "argo": SourceChain(IncoisArgoTemperature()),
    }


@dataclass
class ToolContext:
    ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    chains: dict[str, SourceChain] = field(default_factory=default_chains)
