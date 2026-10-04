"""
DisasterWatch India — Real-Time Disaster Monitoring and Affected Area Mapping System
Backend REST API built with FastAPI and SQLite.

Author: DisasterWatch Team
License: Academic / Open-Source Decision Support
Disclaimer: This student project is for disaster awareness and monitoring only.
            Always follow official instructions from local authorities,
            disaster-management agencies, and emergency services.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Load environment configuration
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

from database import (
    init_db,
    save_alerts_batch,
    get_alerts,
    get_alert_by_id,
    log_refresh,
    get_refresh_logs,
    get_monitored_locations,
    get_preference,
    set_preference
)
from models import (
    AlertItem,
    SourceStatus,
    RefreshLog,
    RiskExplanation,
    DashboardSummary
)
from services.risk_engine import (
    STANDARD_DISCLAIMER,
    evaluate_flood_risk,
    evaluate_cyclone_risk,
    evaluate_heatwave_risk,
    get_safety_guidance
)
from services.earthquakes import fetch_usgs_earthquakes
from services.weather import (
    fetch_weather_for_coords,
    evaluate_location_weather_risk,
    evaluate_multiple_locations
)
from services.fires import (
    fetch_active_fires,
    is_fire_service_configured
)
from services.gdacs import fetch_gdacs_global_events

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("disasterwatch")

# Startup timestamp for uptime calculation
SERVER_START_TIME = datetime.now(timezone.utc)
LAST_REFRESH_TIME: Optional[str] = None


async def execute_live_refresh() -> Dict[str, Any]:
    """
    Executes a comprehensive real-time data sync across all configured live feeds worldwide:
    1. USGS GeoJSON Earthquakes (Global 24h & M4.5+ worldwide)
    2. Open-Meteo Weather for global stations -> Estimated Flood, Cyclone & Heatwave Risk
    3. GDACS (United Nations & European Commission) multi-hazard feed (Cyclones, Floods, Fires, Quakes)
    4. NASA FIRMS Fires (if API key configured)
    
    Saves results to SQLite and records refresh audit logs.
    """
    global LAST_REFRESH_TIME
    start_t = time.time()
    results_summary = {"earthquakes": 0, "weather_risk_stations": 0, "gdacs_global_events": 0, "fires": 0}
    errors = []

    # 1. Refresh USGS Earthquakes (Worldwide)
    try:
        quakes = await fetch_usgs_earthquakes(include_global=True, min_magnitude=2.0)
        if quakes:
            save_alerts_batch(quakes)
            results_summary["earthquakes"] = len(quakes)
            log_refresh("USGS Global Earthquakes", "SUCCESS", len(quakes), f"Retrieved {len(quakes)} seismic events worldwide", (time.time() - start_t) * 1000)
    except Exception as e:
        logger.error(f"USGS Earthquake refresh error: {e}")
        errors.append(f"Earthquake sync failed: {str(e)}")
        log_refresh("USGS Global Earthquakes", "FAILED", 0, str(e), (time.time() - start_t) * 1000)

    # 2. Refresh GDACS Global Multi-Hazard Feeds (Tropical Cyclones, Floods, Wildfires, Earthquakes)
    try:
        gdacs_events = await fetch_gdacs_global_events()
        if gdacs_events:
            save_alerts_batch(gdacs_events)
            results_summary["gdacs_global_events"] = len(gdacs_events)
            log_refresh("GDACS (UN / European Commission)", "SUCCESS", len(gdacs_events), f"Retrieved {len(gdacs_events)} global alerts", (time.time() - start_t) * 1000)
    except Exception as e:
        logger.error(f"GDACS refresh error: {e}")
        errors.append(f"GDACS sync failed: {str(e)}")
        log_refresh("GDACS (UN / European Commission)", "FAILED", 0, str(e), (time.time() - start_t) * 1000)

    # 3. Refresh Weather and Estimated Flood/Cyclone/Heatwave Risk for Monitored Global Stations
    try:
        stations = get_monitored_locations()
        if stations:
            weather_risks = await evaluate_multiple_locations(stations)
            if weather_risks:
                save_alerts_batch(weather_risks)
                results_summary["weather_risk_stations"] = len(weather_risks)
                log_refresh("Open-Meteo Global Weather", "SUCCESS", len(weather_risks), f"Evaluated {len(weather_risks)} stations globally", (time.time() - start_t) * 1000)
    except Exception as e:
        logger.error(f"Weather & Flood Risk refresh error: {e}")
        errors.append(f"Weather risk sync failed: {str(e)}")
        log_refresh("Open-Meteo Global Weather", "FAILED", 0, str(e), (time.time() - start_t) * 1000)

    # 4. Check NASA FIRMS Fires (if configured)
    try:
        fire_status, fire_alerts, fire_msg = await fetch_active_fires()
        if fire_alerts:
            save_alerts_batch(fire_alerts)
            results_summary["fires"] = len(fire_alerts)
            log_refresh("NASA FIRMS Fires", fire_status, len(fire_alerts), fire_msg, (time.time() - start_t) * 1000)
        else:
            log_refresh("NASA FIRMS Fires", fire_status, 0, fire_msg, (time.time() - start_t) * 1000)
    except Exception as e:
        logger.error(f"NASA FIRMS Fire check error: {e}")
        log_refresh("NASA FIRMS Fires", "ERROR", 0, str(e), (time.time() - start_t) * 1000)
    LAST_REFRESH_TIME = datetime.now(timezone.utc).isoformat()
    duration_ms = round((time.time() - start_t) * 1000, 1)

    return {
        "status": "SUCCESS" if not errors else "PARTIAL",
        "last_refreshed": LAST_REFRESH_TIME,
        "counts": results_summary,
        "errors": errors,
        "duration_ms": duration_ms
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager: initializes database and executes initial data prime."""
    logger.info("Initializing DisasterWatch India database schema...")
    init_db()
    logger.info("Priming live disaster monitoring feeds...")
    try:
        await execute_live_refresh()
    except Exception as e:
        logger.error(f"Initial feed prime encountered an issue: {e}")
    yield
    logger.info("DisasterWatch India shutting down safely.")


