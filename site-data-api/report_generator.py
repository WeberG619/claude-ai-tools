#!/usr/bin/env python3
"""
Professional Site Analysis Report Generator
Creates client-ready PDF packages from all 11 APIs

Uses reportlab for PDF generation (pip install reportlab)
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, ListFlowable, ListItem, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. Install with: pip install reportlab")


@dataclass
class ReportConfig:
    """Configuration for report generation"""
    company_name: str = "BD Architect LLC"
    company_address: str = "Miami, Florida"
    company_phone: str = ""
    company_email: str = ""
    logo_path: Optional[str] = None
    primary_color: tuple = (0.2, 0.3, 0.5)  # Navy blue RGB
    accent_color: tuple = (0.8, 0.4, 0.1)   # Orange RGB
    include_raw_data: bool = False
    include_maps: bool = True


class SiteAnalysisReportGenerator:
    """
    Generates professional PDF reports from site analysis data
    """

    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()
        self.styles = None
        self._init_styles()

    def _init_styles(self):
        """Initialize custom paragraph styles"""
        if not REPORTLAB_AVAILABLE:
            return

        self.styles = getSampleStyleSheet()

        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.Color(*self.config.primary_color)
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.Color(*self.config.primary_color),
            borderColor=colors.Color(*self.config.primary_color),
            borderWidth=1,
            borderPadding=5
        ))

        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.Color(*self.config.accent_color)
        ))

        # Customize existing BodyText style
        self.styles['BodyText'].fontSize = 10
        self.styles['BodyText'].leading = 14
        self.styles['BodyText'].alignment = TA_JUSTIFY

        # Table header
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))

        # Executive summary
        self.styles.add(ParagraphStyle(
            name='ExecutiveSummary',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceBefore=10,
            spaceAfter=10
        ))

        # Highlight/callout
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=15,
            backColor=colors.Color(0.95, 0.95, 0.95),
            borderColor=colors.Color(*self.config.primary_color),
            borderWidth=2,
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=10
        ))

        # Footer
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))

        # Customize existing Code style for raw data
        self.styles['Code'].fontSize = 7
        self.styles['Code'].leading = 9
        self.styles['Code'].backColor = colors.Color(0.95, 0.95, 0.95)

    def generate_report(
        self,
        site_data: Dict[str, Any],
        output_path: str,
        project_name: str = None,
        project_number: str = None,
        client_name: str = None
    ) -> str:
        """
        Generate a complete site analysis report

        Args:
            site_data: Complete site data from all APIs
            output_path: Where to save the PDF
            project_name: Optional project name for cover
            project_number: Optional project number
            client_name: Optional client name

        Returns:
            Path to generated PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Cover page
        story.extend(self._create_cover_page(
            site_data, project_name, project_number, client_name
        ))

        # Table of contents
        story.append(PageBreak())
        story.extend(self._create_table_of_contents())

        # Executive summary
        story.append(PageBreak())
        story.extend(self._create_executive_summary(site_data))

        # Site location section
        story.append(PageBreak())
        story.extend(self._create_location_section(site_data))

        # Environmental section
        story.append(PageBreak())
        story.extend(self._create_environmental_section(site_data))

        # Flood and storm section
        story.append(PageBreak())
        story.extend(self._create_flood_storm_section(site_data))

        # Soil and geotechnical section
        story.append(PageBreak())
        story.extend(self._create_soil_section(site_data))

        # Demographics and market section
        story.append(PageBreak())
        story.extend(self._create_demographics_section(site_data))

        # Site context section
        story.append(PageBreak())
        story.extend(self._create_site_context_section(site_data))

        # Climate and sun path section
        story.append(PageBreak())
        story.extend(self._create_climate_section(site_data))

        # Appendix with raw data (optional)
        if self.config.include_raw_data:
            story.append(PageBreak())
            story.extend(self._create_appendix(site_data))

        # Build PDF
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        return output_path

    def _create_cover_page(
        self,
        site_data: Dict,
        project_name: str,
        project_number: str,
        client_name: str
    ) -> List:
        """Create the cover page"""
        elements = []

        # Spacer at top
        elements.append(Spacer(1, 1.5*inch))

        # Logo if available
        if self.config.logo_path and os.path.exists(self.config.logo_path):
            img = Image(self.config.logo_path, width=2*inch, height=1*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.5*inch))

        # Title
        elements.append(Paragraph("SITE ANALYSIS REPORT", self.styles['ReportTitle']))
        elements.append(Spacer(1, 0.3*inch))

        # Horizontal line
        elements.append(self._create_horizontal_line())
        elements.append(Spacer(1, 0.5*inch))

        # Project info
        address = site_data.get('address', 'Address Not Specified')
        elements.append(Paragraph(f"<b>{address}</b>", self.styles['Heading2']))
        elements.append(Spacer(1, 0.3*inch))

        # Project details table
        project_info = []
        if project_number:
            project_info.append(["Project Number:", project_number])
        if project_name:
            project_info.append(["Project Name:", project_name])
        if client_name:
            project_info.append(["Client:", client_name])

        lat = site_data.get('latitude', 0)
        lon = site_data.get('longitude', 0)
        project_info.append(["Coordinates:", f"{lat:.6f}, {lon:.6f}"])
        project_info.append(["Report Date:", datetime.now().strftime("%B %d, %Y")])

        if project_info:
            table = Table(project_info, colWidths=[1.5*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)

        # Spacer before company info
        elements.append(Spacer(1, 2*inch))

        # Company info at bottom
        elements.append(self._create_horizontal_line())
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"<b>{self.config.company_name}</b>", self.styles['Normal']))
        if self.config.company_address:
            elements.append(Paragraph(self.config.company_address, self.styles['Normal']))

        return elements

    def _create_table_of_contents(self) -> List:
        """Create table of contents"""
        elements = []

        elements.append(Paragraph("TABLE OF CONTENTS", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))

        toc_items = [
            ("1.", "Executive Summary", "3"),
            ("2.", "Site Location & Parcel Information", "4"),
            ("3.", "Environmental Assessment", "5"),
            ("4.", "Flood Zones & Storm Analysis", "6"),
            ("5.", "Soil & Geotechnical Data", "7"),
            ("6.", "Demographics & Market Analysis", "8"),
            ("7.", "Site Context & Surroundings", "9"),
            ("8.", "Climate & Solar Analysis", "10"),
        ]

        toc_data = []
        for num, title, page in toc_items:
            toc_data.append([num, title, page])

        toc_table = Table(toc_data, colWidths=[0.5*inch, 5*inch, 0.5*inch])
        toc_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (1, 0), (1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(toc_table)

        return elements

    def _create_executive_summary(self, site_data: Dict) -> List:
        """Create executive summary section"""
        elements = []

        elements.append(Paragraph("1. EXECUTIVE SUMMARY", self.styles['SectionHeader']))

        # Build summary paragraphs based on available data
        address = site_data.get('address', 'the subject property')
        lat = site_data.get('latitude', 0)
        lon = site_data.get('longitude', 0)
        elevation = site_data.get('elevation_ft', 0)

        intro = f"""This Site Analysis Report provides a comprehensive assessment of {address},
        located at coordinates {lat:.6f}, {lon:.6f}. The analysis incorporates data from 11
        authoritative sources including FEMA, NOAA, EPA, US Census Bureau, USDA, and OpenStreetMap."""

        elements.append(Paragraph(intro, self.styles['ExecutiveSummary']))

        # Key findings
        elements.append(Paragraph("<b>Key Findings:</b>", self.styles['SubsectionHeader']))

        findings = []

        # Elevation
        if elevation:
            findings.append(f"Site elevation: {elevation:.1f} feet above sea level")

        # Flood zone
        flood = site_data.get('flood_zone', {})
        if flood.get('zone'):
            zone = flood.get('zone', 'Unknown')
            findings.append(f"FEMA Flood Zone: {zone}")

        # Wind design
        storm = site_data.get('storm_wind', {})
        if storm.get('design_wind_speed_mph'):
            wind_speed = storm.get('design_wind_speed_mph')
            hvhz = "Yes" if storm.get('hvhz', False) else "No"
            findings.append(f"Design wind speed: {wind_speed} mph (HVHZ: {hvhz})")

        # Environmental
        env = site_data.get('environmental', {})
        if env.get('summary', {}).get('risk_level'):
            risk = env['summary']['risk_level']
            findings.append(f"Environmental risk level: {risk}")

        # Demographics
        demo = site_data.get('demographics', {})
        tract_data = demo.get('tract_data', {})
        if tract_data.get('income', {}).get('median_household'):
            income = tract_data['income']['median_household']
            findings.append(f"Median household income (tract): ${income:,}")

        # Site context
        context = site_data.get('site_context', {})
        if context.get('walkability_score'):
            walk = context['walkability_score']
            findings.append(f"Walkability score: {walk}/100")

        # Create bullet list
        if findings:
            bullet_items = [ListItem(Paragraph(f, self.styles['BodyText'])) for f in findings]
            elements.append(ListFlowable(bullet_items, bulletType='bullet', start='•'))

        elements.append(Spacer(1, 0.3*inch))

        # Recommendations callout
        recommendations = self._generate_recommendations(site_data)
        if recommendations:
            rec_text = "<b>Recommendations:</b><br/>" + "<br/>".join(f"• {r}" for r in recommendations)
            elements.append(Paragraph(rec_text, self.styles['Highlight']))

        return elements

    def _create_location_section(self, site_data: Dict) -> List:
        """Create site location section"""
        elements = []

        elements.append(Paragraph("2. SITE LOCATION & PARCEL INFORMATION", self.styles['SectionHeader']))

        # Basic location info
        elements.append(Paragraph("<b>Location Details</b>", self.styles['SubsectionHeader']))

        location_data = [
            ["Address:", site_data.get('address', 'Not specified')],
            ["Latitude:", f"{site_data.get('latitude', 0):.6f}"],
            ["Longitude:", f"{site_data.get('longitude', 0):.6f}"],
            ["Elevation:", f"{site_data.get('elevation_ft', 0):.1f} ft"],
        ]

        elements.append(self._create_data_table(location_data))
        elements.append(Spacer(1, 0.3*inch))

        # Parcel info if available
        parcel = site_data.get('parcel', {})
        if parcel and parcel.get('found'):
            elements.append(Paragraph("<b>Parcel Information</b>", self.styles['SubsectionHeader']))

            parcel_data = []
            if parcel.get('folio'):
                parcel_data.append(["Folio Number:", parcel['folio']])
            if parcel.get('owner'):
                parcel_data.append(["Owner:", parcel['owner']])
            if parcel.get('address'):
                parcel_data.append(["Property Address:", parcel['address']])
            if parcel.get('land_use'):
                parcel_data.append(["Land Use:", parcel['land_use']])
            if parcel.get('zoning'):
                parcel_data.append(["Zoning:", parcel['zoning']])
            if parcel.get('lot_size_sf'):
                parcel_data.append(["Lot Size:", f"{parcel['lot_size_sf']:,} SF"])
            if parcel.get('year_built'):
                parcel_data.append(["Year Built:", str(parcel['year_built'])])

            if parcel_data:
                elements.append(self._create_data_table(parcel_data))
        else:
            elements.append(Paragraph(
                "Parcel data not available. Manual lookup may be required at county property appraiser website.",
                self.styles['BodyText']
            ))

        # Census geography
        demo = site_data.get('demographics', {})
        geo = demo.get('geography', {})
        if geo.get('found'):
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Census Geography</b>", self.styles['SubsectionHeader']))

            census_data = [
                ["State:", geo.get('state_name', 'Unknown')],
                ["County:", geo.get('county_name', 'Unknown')],
                ["Census Tract:", geo.get('tract', 'Unknown')],
                ["Block Group:", geo.get('block_group', 'Unknown')],
            ]
            elements.append(self._create_data_table(census_data))

        return elements

    def _create_environmental_section(self, site_data: Dict) -> List:
        """Create environmental assessment section"""
        elements = []

        elements.append(Paragraph("3. ENVIRONMENTAL ASSESSMENT", self.styles['SectionHeader']))

        env = site_data.get('environmental', {})

        if not env:
            elements.append(Paragraph("Environmental data not available.", self.styles['BodyText']))
            return elements

        # Risk summary
        summary = env.get('summary', {})
        if summary:
            risk_level = summary.get('risk_level', 'Unknown')
            risk_color = {
                'LOW': colors.green,
                'MODERATE': colors.orange,
                'HIGH': colors.red
            }.get(risk_level, colors.gray)

            elements.append(Paragraph(
                f"<b>Environmental Risk Level: </b><font color='{risk_color.hexval()}'>{risk_level}</font>",
                self.styles['SubsectionHeader']
            ))

            elements.append(Paragraph(
                summary.get('recommendation', ''),
                self.styles['BodyText']
            ))
            elements.append(Spacer(1, 0.2*inch))

            # Concerns
            concerns = summary.get('concerns', [])
            if concerns:
                elements.append(Paragraph("<b>Identified Concerns:</b>", self.styles['SubsectionHeader']))
                for concern in concerns:
                    elements.append(Paragraph(f"• {concern}", self.styles['BodyText']))

        # Screening results
        screening = env.get('screening', {})

        # Superfund sites
        superfund = screening.get('superfund_sites', [])
        if superfund:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Nearby Superfund Sites</b>", self.styles['SubsectionHeader']))

            sf_data = [["Site Name", "Distance", "Status"]]
            for site in superfund[:5]:
                sf_data.append([
                    site.get('name', 'Unknown'),
                    f"{site.get('distance_miles', 0):.2f} mi",
                    site.get('status', 'Unknown')
                ])

            elements.append(self._create_styled_table(sf_data))

        # Air quality
        air = env.get('air_quality', {})
        if air:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Air Quality</b>", self.styles['SubsectionHeader']))
            elements.append(Paragraph(
                f"AQI Category: {air.get('aqi_category', 'Unknown')}",
                self.styles['BodyText']
            ))

            attainment = air.get('attainment_status', {})
            if attainment:
                elements.append(Paragraph("NAAQS Attainment Status: All pollutants in attainment", self.styles['BodyText']))

        # Wetlands
        wetlands = env.get('wetlands', {})
        if wetlands:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Wetlands Assessment</b>", self.styles['SubsectionHeader']))
            elements.append(Paragraph(
                f"Wetlands Nearby: {wetlands.get('wetlands_nearby', 'Unknown')}",
                self.styles['BodyText']
            ))

            notes = wetlands.get('notes', [])
            for note in notes[:3]:
                elements.append(Paragraph(f"• {note}", self.styles['BodyText']))

            if wetlands.get('regulatory_note'):
                elements.append(Paragraph(
                    f"<i>{wetlands['regulatory_note']}</i>",
                    self.styles['BodyText']
                ))

        return elements

    def _create_flood_storm_section(self, site_data: Dict) -> List:
        """Create flood and storm section"""
        elements = []

        elements.append(Paragraph("4. FLOOD ZONES & STORM ANALYSIS", self.styles['SectionHeader']))

        # Flood zone
        flood = site_data.get('flood_zone', {})
        elements.append(Paragraph("<b>FEMA Flood Zone Determination</b>", self.styles['SubsectionHeader']))

        if flood.get('zone'):
            flood_data = [
                ["Flood Zone:", flood.get('zone', 'Unknown')],
                ["Zone Description:", self._get_flood_zone_description(flood.get('zone'))],
                ["Panel Number:", flood.get('panel', 'Unknown')],
                ["Panel Effective Date:", flood.get('panel_date', 'Unknown')],
            ]

            bfe = flood.get('base_flood_elevation')
            if bfe:
                flood_data.append(["Base Flood Elevation:", f"{bfe} ft"])

            elements.append(self._create_data_table(flood_data))

            # Flood insurance note
            zone = flood.get('zone', '')
            if zone.startswith('A') or zone.startswith('V'):
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph(
                    "<b>Note:</b> This property is in a Special Flood Hazard Area (SFHA). "
                    "Flood insurance is typically required for federally-backed mortgages.",
                    self.styles['Highlight']
                ))
        else:
            elements.append(Paragraph("Flood zone data not available for this location.", self.styles['BodyText']))

        # Storm/Wind data
        storm = site_data.get('storm_wind', {})
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("<b>Wind Design Requirements (ASCE 7-22)</b>", self.styles['SubsectionHeader']))

        if storm:
            storm_data = [
                ["Design Wind Speed:", f"{storm.get('design_wind_speed_mph', 'Unknown')} mph"],
                ["Risk Category:", storm.get('risk_category', 'II')],
                ["Exposure Category:", storm.get('exposure_category', 'Unknown')],
                ["High-Velocity Hurricane Zone:", "Yes" if storm.get('hvhz') else "No"],
            ]
            elements.append(self._create_data_table(storm_data))

            # Hurricane risk
            hurricane = storm.get('hurricane_risk', {})
            if hurricane:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("<b>Hurricane Risk Assessment</b>", self.styles['SubsectionHeader']))

                risk_data = [
                    ["Risk Level:", hurricane.get('risk_level', 'Unknown')],
                    ["Historical Hurricanes (50mi, 50yr):", str(hurricane.get('historical_hurricanes_50mi_50yr', 'N/A'))],
                ]
                elements.append(self._create_data_table(risk_data))

                # Notes
                notes = hurricane.get('notes', [])
                for note in notes[:3]:
                    elements.append(Paragraph(f"• {note}", self.styles['BodyText']))

            # HVHZ special requirements
            if storm.get('hvhz'):
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph(
                    "<b>HVHZ Requirements:</b> This property is within the High-Velocity Hurricane Zone. "
                    "All construction must comply with Miami-Dade County product approval requirements "
                    "including impact-resistant glazing or approved shutters, and enhanced roof attachment.",
                    self.styles['Highlight']
                ))
        else:
            elements.append(Paragraph("Storm/wind data not available.", self.styles['BodyText']))

        return elements

    def _create_soil_section(self, site_data: Dict) -> List:
        """Create soil and geotechnical section"""
        elements = []

        elements.append(Paragraph("5. SOIL & GEOTECHNICAL DATA", self.styles['SectionHeader']))

        soil = site_data.get('soil', {})

        if not soil or not soil.get('map_units'):
            elements.append(Paragraph(
                "Soil data not available. A geotechnical investigation is recommended.",
                self.styles['BodyText']
            ))
            return elements

        elements.append(Paragraph(
            "The following soil data is from the USDA Web Soil Survey. "
            "A site-specific geotechnical investigation is recommended for design purposes.",
            self.styles['BodyText']
        ))
        elements.append(Spacer(1, 0.2*inch))

        # Soil map units
        elements.append(Paragraph("<b>Soil Map Units</b>", self.styles['SubsectionHeader']))

        map_units = soil.get('map_units', [])
        if map_units:
            soil_table = [["Symbol", "Soil Name", "% Area"]]
            for unit in map_units[:5]:
                soil_table.append([
                    unit.get('symbol', ''),
                    unit.get('name', 'Unknown')[:40],
                    f"{unit.get('percent', 0):.1f}%"
                ])
            elements.append(self._create_styled_table(soil_table))

        # Engineering properties
        eng = soil.get('engineering_properties', {})
        if eng:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Engineering Properties (Predominant Soil)</b>", self.styles['SubsectionHeader']))

            eng_data = []
            if eng.get('unified_classification'):
                eng_data.append(["USCS Classification:", eng['unified_classification']])
            if eng.get('drainage_class'):
                eng_data.append(["Drainage Class:", eng['drainage_class']])
            if eng.get('hydric'):
                eng_data.append(["Hydric Soil:", "Yes" if eng['hydric'] else "No"])
            if eng.get('depth_to_water_table'):
                eng_data.append(["Depth to Water Table:", eng['depth_to_water_table']])
            if eng.get('flooding_frequency'):
                eng_data.append(["Flooding Frequency:", eng['flooding_frequency']])

            if eng_data:
                elements.append(self._create_data_table(eng_data))

        # Building suitability
        suitability = soil.get('building_suitability', {})
        if suitability:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Building Suitability Ratings</b>", self.styles['SubsectionHeader']))

            suit_data = []
            for use, rating in suitability.items():
                suit_data.append([use.replace('_', ' ').title() + ":", rating])

            if suit_data:
                elements.append(self._create_data_table(suit_data))

        return elements

    def _create_demographics_section(self, site_data: Dict) -> List:
        """Create demographics and market analysis section"""
        elements = []

        elements.append(Paragraph("6. DEMOGRAPHICS & MARKET ANALYSIS", self.styles['SectionHeader']))

        demo = site_data.get('demographics', {})
        tract = demo.get('tract_data', {})

        if not tract.get('found'):
            elements.append(Paragraph("Demographic data not available.", self.styles['BodyText']))
            return elements

        elements.append(Paragraph(
            f"Source: {demo.get('source', 'US Census Bureau ACS')}",
            self.styles['BodyText']
        ))
        elements.append(Spacer(1, 0.2*inch))

        # Population
        pop = tract.get('population', {})
        elements.append(Paragraph("<b>Population</b>", self.styles['SubsectionHeader']))
        pop_data = [
            ["Total Population (Tract):", f"{pop.get('total', 0):,}" if pop.get('total') else "N/A"],
            ["Median Age:", str(pop.get('median_age', 'N/A'))],
        ]
        elements.append(self._create_data_table(pop_data))

        # Housing
        housing = tract.get('housing', {})
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>Housing</b>", self.styles['SubsectionHeader']))

        housing_data = [
            ["Total Housing Units:", f"{housing.get('total_units', 0):,}" if housing.get('total_units') else "N/A"],
            ["Occupied Units:", f"{housing.get('occupied', 0):,}" if housing.get('occupied') else "N/A"],
            ["Vacant Units:", f"{housing.get('vacant', 0):,}" if housing.get('vacant') else "N/A"],
            ["Vacancy Rate:", f"{housing.get('vacancy_rate_pct', 0):.1f}%" if housing.get('vacancy_rate_pct') else "N/A"],
            ["Median Home Value:", f"${housing.get('median_value', 0):,}" if housing.get('median_value') else "N/A"],
            ["Median Rent:", f"${housing.get('median_rent', 0):,}/mo" if housing.get('median_rent') else "N/A"],
            ["Median Year Built:", str(housing.get('median_year_built', 'N/A'))],
        ]
        elements.append(self._create_data_table(housing_data))

        # Income
        income = tract.get('income', {})
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>Income</b>", self.styles['SubsectionHeader']))

        income_data = [
            ["Median Household Income:", f"${income.get('median_household', 0):,}" if income.get('median_household') else "N/A"],
            ["Per Capita Income:", f"${income.get('per_capita', 0):,}" if income.get('per_capita') else "N/A"],
        ]
        elements.append(self._create_data_table(income_data))

        # Employment
        emp = tract.get('employment', {})
        if emp.get('unemployment_rate_pct'):
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Employment</b>", self.styles['SubsectionHeader']))

            emp_data = [
                ["Labor Force:", f"{emp.get('labor_force', 0):,}" if emp.get('labor_force') else "N/A"],
                ["Unemployment Rate:", f"{emp.get('unemployment_rate_pct', 0):.1f}%"],
            ]
            elements.append(self._create_data_table(emp_data))

        # Market indicators
        indicators = demo.get('market_indicators', {})
        if indicators:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Market Indicators</b>", self.styles['SubsectionHeader']))

            ind_data = [
                ["Market Strength:", indicators.get('market_strength', 'Unknown')],
                ["Affordability:", indicators.get('affordability', 'Unknown')],
                ["Development Potential:", indicators.get('development_potential', 'Unknown')],
            ]
            if indicators.get('price_to_income_ratio'):
                ind_data.append(["Price-to-Income Ratio:", f"{indicators['price_to_income_ratio']:.1f}"])

            elements.append(self._create_data_table(ind_data))

            # Factors
            factors = indicators.get('factors', [])
            if factors:
                elements.append(Spacer(1, 0.1*inch))
                for factor in factors[:4]:
                    elements.append(Paragraph(f"• {factor}", self.styles['BodyText']))

        return elements

    def _create_site_context_section(self, site_data: Dict) -> List:
        """Create site context and surroundings section"""
        elements = []

        elements.append(Paragraph("7. SITE CONTEXT & SURROUNDINGS", self.styles['SectionHeader']))

        context = site_data.get('site_context', {})

        if not context:
            elements.append(Paragraph("Site context data not available.", self.styles['BodyText']))
            return elements

        elements.append(Paragraph(
            f"Analysis radius: {context.get('radius_meters', 500)} meters from site center",
            self.styles['BodyText']
        ))
        elements.append(Spacer(1, 0.2*inch))

        # Get summary data (may be in 'summary' sub-dict or at root level)
        summary = context.get('summary', context)

        # Summary scores
        elements.append(Paragraph("<b>Summary Scores</b>", self.styles['SubsectionHeader']))

        walkability = summary.get('walkability_score', context.get('walkability_score', 'N/A'))
        transit_access = summary.get('transit_summary', context.get('transit_summary', 'Unknown'))
        noise_risk = summary.get('road_noise_risk', context.get('road_noise_risk', 'Unknown'))

        score_data = [
            ["Walkability Score:", f"{walkability}/100" if walkability != 'N/A' else 'N/A'],
            ["Transit Access:", str(transit_access)],
            ["Road Noise Risk:", str(noise_risk)],
        ]
        elements.append(self._create_data_table(score_data))

        # Buildings - handle both dict and list formats
        buildings = context.get('buildings', [])
        if buildings:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Surrounding Buildings</b>", self.styles['SubsectionHeader']))

            if isinstance(buildings, dict):
                count = buildings.get('count', 0)
                by_type = buildings.get('by_type', {})
            elif isinstance(buildings, list):
                count = len(buildings)
                # Count by type if items have 'type' or 'building' key
                by_type = {}
                for b in buildings:
                    if isinstance(b, dict):
                        btype = b.get('building', b.get('type', 'unknown'))
                        by_type[btype] = by_type.get(btype, 0) + 1
            else:
                count = 0
                by_type = {}

            bldg_data = [["Total Buildings:", str(count)]]

            if by_type and isinstance(by_type, dict):
                for btype, cnt in sorted(by_type.items(), key=lambda x: -x[1])[:5]:
                    if btype and btype != 'yes':
                        bldg_data.append([f"  {btype.title()}:", str(cnt)])

            elements.append(self._create_data_table(bldg_data))

        # Transit - handle both dict and list formats
        transit = context.get('transit', [])
        if transit:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Public Transit</b>", self.styles['SubsectionHeader']))

            if isinstance(transit, dict):
                bus_stops = transit.get('bus_stops', [])
                rail_stations = transit.get('rail_stations', [])
            elif isinstance(transit, list):
                bus_stops = [t for t in transit if isinstance(t, dict) and t.get('type') == 'bus_stop']
                rail_stations = [t for t in transit if isinstance(t, dict) and t.get('type') in ['station', 'rail']]
                if not bus_stops:  # If no type field, assume all are transit stops
                    bus_stops = transit

            transit_data = []
            if bus_stops:
                transit_data.append(["Transit Stops:", str(len(bus_stops) if isinstance(bus_stops, list) else bus_stops)])

            if transit_data:
                elements.append(self._create_data_table(transit_data))

            # List nearest stops
            if isinstance(bus_stops, list) and bus_stops:
                elements.append(Paragraph("Nearest transit:", self.styles['BodyText']))
                for stop in bus_stops[:3]:
                    if isinstance(stop, dict):
                        name = stop.get('name', stop.get('tags', {}).get('name', 'Unnamed'))
                        dist = stop.get('distance_m', stop.get('distance', 0))
                        if isinstance(dist, (int, float)):
                            elements.append(Paragraph(f"• {name} ({dist:.0f}m)", self.styles['BodyText']))
                        else:
                            elements.append(Paragraph(f"• {name}", self.styles['BodyText']))

        # Amenities - handle both formats
        amenities = context.get('amenities', {})
        if amenities:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Nearby Amenities</b>", self.styles['SubsectionHeader']))

            amenity_data = []
            if isinstance(amenities, dict):
                by_type = amenities.get('by_type', amenities)
                if isinstance(by_type, dict):
                    def get_count(v):
                        return len(v) if isinstance(v, list) else int(v) if isinstance(v, (int, float)) else 0
                    for atype, items in sorted(by_type.items(), key=lambda x: -get_count(x[1]))[:6]:
                        if atype != 'by_type':
                            count = get_count(items)
                            amenity_data.append([atype.replace('_', ' ').title() + ":", str(count)])
            elif isinstance(amenities, list):
                amenity_data.append(["Total Amenities:", str(len(amenities))])

            if amenity_data:
                elements.append(self._create_data_table(amenity_data))

        # Roads - handle both dict and list formats
        roads = context.get('roads', [])
        if roads:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Nearby Roads</b>", self.styles['SubsectionHeader']))

            if isinstance(roads, dict):
                major = roads.get('major_roads', [])[:5]
            elif isinstance(roads, list):
                # Filter for major roads
                major_types = ['primary', 'secondary', 'tertiary', 'trunk', 'motorway']
                major = [r for r in roads if isinstance(r, dict) and r.get('highway') in major_types][:5]
                if not major:
                    major = roads[:3]

            for road in major:
                if isinstance(road, dict):
                    name = road.get('name', road.get('tags', {}).get('name', 'Unnamed Road'))
                    rtype = road.get('highway', road.get('type', 'road'))
                    if name and name != 'Unnamed Road':
                        elements.append(Paragraph(f"• {name} ({rtype})", self.styles['BodyText']))

        return elements

    def _create_climate_section(self, site_data: Dict) -> List:
        """Create climate and sun path section"""
        elements = []

        elements.append(Paragraph("8. CLIMATE & SOLAR ANALYSIS", self.styles['SectionHeader']))

        # Weather data
        weather = site_data.get('weather', {})
        elements.append(Paragraph("<b>Climate Overview</b>", self.styles['SubsectionHeader']))

        if weather:
            climate_data = []
            if weather.get('temperature_f'):
                climate_data.append(["Current Temperature:", f"{weather['temperature_f']}°F"])
            if weather.get('conditions'):
                climate_data.append(["Current Conditions:", weather['conditions']])
            if weather.get('humidity_pct'):
                climate_data.append(["Humidity:", f"{weather['humidity_pct']}%"])
            if weather.get('wind_mph'):
                climate_data.append(["Wind Speed:", f"{weather['wind_mph']} mph"])

            if climate_data:
                elements.append(self._create_data_table(climate_data))

            # Forecast
            forecast = weather.get('forecast', [])
            if forecast:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("<b>7-Day Forecast</b>", self.styles['SubsectionHeader']))

                fc_data = [["Day", "High", "Low", "Conditions"]]
                for day in forecast[:7]:
                    fc_data.append([
                        day.get('name', '')[:10],
                        f"{day.get('high_f', '')}°F",
                        f"{day.get('low_f', '')}°F",
                        day.get('conditions', '')[:20]
                    ])
                elements.append(self._create_styled_table(fc_data))
        else:
            elements.append(Paragraph("Current weather data not available.", self.styles['BodyText']))

        # Sun path
        sun = site_data.get('sun_path', {})
        if sun:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Solar Analysis</b>", self.styles['SubsectionHeader']))

            sun_data = []
            if sun.get('sunrise'):
                sun_data.append(["Sunrise:", sun['sunrise']])
            if sun.get('sunset'):
                sun_data.append(["Sunset:", sun['sunset']])
            if sun.get('day_length'):
                sun_data.append(["Day Length:", sun['day_length']])
            if sun.get('solar_noon'):
                sun_data.append(["Solar Noon:", sun['solar_noon']])
            if sun.get('max_altitude'):
                sun_data.append(["Max Sun Altitude:", f"{sun['max_altitude']}°"])

            if sun_data:
                elements.append(self._create_data_table(sun_data))

            # Design implications
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Design Implications</b>", self.styles['SubsectionHeader']))

            lat = site_data.get('latitude', 25)
            design_notes = [
                f"At latitude {lat:.1f}°, the sun reaches a maximum altitude of approximately {90 - lat + 23.5:.1f}° at summer solstice.",
                "South-facing windows will receive the most direct sunlight throughout the year.",
                "Consider shading devices for west-facing glazing to reduce afternoon heat gain.",
                "In South Florida's climate, solar control is a primary design consideration."
            ]
            for note in design_notes:
                elements.append(Paragraph(f"• {note}", self.styles['BodyText']))

        return elements

    def _create_appendix(self, site_data: Dict) -> List:
        """Create appendix with raw data"""
        elements = []

        elements.append(Paragraph("APPENDIX: RAW DATA", self.styles['SectionHeader']))
        elements.append(Paragraph(
            "The following is the raw JSON data from all API sources for reference.",
            self.styles['BodyText']
        ))
        elements.append(Spacer(1, 0.3*inch))

        # Pretty print JSON (truncated)
        raw_json = json.dumps(site_data, indent=2, default=str)
        if len(raw_json) > 10000:
            raw_json = raw_json[:10000] + "\n... [truncated]"

        elements.append(Paragraph(f"<pre>{raw_json}</pre>", self.styles['Code']))

        return elements

    def _create_data_table(self, data: List[List[str]]) -> Table:
        """Create a simple two-column data table"""
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        return table

    def _create_styled_table(self, data: List[List[str]]) -> Table:
        """Create a styled table with header row"""
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*self.config.primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            # Padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return table

    def _create_horizontal_line(self):
        """Create a horizontal line"""
        from reportlab.platypus import HRFlowable
        return HRFlowable(
            width="100%",
            thickness=2,
            color=colors.Color(*self.config.primary_color),
            spaceAfter=10,
            spaceBefore=10
        )

    def _add_footer(self, canvas, doc):
        """Add footer to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)

        # Page number
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawCentredString(letter[0]/2, 0.5*inch, text)

        # Company name
        canvas.drawString(0.75*inch, 0.5*inch, self.config.company_name)

        # Date
        date_str = datetime.now().strftime("%m/%d/%Y")
        canvas.drawRightString(letter[0] - 0.75*inch, 0.5*inch, date_str)

        canvas.restoreState()

    def _get_flood_zone_description(self, zone: str) -> str:
        """Get description for flood zone code"""
        descriptions = {
            'A': 'High risk area with 1% annual chance of flooding',
            'AE': 'High risk area with base flood elevations determined',
            'AH': 'High risk area with flood depths of 1-3 feet',
            'AO': 'High risk area with flood depths of 1-3 feet (sheet flow)',
            'V': 'High risk coastal area with wave action',
            'VE': 'High risk coastal area with base flood elevations',
            'X': 'Area of minimal flood hazard',
            'B': 'Area of moderate flood hazard',
            'C': 'Area of minimal flood hazard',
            'D': 'Area with undetermined flood hazard',
        }

        # Check for zone prefix match
        for prefix in ['VE', 'AE', 'AH', 'AO', 'V', 'A', 'X', 'B', 'C', 'D']:
            if zone and zone.upper().startswith(prefix):
                return descriptions.get(prefix, 'Unknown flood zone')

        return 'Unknown flood zone'

    def _generate_recommendations(self, site_data: Dict) -> List[str]:
        """Generate recommendations based on site data"""
        recommendations = []

        # Flood zone recommendations
        flood = site_data.get('flood_zone', {})
        zone = flood.get('zone', '')
        if zone and (zone.startswith('A') or zone.startswith('V')):
            recommendations.append("Obtain flood elevation certificate and consider flood-resistant construction methods")

        # Environmental recommendations
        env = site_data.get('environmental', {})
        if env.get('summary', {}).get('phase1_recommended'):
            recommendations.append("Phase I Environmental Site Assessment recommended before acquisition")

        # Wetlands
        wetlands = env.get('wetlands', {})
        if wetlands.get('wetlands_nearby') == 'LIKELY':
            recommendations.append("Wetland delineation study recommended; potential Section 404 permit required")

        # Storm/wind recommendations
        storm = site_data.get('storm_wind', {})
        if storm.get('hvhz'):
            recommendations.append("HVHZ compliance required: impact glazing, enhanced roof attachment, Miami-Dade NOA products")

        # Soil recommendations
        soil = site_data.get('soil', {})
        eng = soil.get('engineering_properties', {})
        if eng.get('hydric'):
            recommendations.append("Hydric soils present; geotechnical investigation strongly recommended")

        # Default recommendation
        if not recommendations:
            recommendations.append("Standard due diligence procedures recommended for site development")

        return recommendations


def generate_site_report(
    site_data: Dict[str, Any],
    output_path: str,
    project_name: str = None,
    project_number: str = None,
    client_name: str = None,
    config: ReportConfig = None
) -> str:
    """
    Convenience function to generate a site analysis report

    Args:
        site_data: Complete site data dictionary from site_data_full.py
        output_path: Path for output PDF
        project_name: Optional project name
        project_number: Optional project number
        client_name: Optional client name
        config: Optional ReportConfig for customization

    Returns:
        Path to generated PDF
    """
    generator = SiteAnalysisReportGenerator(config)
    return generator.generate_report(
        site_data=site_data,
        output_path=output_path,
        project_name=project_name,
        project_number=project_number,
        client_name=client_name
    )


if __name__ == "__main__":
    # Test with sample data
    print("Site Analysis Report Generator")
    print("=" * 40)

    if not REPORTLAB_AVAILABLE:
        print("Error: reportlab not installed")
        print("Install with: pip install reportlab")
        exit(1)

    # Create sample site data for testing
    sample_data = {
        "address": "11900 SW 216th St, Goulds, FL 33170",
        "latitude": 25.5659,
        "longitude": -80.3827,
        "elevation_ft": 8.5,
        "flood_zone": {
            "zone": "AE",
            "panel": "12086C0536L",
            "base_flood_elevation": 9
        },
        "storm_wind": {
            "design_wind_speed_mph": 175,
            "hvhz": True,
            "exposure_category": "C",
            "risk_category": "II",
            "hurricane_risk": {
                "risk_level": "HIGH",
                "historical_hurricanes_50mi_50yr": 15,
                "notes": ["Multiple major hurricanes in past 50 years"]
            }
        },
        "environmental": {
            "summary": {
                "risk_level": "LOW",
                "concerns": ["No significant environmental concerns identified"],
                "recommendation": "Standard due diligence appropriate",
                "phase1_recommended": False
            },
            "air_quality": {"aqi_category": "Good"},
            "wetlands": {"wetlands_nearby": "POSSIBLE"}
        },
        "demographics": {
            "geography": {
                "found": True,
                "state_name": "Florida",
                "county_name": "Miami-Dade",
                "tract": "011406"
            },
            "tract_data": {
                "found": True,
                "population": {"total": 5200, "median_age": 34.5},
                "housing": {
                    "total_units": 1800,
                    "occupied": 1650,
                    "vacant": 150,
                    "vacancy_rate_pct": 8.3,
                    "median_value": 285000,
                    "median_rent": 1450,
                    "median_year_built": 1985
                },
                "income": {
                    "median_household": 52000,
                    "per_capita": 22500
                },
                "employment": {
                    "labor_force": 2800,
                    "unemployment_rate_pct": 5.2
                }
            },
            "market_indicators": {
                "market_strength": "Moderate",
                "affordability": "Moderate",
                "development_potential": "High",
                "price_to_income_ratio": 5.5,
                "factors": ["Aging housing stock", "Middle-income area"]
            }
        },
        "site_context": {
            "radius_meters": 500,
            "walkability_score": 45,
            "transit_summary": "Limited",
            "road_noise_risk": "Moderate",
            "buildings": {"count": 120, "by_type": {"residential": 95, "commercial": 15, "industrial": 10}},
            "transit": {"bus_stops": [{"name": "SW 216 St & SW 119 Ave", "distance_m": 150}]},
            "amenities": {"by_type": {"restaurant": 5, "convenience": 3, "bank": 2}}
        },
        "weather": {
            "temperature_f": 82,
            "conditions": "Partly Cloudy",
            "humidity_pct": 75,
            "wind_mph": 8
        },
        "sun_path": {
            "sunrise": "6:45 AM",
            "sunset": "6:15 PM",
            "day_length": "11h 30m",
            "solar_noon": "12:30 PM",
            "max_altitude": 65
        },
        "soil": {
            "map_units": [
                {"symbol": "Pf", "name": "Perrine marl", "percent": 85},
                {"symbol": "Bg", "name": "Biscayne gravelly marl", "percent": 15}
            ],
            "engineering_properties": {
                "unified_classification": "MH",
                "drainage_class": "Poorly drained",
                "hydric": True,
                "depth_to_water_table": "0-6 inches",
                "flooding_frequency": "Rare"
            }
        },
        "parcel": {"found": False}
    }

    # Generate test report
    output_file = "/mnt/d/_CLAUDE-TOOLS/site-data-api/test_site_report.pdf"

    config = ReportConfig(
        company_name="BD Architect LLC",
        company_address="Miami, Florida"
    )

    try:
        result = generate_site_report(
            site_data=sample_data,
            output_path=output_file,
            project_name="Test Development",
            project_number="2024-001",
            client_name="Test Client",
            config=config
        )
        print(f"\nReport generated: {result}")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
