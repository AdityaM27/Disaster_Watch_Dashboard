"""
Weather and Flood Risk Service for DisasterWatch India.
Integrates live meteorological readings from Open-Meteo API.
Evaluates live rainfall, wind speed, and temperature against transparent risk criteria.

IMPORTANT DATA RULE:
- All generated alerts are strictly labeled "Estimated Flood Risk" or "Estimated Risk".
- Never claims an area is currently flooded without official authority confirmation.
- Transparently records why the risk was calculated (e.g. "Normal/minimal rainfall observed", "High rainfall threshold exceeded").
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx

from services.risk_engine import (
    evaluate_flood_risk,
    evaluate_cyclone_risk,
    evaluate_heatwave_risk,
    get_safety_guidance
)

logger = logging.getLogger(__name__)

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_weather_for_coords(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Fetches real-time weather metrics from Open-Meteo for given coordinates.
    Returns dictionary with temperature, humidity, precipitation, rain, wind speed, and gusts.
    """
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_gusts_10m,weather_code",
        "daily": "precipitation_sum,rain_sum,wind_speed_10m_max,temperature_2m_max",
        "timezone": "Asia/Kolkata"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_BASE_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                daily = data.get("daily", {})

                # Extract daily aggregates (first element corresponds to today)
                daily_precip = daily.get("precipitation_sum", [0.0])[0] if daily.get("precipitation_sum") else 0.0
                daily_rain = daily.get("rain_sum", [0.0])[0] if daily.get("rain_sum") else 0.0
                max_wind = daily.get("wind_speed_10m_max", [0.0])[0] if daily.get("wind_speed_10m_max") else 0.0
                max_temp = daily.get("temperature_2m_max", [0.0])[0] if daily.get("temperature_2m_max") else current.get("temperature_2m", 0.0)

                return {
                    "temperature_c": current.get("temperature_2m", 0.0),
                    "humidity_pct": current.get("relative_humidity_2m", 0.0),
                    "hourly_precipitation_mm": current.get("precipitation", 0.0),
                    "hourly_rain_mm": current.get("rain", 0.0),
                    "daily_precipitation_sum_mm": daily_precip or 0.0,
                    "daily_rain_sum_mm": daily_rain or 0.0,
                    "wind_speed_kmh": current.get("wind_speed_10m", 0.0),
                    "wind_gusts_kmh": current.get("wind_gusts_10m", 0.0),
                    "max_wind_speed_kmh": max_wind or 0.0,
                    "max_temperature_c": max_temp or 0.0,
                    "weather_code": current.get("weather_code", 0),
                    "observation_time": current.get("time", datetime.now(timezone.utc).isoformat())
                }
            else:
                logger.warning(f"Open-Meteo returned status {resp.status_code} for ({lat}, {lon})")
                return None
    except Exception as e:
        logger.error(f"Error connecting to Open-Meteo for ({lat}, {lon}): {e}")
        return None


def evaluate_location_weather_risk(
    loc: Dict[str, Any],
    weather_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates weather risk for a monitored location based on actual observed data.
    Generates an AlertItem formatted dictionary labeled as 'Estimated Risk'.
    """
    hourly_rain = weather_data.get("hourly_precipitation_mm", 0.0)
    daily_rain = weather_data.get("daily_precipitation_sum_mm", 0.0)
    wind_kmh = weather_data.get("wind_speed_kmh", 0.0)
    gust_kmh = weather_data.get("wind_gusts_kmh", 0.0)
    temp_c = weather_data.get("temperature_c", 0.0)
    name = loc.get("name", "Unknown Location")
    state = loc.get("state", "India")
    loc_id = loc.get("id", "loc-generic")
    lat = loc["latitude"]
    lon = loc["longitude"]

    # 1. Evaluate Flood Risk
    f_sev, f_score, f_rule, f_details = evaluate_flood_risk(hourly_rain, daily_rain, wind_kmh)

    # 2. Evaluate Cyclone / Wind Risk
    c_sev, c_score, c_rule, c_details = evaluate_cyclone_risk(wind_kmh, gust_kmh)

    # 3. Evaluate Heatwave Risk
    h_sev, h_score, h_rule, h_details = evaluate_heatwave_risk(temp_c)

    # Determine dominant risk category
    # Priority: Severe weather condition if any; default to Flood Risk monitoring
    dominant_type = "Flood Risk"
    dominant_sev = f_sev
    dominant_score = f_score
    dominant_rule = f_rule
    dominant_details = f_details
    safety_guidance = get_safety_guidance("Flood Risk")

    if c_sev in ("High", "Critical") and c_score > dominant_score:
        dominant_type = "Cyclone/Storm"
        dominant_sev = c_sev
        dominant_score = c_score
        dominant_rule = c_rule
        dominant_details = c_details
        safety_guidance = get_safety_guidance("Cyclone/Storm")
    elif h_sev in ("High", "Critical") and h_score > dominant_score:
        dominant_type = "Heatwave"
        dominant_sev = h_sev
        dominant_score = h_score
        dominant_rule = h_rule
        dominant_details = h_details
        safety_guidance = get_safety_guidance("Heatwave")

    now_iso = datetime.now(timezone.utc).isoformat()

    dominant_details.update({
        "all_measured_metrics": {
            "temperature_c": temp_c,
            "humidity_pct": weather_data.get("humidity_pct"),
            "hourly_precipitation_mm": hourly_rain,
            "daily_precipitation_sum_mm": daily_rain,
            "wind_speed_kmh": wind_kmh,
            "wind_gusts_kmh": gust_kmh
        },
        "station_info": {
            "id": loc_id,
            "name": name,
            "state": state,
            "description": loc.get("description", "")
        }
    })

    return {
        "id": f"risk-est-{loc_id}",
        "title": f"Estimated {dominant_type} - {name}, {state}",
        "disaster_type": dominant_type,
        "severity": dominant_sev,
        "status": "Estimated Risk",
        "location_name": f"{name}, {state}",
        "latitude": lat,
        "longitude": lon,
        "magnitude": None,
        "depth_km": None,
        "rainfall_mm": daily_rain,
        "wind_speed_kmh": wind_kmh,
        "temperature_c": temp_c,
        "risk_score": dominant_score,
        "risk_rule_triggered": dominant_rule,
        "risk_calculation_details": dominant_details,
        "safety_guidance": safety_guidance,
        "source_name": "Open-Meteo Real-Time Weather Service",
        "source_url": f"https://open-meteo.com/en/docs#latitude={lat}&longitude={lon}",
        "event_time": weather_data.get("observation_time", now_iso),
        "updated_time": now_iso,
        "is_estimated_zone": True,
        "is_official_alert": False,
        "zone_radius_km": 35.0
    }


async def evaluate_multiple_locations(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates weather risk for a list of monitoring stations concurrently.
    Returns list of evaluated alert dictionaries.
    """
    results: List[Dict[str, Any]] = []

    async def _fetch_and_eval(loc):
        weather = await fetch_weather_for_coords(loc["latitude"], loc["longitude"])
        if weather:
            return evaluate_location_weather_risk(loc, weather)
        return None

    tasks = [_fetch_and_eval(loc) for loc in locations]
    evaluated = await asyncio.gather(*tasks, return_exceptions=True)

    for item in evaluated:
        if isinstance(item, dict):
            results.append(item)
        elif isinstance(item, Exception):
            logger.error(f"Task failed in weather evaluation: {item}")

    return results
