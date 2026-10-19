import json
from datetime import UTC, datetime

import httpx
import pytest

from marine import net
from marine.config import SNAPSHOT_DIR
from marine.sources import base


@pytest.fixture(autouse=True)
def _fresh_circuit_breaker():
    """A host marked unreachable by one test must not be skipped in the next."""
    net.reset()
    yield
    net.reset()


# -- fixtures: network stub (same as test_tools) ------------------------------------------------


@pytest.fixture
def live_from_snapshot(monkeypatch, tmp_path):
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
    monkeypatch.setattr(
        base,
        "client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2.0),
    )
    base._inflight.clear()
    # freeze "now" to the snapshot day so 'tomorrow morning' is covered by the payloads
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
    snap_day = datetime.fromisoformat(manifest["created_at"]).astimezone(UTC)
    import marine.tools.windows as w

    real = w.named_window
    monkeypatch.setattr(
        w,
        "named_window",
        lambda day="tomorrow", part="morning", now=None: real(day, part, now=snap_day),
    )
    import marine.agents.specialists as sp

    monkeypatch.setattr(sp, "named_window", w.named_window)


@pytest.fixture
def network_down(monkeypatch, tmp_path):
    """Wifi off: every request fails to connect and the cache is empty, so every source
    falls to the frozen snapshot; 'tomorrow' is frozen to the snapshot day."""

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        base,
        "client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2.0),
    )
    base._inflight.clear()
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
    snap_day = datetime.fromisoformat(manifest["created_at"]).astimezone(UTC)
    import marine.agents.specialists as sp
    import marine.tools.windows as w

    real = w.named_window
    monkeypatch.setattr(
        w,
        "named_window",
        lambda day="tomorrow", part="morning", now=None: real(day, part, now=snap_day),
    )
    monkeypatch.setattr(sp, "named_window", w.named_window)
