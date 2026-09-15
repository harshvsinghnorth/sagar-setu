"""Source protocol and the cache → network → snapshot chain (CLAUDE.md rule 3).

A `JsonSource` knows how to build a URL for a point query and how to parse the payload into
`Observation`s. Everything about *where the bytes came from* — fresh cache, live network with
a 2 s budget, stale cache, or the frozen snapshot — lives here, so every source degrades the
same way and every observation carries honest provenance and confidence.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import httpx
import truststore
from pydantic import BaseModel

from marine.config import CACHE_DIR, SNAPSHOT_DIR, settings
from marine.ledger import Observation, Provenance

log = logging.getLogger(__name__)

# INCOIS serves an incomplete TLS chain that only the OS trust store can complete.
truststore.inject_into_ssl()

USER_AGENT = "Mozilla/5.0 SagarSetu/0.1 (marine decision support; research)"

CONFIDENCE: dict[Provenance, float] = {
    "live": 1.0,
    "cache": 0.95,
    "stale_cache": 0.7,
    "snapshot": 0.5,
}


class PointQuery(BaseModel):
    lat: float
    lon: float
    start: datetime
    end: datetime


class SourceUnavailable(Exception):
    """Raised when a source produced nothing — no live data, no cache, no snapshot."""


@dataclass
class FetchOutcome:
    payload: dict
    provenance: Provenance
    fetched_at: datetime
    latency_ms: int
    note: str | None = None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# -- HTTP client ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=settings.fetch_timeout_s,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    return _client


# -- disk cache ----------------------------------------------------------------------------


def _cache_path(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".json")


def cache_read(url: str) -> tuple[dict, datetime] | None:
    p = _cache_path(url)
    if not p.exists():
        return None
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
        return rec["payload"], datetime.fromisoformat(rec["fetched_at"])
    except (ValueError, KeyError):
        return None


def cache_write(url: str, payload: dict, fetched_at: datetime) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(url).write_text(
        json.dumps({"fetched_at": fetched_at.isoformat(), "payload": payload}), encoding="utf-8"
    )


# -- snapshot ------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def snapshot_manifest() -> dict:
    p = SNAPSHOT_DIR / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"points": {}, "global": {}}


def snapshot_lookup(
    key: str, lat: float | None, lon: float | None
) -> tuple[dict, datetime, str] | None:
    """Return (payload, fetched_at, note) from the frozen snapshot, nearest point if per-point."""
    m = snapshot_manifest()
    if key in m.get("global", {}):
        rec = m["global"][key]
        path, where = SNAPSHOT_DIR / f"{key}.json", "global"
    else:
        candidates = [
            (haversine_km(lat, lon, p["lat"], p["lon"]), name, p)
            for name, p in m.get("points", {}).items()
            if key in p.get("sources", {}) and p["sources"][key].get("status") == 200
        ]
        if lat is None or not candidates:
            return None
        dist, name, p = min(candidates)
        rec = p["sources"][key]
        path, where = (
            SNAPSHOT_DIR / name / f"{key}.json",
            f"{name} snapshot point, {dist:.0f} km away",
        )
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    fetched_at = datetime.fromisoformat(rec["fetched_at"])
    return payload, fetched_at, f"served from frozen snapshot ({where}), network unavailable"


# -- the chain -----------------------------------------------------------------------------


_inflight: dict[str, asyncio.Future] = {}


async def try_live(url: str, ttl: timedelta) -> FetchOutcome | str:
    """Fresh cache, else live network within the 2 s budget. Returns an error string on failure.
    Concurrent callers of the same URL (wind + visibility share one weather request) await
    one in-flight fetch instead of firing twice."""
    now = datetime.now(UTC)
    cached = cache_read(url)
    if cached and now - cached[1] <= ttl:
        return FetchOutcome(cached[0], "cache", cached[1], 0, None)
    if url in _inflight:
        return await _inflight[url]
    fut: asyncio.Future = asyncio.get_running_loop().create_future()
    _inflight[url] = fut
    try:
        result = await _network(url, now)
        fut.set_result(result)
        return result
    finally:
        _inflight.pop(url, None)


async def _network(url: str, now: datetime) -> FetchOutcome | str:
    t0 = time.perf_counter()
    try:
        r = await client().get(url)
        if r.status_code == 200:
            payload = r.json()
            cache_write(url, payload, now)
            return FetchOutcome(payload, "live", now, round((time.perf_counter() - t0) * 1000))
        error = f"HTTP {r.status_code}"
    except (TimeoutError, httpx.HTTPError, ValueError) as e:
        error = type(e).__name__
    log.warning(
        "fetch failed (%s) after %d ms: %s", error, (time.perf_counter() - t0) * 1000, url[:120]
    )
    return error


def try_fallback(
    url: str, error: str, snapshot_key: str | None, lat: float | None, lon: float | None
) -> FetchOutcome | None:
    """Stale cache of any age, else the frozen snapshot. None if neither exists."""
    now = datetime.now(UTC)
    cached = cache_read(url)
    if cached:
        age_h = (now - cached[1]).total_seconds() / 3600
        return FetchOutcome(
            cached[0],
            "stale_cache",
            cached[1],
            0,
            f"network failed ({error}); serving cached data {age_h:.1f} h old",
        )
    if snapshot_key:
        snap = snapshot_lookup(snapshot_key, lat, lon)
        if snap:
            payload, fetched_at, note = snap
            return FetchOutcome(payload, "snapshot", fetched_at, 0, f"{note} ({error})")
    return None


class JsonSource(ABC):
    """A JSON-over-HTTP source for point queries. Subclasses provide `url` and `parse`."""

    name: str
    snapshot_key: str | None = None
    ttl: timedelta = timedelta(hours=1)
    base_confidence: float = 1.0

    @abstractmethod
    def url(self, q: PointQuery) -> str: ...

    @abstractmethod
    def parse(self, payload: dict, q: PointQuery) -> list[Observation]:
        """Pure: payload → observations. Set variable/value/unit/valid_time/distance_km only;
        source, provenance, confidence, fetched_at, note are stamped by `_stamp`."""

    def _stamp(self, obs: list[Observation], outcome: FetchOutcome) -> list[Observation]:
        for o in obs:
            o.source = self.name
            o.provenance = outcome.provenance
            o.fetched_at = outcome.fetched_at
            o.confidence = round(self.base_confidence * CONFIDENCE[outcome.provenance], 3)
            o.latency_ms = outcome.latency_ms
            if outcome.note:
                o.note = f"{o.note}; {outcome.note}" if o.note else outcome.note
        return obs

    async def fetch_live(self, q: PointQuery) -> list[Observation] | str:
        out = await try_live(self.url(q), self.ttl)
        if isinstance(out, str):
            return out
        return self._stamp(self.parse(out.payload, q), out)

    def shift_window(self, payload: dict, q: PointQuery) -> PointQuery | None:  # noqa: ARG002
        """Optional: when a fallback payload does not cover `q`, propose a window it does cover
        (e.g. same hours on the snapshot's last day). Default: no shifting."""
        return None

    def fetch_fallback(self, q: PointQuery, error: str) -> list[Observation] | None:
        out = try_fallback(self.url(q), error, self.snapshot_key, q.lat, q.lon)
        if out is None:
            return None
        obs = self.parse(out.payload, q)
        if not obs:
            shifted = self.shift_window(out.payload, q)
            if shifted is not None:
                obs = self.parse(out.payload, shifted)
                if obs:
                    out.note = (
                        f"{out.note}; requested window not covered, showing "
                        f"{shifted.start:%Y-%m-%d %H:%M}–{shifted.end:%H:%M} UTC instead"
                    )
        return self._stamp(obs, out)

    async def fetch(self, q: PointQuery) -> list[Observation]:
        """Single-source convenience: live, then this source's own fallback."""
        return await SourceChain(self).fetch(q)


class SourceChain:
    """Rule 3: live down the chain first; only when every source failed, fall back to
    stale cache / snapshot, again in priority order. The snapshot is always available."""

    def __init__(self, *sources: JsonSource):
        self.sources = sources

    async def fetch(self, q: PointQuery) -> list[Observation]:
        errors: dict[str, str] = {}
        for s in self.sources:
            out = await s.fetch_live(q)
            if isinstance(out, list):
                if out:
                    return out
                errors[s.name] = "empty"
            else:
                errors[s.name] = out
        for s in self.sources:
            out = s.fetch_fallback(q, errors[s.name])
            if out:
                return out
        raise SourceUnavailable("; ".join(f"{k}: {v}" for k, v in errors.items()))

    @property
    def names(self) -> list[str]:
        return [s.name for s in self.sources]
