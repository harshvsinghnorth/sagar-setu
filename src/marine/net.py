"""Per-host circuit breaker for every outbound request (data sources and the language model).

On a dead or captive network a request does not fail at once — it waits out its whole
timeout (2 s for a source, longer for the model), and the next question pays it again. After
a CONNECTION-level failure (cannot connect, connect timed out, proxy refused) the host is
skipped for BREAKER_S seconds: callers go straight to their fallback (stale cache, snapshot,
deterministic fast path) and say so. A slow-but-reachable server (read timeout, HTTP 5xx)
does not trip it — that is per-request trouble, not "the network is gone".
"""

from __future__ import annotations

import time

import httpx

from marine.config import settings

BREAKER_S = 60.0
CONNECT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError)

_down: dict[str, tuple[float, str]] = {}  # host -> (monotonic time it was marked, error name)


def host_of(url: str) -> str:
    return httpx.URL(url).host


def skip_reason(url: str) -> str | None:
    """Why this URL's host is being skipped right now, or None if it may be tried."""
    if settings.force_offline:
        return "offline mode (FORCE_OFFLINE=1)"
    rec = _down.get(host_of(url))
    if rec is None:
        return None
    age = time.monotonic() - rec[0]
    if age >= BREAKER_S:
        _down.pop(host_of(url), None)
        return None
    return f"{rec[1]} {age:.0f} s ago; not retried for {BREAKER_S - age:.0f} s"


def record_failure(url: str, exc: BaseException) -> None:
    if isinstance(exc, CONNECT_ERRORS):
        _down[host_of(url)] = (time.monotonic(), type(exc).__name__)


def record_success(url: str) -> None:
    _down.pop(host_of(url), None)


def down_hosts() -> list[str]:
    """Hosts being skipped right now (for /health and the interface's status line)."""
    if settings.force_offline:
        return ["*"]
    now = time.monotonic()
    return sorted(h for h, (t, _) in _down.items() if now - t < BREAKER_S)


def reset() -> None:
    _down.clear()
