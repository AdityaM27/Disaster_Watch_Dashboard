"""
NASA FIRMS Active Fire Service for DisasterWatch India.
Integrates NASA's Fire Information for Resource Management System (FIRMS) API.

IMPORTANT DATA RULE:
- Integrates a real active-fire feed ONLY when a valid NASA FIRMS MAP_KEY is configured in .env.
- If not configured, returns honest empty state: "Fire source not connected yet".
- NEVER generates fake or sample fires.
"""

import os
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import httpx

from services.risk_engine import get_safety_guidance

logger = logging.getLogger(__name__)

# NASA FIRMS API Base Endpoint (Free registration at https://firms.modaps.eosdis.nasa.gov/api/map_key/)
NASA_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def is_fire_service_configured() -> bool:
    """Checks if a valid NASA FIRMS MAP_KEY has been provided in the environment."""
    key = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
    return bool(key and key != "YOUR_NASA_FIRMS_KEY_HERE")


async def fetch_active_fires() -> Tuple[str, List[Dict[str, Any]], str]:
    """
    Fetches real active fire detections for India (bounding box: 68, 6, 97, 37).
    Returns (status_string, alerts_list, status_message).
    
    If no key configured:
      Returns ("Not connected yet", [], "Fire source not connected yet. Add NASA_FIRMS_MAP_KEY in .env.")
    """
    if not is_fire_service_configured():
        return (
            "Not connected yet",
            [],
            "Fire source not connected yet. To enable real active fire monitoring, obtain a free MAP_KEY from NASA FIRMS and configure it in .env."
        )

    map_key = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
    # Bounding box for India: minLon, minLat, maxLon, maxLat
    india_bbox = "68,6,97,37"
    url = f"{NASA_FIRMS_BASE_URL}/{map_key}/VIIRS_SNPP_NRT/{india_bbox}/1"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                text_data = resp.text
                alerts = parse_firms_csv(text_data)
                msg = f"Successfully connected to NASA FIRMS. {len(alerts)} active thermal anomalies retrieved."
                return ("Connected", alerts, msg)
            elif resp.status_code == 403:
                return ("Configuration required", [], "NASA FIRMS API key invalid or unauthorized.")
            else:
                return ("Error", [], f"NASA FIRMS API returned status {resp.status_code}.")
    except Exception as e:
        logger.error(f"Error fetching NASA FIRMS fires: {e}")
        return ("Error", [], f"Network error connecting to NASA FIRMS: {str(e)}")


def parse_firms_csv(csv_text: str) -> List[Dict[str, Any]]:
    """
    Parses CSV data from NASA FIRMS into standardized AlertItem dictionaries.
    """
    alerts = []
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            lat = float(row.get("latitude", 0.0))
            lon = float(row.get("longitude", 0.0))
            bright_ti4 = float(row.get("bright_ti4", 300.0))
            frp = float(row.get("frp", 0.0))  # Fire Radiative Power (MW)
            acq_date = row.get("acq_date", "")
            acq_time = row.get("acq_time", "")
            confidence = row.get("confidence", "nominal")

            # Determine severity based on Fire Radiative Power (FRP in Megawatts)
            if frp > 100.0 or bright_ti4 > 360.0:
                severity = "Critical"
                rule = f"Extreme thermal anomaly (FRP: {frp:.1f} MW, Brightness: {bright_ti4:.1f} K). Severe high-intensity fire front."
                score = 8.5
            elif frp > 30.0 or bright_ti4 > 335.0:
                severity = "High"
                rule = f"High thermal intensity (FRP: {frp:.1f} MW, Brightness: {bright_ti4:.1f} K). Active fire."
                score = 6.8
            elif frp > 10.0:
                severity = "Medium"
                rule = f"Moderate thermal anomaly (FRP: {frp:.1f} MW, Brightness: {bright_ti4:.1f} K)."
                score = 4.5
            else:
                severity = "Low"
                rule = f"Low-intensity thermal anomaly (FRP: {frp:.1f} MW, Brightness: {bright_ti4:.1f} K)."
                score = 2.5

            timestamp_str = f"{acq_date}T{acq_time[:2]}:{acq_time[2:]}:00Z" if len(acq_time) >= 4 else datetime.now(timezone.utc).isoformat()
            now_iso = datetime.now(timezone.utc).isoformat()
            fire_id = f"firms-{lat:.3f}-{lon:.3f}-{acq_date}-{acq_time}"

            alerts.append({
                "id": fire_id,
                "title": f"Active Thermal Anomaly - [{lat:.2f}°N, {lon:.2f}°E]",
                "disaster_type": "Fire",
                "severity": severity,
                "status": "Confirmed Event",
                "location_name": f"Coordinates [{lat:.3f}°N, {lon:.3f}°E]",
                "latitude": lat,
                "longitude": lon,
                "magnitude": None,
                "depth_km": None,
                "rainfall_mm": None,
                "wind_speed_kmh": None,
                "temperature_c": None,
                "risk_score": score,
                "risk_rule_triggered": rule,
                "risk_calculation_details": {
                    "fire_radiative_power_mw": frp,
                    "brightness_temperature_k": bright_ti4,
                    "confidence_level": confidence,
                    "satellite_instrument": "VIIRS / Suomi NPP (NASA FIRMS)"
                },
                "safety_guidance": get_safety_guidance("Fire"),
                "source_name": "NASA FIRMS (Earthdata)",
                "source_url": "https://firms.modaps.eosdis.nasa.gov/",
                "event_time": timestamp_str,
                "updated_time": now_iso,
                "is_estimated_zone": False,
                "is_official_alert": False,
                "zone_radius_km": 10.0
            })
    except Exception as e:
        logger.error(f"Error parsing FIRMS CSV: {e}")

    return alerts
