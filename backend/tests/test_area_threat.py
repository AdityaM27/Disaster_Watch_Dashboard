"""
Unit test suite for the AI Area Disaster Detection & Threat Level Calculation Service.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.area_threat import (
    haversine_km,
    resolve_area_location,
    calculate_area_threat_level,
    perform_area_threat_analysis,
    get_preset_threat_areas
)
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_haversine_distance():
    # Mumbai to Delhi distance is approximately 1150 - 1200 km
    dist = haversine_km(19.0760, 72.8777, 28.6139, 77.2090)
    assert 1100.0 < dist < 1250.0

    # Distance to self should be 0.0
    dist_zero = haversine_km(19.0760, 72.8777, 19.0760, 72.8777)
    assert dist_zero == 0.0


@pytest.mark.anyio
async def test_resolve_area_location_curated():
    loc = await resolve_area_location("mumbai")
    assert "Mumbai" in loc["name"]
    assert 18.0 <= loc["latitude"] <= 20.0
    assert 72.0 <= loc["longitude"] <= 74.0
    assert loc["is_coastal"] is True

    loc_coords = await resolve_area_location(lat=26.14, lon=91.73)
    assert loc_coords["latitude"] == 26.14
    assert loc_coords["longitude"] == 91.73


def test_calculate_area_threat_level():
    mock_location = {
        "name": "Guwahati, Assam",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "is_coastal": False,
        "is_seismic_zone": True
    }
    mock_weather = {
        "temperature_c": 31.0,
        "humidity_pct": 85.0,
        "hourly_rain_mm": 35.0,
        "daily_precipitation_sum_mm": 120.0,
        "wind_speed_kmh": 22.0,
        "wind_gusts_kmh": 35.0,
        "weather_condition": "Heavy Rain"
    }
    mock_alerts = [
        {
            "id": "test-flood-1",
            "title": "Severe Flood Warning - Brahmaputra",
            "disaster_type": "Flood Risk",
            "severity": "Critical",
            "status": "Official Alert",
            "location_name": "Guwahati",
            "distance_km": 15.0
        }
    ]

    analysis = calculate_area_threat_level(mock_location, mock_weather, mock_alerts)
    
    assert "threat_summary" in analysis
    summary = analysis["threat_summary"]
    assert 0.0 <= summary["overall_threat_score"] <= 100.0
    assert summary["threat_tier"] in ["LOW", "MODERATE", "HIGH", "SEVERE", "CRITICAL"]
    assert summary["primary_threat_driver"] == "Flood Risk"
    assert "hazard_breakdown" in analysis
    assert "flood" in analysis["hazard_breakdown"]
    assert "mitigation_directives" in analysis
    assert len(analysis["mitigation_directives"]) == 3


def test_api_threat_areas_endpoint():
    resp = client.get("/api/ai/threat-areas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 5
    assert any(a["id"] == "mumbai" for a in data["areas"])


def test_api_analyze_area_post():
    payload = {"location": "Delhi", "radius_km": 200.0}
    resp = client.post("/api/ai/analyze-area", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "threat_summary" in data
    assert 0.0 <= data["threat_summary"]["overall_threat_score"] <= 100.0
    assert "telemetry_snapshot" in data
    assert "ai_narrative" in data
