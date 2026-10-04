"""
USGS Earthquake Service for DisasterWatch India.
Integrates the official United States Geological Survey (USGS) GeoJSON live feeds.
Retrieves real-time seismic events, parses physical parameters (magnitude, depth, epicenter),
applies the transparent risk engine, and returns standardized AlertItem objects.

Data Source:
Official USGS Earthquake Hazards Program (Public Domain)
Endpoints:
- Regional Subcontinent Feed: fdsnws/event/1/query with bounding box for South Asia & India
- Global Real-time 24h Feed: summary/all_day.geojson
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from services.risk_engine import evaluate_earthquake_risk, get_safety_guidance

logger = logging.getLogger(__name__)

# Primary feeds
USGS_REGIONAL_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_ALL_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
USGS_WEEK_45_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"


async def fetch_usgs_earthquakes(include_global: bool = True, min_magnitude: float = 2.0) -> List[Dict[str, Any]]:
    """
    Fetches real earthquake events worldwide from USGS.
    Ingests global 24h feed, regional subcontinent plate events, and 4.5+ magnitude week events worldwide.
    """
    alerts: List[Dict[str, Any]] = []
    seen_ids = set()

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch Global All-Day Feed (worldwide coverage)
        try:
            resp_global = await client.get(USGS_ALL_DAY_URL)
            if resp_global.status_code == 200:
                geo_json = resp_global.json()
                features = geo_json.get("features", [])
                for f in features:
                    parsed = _parse_usgs_feature(f, is_regional=False)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        alerts.append(parsed)
        except Exception as e:
            logger.error(f"Failed to fetch USGS all_day feed: {e}")

        # 2. Fetch Worldwide M4.5+ weekly events (ensures major quakes from Americas, Asia, Europe, Oceania)
        try:
            resp_week = await client.get(USGS_WEEK_45_URL)
            if resp_week.status_code == 200:
                geo_json = resp_week.json()
                features = geo_json.get("features", [])
                for f in features:
                    parsed = _parse_usgs_feature(f, is_regional=False)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        alerts.append(parsed)
        except Exception as e:
            logger.error(f"Failed to fetch USGS 4.5 week feed: {e}")

        # 3. Fetch Regional Subcontinent Events
        try:
            params = {
                "format": "geojson",
                "minlatitude": "0.0",
                "maxlatitude": "40.0",
                "minlongitude": "60.0",
                "maxlongitude": "100.0",
                "minmagnitude": str(min_magnitude),
                "limit": "100",
                "orderby": "time"
            }
            resp = await client.get(USGS_REGIONAL_URL, params=params)
            if resp.status_code == 200:
                geo_json = resp.json()
                features = geo_json.get("features", [])
                for f in features:
                    parsed = _parse_usgs_feature(f, is_regional=True)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        alerts.append(parsed)
        except Exception as e:
            logger.error(f"Failed to fetch USGS regional earthquakes: {e}")

    return alerts


def _parse_usgs_feature(feature: Dict[str, Any], is_regional: bool = False) -> Optional[Dict[str, Any]]:
    """
    Parses a single GeoJSON feature from USGS into our standardized AlertItem schema.
    Applies the risk engine to determine severity and generate safety guidance.
    """
    try:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])

        if len(coords) < 2:
            return None

        lon = float(coords[0])
        lat = float(coords[1])
        depth_km = float(coords[2]) if len(coords) >= 3 else 10.0

        mag = props.get("mag")
        if mag is None:
            return None
        mag = round(float(mag), 1)

        place = props.get("place") or f"Near [{lat:.2f}, {lon:.2f}]"
        event_time_ms = props.get("time")
        if event_time_ms:
            event_dt = datetime.fromtimestamp(event_time_ms / 1000.0, tz=timezone.utc)
            event_time_iso = event_dt.isoformat()
        else:
            event_time_iso = datetime.now(timezone.utc).isoformat()

        updated_time_ms = props.get("updated")
        if updated_time_ms:
            updated_dt = datetime.fromtimestamp(updated_time_ms / 1000.0, tz=timezone.utc)
            updated_time_iso = updated_dt.isoformat()
        else:
            updated_time_iso = datetime.now(timezone.utc).isoformat()

        usgs_id = feature.get("id") or f"usgs-{int(event_time_ms or 0)}"
        source_url = props.get("url") or f"https://earthquake.usgs.gov/earthquakes/eventpage/{usgs_id}"

        # Evaluate risk transparently using risk engine
        severity, risk_score, rule, details = evaluate_earthquake_risk(mag, depth_km)
        details["usgs_code"] = props.get("code")
        details["felt_reports"] = props.get("felt")
        details["mmi"] = props.get("mmi")
        details["alert_color"] = props.get("alert")
        details["tsunami_flag"] = bool(props.get("tsunami", 0))

        safety_advice = get_safety_guidance("Earthquake")
        if details.get("tsunami_flag"):
            safety_advice += " Tsunami advisory active: Move away from coastal areas to high ground immediately."

        # Magnitude-dependent visual circle radius (in km)
        # Scaled circle for Leaflet visual footprint
        radius_km = max(15.0, (mag ** 2.2) * 2.5)

        return {
            "id": f"usgs-{usgs_id}",
            "title": f"M {mag} Earthquake - {place}",
            "disaster_type": "Earthquake",
            "severity": severity,
            "status": "Confirmed Event",
            "location_name": place,
            "latitude": lat,
            "longitude": lon,
            "magnitude": mag,
            "depth_km": depth_km,
            "rainfall_mm": None,
            "wind_speed_kmh": None,
            "temperature_c": None,
            "risk_score": risk_score,
            "risk_rule_triggered": rule,
            "risk_calculation_details": details,
            "safety_guidance": safety_advice,
            "source_name": "USGS Earthquake Hazards Program",
            "source_url": source_url,
            "event_time": event_time_iso,
            "updated_time": updated_time_iso,
            "is_estimated_zone": False,
            "is_official_alert": False,
            "zone_radius_km": radius_km
        }
    except Exception as e:
        logger.error(f"Error parsing USGS feature: {e}")
        return None
