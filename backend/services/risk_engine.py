"""
Risk Engine for DisasterWatch India.
Provides transparent, rule-based risk evaluation, severity classification,
and standard safety guidance.

Every rule records:
1. Exact triggered rule condition
2. Measured physical parameters
3. Threshold benchmarks
4. Safety guidance
5. Explicit status: Confirmed Event vs Estimated Risk vs Official Alert
"""

from typing import Dict, Any, Tuple
from datetime import datetime, timezone

STANDARD_DISCLAIMER = (
    "This student project is for disaster awareness and monitoring only. "
    "Always follow official instructions from local authorities, "
    "disaster-management agencies, and emergency services."
)

SAFETY_GUIDELINES = {
    "Earthquake": (
        "Drop, Cover, and Hold On; move away from damaged structures after shaking stops."
    ),
    "Flood Risk": (
        "Avoid walking/driving through flood water; move to safer higher ground when instructed by authorities."
    ),
    "Fire": (
        "Follow local evacuation instructions and avoid smoke exposure."
    ),
    "Cyclone/Storm": (
        "Stay indoors, follow official warnings, and avoid coastal/low-lying areas when directed."
    ),
    "Heatwave": (
        "Stay hydrated, avoid peak heat, and check vulnerable people."
    )
}


def evaluate_earthquake_risk(magnitude: float, depth_km: float) -> Tuple[str, float, str, Dict[str, Any]]:
    """
    Evaluates seismic severity based on USGS reported magnitude and focal depth.
    
    Rules:
    - Magnitude < 4.0: Low
    - Magnitude 4.0 to 5.9: Medium
    - Magnitude 6.0 to 6.9: High
    - Magnitude >= 7.0: Critical
    
    Depth adjustment: Shallow quakes (< 30km) produce significantly higher ground acceleration.
    """
    mag = round(float(magnitude), 1)
    depth = round(float(depth_km), 1) if depth_km is not None else 10.0

    if mag < 4.0:
        severity = "Low"
        rule = f"Minor seismic event (Magnitude {mag} < 4.0). Generally felt only by sensitive instruments or few individuals."
        score = 2.0 + (mag / 4.0) * 1.5
    elif mag < 6.0:
        severity = "Medium"
        rule = f"Moderate earthquake (Magnitude {mag} between 4.0 and 5.9). Capable of slight damage to poor structures near epicenter."
        score = 4.0 + ((mag - 4.0) / 2.0) * 2.5
    elif mag < 7.0:
        severity = "High"
        rule = f"Strong earthquake (Magnitude {mag} between 6.0 and 6.9). Capable of destructive shaking within 100km radius."
        score = 6.8 + ((mag - 6.0) / 1.0) * 1.7
    else:
        severity = "Critical"
        rule = f"Major earthquake (Magnitude {mag} >= 7.0). Serious potential for widespread structural damage and emergency response activation."
        score = min(10.0, 8.5 + (mag - 7.0) * 0.75)

    # Note focal depth influence in explanation
    depth_note = "Shallow depth (<30km) enhances surface shaking potential" if depth <= 30 else "Intermediate to deep focal depth (>30km)"

    details = {
        "magnitude": mag,
        "depth_km": depth,
        "depth_context": depth_note,
        "magnitude_scale": "Richter / Moment Magnitude (USGS)",
        "thresholds": {
            "low": "< 4.0",
            "medium": "4.0 - 5.9",
            "high": "6.0 - 6.9",
            "critical": ">= 7.0"
        }
    }

    return severity, round(score, 1), rule, details


