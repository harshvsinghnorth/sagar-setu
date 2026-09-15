"""Test harbours. Every feature must work at all of them — never hardcode one location."""

HARBOURS: dict[str, tuple[float, float]] = {
    "kochi": (9.97, 76.28),  # Kerala, Arabian Sea
    "veraval": (20.90, 70.37),  # Gujarat, high trawler density
    "chennai": (13.09, 80.29),  # Tamil Nadu, Bay of Bengal
    "paradip": (20.26, 86.67),  # Odisha, cyclone-exposed
    "port_blair": (11.62, 92.73),  # Andamans, sparse grid coverage
}

# Gulf of Mannar, ~15 km from the India–Sri Lanka IMBL: the geofencing test case.
GULF_OF_MANNAR: tuple[float, float] = (9.05, 79.10)
