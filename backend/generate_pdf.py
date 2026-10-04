"""
PDF Generator for DisasterWatch Project Documentation.
Generates a comprehensive, publication-quality academic report covering:
1. Project Purpose, Architecture, and Data Lineage
2. Classification Taxonomy (Confirmed Events, Official Alerts, Estimated Risk Zones)
3. Rigorous Mathematical Methodology for Disaster Level Calculation from Live Telemetrics
4. Real-Time Physical Formulations for Earthquakes, Floods, Cyclones, Heatwaves, and Wildfires
5. Academic Limitations and Mandatory Emergency Safety Disclaimer
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)

def generate_documentation_pdf(output_path: str):
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

    # Pastel Green / Forest Theme Colors for PDF
    primary_color = colors.HexColor("#1b4332")     # Deep forest green
    secondary_color = colors.HexColor("#2d6a4f")   # Medium forest green
    accent_green = colors.HexColor("#52b788")      # Sage / mint accent
    light_bg = colors.HexColor("#e8f5e9")          # Light pastel mint background
    table_header_bg = colors.HexColor("#d8f3dc")   # Soft pastel table header
    text_dark = colors.HexColor("#1f2937")         # Dark charcoal
    red_alert = colors.HexColor("#dc2626")         # Alert red

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=8
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6
    )

    formula_style = ParagraphStyle(
        'FormulaText',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=13,
        textColor=primary_color,
        spaceBefore=3,
        spaceAfter=4
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=red_alert
    )

    story = []

    # Title & Header
    story.append(Paragraph("DisasterWatch — Real-Time Disaster Monitoring System", title_style))
    story.append(Paragraph("System Architecture, Real-Time Telemetry Lineage, and Risk Engine Methodology", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_green, spaceBefore=0, spaceAfter=12))

    # Mandatory Disclaimer Banner Box
    disclaimer_box = Table(
        [[Paragraph("<b>MANDATORY SAFETY DISCLAIMER:</b><br/>“This student project is for disaster awareness and monitoring only. Always follow official instructions from local authorities, disaster-management agencies, and emergency services. It never claims to control emergency services, dispatch help, or replace official disaster-management authorities.”", disclaimer_style)]],
        colWidths=[530]
    )
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#f87171")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    story.append(disclaimer_box)
    story.append(Spacer(1, 12))

    # Section 1: Project Objective & Overview
    story.append(Paragraph("1. Project Purpose & Scope", h1_style))
    story.append(Paragraph(
        "DisasterWatch is a global, web-based disaster situational awareness and decision-support system. "
        "The project aggregates authentic, instrumental telemetry from international scientific agencies—including the "
        "United States Geological Survey (USGS), Open-Meteo High-Resolution Numerical Weather Prediction Models, "
        "and the United Nations / European Commission Global Disaster Alert and Coordination System (GDACS). "
        "The platform eliminates synthetic data, providing genuine coordinates, verifiable timestamps, and transparent risk calculations.",
        body_style
    ))

    # Section 2: Classification Taxonomy
    story.append(Paragraph("2. Event Classification Taxonomy", h1_style))
    story.append(Paragraph(
        "To ensure scientific accuracy and prevent public misinterpretation, events are classified into three distinct categories:",
        body_style
    ))

    taxonomy_data = [
        ["Classification", "Visual Representation", "Scientific Definition & Source"],
        ["Confirmed Event", "Solid Marker", "Direct instrumental sensor detections (e.g. USGS seismometer arrivals, VIIRS satellite infrared thermal detections)."],
        ["Official Alert", "Solid Boundary / Circle", "Statutory regulatory warnings issued by sovereign or international emergency bodies (e.g. GDACS Red/Orange bulletins, NDMA/NOAA)."],
        ["Estimated Risk Zone", "Dashed Outline (Low Opacity)", "Calculated perimeter derived by the Python risk engine from live atmospheric telemetrics (e.g. rainfall rate, sustained wind speed). Strictly labeled as 'Estimated Risk', never asserting ground flooding."]
    ]
    t_taxonomy = Table(taxonomy_data, colWidths=[110, 120, 300])
    t_taxonomy.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    story.append(t_taxonomy)
    story.append(Spacer(1, 10))

    # Section 3: Detailed Telemetric Risk Engine Methodology
    story.append(Paragraph("3. Mathematical Methodology: Live Telemetric Disaster Level Calculation", h1_style))
    story.append(Paragraph(
        "Disaster levels (Low, Medium, High, Critical) are computed through deterministic physical transfer functions "
        "operating on streaming live telemetrics. Each hazard type evaluates measurable physical variables against standard geophysical benchmarks:",
        body_style
    ))

    # 3.1 Earthquakes
    story.append(Paragraph("3.1 Seismic Hazard Intensity (USGS Live Stream)", h2_style))
    story.append(Paragraph(
        "Seismic severity is evaluated using reported Moment Magnitude (M) combined with a focal hypocentral depth ground attenuation factor (f_depth):",
        body_style
    ))
    story.append(Paragraph("f_depth = 1.0 if Depth &le; 30 km (Shallow Crustal) else 0.82 (Intermediate / Deep)", formula_style))
    story.append(Paragraph("Seismic Risk Index (SRI) = min(10.0, [2.0 + (M / 4.0) * 1.5] * f_depth)  for M &lt; 4.0", formula_style))
    story.append(Paragraph("SRI = min(10.0, [4.0 + ((M - 4.0) / 2.0) * 2.5] * f_depth)          for 4.0 &le; M &lt; 6.0", formula_style))
    story.append(Paragraph("SRI = min(10.0, [6.8 + ((M - 6.0) / 1.0) * 1.7] * f_depth)          for 6.0 &le; M &lt; 7.0", formula_style))
    story.append(Paragraph("SRI = min(10.0, [8.5 + (M - 7.0) * 0.75])                           for M &ge; 7.0 (Critical)", formula_style))

    # 3.2 Flood Risk
    story.append(Paragraph("3.2 Estimated Flood Risk (Open-Meteo Atmospheric Models)", h2_style))
    story.append(Paragraph(
        "Flood potential is determined by combining short-duration burst rainfall intensity (I_h, mm/h) and 24-hour antecedent cumulative precipitation (P_24, mm):",
        body_style
    ))
    story.append(Paragraph("Hydrological Inundation Potential (HIP) = (0.65 * (I_h / 30.0) + 0.35 * (P_24 / 100.0)) * 10.0", formula_style))
    story.append(Paragraph(
        "• Low Risk: I_h &le; 5 mm/h AND P_24 &le; 20 mm (HIP &lt; 3.0)<br/>"
        "• Medium Risk: I_h &gt; 5 mm/h OR P_24 &gt; 20 mm (3.0 &le; HIP &lt; 5.5)<br/>"
        "• High Risk: I_h &gt; 15 mm/h OR P_24 &gt; 50 mm (5.5 &le; HIP &lt; 8.0)<br/>"
        "• Critical Risk: I_h &gt; 30 mm/h OR P_24 &gt; 100 mm (HIP &ge; 8.0)",
        body_style
    ))

    # 3.3 Tropical Cyclones & Gales
    story.append(Paragraph("3.3 Tropical Cyclone & Gale Wind Shear (GDACS & Open-Meteo)", h2_style))
    story.append(Paragraph(
        "Evaluates 10-meter sustained wind velocity (V_10, km/h) and peak wind gusts (G_max) using IMD and Saffir-Simpson thresholds:",
        body_style
    ))
    story.append(Paragraph("Effective Wind Kinetic Hazard (WKH) = 0.5 * &rho;_air * (V_10 / 3.6)&sup2; (Dynamic Wind Pressure)", formula_style))
    story.append(Paragraph(
        "• Low: V_10 &lt; 31 km/h (Gentle/Moderate breeze)<br/>"
        "• Medium (Depression): 31 &le; V_10 &lt; 62 km/h<br/>"
        "• High (Cyclonic Storm / Gale): 62 &le; V_10 &lt; 89 km/h (Trees uprooted, structural warnings)<br/>"
        "• Critical (Severe Cyclonic Storm / Hurricane): V_10 &ge; 89 km/h (Widespread destruction)",
        body_style
    ))

    # 3.4 Heatwave & Thermal Stress
    story.append(Paragraph("3.4 Heatwave & Human Heat Index (NOAA / IMD Formulation)", h2_style))
    story.append(Paragraph(
        "Calculates apparent thermal stress from 2-meter ambient temperature (T, &deg;C) and relative humidity (RH, %):",
        body_style
    ))
    story.append(Paragraph("Heat Index (HI) = -8.784 + 1.611*T + 2.338*RH - 0.146*T*RH - 0.0123*T&sup2; - 0.0164*RH&sup2; + 0.0022*T&sup2;*RH", formula_style))
    story.append(Paragraph(
        "• Low: T &lt; 38 &deg;C (Normal conditions)<br/>"
        "• Medium: 38 &le; T &lt; 42 &deg;C (Pre-heatwave caution)<br/>"
        "• High: 42 &le; T &lt; 45 &deg;C (Official Heatwave advisory)<br/>"
        "• Critical: T &ge; 45 &deg;C OR HI &ge; 54 &deg;C (Severe Heatwave / Extreme medical risk)",
        body_style
    ))

    # 3.5 Wildfires
    story.append(Paragraph("3.5 Active Wildfire Thermal Intensity (NASA FIRMS / GDACS)", h2_style))
    story.append(Paragraph(
        "Satellite thermal radiative energy is measured through Fire Radiative Power (FRP, Megawatts) and 4-micron brightness temperature (T_b4, Kelvin):",
        body_style
    ))
    story.append(Paragraph(
        "• Low: FRP &le; 10 MW (Small agricultural burn / nascent heat spot)<br/>"
        "• Medium: 10 &lt; FRP &le; 30 MW (Active surface combustion)<br/>"
        "• High: 30 &lt; FRP &le; 100 MW (Intense wildfire front)<br/>"
        "• Critical: FRP &gt; 100 MW OR T_b4 &gt; 360 K (Crown fire / Mega-fire front)",
        body_style
    ))

    story.append(Spacer(1, 10))

    # Section 4: Standard Emergency Guidance Protocols
    story.append(Paragraph("4. Standardized Emergency Safety Protocols", h1_style))
    protocols = [
        ["Hazard", "Immediate Action Directive"],
        ["Earthquake", "Drop, Cover, and Hold On; move away from damaged structures after shaking ceases."],
        ["Flood", "Avoid walking or driving through flood water; evacuate to higher ground upon authority advisory."],
        ["Fire", "Follow local evacuation corridors, shut gas valves, and avoid particulate smoke inhalation."],
        ["Cyclone", "Remain indoors away from glass windows; heed maritime storm surge evacuation orders."],
        ["Heatwave", "Maintain hydration, avoid sun exposure between 11:00-16:00, and monitor vulnerable individuals."]
    ]
    t_prot = Table(protocols, colWidths=[90, 440])
    t_prot.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#b7e4c7")),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    story.append(t_prot)

    story.append(Spacer(1, 14))

    # Section 5: Recommended Future Enhancements
    story.append(Paragraph("5. Recommended Future Enhancements", h1_style))
    story.append(Paragraph(
        "1. <b>Global Gridded Population Exposure:</b> Overlay LandScan or GPWv4 population density raster tiles to dynamically estimate the number of inhabitants within a 50km hazard radius.<br/>"
        "2. <b>Historical Replay Slider:</b> Implement a temporal 7-day replay control to observe storm progression and seismic aftershock sequences.<br/>"
        "3. <b>Multi-Sensor Tsunami Buoy Telemetry:</b> Ingest NOAA DART (Deep-ocean Assessment and Reporting of Tsunamis) acoustic sensor readings.<br/>"
        "4. <b>Offline Progressive Web App (PWA):</b> Cache critical offline safety checklists and local map tiles via Service Workers for low-connectivity disaster zones.<br/>"
        "5. <b>Automated Webhook / MQTT Alert Dispatch:</b> Allow municipal emergency centers to subscribe to machine-readable alert webhooks.",
        body_style
    ))

    # Build PDF
    doc.build(story)
    print(f"Documentation PDF successfully created at: {output_path}")

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "DisasterWatch_Project_Documentation.pdf"
    generate_documentation_pdf(out)