def evaluate_flood_risk(hourly_rain_mm: float, daily_rain_mm: float, wind_kmh: float = 0.0) -> Tuple[str, float, str, Dict[str, Any]]:
    """
    Evaluates Estimated Flood Risk based on live precipitation observations.
    
    IMPORTANT DATA RULE:
    Clearly labelled as 'Estimated Flood Risk', NOT confirmed flooding.
    
    Rules (using IMD/CWC benchmark rainfall intensity metrics):
    - Hourly rain > 30 mm OR 24h rain > 100 mm: Critical Estimated Risk
    - Hourly rain > 15 mm OR 24h rain > 50 mm: High Estimated Risk
    - Hourly rain > 5 mm OR 24h rain > 20 mm: Medium Estimated Risk
    - Hourly rain <= 5 mm AND 24h rain <= 20 mm: Low Estimated Risk
    """
    h_rain = round(float(hourly_rain_mm or 0.0), 1)
    d_rain = round(float(daily_rain_mm or 0.0), 1)
    wind = round(float(wind_kmh or 0.0), 1)

    if h_rain > 30.0 or d_rain > 100.0:
        severity = "Critical"
        rule = f"Critical rainfall threshold exceeded (Hourly: {h_rain} mm, 24h: {d_rain} mm). High probability of severe waterlogging and flash inundation."
        score = 8.8
    elif h_rain > 15.0 or d_rain > 50.0:
        severity = "High"
        rule = f"High rainfall threshold exceeded (Hourly: {h_rain} mm, 24h: {d_rain} mm). Potential for localized urban flooding and stream swelling."
        score = 6.9
    elif h_rain > 5.0 or d_rain > 20.0:
        severity = "Medium"
        rule = f"Moderate precipitation observed (Hourly: {h_rain} mm, 24h: {d_rain} mm). Low-lying drainage delays possible."
        score = 4.5
    else:
        severity = "Low"
        rule = f"Normal/minimal rainfall observed (Hourly: {h_rain} mm, 24h: {d_rain} mm). Well below flood thresholds."
        score = 1.8

    details = {
        "hourly_rain_mm": h_rain,
        "daily_rain_mm": d_rain,
        "wind_speed_kmh": wind,
        "category": "Estimated Flood Risk (Decision Support)",
        "thresholds": {
            "low": "24h rain <= 20mm & hourly <= 5mm",
            "medium": "24h rain 20-50mm or hourly 5-15mm",
            "high": "24h rain 50-100mm or hourly 15-30mm",
            "critical": "24h rain > 100mm or hourly > 30mm"
        }
    }

    return severity, score, rule, details


def evaluate_cyclone_risk(wind_kmh: float, gust_kmh: float = 0.0) -> Tuple[str, float, str, Dict[str, Any]]:
    """
    Evaluates Cyclone / Storm risk based on IMD sustained wind classification.
    """
    wind = round(float(wind_kmh or 0.0), 1)

    if wind >= 89.0:
        severity = "Critical"
        rule = f"Severe cyclonic wind speeds detected ({wind} km/h >= 89 km/h threshold). Structural and coastal threat."
        score = 9.0
    elif wind >= 62.0:
        severity = "High"
        rule = f"Cyclonic storm wind speeds detected ({wind} km/h >= 62 km/h threshold). Gale force winds likely."
        score = 7.0
    elif wind >= 31.0:
        severity = "Medium"
        rule = f"Depression/strong wind advisory ({wind} km/h between 31 and 61 km/h). Rough coastal conditions."
        score = 4.2
    else:
        severity = "Low"
        rule = f"Breeze/light winds ({wind} km/h < 31 km/h). Normal atmospheric parameters."
        score = 1.5

    details = {
        "wind_speed_kmh": wind,
        "gust_speed_kmh": gust_kmh,
        "classification_system": "India Meteorological Department (IMD) Cyclonic Scale",
        "thresholds": {
            "low": "< 31 km/h",
            "medium": "31 - 61 km/h (Depression)",
            "high": "62 - 88 km/h (Cyclonic Storm)",
            "critical": ">= 89 km/h (Severe Cyclonic Storm)"
        }
    }

    return severity, score, rule, details


def evaluate_heatwave_risk(temp_c: float) -> Tuple[str, float, str, Dict[str, Any]]:
    """
    Evaluates Heatwave risk based on IMD criteria for Indian plains.
    """
    temp = round(float(temp_c or 0.0), 1)

    if temp >= 45.0:
        severity = "Critical"
        rule = f"Severe Heatwave threshold reached ({temp}°C >= 45°C). Extreme dehydration and heatstroke risk."
        score = 8.9
    elif temp >= 42.0:
        severity = "High"
        rule = f"Heatwave condition detected ({temp}°C between 42°C and 44.9°C). High risk for vulnerable populations."
        score = 6.8
    elif temp >= 38.0:
        severity = "Medium"
        rule = f"Elevated temperature ({temp}°C between 38°C and 41.9°C). Pre-heatwave caution advised."
        score = 4.0
    else:
        severity = "Low"
        rule = f"Normal temperature range ({temp}°C < 38°C)."
        score = 1.2

    details = {
        "temperature_c": temp,
        "classification_system": "IMD Heatwave Criteria",
        "thresholds": {
            "low": "< 38°C",
            "medium": "38°C - 41.9°C",
            "high": "42°C - 44.9°C (Heatwave)",
            "critical": ">= 45°C (Severe Heatwave)"
        }
    }

    return severity, score, rule, details


def get_safety_guidance(disaster_type: str) -> str:
    """Returns official concise safety advice for a specific disaster category."""
    return SAFETY_GUIDELINES.get(
        disaster_type,
        "Follow advisories issued by national and state disaster management authorities (NDMA/SDMA)."
    )
