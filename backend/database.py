"""
SQLite Database module for DisasterWatch India.
Manages alerts cache, refresh audit logs, monitored stations, and user preferences.
Uses standard Python sqlite3 with JSON serialization for nested risk explanations.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Resolve default DB path relative to disasterwatch-india root
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "disasterwatch.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
if not os.path.isabs(DB_PATH):
    # Ensure relative path starts from project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(project_root, DB_PATH)


def get_db_connection() -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes database tables and seeds reference observation points across India.
    Safe to execute multiple times (CREATE TABLE IF NOT EXISTS).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table: alerts (stores current active and recent historical alerts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            disaster_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            magnitude REAL,
            depth_km REAL,
            rainfall_mm REAL,
            wind_speed_kmh REAL,
            temperature_c REAL,
            risk_score REAL,
            risk_rule_triggered TEXT NOT NULL,
            risk_calculation_details TEXT,
            safety_guidance TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            event_time TEXT NOT NULL,
            updated_time TEXT NOT NULL,
            is_estimated_zone INTEGER DEFAULT 0,
            is_official_alert INTEGER DEFAULT 0,
            zone_radius_km REAL
        )
    """)

    # Table: refresh_logs (audit log for live feed refresh cycles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            events_count INTEGER DEFAULT 0,
            message TEXT,
            duration_ms REAL DEFAULT 0.0
        )
    """)

    # Table: user_preferences (key-value settings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Table: monitored_locations (predefined key cities and flood/seismic basins in India)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT,
            is_coastal INTEGER DEFAULT 0,
            is_seismic_zone INTEGER DEFAULT 0
        )
    """)

    # Seed monitored stations across the world if table is empty or needs global update
    cursor.execute("SELECT COUNT(*) FROM monitored_locations")
    count = cursor.fetchone()[0]
    if count < 25:
        # Clear previous partial list if any and re-seed with global + Indian observation network
        cursor.execute("DELETE FROM monitored_locations")
        seed_stations = [
            # India & South Asia
            ("loc-delhi", "New Delhi", "India", 28.6139, 77.2090, "Yamuna flood plain & seismic zone IV", 0, 1),
            ("loc-mumbai", "Mumbai", "India", 19.0760, 72.8777, "Arabian Sea metropolis, heavy monsoon deluge exposure", 1, 0),
            ("loc-kolkata", "Kolkata", "India", 22.5726, 88.3639, "Hooghly delta basin & Bay of Bengal cyclone surge zone", 1, 0),
            ("loc-chennai", "Chennai", "India", 13.0827, 80.2707, "Coromandel coastal zone & NE monsoon flood plain", 1, 0),
            ("loc-guwahati", "Guwahati", "India", 26.1445, 91.7362, "Brahmaputra high-flood corridor & seismic zone V", 0, 1),
            ("loc-patna", "Patna", "India", 25.5941, 85.1376, "Ganga river basin critical inundation plain", 0, 0),
            ("loc-srinagar", "Srinagar", "India", 34.0837, 74.7973, "Jhelum valley flood basin & Himalayan seismic zone V", 0, 1),
            ("loc-kochi", "Kochi", "India", 9.9312, 76.2673, "Arabian Sea coastal lowland and backwaters flood zone", 1, 0),
            ("loc-bhubaneswar", "Bhubaneswar", "India", 20.2961, 85.8245, "East coast cyclone & Mahanadi delta flood basin", 1, 0),
            ("loc-bhuj", "Bhuj", "India", 23.2420, 69.6669, "Kutch seismic zone V high risk fault line", 0, 1),
            
            # East Asia & Pacific Ring of Fire
            ("loc-tokyo", "Tokyo", "Japan", 35.6762, 139.6503, "Pacific Ring of Fire seismic epicenter & typhoon corridor", 1, 1),
            ("loc-manila", "Manila", "Philippines", 14.5995, 120.9842, "Western Pacific tropical typhoon basin & seismic fault", 1, 1),
            ("loc-jakarta", "Jakarta", "Indonesia", -6.2088, 106.8456, "Java trench subduction zone & coastal subsidence flood basin", 1, 1),
            ("loc-taipei", "Taipei", "Taiwan", 25.0330, 121.5654, "Okinawa trough subduction fault & Pacific typhoon corridor", 1, 1),
            ("loc-bangkok", "Bangkok", "Thailand", 13.7563, 100.5018, "Chao Phraya river delta seasonal flood plain", 1, 0),

            # Americas (Hurricane & Fault Zones)
            ("loc-miami", "Miami", "United States", 25.7617, -80.1918, "Atlantic tropical hurricane landfall belt & storm surge zone", 1, 0),
            ("loc-neworleans", "New Orleans", "United States", 29.9511, -90.0715, "Mississippi delta below sea-level hurricane surge bowl", 1, 0),
            ("loc-sanfrancisco", "San Francisco", "United States", 37.7749, -122.4194, "San Andreas fault zone & coastal atmospheric river flood belt", 1, 1),
            ("loc-mexicocity", "Mexico City", "Mexico", 19.4326, -99.1332, "Cocos plate subduction seismic basin & volcanic ring", 0, 1),
            ("loc-riodejaneiro", "Rio de Janeiro", "Brazil", -22.9068, -43.1729, "Atlantic coastal storm surge & tropical landslide hills", 1, 0),
            ("loc-valparaiso", "Valparaiso", "Chile", -33.0472, -71.6127, "Nazca plate subduction megaquake & tsunami coast", 1, 1),

            # Europe & Mediterranean
            ("loc-london", "London", "United Kingdom", 51.5074, -0.1278, "Thames barrier storm surge & North Atlantic winter gale corridor", 1, 0),
            ("loc-athens", "Athens", "Greece", 37.9838, 23.7275, "Aegean seismic fault & Mediterranean summer heatwave belt", 1, 1),
            ("loc-naples", "Naples", "Italy", 40.8518, 14.2681, "Campi Flegrei / Vesuvius volcanic & seismic risk zone", 1, 1),
            ("loc-reykjavik", "Reykjavik", "Iceland", 64.1466, -21.9426, "Mid-Atlantic ridge volcanic fissure & seismic rift", 1, 1),

            # Oceania
            ("loc-cairns", "Cairns", "Australia", -16.9186, 145.7781, "Coral Sea tropical cyclone impact zone & flood belt", 1, 0),
            ("loc-sydney", "Sydney", "Australia", -33.8688, 151.2093, "East coast low cyclone storm front & bushfire perimeter", 1, 0),
            ("loc-wellington", "Wellington", "New Zealand", -41.2865, 174.7762, "Cook Strait active fault zone & southern gale belt", 1, 1),

            # Africa
            ("loc-antananarivo", "Antananarivo", "Madagascar", -18.8792, 47.5079, "South-West Indian Ocean intense tropical cyclone landfall corridor", 0, 0),
            ("loc-cairo", "Cairo", "Egypt", 30.0444, 31.2357, "Nile delta arid heatwave & flash flood wadi basin", 0, 0),
            ("loc-capetown", "Cape Town", "South Africa", -33.9249, 18.4241, "Cape Peninsula cold front gale storms & wildfire slopes", 1, 0)
        ]
        cursor.executemany("""
            INSERT INTO monitored_locations (id, name, state, latitude, longitude, description, is_coastal, is_seismic_zone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_stations)

    conn.commit()
    conn.close()


def save_alerts_batch(alerts: List[Dict[str, Any]]):
    """
    Inserts or updates a batch of alert records in SQLite.
    Prevents duplicates by primary key 'id'.
    """
    if not alerts:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for a in alerts:
        details_json = json.dumps(a.get("risk_calculation_details", {}))
        cursor.execute("""
            INSERT INTO alerts (
                id, title, disaster_type, severity, status, location_name,
                latitude, longitude, magnitude, depth_km, rainfall_mm,
                wind_speed_kmh, temperature_c, risk_score, risk_rule_triggered,
                risk_calculation_details, safety_guidance, source_name, source_url,
                event_time, updated_time, is_estimated_zone, is_official_alert, zone_radius_km
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                severity=excluded.severity,
                status=excluded.status,
                magnitude=excluded.magnitude,
                depth_km=excluded.depth_km,
                rainfall_mm=excluded.rainfall_mm,
                wind_speed_kmh=excluded.wind_speed_kmh,
                temperature_c=excluded.temperature_c,
                risk_score=excluded.risk_score,
                risk_rule_triggered=excluded.risk_rule_triggered,
                risk_calculation_details=excluded.risk_calculation_details,
                safety_guidance=excluded.safety_guidance,
                updated_time=excluded.updated_time,
                zone_radius_km=excluded.zone_radius_km
        """, (
            a["id"],
            a["title"],
            a["disaster_type"],
            a["severity"],
            a["status"],
            a["location_name"],
            a["latitude"],
            a["longitude"],
            a.get("magnitude"),
            a.get("depth_km"),
            a.get("rainfall_mm"),
            a.get("wind_speed_kmh"),
            a.get("temperature_c"),
            a.get("risk_score"),
            a["risk_rule_triggered"],
            details_json,
            a["safety_guidance"],
            a["source_name"],
            a.get("source_url"),
            a["event_time"],
            a["updated_time"],
            1 if a.get("is_estimated_zone") else 0,
            1 if a.get("is_official_alert") else 0,
            a.get("zone_radius_km")
        ))

    conn.commit()
    conn.close()


def get_alerts(
    disaster_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    official_only: bool = False,
    risk_zones_only: bool = False,
    search: Optional[str] = None,
    limit: int = 250
) -> List[Dict[str, Any]]:
    """
    Fetches alerts with optional filtering by type, severity, status, official flag, and search query.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM alerts WHERE 1=1"
    params: List[Any] = []

    if disaster_type and disaster_type.lower() != "all":
        query += " AND disaster_type = ?"
        params.append(disaster_type)

    if severity and severity.lower() != "all":
        query += " AND severity = ?"
        params.append(severity)

    if status and status.lower() != "all":
        query += " AND status = ?"
        params.append(status)

    if official_only:
        query += " AND is_official_alert = 1"

    if risk_zones_only:
        query += " AND is_estimated_zone = 1"

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query += " AND (location_name LIKE ? OR title LIKE ?)"
        params.extend([search_pattern, search_pattern])

    query += " ORDER BY event_time DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    results = []

    for r in rows:
        d = dict(r)
        d["is_estimated_zone"] = bool(d["is_estimated_zone"])
        d["is_official_alert"] = bool(d["is_official_alert"])
        if d.get("risk_calculation_details"):
            try:
                d["risk_calculation_details"] = json.loads(d["risk_calculation_details"])
            except Exception:
                d["risk_calculation_details"] = {}
        results.append(d)

    conn.close()
    return results


def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single alert record by its unique ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    d = dict(row)
    d["is_estimated_zone"] = bool(d["is_estimated_zone"])
    d["is_official_alert"] = bool(d["is_official_alert"])
    if d.get("risk_calculation_details"):
        try:
            d["risk_calculation_details"] = json.loads(d["risk_calculation_details"])
        except Exception:
            d["risk_calculation_details"] = {}
    return d


def log_refresh(source: str, status: str, count: int, message: str, duration_ms: float = 0.0):
    """Appends a refresh audit record to refresh_logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO refresh_logs (timestamp, source, status, events_count, message, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now_iso, source, status, count, message, duration_ms))
    conn.commit()
    conn.close()


def get_refresh_logs(limit: int = 30) -> List[Dict[str, Any]]:
    """Returns the most recent refresh cycles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM refresh_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monitored_locations() -> List[Dict[str, Any]]:
    """Returns all pre-seeded and user-configured monitoring stations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_locations ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_preference(key: str, value: str):
    """Sets or updates a user preference key-value pair."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO user_preferences (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (key, value, now_iso))
    conn.commit()
    conn.close()


def get_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves a user preference value."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default
