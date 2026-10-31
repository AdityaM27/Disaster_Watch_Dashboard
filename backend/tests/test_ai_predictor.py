"""
Unit test suite for the AI Disaster Future Prediction Engine.
Tests multi-horizon predictions for Flood, Cyclone, Earthquake, and Heatwave.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_predictor import (
    predict_disaster_future,
    predict_flood_trajectory,
    predict_cyclone_trajectory,
    predict_earthquake_aftershocks,
    predict_heatwave_trajectory,
    get_preset_disaster_scenarios
)


def test_ai_flood_prediction():
    res = predict_flood_trajectory("Brahmaputra Basin", 26.14, 91.73, current_rain_mm=30.0, horizon_hours=72)
    assert res["disaster_type"] == "Flood Risk"
    assert len(res["timeline"]) > 5
    assert res["model_confidence_pct"] >= 80.0
    assert "Hydro-Autoregressive" in res["model_name"]
    assert res["peak_risk_hour"] >= 0
    assert any("Cumulative Precipitation" in k for k in res["feature_importance"])


def test_ai_cyclone_prediction():
    res = predict_cyclone_trajectory("Odisha Coast", 19.81, 85.83, current_wind_kmh=95.0, horizon_hours=72)
    assert res["disaster_type"] == "Cyclone/Storm"
    assert "Kaplan-DeMaria" in res["model_name"]
    assert any("Cyclonic Storm" in step.get("predicted_category", "") for step in res["timeline"])


def test_ai_earthquake_aftershocks():
    res = predict_earthquake_aftershocks("Delhi-NCR", 28.61, 77.20, mainshock_mag=6.5, depth_km=15.0, horizon_hours=72)
    assert res["disaster_type"] == "Earthquake"
    assert "Omori-Utsu" in res["model_name"]
    assert res["timeline"][0]["predicted_value"] > res["timeline"][-1]["predicted_value"] # decaying probability
    assert "expected_max_mag" in res["timeline"][0]


def test_ai_heatwave_prediction():
    res = predict_heatwave_trajectory("Vidarbha", 21.14, 79.08, current_temp_c=45.0, horizon_hours=72)
    assert res["disaster_type"] == "Heatwave"
    assert res["timeline"][0]["predicted_value"] > 35.0


def test_ai_dispatcher_and_presets():
    presets = get_preset_disaster_scenarios()
    assert len(presets) >= 4
    for p in presets:
        pred = predict_disaster_future(p["disaster_type"], p["location_name"], p["latitude"], p["longitude"], p["current_value"])
        assert pred["prediction_id"].startswith("ai-pred-")
        assert len(pred["timeline"]) >= 3
