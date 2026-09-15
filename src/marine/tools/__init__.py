"""The tool belt: the typed, agent-callable surface. ~15 functions, all Pydantic at the
boundary, all writing to the request's EvidenceLedger. The planner emits a DAG over these
names; the specialists call them. Nothing here decides safety — `assess_sailing_risk`
just hands ledger values to `marine.risk.rules.evaluate`."""

from marine.tools.context import ToolContext
from marine.tools.locations import LocationQuery, ResolvedLocation, resolve_location
from marine.tools.ocean import (
    Point,
    PointWindow,
    SeriesResult,
    fan_out,
    get_argo_temperature,
    get_chlorophyll,
    get_sea_state,
    get_visibility_forecast,
    get_wave_forecast,
    get_wind_forecast,
)
from marine.tools.safety import (
    RiskQuery,
    SafetyBriefing,
    assess_sailing_risk,
    cyclone_status,
    lightning_status,
    safety_briefing,
)
from marine.tools.spatial import (
    HeadingQuery,
    check_position,
    get_pfz_advisory,
    predict_boundary_crossing,
)
from marine.tools.windows import describe_window, named_window

TOOLS = {
    "resolve_location": resolve_location,
    "get_wave_forecast": get_wave_forecast,
    "get_wind_forecast": get_wind_forecast,
    "get_visibility_forecast": get_visibility_forecast,
    "get_sea_state": get_sea_state,
    "get_chlorophyll": get_chlorophyll,
    "get_argo_temperature": get_argo_temperature,
    "get_pfz_advisory": get_pfz_advisory,
    "check_position": check_position,
    "predict_boundary_crossing": predict_boundary_crossing,
    "assess_sailing_risk": assess_sailing_risk,
    "safety_briefing": safety_briefing,
    "cyclone_status": cyclone_status,
    "lightning_status": lightning_status,
    "fan_out": fan_out,
}

__all__ = [
    "TOOLS",
    "HeadingQuery",
    "LocationQuery",
    "Point",
    "PointWindow",
    "ResolvedLocation",
    "RiskQuery",
    "SafetyBriefing",
    "SeriesResult",
    "ToolContext",
    "assess_sailing_risk",
    "check_position",
    "cyclone_status",
    "describe_window",
    "fan_out",
    "get_argo_temperature",
    "get_chlorophyll",
    "get_pfz_advisory",
    "get_sea_state",
    "get_visibility_forecast",
    "get_wave_forecast",
    "get_wind_forecast",
    "lightning_status",
    "named_window",
    "predict_boundary_crossing",
    "resolve_location",
    "safety_briefing",
]