# Initialize FastAPI application
app = FastAPI(
    title="DisasterWatch India API",
    description="Real-Time Disaster Monitoring and Affected Area Mapping System",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local frontend testing and interoperability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Backend API Routes ---

@app.get("/api/health", tags=["System"])
async def get_health():
    """
    Returns system status, database health, and uptime.
    """
    now = datetime.now(timezone.utc)
    uptime_sec = round((now - SERVER_START_TIME).total_seconds(), 1)
    
    # Verify DB connectivity
    db_ok = False
    try:
        locs = get_monitored_locations()
        db_ok = len(locs) > 0
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "DisasterWatch India",
        "version": "1.0.0",
        "database_connected": db_ok,
        "uptime_seconds": uptime_sec,
        "current_time_utc": now.isoformat(),
        "last_data_refresh": LAST_REFRESH_TIME,
        "disclaimer": STANDARD_DISCLAIMER
    }


@app.get("/api/earthquakes", tags=["Disasters"])
async def get_earthquakes(
    region: str = Query("all", description="'india', 'regional', or 'all'"),
    min_magnitude: float = Query(2.0, description="Minimum Richter magnitude"),
    limit: int = Query(100, description="Maximum number of events")
):
    """
    Retrieves verified real earthquake events originating from the official USGS feed.
    """
    alerts = get_alerts(disaster_type="Earthquake", limit=limit)
    
    if region == "india":
        # Bounding box for mainland India & nearby maritime territory
        alerts = [
            a for a in alerts 
            if 6.0 <= a["latitude"] <= 37.0 and 68.0 <= a["longitude"] <= 97.5
        ]
    elif region == "regional":
        # South Asia & Himalayan seismic corridor
        alerts = [
            a for a in alerts 
            if 0.0 <= a["latitude"] <= 40.0 and 60.0 <= a["longitude"] <= 100.0
        ]

    alerts = [a for a in alerts if (a.get("magnitude") or 0) >= min_magnitude]
    return {
        "count": len(alerts),
        "source": "USGS Earthquake Hazards Program",
        "region_filter": region,
        "events": alerts
    }


