"""Open-Meteo marine + weather. The reliability floor: answers in ~300 ms, no key.

Verified 2026-09-15 (docs/data-sources.md). Response lat/lon is the grid node, not the query
point — that offset is recorded as `distance_km`. Currents arrive in km/h, visibility in m.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from marine.ledger import Observation
from marine.sources.base import JsonSource, PointQuery, haversine_km

KMH_TO_KT = 0.539957

# open-meteo field → (our variable, our unit, factor)
MARINE_VARS: dict[str, tuple[str, str, float]] = {
    "wave_height": ("significant_wave_height", "m", 1.0),
    "wave_period": ("wave_period", "s", 1.0),
    "wave_direction": ("wave_direction", "deg", 1.0),
    "swell_wave_height": ("swell_height", "m", 1.0),
    "swell_wave_period": ("swell_period", "s", 1.0),
    "swell_wave_direction": ("swell_direction", "deg", 1.0),
    "wind_wave_height": ("wind_wave_height", "m", 1.0),
    "wind_wave_period": ("wind_wave_period", "s", 1.0),
    "sea_surface_temperature": ("sea_surface_temperature", "degC", 1.0),
    "ocean_current_velocity": ("current_speed", "kt", KMH_TO_KT),
    "ocean_current_direction": ("current_direction", "deg", 1.0),
}
WEATHER_VARS: dict[str, tuple[str, str, float]] = {
    "wind_speed_10m": ("wind_speed", "kt", 1.0),  # requested in kn
    "wind_gusts_10m": ("wind_gust", "kt", 1.0),
    "wind_direction_10m": ("wind_direction", "deg", 1.0),
    "visibility": ("visibility", "km", 0.001),
    "precipitation": ("precipitation", "mm", 1.0),
    "weather_code": ("weather_code", "wmo_code", 1.0),
    "cape": ("cape", "J/kg", 1.0),
}


def _parse_hourly(
    payload: dict, q: PointQuery, table: dict[str, tuple[str, str, float]]
) -> list[Observation]:
    hourly = payload.get("hourly") or {}
    times = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in hourly.get("time", [])]
    dist = haversine_km(q.lat, q.lon, payload["latitude"], payload["longitude"])
    placeholder = datetime.now(UTC)
    out: list[Observation] = []
    for field, (var, unit, factor) in table.items():
        for t, v in zip(times, hourly.get(field) or [], strict=False):
            if v is None or not (q.start <= t <= q.end):
                continue
            out.append(
                Observation(
                    variable=var,
                    value=round(v * factor, 3),
                    unit=unit,
                    source="",
                    valid_time=t,
                    fetched_at=placeholder,
                    distance_km=round(dist, 1),
                    confidence=1.0,
                )
            )
    return out


def _shift_window(payload: dict, q: PointQuery) -> PointQuery | None:
    """Snapshot fallback for a window the snapshot does not cover: same hours-of-day on the
    last full day the snapshot has. Caller labels the result loudly."""
    times = (payload.get("hourly") or {}).get("time") or []
    if not times:
        return None
    last = datetime.fromisoformat(times[-1]).replace(tzinfo=UTC)
    span = q.end - q.start
    end = last.replace(hour=q.end.hour, minute=0, second=0, microsecond=0)
    if end > last:
        end -= timedelta(days=1)
    return PointQuery(lat=q.lat, lon=q.lon, start=end - span, end=end)


class OpenMeteoMarine(JsonSource):
    name = "open_meteo/marine"
    snapshot_key = "open_meteo_marine"
    ttl = timedelta(hours=1)

    def url(self, q: PointQuery) -> str:
        return (
            "https://marine-api.open-meteo.com/v1/marine"
            f"?latitude={q.lat}&longitude={q.lon}&hourly={','.join(MARINE_VARS)}"
            "&past_days=1&forecast_days=8&timezone=UTC"
        )

    def parse(self, payload: dict, q: PointQuery) -> list[Observation]:
        return _parse_hourly(payload, q, MARINE_VARS)

    shift_window = staticmethod(_shift_window)


class OpenMeteoWeather(JsonSource):
    name = "open_meteo/weather"
    snapshot_key = "open_meteo_weather"
    ttl = timedelta(hours=1)

    def url(self, q: PointQuery) -> str:
        return (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={q.lat}&longitude={q.lon}&hourly={','.join(WEATHER_VARS)}"
            "&wind_speed_unit=kn&past_days=1&forecast_days=8&timezone=UTC"
        )

    def parse(self, payload: dict, q: PointQuery) -> list[Observation]:
        return _parse_hourly(payload, q, WEATHER_VARS)

    shift_window = staticmethod(_shift_window)
