"""Land mask for route search: Natural Earth 1:10m land + minor islands (public domain),
clipped to lon 64–100, lat 0–27 — data/static/ne_10m_land_india_region.geojson.

Finer than the Marine Regions EEZ outline, which treats narrow islands as sea (a route from
Rameswaram could cut straight across the island and the Dhanushkodi strip). Still a
1:10 000 000 product: it closes the Pamban channel between Rameswaram island and the
mainland, and it misses small harbour features. Routes are advice, never a chart.
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import shapely
from shapely.geometry import shape

from marine.config import STATIC_DIR

LAND_FILE = STATIC_DIR / "ne_10m_land_india_region.geojson"


@lru_cache(maxsize=1)
def load_land():
    data = json.loads(LAND_FILE.read_text(encoding="utf-8"))
    land = shapely.union_all([shape(f["geometry"]) for f in data["features"]])
    shapely.prepare(land)
    return land


def is_land(lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    return shapely.contains_xy(load_land(), lons, lats)