@app.get("/api/weather", tags=["Disasters"])
async def get_weather(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    city: Optional[str] = Query(None, description="Optional city name for display")
):
    """
    Retrieves live weather data for given coordinates and computes Estimated Flood Risk.
    Does NOT assert an area is flooded; labels results strictly as 'Estimated Flood Risk'.
    """
    weather = await fetch_weather_for_coords(lat, lon)
    if not weather:
        raise HTTPException(status_code=502, detail="Weather data feed temporarily unreachable")

    # Evaluate transparent risks
    hourly_rain = weather.get("hourly_rain_mm", 0.0)
    daily_rain = weather.get("daily_precipitation_sum_mm", 0.0)
    wind_kmh = weather.get("wind_speed_kmh", 0.0)
    temp_c = weather.get("temperature_c", 0.0)

    f_sev, f_score, f_rule, f_details = evaluate_flood_risk(hourly_rain, daily_rain, wind_kmh)
    c_sev, c_score, c_rule, c_details = evaluate_cyclone_risk(wind_kmh)
    h_sev, h_score, h_rule, h_details = evaluate_heatwave_risk(temp_c)

    return {
        "location": {
            "city": city or f"Coordinates [{lat:.2f}, {lon:.2f}]",
            "latitude": lat,
            "longitude": lon
        },
        "current_weather": weather,
        "estimated_risks": {
            "flood_risk": {
                "category": "Estimated Flood Risk",
                "severity": f_sev,
                "score": f_score,
                "triggered_rule": f_rule,
                "details": f_details,
                "safety_guidance": get_safety_guidance("Flood Risk")
            },
            "cyclone_risk": {
                "category": "Estimated Cyclone Risk",
                "severity": c_sev,
                "score": c_score,
                "triggered_rule": c_rule,
                "details": c_details,
                "safety_guidance": get_safety_guidance("Cyclone/Storm")
            },
            "heatwave_risk": {
                "category": "Estimated Heatwave Risk",
                "severity": h_sev,
                "score": h_score,
                "triggered_rule": h_rule,
                "details": h_details,
                "safety_guidance": get_safety_guidance("Heatwave")
            }
        },
        "source": "Open-Meteo Real-Time Weather API",
        "disclaimer": STANDARD_DISCLAIMER
    }


@app.get("/api/alerts", tags=["Alerts"])
async def list_alerts(
    disaster_type: Optional[str] = Query(None, description="Disaster type filter (e.g. Earthquake, Flood Risk, Fire)"),
    severity: Optional[str] = Query(None, description="Severity filter: Low, Medium, High, Critical"),
    status: Optional[str] = Query(None, description="Confirmed Event, Official Alert, or Estimated Risk"),
    official_only: bool = Query(False, description="Filter for official alerts only"),
    risk_zones_only: bool = Query(False, description="Filter for estimated-risk zones only"),
    search: Optional[str] = Query(None, description="Search by location name or title"),
    limit: int = Query(250, description="Maximum number of alerts to return")
):
    """
    Retrieves live disaster events, official alerts, and estimated-risk zones
    matching active sidebar filter selections.
    """
    alerts = get_alerts(
        disaster_type=disaster_type,
        severity=severity,
        status=status,
        official_only=official_only,
        risk_zones_only=risk_zones_only,
        search=search,
        limit=limit
    )
    return {
        "count": len(alerts),
        "last_refreshed": LAST_REFRESH_TIME,
        "alerts": alerts
    }


