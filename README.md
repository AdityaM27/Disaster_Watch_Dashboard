# DisasterWatch India — Real-Time Disaster Monitoring and Affected Area Mapping System

> **A Production-Quality College Capstone Project**  
> **Purpose:** Web-based emergency situation awareness and disaster decision-support dashboard for India and surrounding regions using real-time telemetry.  
> **Important Disclaimer:** *This student project is for disaster awareness and monitoring only. Always follow official instructions from local authorities, disaster-management agencies, and emergency services. It never claims to control emergency services, dispatch help, or replace official disaster-management authorities.*

---

## 📌 1. Project Overview

**DisasterWatch India** aggregates authentic real-time environmental data—including live global and Indian subcontinent seismic events, high-resolution meteorological observations, and thermal anomaly feeds—onto an interactive, accessible Leaflet geospatial interface.

### Strict Data Integrity Policy
To uphold scientific credibility, DisasterWatch India enforces an absolute **no-fake-data rule**:
- **Zero Synthetic Pins:** No fake disaster events, mocked casualties, simulated notification spam, or synthetic circles are generated.
- **Honest Connection States:** If a third-party feed is unconfigured (such as NASA FIRMS or state CAP alerts requiring authorized credentials), the system reports: `“Source not connected yet”`.
- **Full Data Provenance:** Every event renders its genuine scientific source, exact event time (UTC/IST), last database sync time, and a direct link to the original raw data portal.

---

## 🚀 2. Key Features

- **Interactive Leaflet Cartography:** Centered on India (`22.5937° N, 78.9629° E`) using OpenStreetMap tiles, customizable clustering, and distinct visual boundaries.
- **Real-Time USGS Seismic Integration:** Continuous live ingest of earthquakes from the official USGS GeoJSON feed with magnitude, focal depth, coordinates, and ground-motion context.
- **Transparent Python Risk Engine:** Calculates clearly labeled **“Estimated Flood Risk”**, Cyclone wind advisories, and Heatwave warnings based on live meteorological observations from Open-Meteo across Indian river basins and metros.
- **Visual Taxonomy:**
  - **Confirmed Events:** Solid markers (e.g. USGS seismometer detections).
  - **Official Alerts:** Solid bounded polygons (for statutory NDMA/SDMA warnings).
  - **Estimated Risk Zones:** Dashed perimeters with reduced opacity (mathematically calculated risk models; never asserting an area is inundated without official confirmation).
- **Responsive Emergency UI:** Modern dark slate dashboard optimized for laptops, tablets, and smartphones.
- **Deep Audit & Explanation Panel:** Every alert explains the exact triggered formula, compared thresholds, and official safety guidance.
- **Live Telemetry Charts:** Chart.js plots live seismic magnitude distribution and station rainfall only when authentic data points exist.
- **SQLite Audit Trail:** Tracks every background and manual data refresh cycle with latency and record counts.

---

## 🏗️ 3. System Architecture

```
                       +-----------------------------------+
                       |    External Real-Time Feeds       |
                       |  - USGS Earthquake GeoJSON Feed   |
                       |  - Open-Meteo Atmospheric Models  |
                       |  - NASA FIRMS Active Fires (Opt)  |
                       |  - NDMA / CAP Gateway (Extension) |
                       +-----------------+-----------------+
                                         |
                                         v HTTPX (Async)
                       +-----------------------------------+
                       |   FastAPI REST Backend (Python)   |
                       |  - Ingestion & Validation Layer   |
                       |  - Transparent Python Risk Engine |
                       |  - CORS & Error Recovery          |
                       +-----------------+-----------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
        +-----------------------------+     +-----------------------------+
        |  SQLite Database (data/)    |     |  Frontend Static Serving    |
        |  - alerts table (cached)    |     |  - index.html               |
        |  - refresh_logs audit       |     |  - styles.css (Responsive)  |
        |  - monitored_locations      |     |  - app.js (Vanilla ES6)     |
        |  - user_preferences         |     |  - Leaflet.js + Chart.js    |
        +-----------------------------+     +-----------------------------+
```

### Folder Structure
```
disasterwatch-india/
  backend/
    main.py                  # FastAPI app, REST endpoints, static mounting, CORS
    database.py              # SQLite connection, schema migrations, query methods
    models.py                # Pydantic schemas, data models, validation
    services/
      earthquakes.py         # USGS GeoJSON live feed ingestion & parsing
      weather.py             # Open-Meteo weather & Estimated Flood Risk engine
      fires.py               # NASA FIRMS integration & honest empty state handling
      risk_engine.py         # Transparent risk rules, thresholds, and safety advice
    requirements.txt         # Python dependencies
  frontend/
    index.html               # Semantic HTML5 layout (Dashboard, Details, Sources, About)
    styles.css               # Emergency dark theme, responsive grid/flexbox
    app.js                   # Leaflet map, filters, telemetry chart, API client
  data/
    disasterwatch.db         # Persistent SQLite database (auto-generated)
  .env.example               # Configuration template
  .env                       # Active environment configuration
  README.md                  # Comprehensive project documentation
```

