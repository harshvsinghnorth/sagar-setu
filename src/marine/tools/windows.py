"""Deterministic time windows in IST → UTC. The planner turns phrases into these."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

DayPart = Literal["early_morning", "morning", "afternoon", "evening", "night", "all_day"]
Day = Literal["today", "tomorrow", "day_after"]

# Local hours, [start, end). Small-craft trips typically leave before dawn.
DAY_PARTS: dict[DayPart, tuple[int, int]] = {
    "early_morning": (3, 8),
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 27),  # 21:00 → 03:00 next day
    "all_day": (0, 24),
}


def named_window(
    day: Day = "tomorrow", part: DayPart = "morning", now: datetime | None = None
) -> tuple[datetime, datetime]:
    """UTC (start, end) for e.g. ("tomorrow", "morning") in Indian Standard Time."""
    now_ist = (now or datetime.now(UTC)).astimezone(IST)
    offset = {"today": 0, "tomorrow": 1, "day_after": 2}[day]
    base = now_ist.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=offset)
    h0, h1 = DAY_PARTS[part]
    start, end = base + timedelta(hours=h0), base + timedelta(hours=h1)
    if day == "today" and end <= now_ist:  # the part has passed; roll to tomorrow honestly
        start, end = start + timedelta(days=1), end + timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def describe_window(start: datetime, end: datetime) -> str:
    s, e = start.astimezone(IST), end.astimezone(IST)
    return f"{s:%a %d %b %H:%M}–{e:%H:%M} IST"