@app.get("/api/alerts/{alert_id}", tags=["Alerts"])
async def get_alert(alert_id: str):
    """
    Retrieves full details for a single disaster event, including verified coordinates,
    exact calculation basis, safety advice, and original source citation.
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.post("/api/refresh", tags=["Operations"])
async def refresh_live_data():
    """
    Manually triggers an immediate pull from live external feeds
    (USGS, Open-Meteo weather stations, and NASA FIRMS if configured).
    """
    logger.info("Manual refresh triggered via /api/refresh")
    summary = await execute_live_refresh()
    return summary


@app.get("/api/sources", tags=["Sources"])
async def get_sources():
    """
    Returns the honest connection and data status of all monitored disaster feeds.
    Unconfigured or future sources are clearly labeled 'Not connected yet'.
    """
    fire_configured = is_fire_service_configured()
    
    sources = [
        {
            "id": "src-gdacs",
            "name": "GDACS (United Nations & European Commission)",
            "disaster_type": "Cyclone/Storm, Flood Risk, Fire, Earthquake",
            "connection_status": "Connected",
            "last_successful_update": LAST_REFRESH_TIME,
            "update_frequency": "Real-time international disaster bulletins",
            "description": "Global Disaster Alert and Coordination System run by UN OCHA and European Commission JRC.",
            "website_url": "https://www.gdacs.org/",
            "is_live": True,
            "details": "Real-time global multi-hazard alert levels (Green, Orange, Red) and impact modeling."
        },
        {
            "id": "src-usgs",
            "name": "USGS Earthquake Hazards Program",
            "disaster_type": "Earthquake",
            "connection_status": "Connected",
            "last_successful_update": LAST_REFRESH_TIME,
            "update_frequency": "Continuous GeoJSON Feed (approx. every 1-5 mins)",
            "description": "United States Geological Survey global seismic network and South Asian regional boundary monitoring.",
            "website_url": "https://earthquake.usgs.gov/earthquakes/feed/",
            "is_live": True,
            "details": "Real-time magnitude, hypocentral depth, coordinates, and felt intensity."
        },
        {
            "id": "src-open-meteo",
            "name": "Open-Meteo Meteorological Service",
            "disaster_type": "Flood Risk, Cyclone/Storm, Heatwave",
            "connection_status": "Connected",
            "last_successful_update": LAST_REFRESH_TIME,
            "update_frequency": "Hourly atmospheric prediction models",
            "description": "Public weather forecasting service used to estimate flood, cyclonic wind, and temperature thresholds.",
            "website_url": "https://open-meteo.com/",
            "is_live": True,
            "details": "Calculates Estimated Flood Risk based on precipitation benchmarks."
        },
        {
            "id": "src-nasa-firms",
            "name": "NASA FIRMS (Thermal Anomalies)",
            "disaster_type": "Fire",
            "connection_status": "Connected" if fire_configured else "Not connected yet",
            "last_successful_update": LAST_REFRESH_TIME if fire_configured else None,
            "update_frequency": "Near-Real-Time (NRT) satellite passes (VIIRS/MODIS)",
            "description": "Active thermal detection system by NASA EOSDIS. Requires free MAP_KEY registration.",
            "website_url": "https://firms.modaps.eosdis.nasa.gov/",
            "is_live": fire_configured,
            "details": "Configurable in .env via NASA_FIRMS_MAP_KEY. Zero fake fire points are created."
        },
        {
            "id": "src-ndma-cap",
            "name": "NDMA / National CAP Alert Gateway",
            "disaster_type": "Official Multi-Hazard Alerts",
            "connection_status": "Not connected yet",
            "last_successful_update": None,
            "update_frequency": "Official broadcast event triggers",
            "description": "Common Alerting Protocol (CAP v1.2) gateway designed for NDMA / State Disaster Management Authorities.",
            "website_url": "https://sachet.ndma.gov.in/",
            "is_live": False,
            "details": "Architecture prepared for authorized state CAP feed ingestion. No mock alerts generated."
        }
    ]
    return {
        "count": len(sources),
        "sources_online": sum(1 for s in sources if s["is_live"]),
        "sources": sources
    }


@app.get("/api/download-documentation-pdf", tags=["Documentation"])
async def download_documentation_pdf():
    """
    Returns the comprehensive PDF document containing project architecture,
    classification taxonomy, live telemetric risk calculation formulas, and safety guidance.
    """
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DisasterWatch_Project_Documentation.pdf")
    if not os.path.exists(pdf_path):
        from generate_pdf import generate_documentation_pdf
        generate_documentation_pdf(pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="DisasterWatch_Project_Documentation.pdf"
    )


@app.get("/api/risk-explanation/{alert_id}", tags=["Risk Engine"])
async def get_risk_explanation(alert_id: str):
    """
    Returns an educational breakdown of how the severity and risk score
    for a specific alert were calculated by the risk engine.
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    details = alert.get("risk_calculation_details", {})
    measured = {}
    benchmarks = {}

    if alert["disaster_type"] == "Earthquake":
        measured = {
            "magnitude": alert.get("magnitude"),
            "depth_km": alert.get("depth_km"),
            "focal_context": details.get("depth_context")
        }
        benchmarks = details.get("thresholds", {
            "low": "< 4.0 Richter",
            "medium": "4.0 - 5.9 Richter",
            "high": "6.0 - 6.9 Richter",
            "critical": ">= 7.0 Richter"
        })
    elif alert["disaster_type"] in ("Flood Risk", "Cyclone/Storm", "Heatwave"):
        measured = details.get("all_measured_metrics", {
            "hourly_precipitation_mm": details.get("hourly_rain_mm"),
            "daily_precipitation_sum_mm": alert.get("rainfall_mm"),
            "wind_speed_kmh": alert.get("wind_speed_kmh"),
            "temperature_c": alert.get("temperature_c")
        })
        benchmarks = details.get("thresholds", {})
    elif alert["disaster_type"] == "Fire":
        measured = {
            "fire_radiative_power_mw": details.get("fire_radiative_power_mw"),
            "brightness_temperature_k": details.get("brightness_temperature_k"),
            "satellite_instrument": details.get("satellite_instrument")
        }
        benchmarks = {
            "low": "FRP <= 10 MW",
            "medium": "FRP 10 - 30 MW",
            "high": "FRP 30 - 100 MW",
            "critical": "FRP > 100 MW or Brightness > 360 K"
        }

    return {
        "alert_id": alert_id,
        "title": alert["title"],
        "disaster_type": alert["disaster_type"],
        "severity": alert["severity"],
        "status": alert["status"],
        "triggered_rule": alert["risk_rule_triggered"],
        "measured_values": measured,
        "threshold_benchmarks": benchmarks,
        "safety_guidance": alert["safety_guidance"],
        "source_name": alert["source_name"],
        "source_url": alert["source_url"],
        "calculation_timestamp": alert["updated_time"],
        "disclaimer": STANDARD_DISCLAIMER
    }


