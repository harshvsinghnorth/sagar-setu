"""Circuit breaker: after a connection failure a host is skipped for a while, so a dead network
costs one timeout per host, not one per request. No real network."""

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from marine import net
from marine.agents.llm import GeminiLLM, LLMUnavailable
from marine.sources import base

URL = "https://marine-api.open-meteo.com/v1/marine?latitude=9.97"
REQ = httpx.Request("GET", URL)


def test_connection_failures_trip_the_breaker_slow_servers_do_not():
    net.record_failure(URL, httpx.ReadTimeout("slow", request=REQ))
    assert net.skip_reason(URL) is None  # reachable but slow: try again next time
    net.record_failure(URL, httpx.ConnectTimeout("gone", request=REQ))
    assert "ConnectTimeout" in net.skip_reason(URL)
    assert net.skip_reason("https://api.open-meteo.com/v1/forecast") is None  # per host


def test_breaker_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(net.time, "monotonic", lambda: now[0])
    net.record_failure(URL, httpx.ConnectError("x", request=REQ))
    now[0] += net.BREAKER_S - 1
    assert net.skip_reason(URL) is not None
    now[0] += 2
    assert net.skip_reason(URL) is None


def test_force_offline_refuses_every_host(monkeypatch):
    monkeypatch.setattr(net.settings, "force_offline", True)
    assert "FORCE_OFFLINE" in net.skip_reason(URL)
    assert "FORCE_OFFLINE" in net.skip_reason("https://generativelanguage.googleapis.com/v1beta")
    assert net.down_hosts() == ["*"]


def test_a_success_clears_the_host():
    net.record_failure(URL, httpx.ConnectError("x", request=REQ))
    net.record_success(URL)
    assert net.skip_reason(URL) is None


def test_source_fetch_skips_a_host_that_just_failed(monkeypatch, tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        raise httpx.ConnectError("offline", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(base, "client", lambda: client)
    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    first = asyncio.run(base._network(URL, datetime.now(UTC)))
    second = asyncio.run(base._network(URL + "&x=1", datetime.now(UTC)))
    assert first == "ConnectError"
    assert second.startswith("host unreachable") and len(calls) == 1


def test_gemini_fails_at_once_after_a_connection_failure():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("offline", request=request)

    g = GeminiLLM("k", "m1", fallbacks=["m2"])
    g.transport = httpx.MockTransport(handler)
    with pytest.raises(LLMUnavailable, match="ConnectError"):
        asyncio.run(g.complete("s", "u"))
    with pytest.raises(LLMUnavailable, match="host unreachable"):
        asyncio.run(g.complete("s", "u"))
    assert len(calls) == 1