---

## 🔬 4. Risk Engine Rules & Benchmarks

The system features transparent mathematical evaluation rules implemented in [services/risk_engine.py](file:///home/aditya/disasterwatch-india/backend/services/risk_engine.py):

### A. Earthquake Severity (USGS reported Richter/Moment Magnitude)
- **Low:** Magnitude $< 4.0$. Minor seismic event generally felt only by sensitive instruments.
- **Medium:** Magnitude $4.0 - 5.9$. Moderate earthquake; slight damage possible to poor structures.
- **High:** Magnitude $6.0 - 6.9$. Strong earthquake capable of destructive shaking within 100km radius.
- **Critical:** Magnitude $\ge 7.0$. Major earthquake with severe potential for structural failure.
- *Focal Depth Factor:* Depths $< 30\text{ km}$ are highlighted for higher surface ground acceleration.

### B. Estimated Flood Risk (Open-Meteo Real-Time Precipitation)
> **Labeling Constraint:** Strictly reported as **“Estimated Flood Risk”**, never declaring an area flooded without official regulatory confirmation.
- **Low:** Hourly rainfall $\le 5\text{ mm}$ and 24h accumulation $\le 20\text{ mm}$.
- **Medium:** Hourly rainfall $5 - 15\text{ mm}$ or 24h accumulation $20 - 50\text{ mm}$.
- **High:** Hourly rainfall $15 - 30\text{ mm}$ or 24h accumulation $50 - 100\text{ mm}$.
- **Critical:** Hourly rainfall $> 30\text{ mm}$ or 24h accumulation $> 100\text{ mm}$.

### C. Cyclone / Storm Wind Speeds (IMD Classification Scale)
- **Low:** Wind speed $< 31\text{ km/h}$.
- **Medium (Depression):** Sustained wind $31 - 61\text{ km/h}$.
- **High (Cyclonic Storm):** Sustained wind $62 - 88\text{ km/h}$.
- **Critical (Severe Cyclonic Storm):** Sustained wind $\ge 89\text{ km/h}$.

---

## 🛡️ 5. Standard Safety Guidelines

The application embeds standardized safety protocols in all alerts:
- **Earthquake:** *“Drop, Cover, and Hold On; move away from damaged structures after shaking stops.”*
- **Flood:** *“Avoid walking/driving through flood water; move to safer higher ground when instructed by authorities.”*
- **Fire:** *“Follow local evacuation instructions and avoid smoke exposure.”*
- **Cyclone:** *“Stay indoors, follow official warnings, and avoid coastal/low-lying areas when directed.”*
- **Heatwave:** *“Stay hydrated, avoid peak heat, and check vulnerable people.”*

---

## ⚙️ 6. Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection (to access USGS and Open-Meteo live feeds)

### Step 1: Clone or Navigate to the Project Directory
```bash
cd disasterwatch-india
```

### Step 2: (Optional) Create and Activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r backend/requirements.txt
```
*(If on Debian/Ubuntu with PEP 668 managed environment and not using venv, you can run: `pip install --user --break-system-packages -r backend/requirements.txt`)*

### Step 4: Configure `.env`
Copy the example configuration file:
```bash
cp .env.example .env
```
Default `.env` settings:
```ini
HOST=0.0.0.0
PORT=8000
DEBUG=False
DATABASE_PATH=data/disasterwatch.db

# Live External Data Sources
USGS_EARTHQUAKE_FEED_URL=https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
USGS_EARTHQUAKE_MIN_MAGNITUDE=2.0
OPEN_METEO_API_URL=https://api.open-meteo.com/v1/forecast

# Optional NASA FIRMS API Key (Leave empty if unconfigured)
NASA_FIRMS_MAP_KEY=
```

---

## ▶️ 7. Running the Application

Start the backend server using Uvicorn:
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

Once started:
1. Open your browser and navigate to: **`http://localhost:8000/`**
2. The interactive dashboard will load automatically with real live USGS seismic data and live meteorological risk evaluations for Indian stations.
3. Access interactive Swagger API documentation at: **`http://localhost:8000/docs`**

---

## 📡 8. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service uptime, database health, and disclaimer |
| `GET` | `/api/earthquakes` | USGS verified seismic events (filter by `region=india`, `regional`, or `all`) |
| `GET` | `/api/weather?lat=&lon=&city=` | Real-time weather readings & computed Estimated Flood Risk |
| `GET` | `/api/alerts` | Multi-hazard alerts filtered by disaster type, severity, or search text |
| `GET` | `/api/alerts/{id}` | Complete alert metadata, coordinates, and original source link |
| `POST` | `/api/refresh` | Triggers immediate background sync across all live feeds |
| `GET` | `/api/sources` | Status of all telemetry providers (USGS, Open-Meteo, FIRMS, NDMA) |
| `GET` | `/api/risk-explanation/{id}`| Transparent audit trail showing exact mathematical rule applied |
| `GET` | `/api/summary` | Live metric counters (Active, Critical, Earthquakes, Sources Online) |
| `GET` | `/api/locations` | List of pre-seeded monitoring stations across India |
| `GET` | `/api/refresh-history` | Recent SQLite refresh audit logs |

---

## 🔌 9. Adding Future Disaster Sources

The codebase is built with modular services under `backend/services/`:

1. **Adding a New Data Service:**
   Create a new Python file in `backend/services/` (e.g. `backend/services/tsunami.py`).
2. **Standardizing Output:**
   Return a dictionary matching the schema defined in `backend/models.py:AlertItem`.
3. **Applying the Risk Engine:**
   Import and use `backend/services/risk_engine.py` to evaluate severity and safety guidance.
4. **Registering in `main.py`:**
   Add the feed to `execute_live_refresh()` and append a descriptor to `GET /api/sources`.

---

## 📸 10. Screenshots Placeholders

*(Screenshots can be captured during demonstration and inserted here)*
- `[Screenshot Placeholder: Dashboard Map View with USGS Earthquake markers and Open-Meteo Estimated Risk Zones]`
- `[Screenshot Placeholder: Alert Details Panel with Transparent Risk Engine Threshold Benchmarks]`
- `[Screenshot Placeholder: Data Sources Status Table showing honest connection states]`
- `[Screenshot Placeholder: Live Telemetry Analytics Chart]`

---

## ⚖️ 11. Academic Disclaimer & Limitations

> **REQUIRED MANDATORY DISCLAIMER:**  
> **“This student project is for disaster awareness and monitoring only. Always follow official instructions from local authorities, disaster-management agencies, and emergency services.”**

- **Not an Emergency Dispatch System:** DisasterWatch India does NOT notify 112/police/fire/ambulance or dispatch emergency aid.
- **Estimated Risk Modeling:** Weather-derived flood alerts represent estimated risk perimeters based on numerical weather predictions, not on-the-ground certified flooding.
- **Network Dependency:** Real-time data availability depends on uptime of public scientific services (USGS, Open-Meteo).


---

## 🧪 12. Lab Curriculum & Practical Experiments Mapping

This project serves as a comprehensive Capstone and practical implementation of the Linux Ecosystem, DevOps, and Full-Stack Engineering syllabus:

| Experiment | Curriculum Topic | Project Implementation & File Reference |
|---|---|---|
| **EXP-1** | **The Shell & CLI Mastery** | [`scripts/analyze_telemetry.sh`](file:///home/aditya/disasterwatch-india/scripts/analyze_telemetry.sh) — Uses `find`, `cat`, `grep`, `awk`, Piping (`\|`), and Redirection (`>`, `>>`) to generate automated audit reports. |
| **EXP-2** | **Shell Scripting for Automation** | [`scripts/backup.sh`](file:///home/aditya/disasterwatch-india/scripts/backup.sh) — Bash automation featuring timestamp variables, `for` loops, and `if-else` conditionals to create `.tar.gz` backups. |
| **EXP-4** | **Git & GitHub Fundamentals** | Hosted at [AdityaM27/Disaster_Watch_Dashboard](https://github.com/AdityaM27/Disaster_Watch_Dashboard) with production [`.gitignore`](file:///home/aditya/disasterwatch-india/.gitignore) and semantic commits. |
| **EXP-6** | **Introduction to CI/CD** | [`ci/github_actions_ci.yml`](file:///home/aditya/disasterwatch-india/ci/github_actions_ci.yml) — Automated GitHub Actions CI workflow executing [`backend/tests/test_risk_engine.py`](file:///home/aditya/disasterwatch-india/backend/tests/test_risk_engine.py) via `pytest`. |
| **EXP-7** | **Environment Management** | Isolated runtime via [`backend/requirements.txt`](file:///home/aditya/disasterwatch-india/backend/requirements.txt) (pip) and [`environment.yml`](file:///home/aditya/disasterwatch-india/environment.yml) (Conda/Mamba). |
| **EXP-9** | **Containerization with Docker** | Multi-stage [`Dockerfile`](file:///home/aditya/disasterwatch-india/Dockerfile) and [`docker-compose.yml`](file:///home/aditya/disasterwatch-india/docker-compose.yml) allowing isolated deployment. |
| **EXP-11** | **Serial Communication (UART)** | [`hardware_bridge/serial_sensor_ingest.py`](file:///home/aditya/disasterwatch-india/hardware_bridge/serial_sensor_ingest.py) — Ingests live Arduino CSV telemetry (`Temperature, Humidity, Rain`) via UART into the risk engine. |
| **EXP-12** | **AI-Assisted Full Stack Development** | [`streamlit_dashboard.py`](file:///home/aditya/disasterwatch-india/streamlit_dashboard.py) — Interactive Streamlit Web Dashboard visualizing telemetry datasets with filters, geospatial maps, and CSV exports (`streamlit run streamlit_dashboard.py`). |
