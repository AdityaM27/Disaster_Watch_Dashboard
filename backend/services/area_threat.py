"""
AI Specific Area Disaster Detection & Threat Level Calculation Service for DisasterWatch India.
Enables real-time hazard detection, multi-source telemetry ingestion, and composite threat level scoring
for any specific geographic area (city, district, basin, or coordinates).
"""

import math
import uuid
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import httpx

from database import get_db_connection, get_monitored_locations
from services.weather import fetch_weather_for_coords

logger = logging.getLogger("disasterwatch.area_threat")

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Curated reference dictionary for instant offline fallback and key regional hubs
CURATED_AREA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "mumbai": {
        "name": "Mumbai, Maharashtra, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "country": "India",
        "state": "Maharashtra",
        "elevation_m": 14.0,
        "is_coastal": True,
        "is_seismic_zone": False,
        "typical_hazards": ["Flood Risk", "Cyclone/Storm"]
    },
    "delhi": {
        "name": "New Delhi, Delhi-NCR, India",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "country": "India",
        "state": "Delhi",
        "elevation_m": 216.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Earthquake", "Heatwave", "Flood Risk"]
    },
    "kolkata": {
        "name": "Kolkata, West Bengal, India",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "country": "India",
        "state": "West Bengal",
        "elevation_m": 9.0,
        "is_coastal": True,
        "is_seismic_zone": False,
        "typical_hazards": ["Cyclone/Storm", "Flood Risk"]
    },
    "chennai": {
        "name": "Chennai, Tamil Nadu, India",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "country": "India",
        "state": "Tamil Nadu",
        "elevation_m": 6.0,
        "is_coastal": True,
        "is_seismic_zone": False,
        "typical_hazards": ["Cyclone/Storm", "Flood Risk"]
    },
    "bengaluru": {
        "name": "Bengaluru, Karnataka, India",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "country": "India",
        "state": "Karnataka",
        "elevation_m": 920.0,
        "is_coastal": False,
        "is_seismic_zone": False,
        "typical_hazards": ["Flood Risk"]
    },
    "guwahati": {
        "name": "Guwahati, Brahmaputra Valley, Assam, India",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "country": "India",
        "state": "Assam",
        "elevation_m": 55.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Flood Risk", "Earthquake"]
    },
    "puri": {
        "name": "Puri Coastal Corridor, Odisha, India",
        "latitude": 19.8135,
        "longitude": 85.8312,
        "country": "India",
        "state": "Odisha",
        "elevation_m": 5.0,
        "is_coastal": True,
        "is_seismic_zone": False,
        "typical_hazards": ["Cyclone/Storm", "Flood Risk"]
    },
    "shimla": {
        "name": "Shimla, Himachal Pradesh, India",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "country": "India",
        "state": "Himachal Pradesh",
        "elevation_m": 2200.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Earthquake", "Flood Risk"]
    },
    "kochi": {
        "name": "Kochi, Kerala, India",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "country": "India",
        "state": "Kerala",
        "elevation_m": 4.0,
        "is_coastal": True,
        "is_seismic_zone": False,
        "typical_hazards": ["Flood Risk", "Cyclone/Storm"]
    },
    "patna": {
        "name": "Patna, Bihar, India",
        "latitude": 25.5941,
        "longitude": 85.1376,
        "country": "India",
        "state": "Bihar",
        "elevation_m": 53.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Flood Risk", "Heatwave"]
    },
    "srinagar": {
        "name": "Srinagar, Jammu & Kashmir, India",
        "latitude": 34.0837,
        "longitude": 74.7973,
        "country": "India",
        "state": "Jammu and Kashmir",
        "elevation_m": 1585.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Earthquake", "Flood Risk"]
    },
    "nagpur": {
        "name": "Nagpur, Vidarbha, Maharashtra, India",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "country": "India",
        "state": "Maharashtra",
        "elevation_m": 310.0,
        "is_coastal": False,
        "is_seismic_zone": False,
        "typical_hazards": ["Heatwave"]
    },
    "bhuj": {
        "name": "Bhuj, Kutch, Gujarat, India",
        "latitude": 23.2420,
        "longitude": 69.6669,
        "country": "India",
        "state": "Gujarat",
        "elevation_m": 110.0,
        "is_coastal": False,
        "is_seismic_zone": True,
        "typical_hazards": ["Earthquake", "Heatwave"]
    },
    "tokyo": {
        "name": "Tokyo, Kanto Region, Japan",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "country": "Japan",
        "state": "Tokyo",
        "elevation_m": 40.0,
        "is_coastal": True,
        "is_seismic_zone": True,
        "typical_hazards": ["Earthquake", "Cyclone/Storm"]
    },
    "london": {
        "name": "London, Greater London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "country": "United Kingdom",
        "state": "England",
        "elevation_m": 25.0,
        "is_coastal": False,
        "is_seismic_zone": False,
        "typical_hazards": ["Flood Risk"]
    }
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


