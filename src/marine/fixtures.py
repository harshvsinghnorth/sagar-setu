"""Test harbours. Every feature must work at all of them — never hardcode one location."""

HARBOURS: dict[str, tuple[float, float]] = {
    "kochi": (9.97, 76.28),  # Kerala, Arabian Sea
    "veraval": (20.90, 70.37),  # Gujarat, high trawler density
    "chennai": (13.09, 80.29),  # Tamil Nadu, Bay of Bengal
    "paradip": (20.26, 86.67),  # Odisha, cyclone-exposed
    "port_blair": (11.62, 92.73),  # Andamans, sparse grid coverage
}

# Gulf of Mannar, ~15 km from the India–Sri Lanka IMBL: the geofencing test case.
GULF_OF_MANNAR: tuple[float, float] = (9.15, 79.40)

# Major fishing harbours missing from INCOIS's landing-centre layer. Coordinates are the
# harbour basin, read off public charts; good to ~1 km, which is far inside any grid cell.
KNOWN_PORTS: dict[str, tuple[float, float]] = {
    "rameswaram": (9.29, 79.31),  # Tamil Nadu, Palk Bay side — IMBL detentions
    "kasimedu": (13.12, 80.30),  # Chennai fishing harbour
    "mangalore": (12.85, 74.83),
    "malpe": (13.35, 74.70),
    "karwar": (14.81, 74.12),
    "visakhapatnam": (17.69, 83.29),
    "sassoon dock": (18.92, 72.83),  # Mumbai
    "porbandar": (21.64, 69.60),
    "digha": (21.62, 87.52),
    "puri": (19.80, 85.83),
    "kanyakumari": (8.08, 77.55),
    "vizhinjam": (8.38, 76.99),
    "beypore": (11.17, 75.80),
    "nagapattinam": (10.77, 79.85),
    "cuddalore": (11.72, 79.78),
    "kakinada": (16.94, 82.26),
}
