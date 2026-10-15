"""
Unit test suite for DisasterWatch Risk Engine and Backend API.
Demonstrates automated testing in EXP-6 (CI/CD GitHub Actions).
"""

import sys
import os
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.risk_engine import (
    evaluate_flood_risk,
    evaluate_cyclone_risk,
    evaluate_heatwave_risk,
    evaluate_earthquake_risk,
    get_safety_guidance
)


def test_flood_risk_normal():
    """Verify minimal rainfall triggers Low estimated risk."""
    sev, score, rule, details = evaluate_flood_risk(hourly_rain_mm=0.0, daily_rain_mm=2.0, wind_kmh=10.0)
    assert sev == "Low"
    assert score <= 3.0
    assert "below flood thresholds" in rule.lower()


def test_flood_risk_critical():
    """Verify extreme rainfall triggers High or Critical estimated risk."""
    sev, score, rule, details = evaluate_flood_risk(hourly_rain_mm=75.0, daily_rain_mm=250.0, wind_kmh=60.0)
    assert sev in ("High", "Critical")
    assert score >= 7.0
    assert "critical rainfall" in rule.lower() or "inundation" in rule.lower()


def test_cyclone_risk_calm_vs_severe():
    """Verify wind speed thresholds for cyclone advisories."""
    calm_sev, calm_score, calm_rule, _ = evaluate_cyclone_risk(wind_kmh=15.0, gust_kmh=20.0)
    assert calm_sev == "Low"

    gale_sev, gale_score, gale_rule, _ = evaluate_cyclone_risk(wind_kmh=95.0, gust_kmh=120.0)
    assert gale_sev in ("High", "Critical")
    assert gale_score >= 7.0


def test_heatwave_risk():
    """Verify temperature thresholds for heatwave evaluation."""
    normal_sev, _, _, _ = evaluate_heatwave_risk(temp_c=30.0)
    assert normal_sev == "Low"

    extreme_sev, score, _, _ = evaluate_heatwave_risk(temp_c=46.5)
    assert extreme_sev in ("High", "Critical")
    assert score >= 7.0


def test_earthquake_severity_thresholds():
    """Verify seismic magnitude categorization."""
    assert evaluate_earthquake_risk(3.2, 10.0)[0] == "Low"
    assert evaluate_earthquake_risk(4.8, 10.0)[0] == "Medium"
    assert evaluate_earthquake_risk(6.3, 10.0)[0] == "High"
    assert evaluate_earthquake_risk(7.5, 10.0)[0] == "Critical"


def test_safety_guidance_dispatch():
    """Verify appropriate safety instructions are returned by disaster type."""
    eq_advice = get_safety_guidance("Earthquake")
    assert "Drop" in eq_advice or "Hold" in eq_advice

    flood_advice = get_safety_guidance("Flood Risk")
    assert "water" in flood_advice.lower() or "ground" in flood_advice.lower()
