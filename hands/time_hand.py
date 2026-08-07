"""
Chhoti Don - Hands Layer :: Time & Calendar Hand

Date/time, timezone and calendar helpers built entirely on the standard library
(datetime, zoneinfo, calendar) — no third-party dependencies, so this hand is
always available. Named timezones use zoneinfo when the tz database is present
and fall back to local time (with a note) when it is not.

    tm.execute("time", "current_time", {"timezone": "Asia/Kolkata"})
    tm.execute("time", "calendar_month", {"year": 2026, "month": 7})
    tm.execute("time", "festival_lookup", {"upcoming": True})
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission

# Fixed-date festivals/holidays (month, day) → name. Computed for any year.
_FIXED_FESTIVALS: Dict[tuple, str] = {
    (1, 1): "New Year's Day",
    (1, 26): "Republic Day (India)",
    (2, 14): "Valentine's Day",
    (3, 8): "International Women's Day",
    (4, 22): "Earth Day",
    (5, 1): "Labour Day",
    (6, 21): "International Yoga Day",
    (8, 15): "Independence Day (India)",
    (10, 2): "Gandhi Jayanti",
    (10, 31): "Halloween",
    (11, 14): "Children's Day (India)",
    (12, 25): "Christmas Day",
    (12, 31): "New Year's Eve",
}

# Lunar / variable-date festivals by year (curated; approximate for planning).
_VARIABLE_FESTIVALS: Dict[int, Dict[str, str]] = {
    2025: {"Holi": "2025-03-14", "Eid al-Fitr": "2025-03-31", "Diwali": "2025-10-20",
           "Raksha Bandhan": "2025-08-09", "Dussehra": "2025-10-02"},
    2026: {"Holi": "2026-03-04", "Eid al-Fitr": "2026-03-20", "Diwali": "2026-11-08",
           "Raksha Bandhan": "2026-08-28", "Dussehra": "2026-10-20"},
    2027: {"Holi": "2027-03-22", "Eid al-Fitr": "2027-03-10", "Diwali": "2027-10-29",
           "Raksha Bandhan": "2027-08-17", "Dussehra": "2027-10-09"},
}


class TimeHand(BaseHand):
    """Date, time, timezone and calendar operations (stdlib only)."""

    name = "time"
    description = "Current time/date, timezone info, week numbers, calendar and festival lookup."

    def __init__(self) -> None:
        super().__init__()
        R = Permission.READ_ONLY
        self.register("now", self.now, permission=R, doc="Full date/time breakdown for a timezone.")
        self.register("current_time", self.current_time, permission=R, doc="Current wall-clock time.")
        self.register("current_date", self.current_date, permission=R, doc="Current date (ISO).")
        self.register("day", self.day, permission=R, doc="Current weekday name and number.")
        self.register("month", self.month, permission=R, doc="Current month name and number.")
        self.register("year", self.year, permission=R, doc="Current year.")
        self.register("timezone_info", self.timezone_info, permission=R, doc="UTC offset and tz name.")
        self.register("week_number", self.week_number, permission=R, doc="ISO week number for a date.")
        self.register("day_of_year", self.day_of_year, permission=R, doc="Ordinal day-of-year for a date.")
        self.register("is_leap_year", self.is_leap_year, permission=R, doc="Whether a year is a leap year.")
        self.register("calendar_month", self.calendar_month, permission=R, doc="Month grid (weeks of day numbers).")
        self.register("days_until", self.days_until, permission=R, doc="Days from today until a target date.")
        self.register("festival_lookup", self.festival_lookup, permission=R, doc="Look up festivals by name/date/upcoming.")

    # ── Timezone helpers ─────────────────────────────────────
    @staticmethod
    def _tz(name: str = ""):
        """Return a tzinfo for a name, or None (local) with graceful fallback."""
        if not name or name.lower() in ("local", "system"):
            return None, None
        if name.upper() == "UTC":
            return timezone.utc, None
        try:
            from zoneinfo import ZoneInfo

            return ZoneInfo(name), None
        except Exception as exc:
            return None, f"Timezone {name!r} unavailable ({exc}); using local time."

    def _now(self, tz_name: str = "") -> Dict[str, Any]:
        """Resolve 'now' in the requested timezone (or local)."""
        tz, note = self._tz(tz_name)
        dt = datetime.now(tz) if tz else datetime.now().astimezone()
        return {"dt": dt, "note": note, "requested_tz": tz_name or "local"}

    @staticmethod
    def _parse_date(value: str = "") -> date:
        """Parse an ISO date string, defaulting to today when empty."""
        if not value:
            return date.today()
        return datetime.strptime(value, "%Y-%m-%d").date()

    # ── Capabilities ─────────────────────────────────────────
    def now(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002 - public param name
        """Return a full date/time breakdown for a timezone."""
        info = self._now(timezone)
        dt: datetime = info["dt"]
        out = {
            "iso": dt.isoformat(),
            "date": dt.date().isoformat(),
            "time": dt.strftime("%H:%M:%S"),
            "weekday": dt.strftime("%A"),
            "day": dt.day,
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "year": dt.year,
            "timezone": str(dt.tzinfo),
            "utc_offset": dt.strftime("%z") or "+0000",
            "week_number": dt.isocalendar().week,
            "requested_tz": info["requested_tz"],
        }
        if info["note"]:
            out["note"] = info["note"]
        return out

    def current_time(self, timezone: str = "", format: str = "%H:%M:%S") -> Dict[str, Any]:  # noqa: A002
        """Return the current wall-clock time."""
        info = self._now(timezone)
        dt: datetime = info["dt"]
        out = {"time": dt.strftime(format), "timezone": str(dt.tzinfo), "iso": dt.isoformat()}
        if info["note"]:
            out["note"] = info["note"]
        return out

    def current_date(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the current date (ISO plus friendly form)."""
        info = self._now(timezone)
        dt: datetime = info["dt"]
        out = {"date": dt.date().isoformat(), "friendly": dt.strftime("%A, %d %B %Y")}
        if info["note"]:
            out["note"] = info["note"]
        return out

    def day(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the current weekday name and ISO weekday number (Mon=1)."""
        dt: datetime = self._now(timezone)["dt"]
        return {"weekday": dt.strftime("%A"), "iso_weekday": dt.isoweekday(), "day_of_month": dt.day}

    def month(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the current month name and number."""
        dt: datetime = self._now(timezone)["dt"]
        return {"month": dt.month, "month_name": dt.strftime("%B")}

    def year(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the current year."""
        dt: datetime = self._now(timezone)["dt"]
        return {"year": dt.year, "is_leap_year": calendar.isleap(dt.year)}

    def timezone_info(self, timezone: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the UTC offset and tz name for a timezone."""
        info = self._now(timezone)
        dt: datetime = info["dt"]
        out = {"timezone": str(dt.tzinfo), "utc_offset": dt.strftime("%z") or "+0000",
               "abbreviation": dt.strftime("%Z")}
        if info["note"]:
            out["note"] = info["note"]
        return out

    def week_number(self, date: str = "") -> Dict[str, Any]:  # noqa: A002 - public param name
        """Return the ISO week number and year for a date (default today)."""
        d = self._parse_date(date)
        iso = d.isocalendar()
        return {"date": d.isoformat(), "iso_year": iso.year, "week_number": iso.week, "iso_weekday": iso.weekday}

    def day_of_year(self, date: str = "") -> Dict[str, Any]:  # noqa: A002
        """Return the ordinal day-of-year for a date (default today)."""
        d = self._parse_date(date)
        return {"date": d.isoformat(), "day_of_year": d.timetuple().tm_yday}

    def is_leap_year(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Return whether a year is a leap year (default current year)."""
        y = int(year) if year is not None else date.today().year
        return {"year": y, "is_leap_year": calendar.isleap(y)}

    def calendar_month(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Return a month as weeks of day numbers (0 = padding)."""
        today = date.today()
        y = int(year) if year is not None else today.year
        m = int(month) if month is not None else today.month
        if not 1 <= m <= 12:
            raise ValueError("month must be 1..12")
        weeks = calendar.monthcalendar(y, m)
        return {"year": y, "month": m, "month_name": calendar.month_name[m],
                "weeks": weeks, "weekday_header": list(calendar.day_abbr)}

    def days_until(self, date: str) -> Dict[str, Any]:  # noqa: A002 - public param name
        """Return the number of days from today until a target ISO date."""
        target = self._parse_date(date)
        # `date` is shadowed by the param here, so get today via datetime.
        delta = (target - datetime.now().date()).days
        return {"target": target.isoformat(), "days_until": delta,
                "is_past": delta < 0, "is_today": delta == 0}

    # ── Festivals ────────────────────────────────────────────
    def _festivals_for_year(self, year: int) -> List[Dict[str, str]]:
        """Build the festival list for a year (fixed + curated variable)."""
        out: List[Dict[str, str]] = []
        for (mth, dy), name in _FIXED_FESTIVALS.items():
            try:
                out.append({"name": name, "date": date(year, mth, dy).isoformat(), "type": "fixed"})
            except ValueError:
                continue
        for name, iso in _VARIABLE_FESTIVALS.get(year, {}).items():
            out.append({"name": name, "date": iso, "type": "variable"})
        out.sort(key=lambda f: f["date"])
        return out

    def festival_lookup(self, name: str = "", year: Optional[int] = None,
                        upcoming: bool = False) -> Dict[str, Any]:
        """Look up festivals by name, by year, or the next upcoming ones.

        Fixed-date holidays are computed for any year; lunar/variable festivals
        come from a curated table (approximate, for planning).
        """
        today = date.today()
        y = int(year) if year is not None else today.year
        festivals = self._festivals_for_year(y)

        if name:
            q = name.strip().lower()
            matches = [f for f in festivals if q in f["name"].lower()]
            # Look into next year too when searching by name near year-end.
            if not matches and year is None:
                matches = [f for f in self._festivals_for_year(y + 1) if q in f["name"].lower()]
            return {"query": name, "count": len(matches), "festivals": matches}

        if upcoming:
            todays_iso = today.isoformat()
            ahead = [f for f in festivals if f["date"] >= todays_iso]
            if len(ahead) < 5 and year is None:  # top up from next year
                ahead += self._festivals_for_year(y + 1)
            return {"upcoming": True, "count": len(ahead[:10]), "festivals": ahead[:10]}

        return {"year": y, "count": len(festivals), "festivals": festivals}
