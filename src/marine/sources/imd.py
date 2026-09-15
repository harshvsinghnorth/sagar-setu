"""IMD (India Meteorological Department).

Verified 2026-09-15: every `api.imd.gov.in/api/v1/*` endpoint returns
`401 {"error": "API key missing"}` and the public mausam.imd.gov.in variant needs IP
whitelisting. Until the team obtains a key this module reports *why* cyclone and lightning
data are missing, so the answer can say so instead of guessing (CLAUDE.md: degrade loudly).

When `IMD_API_KEY` is set, `available()` flips to True and the fetchers below run. Their
request/response shapes are a best guess from the documentation and MUST be verified live
before being trusted — hence they raise `NotVerified` rather than returning data.
"""

from __future__ import annotations

from marine.config import settings

BASE = "https://api.imd.gov.in/api/v1"
SOURCE_NAME = "imd"

MISSING_REASON = (
    "IMD API requires an API key (401 'API key missing' on 2026-09-15); "
    "no live cyclone-track or lightning feed until one is configured"
)


class NotVerified(Exception):
    """The endpoint exists but its response shape has never been observed by us."""


def available() -> bool:
    return bool(settings.imd_api_key)


def missing_reason() -> str:
    return MISSING_REASON if not available() else "IMD endpoint shape not yet verified live"


async def fetch_cyclone_cone() -> dict:
    if not available():
        raise NotVerified(MISSING_REASON)
    raise NotVerified(f"{BASE}/cyclone_cou: key present but response schema unverified")


async def fetch_lightning() -> dict:
    if not available():
        raise NotVerified(MISSING_REASON)
    raise NotVerified(f"{BASE}/lightning: key present but response schema unverified")
