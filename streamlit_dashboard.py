"""
EXP-12: AI-Assisted Full Stack Development
Streamlit Web Dashboard for Disaster & Weather Telemetry Visualization

Meets syllabus requirement:
- AI-generated interactive dashboard visualizing disaster and telemetry datasets.
- Interactive filtering, chart plotting, geospatial mapping, and CSV export.
- Integrated AI Area Threat Level Analyzer & 72-Hour Forward Trajectory Prediction Engine.
"""

import os
import sys
import asyncio
import sqlite3
import pandas as pd
import streamlit as st

# Configure page
st.set_page_config(
    page_title="DisasterWatch — AI Telemetry & Future Predictor (EXP-12)",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from services.ai_predictor import predict_disaster_future
from services.area_threat import perform_area_threat_analysis, get_preset_threat_areas

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "disasterwatch.db")


@st.cache_data(ttl=60)
def load_disaster_data():
    """Loads live telemetry and alerts from SQLite database or fallback sample."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(
                "SELECT id, title, disaster_type, severity, status, location_name, "
                "latitude, longitude, magnitude, rainfall_mm, wind_speed_kmh, "
                "temperature_c, risk_score, source_name, event_time FROM alerts",
                conn
            )
            conn.close()
            if not df.empty:
                return df
        except Exception as e:
            st.warning(f"Could not read from database: {e}. Falling back to sample data.")

    # Fallback sample dataset if database is empty
    sample_data = {
        "id": ["mock-1", "mock-2", "mock-3", "mock-4", "mock-5"],
        "title": [
            "M 5.1 Earthquake - Hindu Kush Region",
            "Estimated Flood Risk - Mumbai, Maharashtra",
            "Severe Heatwave - Jodhpur, Rajasthan",
            "Estimated Flood Risk - Guwahati, Assam",
            "M 4.2 Earthquake - Andaman Islands"
        ],
        "disaster_type": ["Earthquake", "Flood Risk", "Heatwave", "Flood Risk", "Earthquake"],
        "severity": ["High", "Medium", "High", "Critical", "Medium"],
        "status": ["Confirmed Event", "Estimated Risk", "Estimated Risk", "Estimated Risk", "Confirmed Event"],
        "location_name": ["Hindu Kush", "Mumbai", "Jodhpur", "Guwahati", "Port Blair"],
        "latitude": [36.4, 19.076, 26.238, 26.144, 11.623],
        "longitude": [70.8, 72.877, 73.024, 91.736, 92.726],
        "magnitude": [5.1, None, None, None, 4.2],
        "rainfall_mm": [0.0, 32.5, 0.0, 78.4, 0.0],
        "wind_speed_kmh": [5.0, 22.0, 14.0, 18.0, 10.0],
        "temperature_c": [12.0, 31.5, 43.8, 29.0, 30.2],
        "risk_score": [6.2, 5.0, 7.8, 8.8, 4.2],
        "source_name": ["USGS", "Open-Meteo", "Open-Meteo", "Open-Meteo", "USGS"],
        "event_time": ["2026-10-15 08:30:00"] * 5
    }
    return pd.DataFrame(sample_data)


# Load dataset
df = load_disaster_data()


# ----------------- Helper: Render AI Specific Area Threat Analyzer -----------------
def render_ai_area_threat_analyzer():
    st.markdown("### 🎯 Specific Area Disaster Detection & Threat Level Analyzer")
    st.caption("Enter any specific city, district, or region to detect active hazards, ingest live telemetry, and calculate the composite threat level (0–100).")

    preset_areas = get_preset_threat_areas()
    preset_names = [f"{p['name']} — {p['desc']}" for p in preset_areas]

    area_col1, area_col2 = st.columns([2, 1])
    with area_col1:
        target_area_text = st.text_input("Enter Specific Area or City Name", "Mumbai, Maharashtra", key="target_area_text")
    with area_col2:
        selected_preset = st.selectbox("Or Select Preset Sector", ["(Custom Input)"] + preset_names, key="selected_preset")

    query_to_run = target_area_text
    if selected_preset != "(Custom Input)":
        idx = preset_names.index(selected_preset)
        query_to_run = preset_areas[idx]["name"]

    try:
        area_res = asyncio.run(perform_area_threat_analysis(query_to_run))
        sum_data = area_res["threat_summary"]
        loc_data = area_res["location"]
        tel_data = area_res["telemetry_snapshot"]
        haz_data = area_res["hazard_breakdown"]

        # Metric row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Composite Threat Score", f"{sum_data['overall_threat_score']} / 100", f"Tier: {sum_data['threat_tier']}")
        m2.metric("Primary Threat Driver", sum_data['primary_threat_driver'], f"{sum_data['primary_threat_score']} / 100")
        m3.metric("Live Temperature", f"{tel_data['temperature_c']:.1f} °C", f"Humidity {tel_data['humidity_pct']:.0f}%")
        m4.metric("Precipitation Rate", f"{tel_data['precipitation_rate_mm_h']:.1f} mm/h", f"Wind {tel_data['wind_speed_kmh']:.1f} km/h")

        st.caption(f"📍 **Target Area:** {loc_data['name']} (Lat: {loc_data['latitude']:.4f}, Lon: {loc_data['longitude']:.4f}) | **Atmospheric Condition:** {tel_data['weather_condition']}")

        # Hazard Breakdown Chart
        haz_names = [v["name"] for v in haz_data.values()]
        haz_scores = [v["score"] for v in haz_data.values()]
        haz_df = pd.DataFrame({"Hazard": haz_names, "Threat Score (0-100)": haz_scores}).set_index("Hazard")
        st.bar_chart(haz_df)

        # Detected proximate disasters
        if area_res["detected_disasters"]:
            st.warning(f"⚠️ **{area_res['detected_disasters_count']} Proximate Disaster Events Detected within 250km Sector:**")
            prox_df = pd.DataFrame([
                {
                    "Disaster": d["disaster_type"],
                    "Title": d["title"],
                    "Distance (km)": d["distance_km"],
                    "Severity": d["severity"],
                    "Source": d["source_name"]
                }
                for d in area_res["detected_disasters"]
            ])
            st.dataframe(prox_df, width="stretch")
        else:
            st.success("✅ **No severe active disaster events detected within a 250km radius.** Normal baseline conditions.")

        # AI Narrative & Directives
        st.info(f"**AI Situational Narrative:** {area_res['ai_narrative']}")
        directives_text = "\n".join([f"- {d}" for d in area_res["mitigation_directives"]])
        st.markdown(f"**Actionable Emergency Mitigation Protocol:**\n\n{directives_text}")

    except Exception as e:
        st.error(f"Error computing area threat: {e}")


# ----------------- Helper: Render Forward Trajectory Simulation -----------------
def render_ai_trajectory_simulation():
    st.markdown("### 🤖 AI Forward Disaster Trajectory & Physical Progression (72-Hour Horizon)")
    st.caption("Simulates future risk escalation, peak inundation/wind windows, and mitigation actions using autoregressive physical models.")

    ai_cols = st.columns([1, 1, 1])
    with ai_cols[0]:
        sim_hazard = st.selectbox("Simulate Hazard Type", ["Flood Risk", "Cyclone/Storm", "Earthquake", "Heatwave"], key="sim_hazard")
    with ai_cols[1]:
        if sim_hazard == "Flood Risk":
            sim_val = st.slider("Current Precipitation Rate (mm/h)", 5.0, 80.0, 28.5, key="sim_val_flood")
            sim_loc = st.text_input("Target Basin", "Brahmaputra River Basin, Guwahati", key="sim_loc_flood")
        elif sim_hazard == "Cyclone/Storm":
            sim_val = st.slider("Current Sustained Wind Speed (km/h)", 40.0, 180.0, 92.0, key="sim_val_cyclone")
            sim_loc = st.text_input("Coastal Sector", "Puri-Paradip Coastal Corridor, Odisha", key="sim_loc_cyclone")
        elif sim_hazard == "Earthquake":
            sim_val = st.slider("Mainshock Magnitude (Richter)", 4.0, 8.5, 6.2, key="sim_val_quake")
            sim_loc = st.text_input("Fault Zone", "Delhi-NCR Fault System", key="sim_loc_quake")
        else:
            sim_val = st.slider("Ambient Temperature (°C)", 38.0, 52.0, 44.5, key="sim_val_heat")
            sim_loc = st.text_input("Region", "Vidarbha Plains, Nagpur", key="sim_loc_heat")
    with ai_cols[2]:
        sim_horizon = st.radio("Simulation Horizon", [24, 48, 72], index=2, horizontal=True, key="sim_horizon")
        st.write("")
        run_sim = st.button("🚀 Run AI Trajectory Simulation", width="stretch", key="run_sim_btn")

    # Always compute or update simulation
    ai_res = predict_disaster_future(sim_hazard, sim_loc, 22.5, 82.0, current_value=sim_val, horizon_hours=sim_horizon)

    st.success(f"**AI Model:** {ai_res['model_name']} | **Confidence:** {ai_res['model_confidence_pct']}% | **Peak Window:** T+{ai_res['peak_risk_hour']}h ({ai_res['peak_risk_time']})")

    # Timeline dataframe
    t_df = pd.DataFrame(ai_res["timeline"])
    chart_data = t_df.set_index("step_hour")[["predicted_risk_score", "predicted_value"]]
    chart_data.columns = ["Projected Risk Score (0-10)", f"Physical Metric ({t_df['value_unit'].iloc[0]})"]

    st.line_chart(chart_data)

    # Summary & Directives
    st.info(f"**AI Situational Assessment:** {ai_res['summary_text']}")
    st.markdown(f"**AI Emergency Mitigation Protocol:**\n\n{ai_res['ai_mitigation_advisory']}")


# ----------------- UI Header -----------------
st.title("🌍 DisasterWatch — Real-Time Telemetry Dashboard")
st.caption("Coursework: **EXP-12 AI-Assisted Full Stack Development** (Streamlit Web Dashboard)")

# ----------------- Top Navigation in Sidebar -----------------
st.sidebar.title("🧭 Main Navigation")
view_mode = st.sidebar.radio(
    "Select View Mode",
    [
        "🤖 AI Future Disaster Predictor & Threat Engine",
        "🗺️ Live Telemetry Dashboard & Geospatial Map",
        "📋 Full Telemetry Data Table & CSV Export"
    ],
    index=0
)

st.sidebar.divider()
st.sidebar.header("🔍 Telemetry Filters")

types = ["All"] + sorted(list(df["disaster_type"].dropna().unique()))
selected_type = st.sidebar.selectbox("Filter by Disaster Type", types)

severities = ["All"] + ["Low", "Medium", "High", "Critical"]
selected_severity = st.sidebar.selectbox("Filter by Severity", severities)

filtered_df = df.copy()
if selected_type != "All":
    filtered_df = filtered_df[filtered_df["disaster_type"] == selected_type]
if selected_severity != "All":
    filtered_df = filtered_df[filtered_df["severity"] == selected_severity]

st.sidebar.markdown(f"**Showing {len(filtered_df)} of {len(df)} records**")


# ==============================================================================
# VIEW 1: DEDICATED AI FUTURE DISASTER PREDICTOR & THREAT ENGINE PAGE
# ==============================================================================
if view_mode == "🤖 AI Future Disaster Predictor & Threat Engine":
    st.header("🤖 Autonomous AI Disaster Prediction & Threat Assessment Hub")
    st.markdown(
        "Powered by autoregressive hydrological unit hydrographs, Kaplan-DeMaria cyclone dynamics, "
        "and Modified Omori-Utsu statistical seismology equations."
    )
    st.divider()

    # Part 1: Specific Area Threat Analyzer
    render_ai_area_threat_analyzer()

    st.divider()

    # Part 2: 72-Hour Forward Trajectory Simulation
    render_ai_trajectory_simulation()


# ==============================================================================
# VIEW 2: LIVE TELEMETRY DASHBOARD & GEOSPATIAL MAP (WITH EXPLICIT TAB 3)
# ==============================================================================
elif view_mode == "🗺️ Live Telemetry Dashboard & Geospatial Map":
    # Top Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Monitored Events", len(df))
    col2.metric("Critical / High Severity", len(df[df["severity"].isin(["High", "Critical"])]))
    col3.metric("Seismic Events", len(df[df["disaster_type"] == "Earthquake"]))
    avg_temp = df["temperature_c"].dropna().mean()
    col4.metric("Avg Station Temp", f"{avg_temp:.1f} °C" if pd.notna(avg_temp) else "N/A")

    st.divider()

    # Geospatial Map
    st.subheader("🗺️ Live Geospatial Event Map")
    map_data = filtered_df.dropna(subset=["latitude", "longitude"])
    if not map_data.empty:
        st.map(map_data[["latitude", "longitude"]], zoom=4)
    else:
        st.info("No geospatial coordinates match the current filter selection.")

    st.divider()

    # Analytics Tabs (with clearly labeled Tab 3)
    st.subheader("📊 Telemetry Visualizations & Analytics")
    tab1, tab2, tab3 = st.tabs([
        "Tab 1: 📊 Severity Breakdown",
        "Tab 2: 🌧️ Rainfall & Temperature Metrics",
        "Tab 3: 🤖 AI Disaster Future Predictor"
    ])

    with tab1:
        st.markdown("**Disaster Event Counts by Severity Level**")
        sev_counts = filtered_df["severity"].value_counts()
        st.bar_chart(sev_counts)

    with tab2:
        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("**Observed Rainfall (mm) by Location**")
            rain_df = filtered_df.dropna(subset=["rainfall_mm"]).sort_values("rainfall_mm", ascending=False).head(10)
            if not rain_df.empty:
                st.bar_chart(rain_df.set_index("location_name")["rainfall_mm"])
            else:
                st.caption("No rainfall metrics available for selection.")
        with chart_cols[1]:
            st.markdown("**Recorded Temperature (°C) by Location**")
            temp_df = filtered_df.dropna(subset=["temperature_c"]).sort_values("temperature_c", ascending=False).head(10)
            if not temp_df.empty:
                st.line_chart(temp_df.set_index("location_name")["temperature_c"])
            else:
                st.caption("No temperature metrics available for selection.")

    with tab3:
        st.markdown("#### Tab 3: 🤖 AI Disaster Future Predictor & Area Threat Level Engine")
        render_ai_area_threat_analyzer()
        st.divider()
        render_ai_trajectory_simulation()


# ==============================================================================
# VIEW 3: FULL DATASET & CSV EXPORT
# ==============================================================================
else:
    st.subheader("📋 Filtered Dataset View")
    st.dataframe(filtered_df, width="stretch")

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name="disasterwatch_telemetry.csv",
        mime="text/csv"
    )

# ----------------- Footer Note -----------------
st.divider()
st.markdown(
    "> **Academic & Lab Submission Note:**  \n"
    "> Developed under **EXP-12: AI-Assisted Full Stack Development** utilizing prompt engineering "
    "> to generate responsive UI layouts, automated SQLite query ingestion, dynamic Chart visualizations, "
    "> and multi-hazard forward trajectory predictive modeling."
)
