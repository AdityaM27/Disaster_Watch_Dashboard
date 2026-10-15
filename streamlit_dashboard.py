"""
EXP-12: AI-Assisted Full Stack Development
Streamlit Web Dashboard for Disaster & Weather Telemetry Visualization

Meets syllabus requirement:
- AI-generated interactive dashboard visualizing disaster and telemetry datasets.
- Interactive filtering, chart plotting, geospatial mapping, and CSV export.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st

# Configure page
st.set_page_config(
    page_title="DisasterWatch — Streamlit Telemetry (EXP-12)",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# ----------------- UI Header -----------------
st.title("🌍 DisasterWatch — Real-Time Telemetry Dashboard")
st.caption("Coursework: **EXP-12 AI-Assisted Full Stack Development** (Streamlit Web Dashboard)")

# ----------------- Sidebar Filters -----------------
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

st.sidebar.divider()
st.sidebar.markdown(f"**Showing {len(filtered_df)} of {len(df)} records**")

# ----------------- Top Summary Metrics -----------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Monitored Events", len(df))
col2.metric("Critical / High Severity", len(df[df["severity"].isin(["High", "Critical"])]))
col3.metric("Seismic Events", len(df[df["disaster_type"] == "Earthquake"]))
avg_temp = df["temperature_c"].dropna().mean()
col4.metric("Avg Station Temp", f"{avg_temp:.1f} °C" if pd.notna(avg_temp) else "N/A")

st.divider()

# ----------------- Geospatial Map -----------------
st.subheader("🗺️ Live Geospatial Event Map")
map_data = filtered_df.dropna(subset=["latitude", "longitude"])
if not map_data.empty:
    st.map(map_data[["latitude", "longitude"]], zoom=4)
else:
    st.info("No geospatial coordinates match the current filter selection.")

# ----------------- Analytics Charts -----------------
st.subheader("📊 Telemetry Visualizations")
tab1, tab2 = st.tabs(["Severity Breakdown", "Rainfall & Temperature Metrics"])

with tab1:
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

# ----------------- Raw Data Table & CSV Download -----------------
st.subheader("📋 Filtered Dataset View")
st.dataframe(filtered_df, use_container_width=True)

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
    "> to generate responsive UI layouts, automated SQLite query ingestion, and dynamic Chart visualizations."
)
