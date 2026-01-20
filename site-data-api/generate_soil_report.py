#!/usr/bin/env python3
"""
Professional Soil Report Generator
Creates PDF soil reports from USDA data for architecture/construction projects
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import PageBreak, HRFlowable
from datetime import datetime
import os

from soil_data import get_soil_data, DRAINAGE_DESCRIPTIONS, HYDRO_GROUP_DESCRIPTIONS


def generate_soil_report(
    project_name: str,
    project_address: str,
    lat: float,
    lon: float,
    output_path: str = None,
    elevation_ft: float = None,
    flood_zone: str = None
) -> str:
    """
    Generate a professional soil report PDF

    Args:
        project_name: Name of the project
        project_address: Full address
        lat: Latitude
        lon: Longitude
        output_path: Where to save PDF (default: current dir)
        elevation_ft: Site elevation if known
        flood_zone: FEMA flood zone if known

    Returns:
        Path to generated PDF
    """

    # Get soil data
    soil = get_soil_data(lat, lon)

    # Set output path
    if output_path is None:
        safe_name = project_name.replace(" ", "_").replace("/", "-")
        output_path = f"{safe_name}_Soil_Report.pdf"

    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=6,
        textColor=colors.HexColor('#1a365d'),
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4a5568'),
        alignment=1,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5282'),
        spaceBefore=20,
        spaceAfter=10,
        borderPadding=5
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#718096'),
        leftIndent=20,
        spaceAfter=6
    )

    warning_style = ParagraphStyle(
        'Warning',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#c53030'),
        backColor=colors.HexColor('#fff5f5'),
        borderPadding=10,
        spaceBefore=10,
        spaceAfter=10
    )

    # Build content
    content = []

    # Header
    content.append(Paragraph("PRELIMINARY SOIL REPORT", title_style))
    content.append(Paragraph(f"Generated from USDA Soil Survey Data", subtitle_style))

    # Horizontal line
    content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c5282')))
    content.append(Spacer(1, 20))

    # Project Info Table
    project_data = [
        ["PROJECT NAME:", project_name],
        ["PROJECT ADDRESS:", project_address],
        ["COORDINATES:", f"{lat:.6f}°N, {lon:.6f}°W"],
        ["REPORT DATE:", datetime.now().strftime("%B %d, %Y")],
    ]

    if elevation_ft:
        project_data.append(["SITE ELEVATION:", f"{elevation_ft} ft NAVD88"])
    if flood_zone:
        project_data.append(["FEMA FLOOD ZONE:", flood_zone])

    project_table = Table(project_data, colWidths=[2*inch, 4.5*inch])
    project_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONT', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    content.append(project_table)
    content.append(Spacer(1, 20))

    # Soil Classification Section
    content.append(Paragraph("1. SOIL CLASSIFICATION", section_style))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))

    soil_class_data = [
        ["Map Unit Name:", soil.get('soil_name', 'Unknown')],
        ["Dominant Component:", soil.get('component_name', 'Unknown')],
        ["Component Percentage:", f"{soil.get('component_percent', 'N/A')}%"],
        ["Taxonomic Class:", soil.get('taxonomic_class', 'Unknown')],
        ["Soil Order:", soil.get('soil_order', 'Unknown')],
        ["Slope:", f"{soil.get('slope_percent', 'N/A')}%"],
    ]

    class_table = Table(soil_class_data, colWidths=[2*inch, 4.5*inch])
    class_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONT', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    content.append(class_table)
    content.append(Spacer(1, 15))

    # Drainage & Hydrology Section
    content.append(Paragraph("2. DRAINAGE & HYDROLOGY", section_style))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))

    drainage = soil.get('drainage_class', 'Unknown')
    hydro = soil.get('hydrologic_group', 'Unknown')

    drainage_data = [
        ["Drainage Class:", drainage],
        ["Drainage Description:", soil.get('drainage_description', 'N/A')],
        ["Hydrologic Soil Group:", hydro],
        ["Hydrologic Description:", soil.get('hydrologic_description', 'N/A')],
    ]

    drainage_table = Table(drainage_data, colWidths=[2*inch, 4.5*inch])
    drainage_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONT', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    content.append(drainage_table)
    content.append(Spacer(1, 10))

    # Hydrologic Group explanation
    content.append(Paragraph("<b>Hydrologic Soil Group Reference:</b>", body_style))

    hydro_ref = [
        ["Group", "Runoff Potential", "Description"],
        ["A", "Low", "Sandy, deep, well drained - High infiltration"],
        ["B", "Moderate", "Moderately deep, moderate drainage"],
        ["C", "Moderately High", "Slow infiltration, impeding layer"],
        ["D", "High", "Clay, high water table, or shallow bedrock"],
    ]

    hydro_table = Table(hydro_ref, colWidths=[0.75*inch, 1.5*inch, 4.25*inch])
    hydro_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#edf2f7')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))

    # Highlight current group
    if hydro in ['A', 'B', 'C', 'D']:
        row_idx = ['A', 'B', 'C', 'D'].index(hydro) + 1
        hydro_table.setStyle(TableStyle([
            ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#bee3f8')),
            ('FONT', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
        ]))

    content.append(hydro_table)
    content.append(Spacer(1, 15))

    # Engineering Considerations Section
    content.append(Paragraph("3. ENGINEERING CONSIDERATIONS", section_style))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))

    eng_notes = soil.get('engineering_notes', '').split('; ')
    for note in eng_notes:
        if note.strip():
            bullet = "•" if not note.startswith("FL:") else "⚠"
            content.append(Paragraph(f"{bullet} {note}", body_style))

    content.append(Spacer(1, 10))

    # Krome soil specific notes (common in South Florida)
    if 'krome' in soil.get('soil_name', '').lower():
        content.append(Paragraph("<b>KROME SOIL CHARACTERISTICS (South Florida):</b>", body_style))
        krome_notes = [
            "• Shallow depth to limestone bedrock (typically 6-20 inches)",
            "• Very gravelly texture with limestone fragments",
            "• Moderately alkaline pH (7.4-8.4)",
            "• Low water holding capacity",
            "• Rock plowing or scarification often required for landscaping",
            "• Foundation excavation may require rock chipping/drilling",
            "• Excellent load-bearing capacity once bedrock is reached",
        ]
        for note in krome_notes:
            content.append(Paragraph(note, note_style))

    content.append(Spacer(1, 15))

    # Construction Recommendations Section
    content.append(Paragraph("4. CONSTRUCTION RECOMMENDATIONS", section_style))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))

    # Foundation recommendations based on soil type
    content.append(Paragraph("<b>Foundation:</b>", body_style))
    if 'krome' in soil.get('soil_name', '').lower() or 'lithic' in soil.get('taxonomic_class', '').lower():
        content.append(Paragraph("• Spread footings bearing on limestone bedrock recommended", note_style))
        content.append(Paragraph("• Verify depth to rock with test borings at foundation locations", note_style))
        content.append(Paragraph("• Consider drilled shaft foundations for heavy loads", note_style))
    elif drainage in ['Poorly drained', 'Very poorly drained']:
        content.append(Paragraph("• Deep foundation system (piles) may be required", note_style))
        content.append(Paragraph("• Dewatering during construction likely necessary", note_style))
        content.append(Paragraph("• Waterproofing of below-grade elements critical", note_style))
    else:
        content.append(Paragraph("• Standard spread footings likely suitable pending geotechnical verification", note_style))

    content.append(Spacer(1, 10))

    # Stormwater recommendations
    content.append(Paragraph("<b>Stormwater Management:</b>", body_style))
    if hydro == 'D':
        content.append(Paragraph("• HIGH RUNOFF POTENTIAL - Detention/retention required", note_style))
        content.append(Paragraph("• Consider exfiltration trenches into limestone", note_style))
        content.append(Paragraph("• Pervious pavement may have limited effectiveness", note_style))
        content.append(Paragraph("• Consult SFWMD for permit requirements", note_style))
    elif hydro == 'A':
        content.append(Paragraph("• High infiltration capacity - pervious surfaces effective", note_style))
        content.append(Paragraph("• Dry retention areas suitable", note_style))
    else:
        content.append(Paragraph("• Standard retention/detention per local requirements", note_style))

    content.append(Spacer(1, 10))

    # Earthwork
    content.append(Paragraph("<b>Earthwork:</b>", body_style))
    if 'gravelly' in soil.get('soil_name', '').lower() or 'rock' in soil.get('soil_name', '').lower():
        content.append(Paragraph("• Rock excavation equipment may be required", note_style))
        content.append(Paragraph("• Blasting unlikely to be permitted in urban area", note_style))
        content.append(Paragraph("• Budget for rock removal/disposal", note_style))

    content.append(Spacer(1, 20))

    # Disclaimer Section
    content.append(Paragraph("5. LIMITATIONS & DISCLAIMER", section_style))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))

    disclaimer_text = """
    <b>IMPORTANT:</b> This preliminary soil report is generated from USDA-NRCS Soil Survey data
    and is intended for preliminary planning purposes only. Soil surveys are conducted at a scale
    of 1:12,000 to 1:24,000 and may not reflect localized conditions at specific sites.
    <br/><br/>
    <b>This report does not replace a site-specific geotechnical investigation.</b>
    <br/><br/>
    A licensed geotechnical engineer should be retained to perform:
    <br/>• Standard Penetration Test (SPT) borings
    <br/>• Laboratory testing of soil/rock samples
    <br/>• Foundation design recommendations
    <br/>• Earthwork and compaction specifications
    <br/><br/>
    For multi-story construction, geotechnical investigation is typically required by the
    Florida Building Code and local jurisdictions.
    """

    content.append(Paragraph(disclaimer_text, note_style))
    content.append(Spacer(1, 20))

    # Data Source
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    content.append(Spacer(1, 10))

    source_text = f"""
    <b>Data Source:</b> USDA-NRCS Soil Data Access (SDA) Web Service<br/>
    <b>Survey Area:</b> Miami-Dade County, Florida<br/>
    <b>Report Generated:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br/>
    <b>Generated By:</b> Site Data API Tool - BD Architect LLC
    """
    content.append(Paragraph(source_text, note_style))

    # Build PDF
    doc.build(content)

    return os.path.abspath(output_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python generate_soil_report.py \"Project Name\" \"Address\" lat lon [output.pdf]")
        print("Example: python generate_soil_report.py \"Goulds Tower-1\" \"SW 216th St, Goulds, FL\" 25.5659 -80.3827")
        sys.exit(1)

    project = sys.argv[1]
    address = sys.argv[2]
    lat = float(sys.argv[3])
    lon = float(sys.argv[4])
    output = sys.argv[5] if len(sys.argv) > 5 else None

    print(f"Generating soil report for {project}...")
    pdf_path = generate_soil_report(project, address, lat, lon, output)
    print(f"Report saved to: {pdf_path}")