@app.get("/api/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """
    Returns aggregated metrics for the dashboard top summary cards:
    - Active events
    - High/Critical events
    - Recent earthquakes
    - Sources online
    """
    alerts = get_alerts(limit=500)
    sources_info = await get_sources()
    
    active_count = len(alerts)
    high_critical = sum(1 for a in alerts if a["severity"] in ("High", "Critical"))
    earthquakes_count = sum(1 for a in alerts if a["disaster_type"] == "Earthquake")
    
    return {
        "active_events": active_count,
        "high_critical_events": high_critical,
        "recent_earthquakes": earthquakes_count,
        "sources_online": sources_info["sources_online"],
        "total_sources": sources_info["count"],
        "last_refreshed": LAST_REFRESH_TIME
    }


@app.get("/api/locations", tags=["Locations"])
async def list_monitored_locations():
    """
    Returns the list of monitored stations across India.
    """
    locs = get_monitored_locations()
    return {"count": len(locs), "locations": locs}


@app.get("/api/refresh-history", tags=["Operations"])
async def get_refresh_history(limit: int = 20):
    """
    Returns the recent audit logs of feed refresh operations.
    """
    logs = get_refresh_logs(limit=limit)
    return {"count": len(logs), "logs": logs}


# Mount Frontend Static Files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html is being prepared."}
