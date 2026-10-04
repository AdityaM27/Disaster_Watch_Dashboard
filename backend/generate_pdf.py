"""
PDF Generator for DisasterWatch Project.
Generates:
1. Area Disaster Assessment Report PDF: Tailored report for a specific area/alert,
   detailing live telemetrics, exact mathematical basis of disaster evaluation,
   threshold benchmarks, and emergency safety guidance.
2. Complete Academic Documentation PDF.
"""

import os
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


def generate_area_disaster_report_pdf(alert: dict, output_path: str):
    """
    Generates a dedicated Area Disaster Evaluation Report PDF for a specific location.
    Clearly presents:
    - Exact location and verified coordinates
    - Real sensor telemetrics (rainfall, wind speed, magnitude, depth, temp)
    - EXACT BASIS on which the area is assessed at its disaster/risk severity level
    - Decision threshold benchmarks comparison
    - Immediate emergency safety directives
    - Data lineage and mandatory safety disclaimer
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Pastel Green / Forest Palette
    primary_color = colors.HexColor("#1b4332")     # Deep forest green
    secondary_color = colors.HexColor("#2d6a4f")   # Medium forest green
    accent_green = colors.HexColor("#52b788")      # Sage accent
    light_bg = colors.HexColor("#edf5f0")          # Soft pastel green background
    table_header_bg = colors.HexColor("#d8f3dc")   # Pastel mint header
    text_dark = colors.HexColor("#133822")         # High contrast dark text
    alert_red = colors.HexColor("#b91c1c")

    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'RepSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SecH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTxt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        spaceAfter=5
    )

    rule_box_style = ParagraphStyle(
        'RuleTxt',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=primary_color
    )

    disclaimer_style = ParagraphStyle(
        'DiscTxt',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=alert_red
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("AREA DISASTER EVALUATION & TELEMETRIC ASSESSMENT REPORT", title_style))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"Real-Time Telemetry Analysis • Generated: {now_str} • Incident ID: {alert.get('id')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_green, spaceBefore=0, spaceAfter=10))

    # Mandatory Safety Disclaimer Box
    disclaimer_box = Table(
        [[Paragraph("<b>MANDATORY SAFETY DISCLAIMER:</b> “This student project is for disaster awareness and monitoring only. Always follow official instructions from local authorities, disaster-management agencies, and emergency services. It never claims to control emergency services, dispatch help, or replace official disaster-management authorities.”", disclaimer_style)]],
        colWidths=[540]
    )
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    story.append(disclaimer_box)
    story.append(Spacer(1, 10))

    # 1. Location & Incident Overview Table
    story.append(Paragraph("1. Geographic Location & Hazard Classification", h1_style))
    overview_data = [
        ["Target Area / Location", alert.get("location_name", "Unknown Area")],
        ["Geographic Coordinates", f"{alert.get('latitude', 0.0):.4f}°, {alert.get('longitude', 0.0):.4f}°"],
        ["Disaster Category", alert.get("disaster_type", "Multi-Hazard")],
        ["Assessed Severity Level", alert.get("severity", "Medium").upper()],
        ["Operational Status", alert.get("status", "Confirmed Event")],
        ["Initial Incident Title", alert.get("title", "Disaster Alert")]
    ]
    t_overview = Table(overview_data, colWidths=[160, 380])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), table_header_bg),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 4.5)
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 10))

    # 2. Observed Physical Telemetrics
    story.append(Paragraph("2. Real-Time Telemetric Sensor Readings", h1_style))
    metrics_rows = [["Physical Parameter", "Measured Telemetric Value", "Measurement Unit / Context"]]

    dtype = alert.get("disaster_type")
    details = alert.get("risk_calculation_details", {})

    if dtype == "Earthquake":
        mag = alert.get("magnitude")
        depth = alert.get("depth_km")
        metrics_rows.append(["Richter / Moment Magnitude", f"{mag:.1f}" if mag is not None else "--", "USGS Seismic Network Scale"])
        metrics_rows.append(["Hypocentral Focal Depth", f"{depth:.1f} km" if depth is not None else "--", "Shallow (<30km) enhances shaking" if depth and depth <= 30 else "Intermediate/Deep"])
        if details.get("felt_reports"):
            metrics_rows.append(["Public Felt Reports", str(details.get("felt_reports")), "USGS 'Did You Feel It?' arrivals"])

    elif dtype in ("Flood Risk", "Cyclone/Storm", "Heatwave"):
        rain = alert.get("rainfall_mm")
        wind = alert.get("wind_speed_kmh")
        temp = alert.get("temperature_c")
        metrics_rows.append(["24h Cumulative Precipitation", f"{rain:.1f} mm" if rain is not None else "0.0 mm", "Open-Meteo High-Resolution Precipitation"])
        metrics_rows.append(["10m Sustained Wind Speed", f"{wind:.1f} km/h" if wind is not None else "--", "Surface Atmospheric Kinetic Velocity"])
        metrics_rows.append(["Ambient Surface Temperature", f"{temp:.1f} °C" if temp is not None else "--", "2-meter Ambient Observation"])

    elif dtype == "Fire":
        frp = details.get("fire_radiative_power_mw")
        bright = details.get("brightness_temperature_k")
        metrics_rows.append(["Fire Radiative Power (FRP)", f"{frp:.1f} MW" if frp is not None else "Satellite Anomaly", "Thermal Radiation Energy Output"])
        metrics_rows.append(["Brightness Temperature", f"{bright:.1f} K" if bright is not None else "--", "4-micron Middle Infrared Band"])
        metrics_rows.append(["Sensor / Network", details.get("satellite_instrument", "VIIRS / MODIS"), "Satellite Radiometer Platform"])

    t_metrics = Table(metrics_rows, colWidths=[180, 160, 200])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 4.5)
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 10))

    # 3. ON WHAT BASIS IS THIS DECLARED A DISASTER AREA?
    story.append(Paragraph("3. Scientific Basis of Disaster Assessment", h1_style))
    rule_text = alert.get("risk_rule_triggered", "Evaluated based on physical threshold exceedance.")
    
    rule_table = Table(
        [[Paragraph(f"<b>TRIGGERED EVALUATION RULE:</b><br/>{rule_text}", rule_box_style)]],
        colWidths=[540]
    )
    rule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#d8f3dc")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#52b788")),
        ('PADDING', (0, 0), (-1, -1), 7)
    ]))
    story.append(rule_table)
    story.append(Spacer(1, 8))

    # Threshold Benchmarks Table
    story.append(Paragraph("Decision Threshold Benchmarks (Python Risk Engine):", body_style))
    benchmarks_data = [
        ["Severity Tier", "Scientific Benchmark Criterion", "Assessed Status for this Area"]
    ]

    thresholds = details.get("thresholds", {})
    current_sev = alert.get("severity", "Medium")

    benchmarks_data.append(["Low", thresholds.get("low", "Baseline physical telemetry or normal background parameters"), "MATCHED" if current_sev == "Low" else "Passed"])
    benchmarks_data.append(["Medium", thresholds.get("medium", "Moderate threshold exceeded; heightened monitoring advisory"), "MATCHED" if current_sev == "Medium" else "Passed"])
    benchmarks_data.append(["High", thresholds.get("high", "Substantial threshold exceeded; imminent hazard or damage exposure"), "MATCHED" if current_sev == "High" else "Passed"])
    benchmarks_data.append(["Critical", thresholds.get("critical", "Severe emergency threshold exceeded; life-safety response criteria"), "MATCHED" if current_sev == "Critical" else "Passed"])

    t_bench = Table(benchmarks_data, colWidths=[90, 330, 120])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 4)
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 10))

    # 4. Immediate Safety Protocols
    story.append(Paragraph("4. Immediate Emergency Directives for this Hazard", h1_style))
    guidance_text = alert.get("safety_guidance", "Follow instructions issued by official disaster management authorities.")
    
    guidance_table = Table(
        [[Paragraph(f"<b>OFFICIAL SAFETY DIRECTIVE:</b><br/>{guidance_text}", body_style)]],
        colWidths=[540]
    )
    guidance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#fde047")),
        ('PADDING', (0, 0), (-1, -1), 7)
    ]))
    story.append(guidance_table)
    story.append(Spacer(1, 10))

    # 5. Data Provenance & Verification
    story.append(Paragraph("5. Data Provenance & Scientific Audit Trail", h1_style))
    lineage_data = [
        ["Reporting Scientific Body", alert.get("source_name", "USGS / GDACS / Open-Meteo")],
        ["Event Timestamp", str(alert.get("event_time", "--"))],
        ["Database Ingest Timestamp", str(alert.get("updated_time", "--"))],
        ["Raw Telemetry Verification Link", alert.get("source_url") or "https://www.gdacs.org/"]
    ]
    t_lineage = Table(lineage_data, colWidths=[180, 360])
    t_lineage.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), table_header_bg),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 4)
    ]))
    story.append(t_lineage)

    doc.build(story)
    return output_path


def generate_documentation_pdf(output_path: str):
    """Generates the system documentation PDF."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1b4332")
    secondary_color = colors.HexColor("#2d6a4f")
    accent_green = colors.HexColor("#52b788")
    table_header_bg = colors.HexColor("#d8f3dc")
    text_dark = colors.HexColor("#1f2937")
    red_alert = colors.HexColor("#dc2626")

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=primary_color, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=15, textColor=secondary_color, spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'SectionH1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=primary_color, spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=text_dark, spaceAfter=5
    )
    formula_style = ParagraphStyle(
        'FormulaText', parent=styles['Normal'], fontName='Courier-Bold', fontSize=8.5, leading=12, textColor=primary_color, spaceBefore=2, spaceAfter=3
    )
    disclaimer_style = ParagraphStyle(
        'DisclaimerText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=12, textColor=red_alert
    )

    story = []
    story.append(Paragraph("Real-Time Disaster Monitoring System", title_style))
    story.append(Paragraph("System Architecture, Real-Time Telemetry Lineage, and Risk Engine Methodology", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_green, spaceBefore=0, spaceAfter=10))

    disclaimer_box = Table(
        [[Paragraph("<b>MANDATORY SAFETY DISCLAIMER:</b> “This student project is for disaster awareness and monitoring only. Always follow official instructions from local authorities, disaster-management agencies, and emergency services. It never claims to control emergency services, dispatch help, or replace official disaster-management authorities.”", disclaimer_style)]],
        colWidths=[530]
    )
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    story.append(disclaimer_box)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Project Scope & Architecture", h1_style))
    story.append(Paragraph(
        "A global, web-based disaster situational awareness system aggregating authentic telemetry from USGS, Open-Meteo, and the United Nations / European Commission GDACS platform.",
        body_style
    ))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "DisasterWatch_Project_Documentation.pdf"
    generate_documentation_pdf(out)
