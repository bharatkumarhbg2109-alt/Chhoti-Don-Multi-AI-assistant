"""
Chhoti Don - Hands Layer :: Weather Hand

Weather + air-quality using Open-Meteo (free, no API key). Locations are
auto-detected: a place name is geocoded via Open-Meteo's geocoding API, and
when no location is given the hand falls back to the configured default or a
best-effort IP lookup. If the provider or the network is unavailable the hand
degrades gracefully to a browser-search fallback instead of crashing.

    tm.execute("weather", "current_weather", {"location": "Delhi"})
    tm.execute("weather", "tomorrow_weather", {"location": "Mumbai"})
    tm.execute("weather", "forecast", {"location": "London", "days": 7})
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission

# ── Provider endpoints (single place to configure; env-overridable) ──
_GEOCODE_URL = os.environ.get(
    "CHHOTI_DON_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search"
)
_FORECAST_URL = os.environ.get(
    "CHHOTI_DON_WEATHER_URL", "https://api.open-meteo.com/v1/forecast"
)
_AQI_URL = os.environ.get(
    "CHHOTI_DON_AQI_URL", "https://air-quality-api.open-meteo.com/v1/air-quality"
)
_IP_LOOKUP_URL = os.environ.get("CHHOTI_DON_IP_LOOKUP_URL", "http://ip-api.com/json")

# ── Defaults (no hardcoded location; env-overridable) ────────────────
_DEFAULT_LOCATION = os.environ.get("CHHOTI_DON_DEFAULT_LOCATION", "").strip()
_DEFAULT_UNITS = os.environ.get("CHHOTI_DON_WEATHER_UNITS", "metric").strip().lower()
_HTTP_TIMEOUT = float(os.environ.get("CHHOTI_DON_WEATHER_TIMEOUT", "10"))

# WMO weather interpretation codes → human description.
_WMO: Dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def _describe_code(code: Optional[int]) -> str:
    """Map a WMO weather code to a readable description."""
    if code is None:
        return "Unknown"
    return _WMO.get(int(code), f"Code {code}")


class WeatherHand(BaseHand):
    """Current weather, forecasts and air quality via Open-Meteo."""

    name = "weather"
    description = "Weather, forecast and air quality (Open-Meteo) with location auto-detection."
    dependencies = ["requests"]

    def __init__(self, search_hand: Optional[BaseHand] = None) -> None:
        super().__init__()
        # Optional injected Search Hand used for the browser-search fallback.
        self.search_hand = search_hand
        self._geo_cache: Dict[str, Dict[str, Any]] = {}

        R = Permission.READ_ONLY
        self.register("current_weather", self.current_weather, permission=R, doc="Current conditions for a location.")
        self.register("tomorrow_weather", self.tomorrow_weather, permission=R, doc="Tomorrow's forecast for a location.")
        self.register("forecast", self.forecast, permission=R, doc="Multi-day (default 7) forecast.")
        self.register("rain_probability", self.rain_probability, permission=R, doc="Rain probability for today/tomorrow.")
        self.register("humidity", self.humidity, permission=R, doc="Current relative humidity.")
        self.register("wind", self.wind, permission=R, doc="Current wind speed and direction.")
        self.register("temperature", self.temperature, permission=R, doc="Current temperature.")
        self.register("sunrise", self.sunrise, permission=R, doc="Sunrise time for today.")
        self.register("sunset", self.sunset, permission=R, doc="Sunset time for today.")
        self.register("uv_index", self.uv_index, permission=R, doc="Max UV index for today.")
        self.register("air_quality", self.air_quality, permission=R, doc="Air quality index (AQI) if available.")
        self.register("weather_status", self.weather_status, permission=R, doc="Provider reachability status.")

    # ── Units ────────────────────────────────────────────────
    @staticmethod
    def _unit_params(units: str) -> Dict[str, str]:
        """Map metric/imperial to Open-Meteo unit query params."""
        if (units or _DEFAULT_UNITS) == "imperial":
            return {"temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch"}
        return {"temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm"}

    # ── Location resolution (auto-detect) ────────────────────
    def _resolve(
        self,
        location: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Resolve a request into latitude/longitude and a display name.

        Priority: explicit lat/lon → geocoded location name → configured
        default → IP-based auto-detect. Raises with a clear message if none
        succeed so the caller (base.run) returns a structured error.
        """
        if latitude is not None and longitude is not None:
            return {"name": location or f"{latitude},{longitude}", "latitude": float(latitude),
                    "longitude": float(longitude), "source": "coordinates"}

        place = (location or _DEFAULT_LOCATION).strip()
        if place:
            return self._geocode(place)

        # No location supplied anywhere → try IP auto-detect.
        auto = self._ip_locate()
        if auto:
            return auto
        raise ValueError(
            "No location given and auto-detect failed. Provide 'location' or "
            "latitude/longitude, or set CHHOTI_DON_DEFAULT_LOCATION."
        )

    def _geocode(self, place: str) -> Dict[str, Any]:
        """Geocode a place name via Open-Meteo's geocoding API (cached)."""
        key = place.lower()
        if key in self._geo_cache:
            return self._geo_cache[key]
        import requests

        resp = requests.get(
            _GEOCODE_URL,
            params={"name": place, "count": 1, "format": "json"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if not results:
            raise LookupError(f"Location not found: {place!r}")
        top = results[0]
        loc = {
            "name": ", ".join(str(p) for p in (top.get("name"), top.get("admin1"), top.get("country")) if p),
            "latitude": top["latitude"],
            "longitude": top["longitude"],
            "timezone": top.get("timezone"),
            "source": "geocode",
        }
        self._geo_cache[key] = loc
        return loc

    def _ip_locate(self) -> Optional[Dict[str, Any]]:
        """Best-effort IP-based geolocation. Returns None on any failure."""
        try:
            import requests

            resp = requests.get(_IP_LOOKUP_URL, timeout=_HTTP_TIMEOUT)
            data = resp.json()
            if data.get("status") == "success" or ("lat" in data and "lon" in data):
                name = ", ".join(str(p) for p in (data.get("city"), data.get("country")) if p)
                return {"name": name or "auto-detected", "latitude": data["lat"],
                        "longitude": data["lon"], "source": "ip"}
        except Exception:
            pass
        return None

    # ── Core fetch ───────────────────────────────────────────
    def _fetch(self, loc: Dict[str, Any], units: str, days: int = 7) -> Dict[str, Any]:
        """Fetch normalized current + daily weather for a resolved location."""
        import requests

        params = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "timezone": "auto",
            "forecast_days": max(1, min(16, int(days))),
            "current": ",".join([
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m",
            ]),
            "daily": ",".join([
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "precipitation_probability_max", "sunrise", "sunset",
                "uv_index_max", "wind_speed_10m_max",
            ]),
        }
        params.update(self._unit_params(units))
        resp = requests.get(_FORECAST_URL, params=params, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return self._normalize(loc, data)

    @staticmethod
    def _normalize(loc: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Shape the raw Open-Meteo payload into a stable, friendly structure."""
        cur = data.get("current", {}) or {}
        cur_units = data.get("current_units", {}) or {}
        daily = data.get("daily", {}) or {}
        days: List[Dict[str, Any]] = []
        dates = daily.get("time", []) or []
        for i, date in enumerate(dates):
            def _at(field: str) -> Any:
                seq = daily.get(field) or []
                return seq[i] if i < len(seq) else None
            days.append({
                "date": date,
                "condition": _describe_code(_at("weather_code")),
                "temp_max": _at("temperature_2m_max"),
                "temp_min": _at("temperature_2m_min"),
                "rain_probability": _at("precipitation_probability_max"),
                "sunrise": _at("sunrise"),
                "sunset": _at("sunset"),
                "uv_index_max": _at("uv_index_max"),
                "wind_max": _at("wind_speed_10m_max"),
            })
        return {
            "location": loc.get("name"),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "timezone": data.get("timezone"),
            "units": {
                "temperature": cur_units.get("temperature_2m"),
                "wind_speed": cur_units.get("wind_speed_10m"),
            },
            "current": {
                "temperature": cur.get("temperature_2m"),
                "feels_like": cur.get("apparent_temperature"),
                "humidity": cur.get("relative_humidity_2m"),
                "precipitation": cur.get("precipitation"),
                "condition": _describe_code(cur.get("weather_code")),
                "wind_speed": cur.get("wind_speed_10m"),
                "wind_direction": cur.get("wind_direction_10m"),
            },
            "daily": days,
        }

    def _weather_for(self, location: str, latitude: Optional[float],
                     longitude: Optional[float], units: str, days: int = 7) -> Dict[str, Any]:
        """Resolve + fetch, with a browser-search fallback on provider failure."""
        loc = self._resolve(location, latitude, longitude)
        try:
            return self._fetch(loc, units, days=days)
        except Exception as exc:
            fallback = self._search_fallback(loc.get("name", location), exc)
            if fallback is not None:
                return fallback
            raise

    def _search_fallback(self, place: str, exc: Exception) -> Optional[Dict[str, Any]]:
        """Fallback to a web search when Open-Meteo is unreachable."""
        query = f"weather in {place}" if place else "weather"
        note = f"Open-Meteo unavailable ({exc}); using search fallback."
        if self.search_hand is not None and self.search_hand.is_available():
            try:
                res = self.search_hand.run("duckduckgo_search", {"query": query, "limit": 3})
                return {"__envelope__": True, "status": "success", "hand": self.name,
                        "action": "weather", "result": {"fallback": "search", "query": query,
                        "note": note, "search": res.get("result")}, "error": None}
            except Exception:
                pass
        # Last resort: hand back a search URL so the caller can still act.
        return {"__envelope__": True, "status": "unavailable", "hand": self.name,
                "action": "weather", "error": note,
                "result": {"fallback": "search_url",
                           "search_url": "https://duckduckgo.com/?q=" + query.replace(" ", "+")}}

    # ── Capabilities ─────────────────────────────────────────
    def current_weather(self, location: str = "", latitude: Optional[float] = None,
                        longitude: Optional[float] = None, units: str = "") -> Dict[str, Any]:
        """Return current conditions (temp, humidity, wind, condition)."""
        data = self._weather_for(location, latitude, longitude, units, days=1)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        return {"location": data["location"], "current": data["current"],
                "timezone": data["timezone"], "units": data["units"]}

    def tomorrow_weather(self, location: str = "", latitude: Optional[float] = None,
                         longitude: Optional[float] = None, units: str = "") -> Dict[str, Any]:
        """Return tomorrow's daily forecast."""
        data = self._weather_for(location, latitude, longitude, units, days=2)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        days = data["daily"]
        tomorrow = days[1] if len(days) > 1 else (days[0] if days else None)
        return {"location": data["location"], "tomorrow": tomorrow, "units": data["units"]}

    def forecast(self, location: str = "", days: int = 7, latitude: Optional[float] = None,
                 longitude: Optional[float] = None, units: str = "") -> Dict[str, Any]:
        """Return a multi-day forecast (default 7 days)."""
        data = self._weather_for(location, latitude, longitude, units, days=days)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        return {"location": data["location"], "days": len(data["daily"]),
                "forecast": data["daily"], "units": data["units"]}

    def rain_probability(self, location: str = "", day: str = "today",
                         latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return the max rain probability for today or tomorrow."""
        data = self._weather_for(location, latitude, longitude, units="", days=2)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        idx = 1 if str(day).lower() in ("tomorrow", "1") else 0
        days = data["daily"]
        target = days[idx] if idx < len(days) else (days[0] if days else {})
        return {"location": data["location"], "day": target.get("date"),
                "rain_probability_percent": target.get("rain_probability")}

    def _current_field(self, location: str, latitude: Optional[float],
                       longitude: Optional[float], units: str, field: str) -> Dict[str, Any]:
        """Shared accessor returning one current-conditions field."""
        data = self._weather_for(location, latitude, longitude, units, days=1)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        return {"location": data["location"], field: data["current"].get(field), "units": data["units"]}

    def humidity(self, location: str = "", latitude: Optional[float] = None,
                 longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return current relative humidity (%)."""
        return self._current_field(location, latitude, longitude, "", "humidity")

    def temperature(self, location: str = "", latitude: Optional[float] = None,
                    longitude: Optional[float] = None, units: str = "") -> Dict[str, Any]:
        """Return current temperature."""
        return self._current_field(location, latitude, longitude, units, "temperature")

    def wind(self, location: str = "", latitude: Optional[float] = None,
             longitude: Optional[float] = None, units: str = "") -> Dict[str, Any]:
        """Return current wind speed and direction."""
        data = self._weather_for(location, latitude, longitude, units, days=1)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        cur = data["current"]
        return {"location": data["location"], "wind_speed": cur.get("wind_speed"),
                "wind_direction": cur.get("wind_direction"), "units": data["units"]}

    def _today_daily_field(self, location: str, latitude: Optional[float],
                           longitude: Optional[float], field: str, out_key: str) -> Dict[str, Any]:
        """Shared accessor returning one of today's daily fields."""
        data = self._weather_for(location, latitude, longitude, units="", days=1)
        if isinstance(data, dict) and data.get("__envelope__"):
            return data
        today = data["daily"][0] if data["daily"] else {}
        return {"location": data["location"], out_key: today.get(field)}

    def sunrise(self, location: str = "", latitude: Optional[float] = None,
                longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return today's sunrise time."""
        return self._today_daily_field(location, latitude, longitude, "sunrise", "sunrise")

    def sunset(self, location: str = "", latitude: Optional[float] = None,
               longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return today's sunset time."""
        return self._today_daily_field(location, latitude, longitude, "sunset", "sunset")

    def uv_index(self, location: str = "", latitude: Optional[float] = None,
                 longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return today's maximum UV index."""
        return self._today_daily_field(location, latitude, longitude, "uv_index_max", "uv_index_max")

    def air_quality(self, location: str = "", latitude: Optional[float] = None,
                    longitude: Optional[float] = None) -> Dict[str, Any]:
        """Return air quality (European AQI, PM2.5, PM10) if available."""
        loc = self._resolve(location, latitude, longitude)
        import requests

        params = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "timezone": "auto",
            "current": "european_aqi,us_aqi,pm10,pm2_5,ozone,nitrogen_dioxide",
        }
        resp = requests.get(_AQI_URL, params=params, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        cur = (resp.json().get("current", {}) or {})
        return {
            "location": loc.get("name"),
            "european_aqi": cur.get("european_aqi"),
            "us_aqi": cur.get("us_aqi"),
            "pm2_5": cur.get("pm2_5"),
            "pm10": cur.get("pm10"),
            "ozone": cur.get("ozone"),
            "nitrogen_dioxide": cur.get("nitrogen_dioxide"),
        }

    def weather_status(self) -> Dict[str, Any]:
        """Report provider reachability without raising."""
        import requests

        try:
            resp = requests.get(_FORECAST_URL,
                                params={"latitude": 0, "longitude": 0, "current": "temperature_2m"},
                                timeout=_HTTP_TIMEOUT)
            reachable = resp.status_code == 200
        except Exception as exc:
            return {"provider": "open-meteo", "reachable": False, "error": str(exc),
                    "fallback": "search" if self.search_hand else "search_url"}
        return {"provider": "open-meteo", "reachable": reachable,
                "default_location": _DEFAULT_LOCATION or None, "default_units": _DEFAULT_UNITS}
