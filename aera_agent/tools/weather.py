"""Weather lookup (Open-Meteo + Nominatim — no API key)."""

import urllib.parse

from . import tool
from ._http import http_json

# Open-Meteo weather codes → human description
_CODE_MAP = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "icy fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "heavy showers", 82: "violent showers",
    95: "thunderstorm", 96: "thunderstorm with hail",
    99: "severe thunderstorm with hail",
}


@tool(
    description="Get current weather and short forecast for a city or place name.",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or place, e.g. 'Kathmandu' or 'Paris, France'"},
            "units":    {"type": "string", "enum": ["metric", "imperial"], "default": "metric"},
        },
        "required": ["location"],
    },
)
def get_weather(location: str, units: str = "metric") -> str:
    # 1. geocode
    geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": location, "count": 1})
    geo = http_json(geo_url)
    if not geo.get("results"):
        return f"Location not found: {location}"
    place = geo["results"][0]
    lat, lon = place["latitude"], place["longitude"]
    label = f"{place['name']}, {place.get('country', '')}".strip(", ")

    # 2. forecast
    temp_unit = "fahrenheit" if units == "imperial" else "celsius"
    wind_unit = "mph" if units == "imperial" else "kmh"
    wx_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
        "daily":   "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "temperature_unit": temp_unit, "wind_speed_unit": wind_unit,
        "timezone": "auto", "forecast_days": 3,
    })
    wx = http_json(wx_url)
    cur = wx["current"]; daily = wx["daily"]
    cond = _CODE_MAP.get(cur["weather_code"], "unknown")
    t_unit = "°F" if units == "imperial" else "°C"
    w_unit = "mph" if units == "imperial" else "km/h"

    out = [f"Weather in {label}: {cond}, {cur['temperature_2m']}{t_unit} "
           f"(feels {cur['apparent_temperature']}{t_unit}), "
           f"humidity {cur['relative_humidity_2m']}%, wind {cur['wind_speed_10m']} {w_unit}."]
    for i in range(min(3, len(daily["time"]))):
        out.append(f"  {daily['time'][i]}: "
                   f"{daily['temperature_2m_min'][i]}–{daily['temperature_2m_max'][i]}{t_unit}, "
                   f"{_CODE_MAP.get(daily['weather_code'][i], '?')}, "
                   f"precip {daily['precipitation_probability_max'][i]}%")
    return "\n".join(out)
