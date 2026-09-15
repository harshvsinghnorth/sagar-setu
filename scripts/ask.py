"""Phase 2 exit criterion: answer "is it safe off <harbour> tomorrow" from the tool belt
alone — no LLM — with the verdict, its reasons, and the full evidence ledger.

  uv run python scripts/ask.py kochi
  uv run python scripts/ask.py "fort kochi" --day today --part afternoon --vessel motorised
  uv run python scripts/ask.py --lat 9.15 --lon 79.40 --heading 90 --speed 8   # Gulf of Mannar
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.risk.thresholds import VesselClass  # noqa: E402
from marine.tools import (  # noqa: E402
    LocationQuery,
    Point,
    RiskQuery,
    ToolContext,
    get_pfz_advisory,
    named_window,
    resolve_location,
    safety_briefing,
)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("place", nargs="?", default="kochi")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--day", default="tomorrow", choices=["today", "tomorrow", "day_after"])
    ap.add_argument("--part", default="morning")
    ap.add_argument("--vessel", default="traditional", choices=[v.value for v in VesselClass])
    ap.add_argument("--heading", type=float)
    ap.add_argument("--speed", type=float)
    ap.add_argument("--ledger", action="store_true", help="print every ledger row")
    a = ap.parse_args()

    t0 = time.perf_counter()
    ctx = ToolContext()
    if a.lat is not None and a.lon is not None:
        name, lat, lon = f"{a.lat:.2f}N {a.lon:.2f}E", a.lat, a.lon
    else:
        loc = resolve_location(LocationQuery(name=a.place))
        if loc is None:
            print(f"could not resolve '{a.place}'")
            return
        name, lat, lon = loc.name, loc.lat, loc.lon
        print(
            f"location: {loc.name} ({loc.lat}, {loc.lon}) via {loc.match} {loc.score}"
            + (f", INCOIS sector {loc.sector_id} {loc.sector_name}" if loc.sector_id else "")
        )

    start, end = named_window(a.day, a.part)
    q = RiskQuery(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        vessel=VesselClass(a.vessel),
        heading_deg=a.heading,
        speed_kt=a.speed,
    )
    brief, pfz = await asyncio.gather(
        safety_briefing(ctx, q), get_pfz_advisory(ctx, Point(lat=lat, lon=lon))
    )
    total_ms = round((time.perf_counter() - t0) * 1000)
    v = brief.verdict

    print(f"\n=== {v.label} === for a {v.vessel_class} craft off {name}, {brief.window}")
    print(
        f"status: {v.status}   engine: {v.computed_ms} ms   fetch+risk: {brief.elapsed_ms} ms   total: {total_ms} ms"
    )
    for r in v.reasons:
        print(f"  ! {r}")
    print("parameters:")
    for p in v.parameters:
        lvl = p.level.name if p.level is not None else "—"
        print(
            f"  {p.parameter:<12} {lvl:<8} {p.status:<10} {p.reason}"
            + (f"  [{', '.join(p.evidence)}]" if p.evidence else "")
        )
    if v.data_gaps:
        print("data gaps:")
        for g in v.data_gaps:
            print(f"  - {g}")

    print(f"\nPFZ: advisory {pfz.advisory_date or 'unavailable'} ({pfz.source_status})")
    if pfz.zones:
        for i, z in enumerate(pfz.zones, 1):
            print(
                f"  #{i} {z.state} {z.distance_km} km {z.compass} ({z.bearing_deg}°), line {z.length_km} km, nearest point {z.nearest_lat}, {z.nearest_lon}"
            )
    else:
        print(f"  {pfz.note}")

    led = ctx.ledger
    print(
        f"\nledger: {len(led.observations)} observations, {len(led.missing)} missing; sources: {led.sources()}; degraded={led.degraded()}"
    )
    if a.ledger:
        for o in led.observations:
            print(
                f"  {o.id} {o.variable:<24} {o.value:>8g} {o.unit:<6} {o.source:<28} valid {o.valid_time:%m-%d %H:%M}Z fetched {o.fetched_at:%H:%M}Z {o.distance_km:>5.1f} km conf {o.confidence:.2f} {o.provenance}"
                + (f"  {o.note}" if o.note else "")
            )
    for m in led.missing:
        print(f"  MISSING {m.variable}: {m.reason}")
    print(f"calibration: {v.calibration}")


if __name__ == "__main__":
    asyncio.run(main())