async def resolve_area_location(
    query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """
    Resolves a location query or coordinate pair to structured geographic metadata.
    Attempts curated registry -> Open-Meteo Geocoding API -> Monitored stations fallback.
    """
    if lat is not None and lon is not None:
        loc_name = query if query and query.strip() else f"Coordinates [{lat:.4f}, {lon:.4f}]"
        return {
            "name": loc_name,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "country": "Global Coordinate",
            "state": "Local Area",
            "elevation_m": 50.0,
            "is_coastal": False,
            "is_seismic_zone": False
        }

    if not query or not query.strip():
        # Default to Mumbai
        return CURATED_AREA_REGISTRY["mumbai"]

    q_clean = query.strip()
    q_lower = q_clean.lower()

    # 1. Check curated area registry (exact or partial keyword match)
    for key, info in CURATED_AREA_REGISTRY.items():
        if key in q_lower or q_lower in key or q_lower in info["name"].lower():
            return {
                "name": info["name"],
                "latitude": info["latitude"],
                "longitude": info["longitude"],
                "country": info["country"],
                "state": info.get("state", ""),
                "elevation_m": info.get("elevation_m", 50.0),
                "is_coastal": info.get("is_coastal", False),
                "is_seismic_zone": info.get("is_seismic_zone", False)
            }

    # 2. Query Open-Meteo Free Geocoding API
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                OPEN_METEO_GEOCODING_URL,
                params={"name": q_clean, "count": 1, "language": "en", "format": "json"}
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    first = results[0]
                    name_parts = [first.get("name", q_clean)]
                    if first.get("admin1"):
                        name_parts.append(first["admin1"])
                    if first.get("country"):
                        name_parts.append(first["country"])
                    full_name = ", ".join(name_parts)

                    lat_val = float(first.get("latitude", 20.0))
                    lon_val = float(first.get("longitude", 78.0))
                    elev = float(first.get("elevation", 50.0))

                    # Heuristic seismic / coastal check
                    is_seismic = (24.0 <= lat_val <= 36.0 and 70.0 <= lon_val <= 96.0) or ("Japan" in full_name)
                    is_coastal = elev < 20.0 and ("coastal" in q_lower or "sea" in q_lower or "bay" in q_lower or elev < 10.0)

                    return {
                        "name": full_name,
                        "latitude": lat_val,
                        "longitude": lon_val,
                        "country": first.get("country", "Global"),
                        "state": first.get("admin1", ""),
                        "elevation_m": elev,
                        "is_coastal": is_coastal,
                        "is_seismic_zone": is_seismic
                    }
    except Exception as e:
        logger.warning(f"Geocoding API network issue for query '{query}': {e}")

    # 3. Check SQLite monitored stations
    try:
        stations = get_monitored_locations()
        for s in stations:
            if q_lower in s["name"].lower() or q_lower in s["state"].lower():
                return {
                    "name": f"{s['name']}, {s['state']}",
                    "latitude": s["latitude"],
                    "longitude": s["longitude"],
                    "country": s["state"],
                    "state": s["state"],
                    "elevation_m": 50.0,
                    "is_coastal": bool(s.get("is_coastal", 0)),
                    "is_seismic_zone": bool(s.get("is_seismic_zone", 0))
                }
    except Exception as e:
        logger.warning(f"Error querying monitored stations fallback: {e}")

    # 4. Fallback default coordinates
    return {
        "name": f"{q_clean} (Estimated Region)",
        "latitude": 20.5937,
        "longitude": 78.9629,
        "country": "India",
        "state": "National Center",
        "elevation_m": 50.0,
        "is_coastal": False,
        "is_seismic_zone": False
    }


def find_active_disasters_near_area(
    lat: float,
    lon: float,
    radius_km: float = 250.0
) -> List[Dict[str, Any]]:
    """
    Searches active alerts in SQLite database within a radius of the specified point.
    Returns matching disaster events sorted by proximity and severity.
    """
    matched: List[Dict[str, Any]] = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, disaster_type, severity, status, location_name,
                   latitude, longitude, magnitude, depth_km, rainfall_mm,
                   wind_speed_kmh, temperature_c, risk_score, source_name, event_time
            FROM alerts
        """)
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            a_lat = r["latitude"]
            a_lon = r["longitude"]
            dist = haversine_km(lat, lon, a_lat, a_lon)
            if dist <= radius_km:
                matched.append({
                    "id": r["id"],
                    "title": r["title"],
                    "disaster_type": r["disaster_type"],
                    "severity": r["severity"],
                    "status": r["status"],
                    "location_name": r["location_name"],
                    "distance_km": round(dist, 1),
                    "magnitude": r["magnitude"],
                    "depth_km": r["depth_km"],
                    "rainfall_mm": r["rainfall_mm"],
                    "wind_speed_kmh": r["wind_speed_kmh"],
                    "temperature_c": r["temperature_c"],
                    "risk_score": r["risk_score"],
                    "source_name": r["source_name"],
                    "event_time": r["event_time"]
                })

        # Sort by severity weight then distance
        sev_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        matched.sort(key=lambda x: (-sev_order.get(x["severity"], 0), x["distance_km"]))
    except Exception as e:
        logger.error(f"Error querying active alerts near area: {e}")

    return matched


def calculate_area_threat_level(
    location: Dict[str, Any],
    weather: Optional[Dict[str, Any]],
    nearby_disasters: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculates multi-hazard threat scores and an overall composite Threat Level (0-100)
    for a specific geographic area based on real-time telemetry, geographic vulnerability,
    and proximate disaster events.
    """
    # Safe extraction of live weather metrics
    w = weather or {}
    temp_c = float(w.get("temperature_c", 28.0))
    humidity_pct = float(w.get("humidity_pct", 65.0))
    rain_h = float(w.get("hourly_rain_mm", 0.0))
    rain_24 = float(w.get("daily_precipitation_sum_mm", 0.0))
    wind_kmh = float(w.get("wind_speed_kmh", 12.0))
    wind_gusts = float(w.get("wind_gusts_kmh", 18.0))
    weather_cond = w.get("weather_condition", "Clear / Normal")

    is_coastal = location.get("is_coastal", False)
    is_seismic_zone = location.get("is_seismic_zone", False)

    # 1. FLOOD THREAT CALCULATION (0 - 100)
    flood_score = 10.0
    flood_indicators = []

    # Precipitation contribution
    if rain_h >= 30.0 or rain_24 >= 100.0:
        flood_score = 85.0 + min(13.0, (rain_h - 30.0) * 0.5)
        flood_indicators.append(f"Torrential cloudburst precipitation ({rain_h:.1f} mm/h, 24h: {rain_24:.1f} mm)")
    elif rain_h >= 15.0 or rain_24 >= 50.0:
        flood_score = 62.0 + (rain_h - 15.0) * 1.5
        flood_indicators.append(f"Heavy rainfall accumulation ({rain_h:.1f} mm/h, 24h: {rain_24:.1f} mm)")
    elif rain_h >= 5.0 or rain_24 >= 25.0:
        flood_score = 38.0 + (rain_h - 5.0) * 2.0
        flood_indicators.append(f"Moderate precipitation ({rain_h:.1f} mm/h)")
    else:
        flood_score = max(8.0, rain_h * 3.0 + rain_24 * 0.4)
        flood_indicators.append("Precipitation levels within normal drainage capacity")

    # Proximity to active flood alerts
    flood_alerts_near = [d for d in nearby_disasters if "flood" in d["disaster_type"].lower()]
    if flood_alerts_near:
        closest = flood_alerts_near[0]
        proximity_boost = max(0.0, 25.0 * (1.0 - closest["distance_km"] / 200.0))
        flood_score = min(98.0, flood_score + proximity_boost)
        flood_indicators.append(f"Active flood risk zone detected {closest['distance_km']} km away ({closest['title']})")

    if is_coastal:
        flood_score = min(98.0, flood_score + 5.0)

    flood_score = round(min(98.0, max(5.0, flood_score)), 1)

    # 2. CYCLONE / WIND STORM THREAT CALCULATION (0 - 100)
    cyclone_score = 8.0
    cyclone_indicators = []

    if wind_kmh >= 90.0 or wind_gusts >= 115.0:
        cyclone_score = 88.0 + min(10.0, (wind_kmh - 90.0) * 0.3)
        cyclone_indicators.append(f"Severe gale/storm winds ({wind_kmh:.1f} km/h, gusts {wind_gusts:.1f} km/h)")
    elif wind_kmh >= 60.0 or wind_gusts >= 75.0:
        cyclone_score = 65.0 + (wind_kmh - 60.0) * 0.7
        cyclone_indicators.append(f"Squally winds ({wind_kmh:.1f} km/h)")
    elif wind_kmh >= 35.0:
        cyclone_score = 35.0 + (wind_kmh - 35.0) * 1.1
        cyclone_indicators.append(f"Breezy to moderate winds ({wind_kmh:.1f} km/h)")
    else:
        cyclone_score = max(5.0, wind_kmh * 0.8)
        cyclone_indicators.append("Atmospheric wind velocity calm to gentle")

    cyclone_alerts_near = [d for d in nearby_disasters if "cyclone" in d["disaster_type"].lower() or "storm" in d["disaster_type"].lower()]
    if cyclone_alerts_near:
        closest_c = cyclone_alerts_near[0]
        c_boost = max(0.0, 30.0 * (1.0 - closest_c["distance_km"] / 250.0))
        cyclone_score = min(98.0, cyclone_score + c_boost)
        cyclone_indicators.append(f"Active tropical cyclone system within {closest_c['distance_km']} km")

    if is_coastal:
        cyclone_score = min(98.0, cyclone_score + 8.0)
        cyclone_indicators.append("High coastal marine exposure")

    cyclone_score = round(min(98.0, max(5.0, cyclone_score)), 1)

    # 3. SEISMIC THREAT CALCULATION (0 - 100)
    seismic_score = 15.0 if is_seismic_zone else 8.0
    seismic_indicators = []

    if is_seismic_zone:
        seismic_indicators.append("Situated in active tectonic / seismic fault zone (BIS Zone IV/V)")

    quake_alerts_near = [d for d in nearby_disasters if d["disaster_type"] == "Earthquake"]
    if quake_alerts_near:
        # Distance-attenuated seismic energy
        total_seismic_impact = 0.0
        for q in quake_alerts_near[:5]:
            mag = float(q.get("magnitude") or 3.5)
            dist = max(5.0, float(q["distance_km"]))
            # Joyner-Boore geometric attenuation proxy
            energy_term = 10.0 ** (0.7 * (mag - 3.0))
            attenuation = 1.0 / (1.0 + (dist / 45.0) ** 1.8)
            quake_impact = energy_term * attenuation * 3.5
            total_seismic_impact += quake_impact

        seismic_score = min(98.0, seismic_score + total_seismic_impact)
        closest_q = quake_alerts_near[0]
        seismic_indicators.append(
            f"Seismic activity detected: M{closest_q.get('magnitude', '?')} event recorded {closest_q['distance_km']} km away"
        )
    else:
        seismic_indicators.append("No significant seismic hypocenters recorded in vicinity within 250 km")

    seismic_score = round(min(98.0, max(5.0, seismic_score)), 1)

    # 4. HEATWAVE THREAT CALCULATION (0 - 100)
    heat_score = 10.0
    heat_indicators = []

    # Heat index proxy
    heat_index = temp_c + (humidity_pct / 100.0) * 4.0

    if temp_c >= 45.0 or heat_index >= 48.0:
        heat_score = 88.0 + min(10.0, (temp_c - 45.0) * 2.0)
        heat_indicators.append(f"Extreme heatwave emergency ({temp_c:.1f}°C, heat index {heat_index:.1f}°C)")
    elif temp_c >= 42.0 or heat_index >= 45.0:
        heat_score = 70.0 + (temp_c - 42.0) * 5.0
        heat_indicators.append(f"Severe heatwave condition ({temp_c:.1f}°C)")
    elif temp_c >= 38.0:
        heat_score = 45.0 + (temp_c - 38.0) * 6.0
        heat_indicators.append(f"Elevated thermal stress ({temp_c:.1f}°C)")
    elif temp_c <= 5.0:
        heat_score = 30.0
        heat_indicators.append(f"Cold wave conditions ({temp_c:.1f}°C)")
    else:
        heat_score = max(5.0, (temp_c / 35.0) * 25.0)
        heat_indicators.append(f"Ambient temperature within tolerable seasonal band ({temp_c:.1f}°C)")

    heat_score = round(min(98.0, max(5.0, heat_score)), 1)

    # 5. WILDFIRE THREAT CALCULATION (0 - 100)
    fire_score = 8.0
    fire_indicators = []

    fire_alerts_near = [d for d in nearby_disasters if d["disaster_type"] == "Fire"]
    if fire_alerts_near:
        closest_f = fire_alerts_near[0]
        f_boost = max(0.0, 50.0 * (1.0 - closest_f["distance_km"] / 100.0))
        fire_score = min(95.0, 30.0 + f_boost)
        fire_indicators.append(f"Satellite thermal anomaly / active fire detected {closest_f['distance_km']} km away")
    elif temp_c >= 40.0 and humidity_pct <= 25.0 and wind_kmh >= 25.0:
        fire_score = 65.0
        fire_indicators.append("Red flag conditions: high temperature, critically dry humidity (<25%) and gusty winds")
    else:
        fire_score = max(5.0, 10.0 if humidity_pct < 35.0 else 5.0)
        fire_indicators.append("Low thermal ignition susceptibility in sector")

    fire_score = round(min(98.0, max(5.0, fire_score)), 1)

    # 6. COMPOSITE THREAT LEVEL CALCULATION (0 - 100)
    hazard_scores = {
        "Flood Risk": flood_score,
        "Cyclone/Storm": cyclone_score,
        "Earthquake": seismic_score,
        "Heatwave": heat_score,
        "Fire": fire_score
    }

    # Find dominant driver
    sorted_hazards = sorted(hazard_scores.items(), key=lambda x: x[1], reverse=True)
    primary_hazard, max_score = sorted_hazards[0]
    other_scores_sum = sum(score for hazard, score in sorted_hazards[1:])

    # Multi-hazard compounding formula
    compounding_factor = 0.12
    composite_threat = max_score + (compounding_factor * other_scores_sum)
    composite_threat = round(min(99.0, max(10.0, composite_threat)), 1)

    # Threat Tier Classification
    if composite_threat >= 85.0:
        threat_tier = "CRITICAL"
        threat_color = "#991b1b"
        threat_badge_class = "crit"
        tier_desc = "Extreme multi-hazard threat. Severe danger to life and critical infrastructure."
    elif composite_threat >= 70.0:
        threat_tier = "SEVERE"
        threat_color = "#ef4444"
        threat_badge_class = "crit"
        tier_desc = "Severe hazard escalation imminent. Urgent precautionary measures required."
    elif composite_threat >= 50.0:
        threat_tier = "HIGH"
        threat_color = "#f97316"
        threat_badge_class = "high"
        tier_desc = "High hazard probability. Municipal authorities and citizens should maintain high alert."
    elif composite_threat >= 30.0:
        threat_tier = "MODERATE"
        threat_color = "#eab308"
        threat_badge_class = "med"
        tier_desc = "Moderate localized vulnerability. Normal activities permissible with weather vigilance."
    else:
        threat_tier = "LOW"
        threat_color = "#10b981"
        threat_badge_class = "low"
        tier_desc = "Low hazard baseline. No imminent emergency triggers detected in this sector."

    # Generate AI Narrative Synthesis
    loc_display = location["name"]
    ai_narrative = (
        f"AI Multi-Hazard Assessment for {loc_display}: Overall Threat Level is calculated at "
        f"{composite_threat}/100 ({threat_tier} THREAT). "
        f"The primary hazard driver is '{primary_hazard}' (Score: {max_score}/100). "
        f"Real-time sensor telemetry indicates temperature at {temp_c:.1f}°C, humidity at {humidity_pct:.0f}%, "
        f"precipitation rate at {rain_h:.1f} mm/h, and atmospheric wind speed at {wind_kmh:.1f} km/h. "
    )

    if nearby_disasters:
        top_events = ", ".join([f"{d['disaster_type']} ({d['title']}, {d['distance_km']}km away)" for d in nearby_disasters[:3]])
        ai_narrative += f"Spatial query identified {len(nearby_disasters)} proximate active disaster events: {top_events}. "
    else:
        ai_narrative += "No severe active disaster hypocenters or GDACS bulletins were detected within a 250km radius. "

    if threat_tier in ("CRITICAL", "SEVERE"):
        ai_narrative += "Immediate response activation and community shelter preparations are strongly advised."
    elif threat_tier == "HIGH":
        ai_narrative += "Vulnerable low-lying settlements and unreinforced structures should implement preventive safeguards."
    else:
        ai_narrative += "Continuous environmental telemetry monitoring remains active."

    # Mitigation directives
    directives = []
    if primary_hazard == "Flood Risk":
        directives = [
            "P1: Inspect and clear storm drainage culverts; avoid underpasses and riverbank embankments.",
            "P2: Activate municipal water pumping stations and pre-position SDRF inflatable boats.",
            "P3: Citizens in low-lying zones should store emergency drinking water and secure electrical mains."
        ]
    elif primary_hazard == "Cyclone/Storm":
        directives = [
            "P1: Suspend marine fishing operations and anchor coastal sea vessels immediately.",
            "P2: Secure or dismantle loose hoardings, temporary roofing sheets, and tree branches near powerlines.",
            "P3: Identify closest cyclone shelter and keep charged emergency battery packs ready."
        ]
    elif primary_hazard == "Earthquake":
        directives = [
            "P1: Practice Drop, Cover, and Hold On; identify safe open clearings away from glass facades.",
            "P2: Structural engineering triage for critical hospital and water infrastructure.",
            "P3: Shut off municipal gas utility valves to prevent secondary post-quake fire hazards."
        ]
    elif primary_hazard == "Heatwave":
        directives = [
            "P1: Enforce mandatory rest intervals for outdoor manual labor between 12:00 PM and 4:00 PM.",
            "P2: Deploy shaded oral rehydration salts (ORS) kiosks at transit terminals.",
            "P3: Citizens should avoid peak direct solar exposure and ensure hydration for the elderly."
        ]
    else:
        directives = [
            "P1: Maintain regular checks of official NDMA and state disaster authority bulletins.",
            "P2: Keep standard emergency kit prepared (first aid, flashlight, dry rations, emergency radio).",
            "P3: In case of local emergency, call National Emergency Number 112 or NDMA Helpline 1078."
        ]

    return {
        "analysis_id": f"threat-{uuid.uuid4().hex[:8]}",
        "evaluated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "location": location,
        "threat_summary": {
            "overall_threat_score": composite_threat,
            "threat_tier": threat_tier,
            "threat_color": threat_color,
            "threat_badge_class": threat_badge_class,
            "primary_threat_driver": primary_hazard,
            "primary_threat_score": max_score,
            "tier_description": tier_desc
        },
        "telemetry_snapshot": {
            "temperature_c": temp_c,
            "humidity_pct": humidity_pct,
            "precipitation_rate_mm_h": rain_h,
            "daily_precipitation_sum_mm": rain_24,
            "wind_speed_kmh": wind_kmh,
            "wind_gusts_kmh": wind_gusts,
            "weather_condition": weather_cond
        },
        "hazard_breakdown": {
            "flood": {
                "name": "Flood Risk",
                "score": flood_score,
                "tier": "Critical" if flood_score >= 80 else ("High" if flood_score >= 60 else ("Medium" if flood_score >= 35 else "Low")),
                "indicators": flood_indicators
            },
            "cyclone": {
                "name": "Cyclone / Wind Storm",
                "score": cyclone_score,
                "tier": "Critical" if cyclone_score >= 80 else ("High" if cyclone_score >= 60 else ("Medium" if cyclone_score >= 35 else "Low")),
                "indicators": cyclone_indicators
            },
            "seismic": {
                "name": "Earthquake / Seismic",
                "score": seismic_score,
                "tier": "Critical" if seismic_score >= 80 else ("High" if seismic_score >= 60 else ("Medium" if seismic_score >= 35 else "Low")),
                "indicators": seismic_indicators
            },
            "heatwave": {
                "name": "Heatwave / Thermal Stress",
                "score": heat_score,
                "tier": "Critical" if heat_score >= 80 else ("High" if heat_score >= 60 else ("Medium" if heat_score >= 35 else "Low")),
                "indicators": heat_indicators
            },
            "wildfire": {
                "name": "Wildfire / Hotspot",
                "score": fire_score,
                "tier": "Critical" if fire_score >= 80 else ("High" if fire_score >= 60 else ("Medium" if fire_score >= 35 else "Low")),
                "indicators": fire_indicators
            }
        },
        "detected_disasters_count": len(nearby_disasters),
        "detected_disasters": nearby_disasters[:10],
        "ai_narrative": ai_narrative,
        "mitigation_directives": directives
    }


async def perform_area_threat_analysis(
    query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 250.0
) -> Dict[str, Any]:
    """
    High-level orchestrator: Resolves location, fetches real-time telemetry,
    queries active proximate alerts, and evaluates the comprehensive AI threat level.
    """
    loc_info = await resolve_area_location(query=query, lat=lat, lon=lon)
    lat_val = loc_info["latitude"]
    lon_val = loc_info["longitude"]

    # 1. Fetch live meteorological observations
    weather_data = None
    try:
        weather_data = await fetch_weather_for_coords(lat_val, lon_val)
    except Exception as e:
        logger.warning(f"Could not fetch live weather for [{lat_val}, {lon_val}]: {e}")

    # 2. Query active proximate alerts in DB
    nearby_alerts = find_active_disasters_near_area(lat_val, lon_val, radius_km=radius_km)

    # 3. Calculate multi-hazard threat model
    analysis = calculate_area_threat_level(loc_info, weather_data, nearby_alerts)
    return analysis


def get_preset_threat_areas() -> List[Dict[str, Any]]:
    """Returns curated popular areas for quick demo clicks."""
    return [
        {"id": "mumbai", "name": "Mumbai", "region": "Maharashtra, India", "desc": "Coastal Metropolis & Monsoon Catchment"},
        {"id": "delhi", "name": "Delhi-NCR", "region": "North India", "desc": "Yamuna Basin & Seismic Zone IV"},
        {"id": "guwahati", "name": "Guwahati", "region": "Assam, India", "desc": "Brahmaputra Flood Plain & Seismic Zone V"},
        {"id": "kolkata", "name": "Kolkata", "region": "West Bengal, India", "desc": "Bay of Bengal Cyclone & Delta Surge"},
        {"id": "puri", "name": "Puri-Paradip", "region": "Odisha, India", "desc": "Eastern Cyclone Landfall Belt"},
        {"id": "shimla", "name": "Shimla", "region": "Himachal Pradesh", "desc": "Himalayan Landslide & Seismic Zone"},
        {"id": "chennai", "name": "Chennai", "region": "Tamil Nadu, India", "desc": "Coromandel Coast & NE Monsoon Plain"},
        {"id": "kochi", "name": "Kochi", "region": "Kerala, India", "desc": "Arabian Sea Inundation & Backwaters"},
        {"id": "tokyo", "name": "Tokyo", "region": "Japan", "desc": "Pacific Ring of Fire & Typhoon Belt"}
    ]
