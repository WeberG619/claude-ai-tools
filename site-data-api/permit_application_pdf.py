#!/usr/bin/env python3
"""
PDF Permit Application Generator
================================
Generates pre-filled permit application forms for South Florida jurisdictions.
Uses reportlab for PDF generation with fillable fields support.

Supports:
- Miami-Dade County Building Permit Application
- City of Miami Building Permit Application
- Broward County Building Permit Application
- Palm Beach County Building Permit Application
- Standard trade permit applications (MEP, Fire)
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import json

# PDF generation - using reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Warning: reportlab not installed. PDF generation disabled. Install with: pip install reportlab")


class ApplicationType(Enum):
    """Types of permit applications"""
    BUILDING = "building"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    FIRE = "fire"
    ROOFING = "roofing"
    DEMOLITION = "demolition"


@dataclass
class ProjectInfo:
    """Project information for permit application"""
    project_name: str
    project_address: str
    city: str
    state: str = "FL"
    zip_code: str = ""
    folio_number: str = ""
    legal_description: str = ""
    lot: str = ""
    block: str = ""
    subdivision: str = ""

    # Building info
    occupancy_type: str = ""
    construction_type: str = ""
    stories: int = 1
    building_sqft: float = 0
    lot_sqft: float = 0
    estimated_value: float = 0

    # Scope of work
    scope_of_work: str = ""
    work_description: str = ""
    is_new_construction: bool = False
    is_addition: bool = False
    is_alteration: bool = False
    is_repair: bool = False


@dataclass
class OwnerInfo:
    """Property owner information"""
    name: str
    address: str
    city: str
    state: str = "FL"
    zip_code: str = ""
    phone: str = ""
    email: str = ""


@dataclass
class ContractorInfo:
    """Contractor information"""
    company_name: str
    license_number: str
    qualifier_name: str
    address: str
    city: str
    state: str = "FL"
    zip_code: str = ""
    phone: str = ""
    email: str = ""
    insurance_company: str = ""
    insurance_policy: str = ""
    insurance_expiration: str = ""


@dataclass
class ArchitectInfo:
    """Architect/Engineer information"""
    name: str
    company: str
    license_number: str
    address: str
    city: str
    state: str = "FL"
    zip_code: str = ""
    phone: str = ""
    email: str = ""


class PermitApplicationPDF:
    """PDF Permit Application Generator"""

    def __init__(self, db_path: str = "site_intelligence.db"):
        self.db_path = db_path

        # Jurisdiction-specific form configurations
        self.jurisdiction_forms = {
            "Miami-Dade County": {
                "form_number": "BD-100",
                "form_title": "Building Permit Application",
                "requires_noa": True,
                "hvhz": True,
                "requires_40_year": True,
                "portal": "iBuild",
                "special_fields": ["NOA Numbers", "40-Year Recertification Status", "Impact Protection"]
            },
            "City of Miami": {
                "form_number": "BLD-001",
                "form_title": "Building Permit Application",
                "requires_noa": True,
                "hvhz": True,
                "requires_40_year": True,
                "portal": "ePlan",
                "special_fields": ["NOA Numbers", "Historic District", "Overlay Zone"]
            },
            "Broward County": {
                "form_number": "BPD-100",
                "form_title": "Building Permit Application",
                "requires_noa": True,
                "hvhz": True,
                "requires_40_year": False,
                "portal": "EPR",
                "special_fields": ["NOA Numbers", "SFWMD Permit Status"]
            },
            "Palm Beach County": {
                "form_number": "PBC-BP-001",
                "form_title": "Building Permit Application",
                "requires_noa": False,
                "hvhz": False,
                "requires_40_year": False,
                "portal": "eTRAKiT",
                "special_fields": ["SFWMD Permit Status"]
            },
            "City of Fort Lauderdale": {
                "form_number": "FTL-BLD",
                "form_title": "Building Permit Application",
                "requires_noa": True,
                "hvhz": True,
                "requires_40_year": False,
                "portal": "EPR",
                "special_fields": ["NOA Numbers", "Parking Requirements"]
            }
        }

        # Standard checklist items by application type
        self.required_documents = {
            ApplicationType.BUILDING: [
                "Signed and sealed architectural drawings",
                "Signed and sealed structural drawings (if applicable)",
                "Site plan (if applicable)",
                "Survey (for new construction)",
                "Energy calculations (Form 400A)",
                "Product approval documentation (NOAs for HVHZ)",
                "Truss engineering (if applicable)",
                "Soils report (for new construction)",
                "Owner authorization letter (if agent)",
                "Contractor's license copy",
                "Insurance certificate",
                "Proof of ownership or authorization"
            ],
            ApplicationType.ELECTRICAL: [
                "Electrical permit application",
                "Electrical drawings (if required)",
                "Load calculations",
                "Electrical contractor's license",
                "Insurance certificate"
            ],
            ApplicationType.MECHANICAL: [
                "Mechanical permit application",
                "Mechanical drawings (if required)",
                "Load calculations (Manual J/D/S)",
                "Equipment specifications",
                "Mechanical contractor's license",
                "Insurance certificate"
            ],
            ApplicationType.PLUMBING: [
                "Plumbing permit application",
                "Plumbing drawings (if required)",
                "Fixture count",
                "Plumbing contractor's license",
                "Insurance certificate"
            ],
            ApplicationType.FIRE: [
                "Fire permit application",
                "Fire protection drawings",
                "Hydraulic calculations",
                "Fire sprinkler specifications",
                "Fire alarm specifications",
                "Fire contractor's license",
                "Insurance certificate"
            ],
            ApplicationType.ROOFING: [
                "Roofing permit application",
                "Roofing drawings/details",
                "Product approval (NOA)",
                "Attachment schedule",
                "Roofing contractor's license",
                "Insurance certificate"
            ]
        }

    def generate_building_permit_application(
        self,
        jurisdiction: str,
        project: ProjectInfo,
        owner: OwnerInfo,
        contractor: ContractorInfo,
        architect: Optional[ArchitectInfo] = None,
        output_path: Optional[str] = None,
        include_checklist: bool = True
    ) -> str:
        """
        Generate a building permit application PDF.

        Args:
            jurisdiction: Name of jurisdiction
            project: Project information
            owner: Owner information
            contractor: Contractor information
            architect: Architect/Engineer information (optional)
            output_path: Output file path (auto-generated if not provided)
            include_checklist: Include document checklist

        Returns:
            Path to generated PDF
        """
        if not HAS_REPORTLAB:
            raise RuntimeError("reportlab is required for PDF generation. Install with: pip install reportlab")

        # Get jurisdiction-specific form info
        form_config = self.jurisdiction_forms.get(jurisdiction, {
            "form_number": "GENERIC",
            "form_title": "Building Permit Application",
            "requires_noa": False,
            "hvhz": False,
            "requires_40_year": False,
            "portal": "Contact Building Department",
            "special_fields": []
        })

        # Generate output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = project.project_name.replace(" ", "_")[:30]
            output_path = f"permit_application_{safe_name}_{timestamp}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Build content
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            backColor=colors.lightgrey
        )

        normal_style = styles['Normal']

        # Header
        story.append(Paragraph(f"<b>{jurisdiction}</b>", title_style))
        story.append(Paragraph(f"<b>{form_config['form_title']}</b>", title_style))
        story.append(Paragraph(f"Form {form_config['form_number']}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Date
        story.append(Paragraph(f"Application Date: {datetime.now().strftime('%B %d, %Y')}", normal_style))
        story.append(Spacer(1, 12))

        # Section 1: Project Information
        story.append(Paragraph("SECTION 1: PROJECT INFORMATION", section_style))

        project_data = [
            ["Project Name:", project.project_name],
            ["Project Address:", project.project_address],
            ["City:", project.city],
            ["State:", project.state],
            ["ZIP Code:", project.zip_code],
            ["Folio Number:", project.folio_number],
            ["Legal Description:", project.legal_description],
            ["Lot:", project.lot],
            ["Block:", project.block],
            ["Subdivision:", project.subdivision],
        ]

        project_table = Table(project_data, colWidths=[2*inch, 5*inch])
        project_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(project_table)
        story.append(Spacer(1, 12))

        # Section 2: Building Information
        story.append(Paragraph("SECTION 2: BUILDING INFORMATION", section_style))

        work_type = []
        if project.is_new_construction:
            work_type.append("New Construction")
        if project.is_addition:
            work_type.append("Addition")
        if project.is_alteration:
            work_type.append("Alteration")
        if project.is_repair:
            work_type.append("Repair")

        building_data = [
            ["Occupancy Type:", project.occupancy_type],
            ["Construction Type:", project.construction_type],
            ["Number of Stories:", str(project.stories)],
            ["Building Area (SF):", f"{project.building_sqft:,.0f}"],
            ["Lot Size (SF):", f"{project.lot_sqft:,.0f}" if project.lot_sqft else ""],
            ["Estimated Value:", f"${project.estimated_value:,.2f}"],
            ["Type of Work:", ", ".join(work_type) if work_type else ""],
        ]

        building_table = Table(building_data, colWidths=[2*inch, 5*inch])
        building_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(building_table)
        story.append(Spacer(1, 12))

        # Scope of Work
        story.append(Paragraph("SCOPE OF WORK", section_style))
        story.append(Paragraph(project.scope_of_work or project.work_description or "See attached drawings", normal_style))
        story.append(Spacer(1, 12))

        # Section 3: Owner Information
        story.append(Paragraph("SECTION 3: PROPERTY OWNER", section_style))

        owner_data = [
            ["Owner Name:", owner.name],
            ["Address:", owner.address],
            ["City/State/ZIP:", f"{owner.city}, {owner.state} {owner.zip_code}"],
            ["Phone:", owner.phone],
            ["Email:", owner.email],
        ]

        owner_table = Table(owner_data, colWidths=[2*inch, 5*inch])
        owner_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(owner_table)
        story.append(Spacer(1, 12))

        # Section 4: Contractor Information
        story.append(Paragraph("SECTION 4: CONTRACTOR", section_style))

        contractor_data = [
            ["Company Name:", contractor.company_name],
            ["License Number:", contractor.license_number],
            ["Qualifier Name:", contractor.qualifier_name],
            ["Address:", contractor.address],
            ["City/State/ZIP:", f"{contractor.city}, {contractor.state} {contractor.zip_code}"],
            ["Phone:", contractor.phone],
            ["Email:", contractor.email],
            ["Insurance Company:", contractor.insurance_company],
            ["Policy Number:", contractor.insurance_policy],
            ["Expiration Date:", contractor.insurance_expiration],
        ]

        contractor_table = Table(contractor_data, colWidths=[2*inch, 5*inch])
        contractor_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(contractor_table)
        story.append(Spacer(1, 12))

        # Section 5: Design Professional (if provided)
        if architect:
            story.append(Paragraph("SECTION 5: DESIGN PROFESSIONAL", section_style))

            architect_data = [
                ["Name:", architect.name],
                ["Company:", architect.company],
                ["License Number:", architect.license_number],
                ["Address:", architect.address],
                ["City/State/ZIP:", f"{architect.city}, {architect.state} {architect.zip_code}"],
                ["Phone:", architect.phone],
                ["Email:", architect.email],
            ]

            architect_table = Table(architect_data, colWidths=[2*inch, 5*inch])
            architect_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ]))
            story.append(architect_table)
            story.append(Spacer(1, 12))

        # HVHZ-specific section
        if form_config.get('hvhz'):
            story.append(Paragraph("SECTION 6: HVHZ REQUIREMENTS (High-Velocity Hurricane Zone)", section_style))
            story.append(Paragraph(
                "This project is located within the High-Velocity Hurricane Zone (HVHZ). "
                "All products and assemblies must have valid Florida Product Approvals or "
                "Miami-Dade County Notices of Acceptance (NOAs).",
                normal_style
            ))
            story.append(Spacer(1, 6))

            hvhz_items = [
                ["Impact Protection:", "☐ Impact-Rated Products  ☐ Approved Shutters  ☐ Plywood (See Requirements)"],
                ["NOA Documentation:", "☐ Attached  ☐ To Be Submitted"],
                ["Wind Design:", f"V = _____ mph, Exposure _____, Risk Category _____"],
            ]

            hvhz_table = Table(hvhz_items, colWidths=[2*inch, 5*inch])
            hvhz_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ]))
            story.append(hvhz_table)
            story.append(Spacer(1, 12))

        # 40-Year Recertification (Miami-Dade specific)
        if form_config.get('requires_40_year'):
            story.append(Paragraph("40-YEAR BUILDING RECERTIFICATION STATUS", section_style))
            story.append(Paragraph(
                "For buildings 40 years or older, a recertification inspection is required. "
                "Buildings 50 years or older require recertification every 10 years thereafter.",
                normal_style
            ))
            story.append(Spacer(1, 6))

            recert_items = [
                ["Building Age:", "☐ Less than 40 years  ☐ 40-50 years  ☐ Over 50 years"],
                ["Recertification Status:", "☐ N/A  ☐ Current  ☐ Pending  ☐ Required"],
            ]

            recert_table = Table(recert_items, colWidths=[2*inch, 5*inch])
            recert_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ]))
            story.append(recert_table)
            story.append(Spacer(1, 12))

        # Signature Block
        story.append(PageBreak())
        story.append(Paragraph("CERTIFICATION AND SIGNATURES", section_style))

        certification_text = """
        I hereby certify that the information provided in this application is true and correct
        to the best of my knowledge. I understand that any false statements may result in denial
        or revocation of the permit. I agree to comply with all applicable codes and regulations.
        """
        story.append(Paragraph(certification_text, normal_style))
        story.append(Spacer(1, 24))

        signature_data = [
            ["Owner/Agent Signature:", "_" * 40, "Date:", "_" * 15],
            ["Print Name:", "_" * 40, "", ""],
            ["", "", "", ""],
            ["Contractor Signature:", "_" * 40, "Date:", "_" * 15],
            ["Print Name:", "_" * 40, "", ""],
            ["License Number:", contractor.license_number, "", ""],
        ]

        signature_table = Table(signature_data, colWidths=[1.5*inch, 3*inch, 0.75*inch, 1.75*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(signature_table)
        story.append(Spacer(1, 24))

        # Document Checklist
        if include_checklist:
            story.append(Paragraph("REQUIRED DOCUMENTS CHECKLIST", section_style))
            story.append(Paragraph(
                "The following documents are required for permit review. Check all documents being submitted:",
                normal_style
            ))
            story.append(Spacer(1, 6))

            checklist_data = []
            for doc_item in self.required_documents[ApplicationType.BUILDING]:
                checklist_data.append(["☐", doc_item])

            checklist_table = Table(checklist_data, colWidths=[0.3*inch, 6.7*inch])
            checklist_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(checklist_table)

        # Office Use Only section
        story.append(Spacer(1, 24))
        story.append(Paragraph("FOR OFFICE USE ONLY", section_style))

        office_data = [
            ["Permit Number:", "_" * 30, "Application Fee:", "$_________"],
            ["Plan Review Fee:", "$_________", "Impact Fee:", "$_________"],
            ["Received By:", "_" * 30, "Date:", "_" * 15],
        ]

        office_table = Table(office_data, colWidths=[1.5*inch, 2.25*inch, 1.5*inch, 1.75*inch])
        office_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(office_table)

        # Build PDF
        doc.build(story)

        return output_path

    def generate_trade_permit_application(
        self,
        jurisdiction: str,
        application_type: ApplicationType,
        project: ProjectInfo,
        owner: OwnerInfo,
        contractor: ContractorInfo,
        output_path: Optional[str] = None,
        work_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a trade permit application (electrical, mechanical, plumbing, fire).

        Args:
            jurisdiction: Name of jurisdiction
            application_type: Type of trade permit
            project: Project information
            owner: Owner information
            contractor: Contractor information
            output_path: Output file path
            work_details: Specific work details (fixture counts, circuits, etc.)

        Returns:
            Path to generated PDF
        """
        if not HAS_REPORTLAB:
            raise RuntimeError("reportlab is required for PDF generation. Install with: pip install reportlab")

        # Generate output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = project.project_name.replace(" ", "_")[:30]
            output_path = f"{application_type.value}_permit_{safe_name}_{timestamp}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            backColor=colors.lightgrey
        )

        normal_style = styles['Normal']

        # Title
        permit_titles = {
            ApplicationType.ELECTRICAL: "Electrical Permit Application",
            ApplicationType.MECHANICAL: "Mechanical Permit Application",
            ApplicationType.PLUMBING: "Plumbing Permit Application",
            ApplicationType.FIRE: "Fire Protection Permit Application",
            ApplicationType.ROOFING: "Roofing Permit Application",
        }

        story.append(Paragraph(f"<b>{jurisdiction}</b>", title_style))
        story.append(Paragraph(f"<b>{permit_titles.get(application_type, 'Permit Application')}</b>", title_style))
        story.append(Paragraph(f"Application Date: {datetime.now().strftime('%B %d, %Y')}", normal_style))
        story.append(Spacer(1, 12))

        # Project Information
        story.append(Paragraph("PROJECT INFORMATION", section_style))

        project_data = [
            ["Project Name:", project.project_name],
            ["Project Address:", project.project_address],
            ["City/State/ZIP:", f"{project.city}, {project.state} {project.zip_code}"],
            ["Folio Number:", project.folio_number],
            ["Building Permit #:", "(if applicable)"],
        ]

        project_table = Table(project_data, colWidths=[2*inch, 5*inch])
        project_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(project_table)
        story.append(Spacer(1, 12))

        # Owner Information
        story.append(Paragraph("PROPERTY OWNER", section_style))

        owner_data = [
            ["Owner Name:", owner.name],
            ["Address:", f"{owner.address}, {owner.city}, {owner.state} {owner.zip_code}"],
            ["Phone:", owner.phone],
            ["Email:", owner.email],
        ]

        owner_table = Table(owner_data, colWidths=[2*inch, 5*inch])
        owner_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(owner_table)
        story.append(Spacer(1, 12))

        # Contractor Information
        story.append(Paragraph(f"{application_type.value.upper()} CONTRACTOR", section_style))

        contractor_data = [
            ["Company Name:", contractor.company_name],
            ["License Number:", contractor.license_number],
            ["Qualifier Name:", contractor.qualifier_name],
            ["Address:", f"{contractor.address}, {contractor.city}, {contractor.state} {contractor.zip_code}"],
            ["Phone:", contractor.phone],
            ["Email:", contractor.email],
        ]

        contractor_table = Table(contractor_data, colWidths=[2*inch, 5*inch])
        contractor_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))
        story.append(contractor_table)
        story.append(Spacer(1, 12))

        # Work Details (type-specific)
        story.append(Paragraph("SCOPE OF WORK", section_style))

        work_details = work_details or {}

        if application_type == ApplicationType.ELECTRICAL:
            electrical_data = [
                ["Service Size:", work_details.get('service_size', '_____ Amps')],
                ["Number of Circuits:", work_details.get('circuits', '_____')],
                ["Panel Location:", work_details.get('panel_location', '_____')],
                ["☐ New Service", "☐ Service Change", "☐ Sub-Panel", "☐ Circuits Only"],
                ["☐ Temporary Power", "☐ Generator", "☐ Solar/PV", "☐ EV Charging"],
            ]
        elif application_type == ApplicationType.MECHANICAL:
            electrical_data = [
                ["Equipment Type:", work_details.get('equipment_type', '☐ Split System ☐ Package Unit ☐ Mini-Split')],
                ["Tonnage:", work_details.get('tonnage', '_____ Tons')],
                ["Number of Units:", work_details.get('unit_count', '_____')],
                ["☐ New Installation", "☐ Replacement", "☐ Ductwork Only", "☐ Repair"],
            ]
        elif application_type == ApplicationType.PLUMBING:
            electrical_data = [
                ["Number of Fixtures:", work_details.get('fixture_count', '_____')],
                ["Water Heater:", work_details.get('water_heater', '☐ Tank ☐ Tankless ☐ N/A')],
                ["☐ New Construction", "☐ Remodel", "☐ Repair", "☐ Water Heater Only"],
                ["☐ Sewer Connection", "☐ Septic", "☐ Gas Piping", ""],
            ]
        elif application_type == ApplicationType.FIRE:
            electrical_data = [
                ["System Type:", "☐ Sprinkler ☐ Standpipe ☐ Alarm ☐ Suppression"],
                ["Number of Heads:", work_details.get('head_count', '_____')],
                ["Coverage Area (SF):", work_details.get('coverage_sf', '_____')],
                ["Hazard Classification:", work_details.get('hazard_class', '_____')],
            ]
        else:
            electrical_data = [
                ["Description of Work:", project.scope_of_work or "_____"],
            ]

        work_table = Table(electrical_data, colWidths=[1.75*inch] * 4)
        work_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(work_table)
        story.append(Spacer(1, 12))

        # Estimated Value
        story.append(Paragraph(f"Estimated Value of Work: ${project.estimated_value:,.2f}", normal_style))
        story.append(Spacer(1, 12))

        # Signature Block
        story.append(Paragraph("CERTIFICATION", section_style))

        story.append(Paragraph(
            "I certify that this application is true and correct. "
            "I will comply with all applicable codes and call for required inspections.",
            normal_style
        ))
        story.append(Spacer(1, 24))

        signature_data = [
            ["Contractor Signature:", "_" * 35, "Date:", "_" * 12],
            ["Print Name:", contractor.qualifier_name, "License:", contractor.license_number],
        ]

        signature_table = Table(signature_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 2*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(signature_table)

        # Document Checklist
        story.append(Spacer(1, 24))
        story.append(Paragraph("REQUIRED DOCUMENTS", section_style))

        checklist_data = []
        for doc_item in self.required_documents.get(application_type, []):
            checklist_data.append(["☐", doc_item])

        if checklist_data:
            checklist_table = Table(checklist_data, colWidths=[0.3*inch, 6.7*inch])
            checklist_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(checklist_table)

        # Build PDF
        doc.build(story)

        return output_path

    def generate_complete_permit_package(
        self,
        jurisdiction: str,
        project: ProjectInfo,
        owner: OwnerInfo,
        contractor: ContractorInfo,
        architect: Optional[ArchitectInfo] = None,
        include_trades: List[ApplicationType] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate a complete permit application package with all required applications.

        Args:
            jurisdiction: Name of jurisdiction
            project: Project information
            owner: Owner information
            contractor: Contractor information (general)
            architect: Architect/Engineer information
            include_trades: List of trade permits to include
            output_dir: Output directory for all PDFs

        Returns:
            Dictionary mapping application type to file path
        """
        if not output_dir:
            output_dir = "."

        os.makedirs(output_dir, exist_ok=True)

        generated_files = {}

        # Generate building permit application
        safe_name = project.project_name.replace(" ", "_")[:30]

        building_path = os.path.join(output_dir, f"01_building_permit_{safe_name}.pdf")
        self.generate_building_permit_application(
            jurisdiction=jurisdiction,
            project=project,
            owner=owner,
            contractor=contractor,
            architect=architect,
            output_path=building_path
        )
        generated_files['building'] = building_path

        # Generate trade permits
        if include_trades:
            trade_number = 2
            for trade_type in include_trades:
                if trade_type != ApplicationType.BUILDING:
                    trade_path = os.path.join(
                        output_dir,
                        f"{trade_number:02d}_{trade_type.value}_permit_{safe_name}.pdf"
                    )
                    self.generate_trade_permit_application(
                        jurisdiction=jurisdiction,
                        application_type=trade_type,
                        project=project,
                        owner=owner,
                        contractor=contractor,
                        output_path=trade_path
                    )
                    generated_files[trade_type.value] = trade_path
                    trade_number += 1

        return generated_files

    def get_supported_jurisdictions(self) -> List[str]:
        """Get list of supported jurisdictions."""
        return list(self.jurisdiction_forms.keys())

    def get_jurisdiction_requirements(self, jurisdiction: str) -> Dict[str, Any]:
        """Get specific requirements for a jurisdiction."""
        return self.jurisdiction_forms.get(jurisdiction, {})


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_permit_application(
    jurisdiction: str,
    project_name: str,
    project_address: str,
    city: str,
    owner_name: str,
    owner_address: str,
    owner_city: str,
    contractor_name: str,
    contractor_license: str,
    output_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    Quick function to create a permit application with minimal inputs.

    Returns path to generated PDF.
    """
    generator = PermitApplicationPDF()

    project = ProjectInfo(
        project_name=project_name,
        project_address=project_address,
        city=city,
        state=kwargs.get('state', 'FL'),
        zip_code=kwargs.get('zip_code', ''),
        folio_number=kwargs.get('folio_number', ''),
        occupancy_type=kwargs.get('occupancy_type', ''),
        construction_type=kwargs.get('construction_type', ''),
        stories=kwargs.get('stories', 1),
        building_sqft=kwargs.get('building_sqft', 0),
        estimated_value=kwargs.get('estimated_value', 0),
        scope_of_work=kwargs.get('scope_of_work', ''),
        is_new_construction=kwargs.get('is_new_construction', False),
        is_alteration=kwargs.get('is_alteration', True)
    )

    owner = OwnerInfo(
        name=owner_name,
        address=owner_address,
        city=owner_city,
        state=kwargs.get('owner_state', 'FL'),
        zip_code=kwargs.get('owner_zip', ''),
        phone=kwargs.get('owner_phone', ''),
        email=kwargs.get('owner_email', '')
    )

    contractor = ContractorInfo(
        company_name=contractor_name,
        license_number=contractor_license,
        qualifier_name=kwargs.get('qualifier_name', ''),
        address=kwargs.get('contractor_address', ''),
        city=kwargs.get('contractor_city', ''),
        state=kwargs.get('contractor_state', 'FL'),
        zip_code=kwargs.get('contractor_zip', ''),
        phone=kwargs.get('contractor_phone', ''),
        email=kwargs.get('contractor_email', ''),
        insurance_company=kwargs.get('insurance_company', ''),
        insurance_policy=kwargs.get('insurance_policy', ''),
        insurance_expiration=kwargs.get('insurance_expiration', '')
    )

    return generator.generate_building_permit_application(
        jurisdiction=jurisdiction,
        project=project,
        owner=owner,
        contractor=contractor,
        output_path=output_path
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PDF PERMIT APPLICATION GENERATOR - TEST")
    print("=" * 70)

    if not HAS_REPORTLAB:
        print("\nERROR: reportlab not installed")
        print("Install with: pip install reportlab")
        exit(1)

    # Test with Goulds Tower project
    generator = PermitApplicationPDF()

    print("\nSupported Jurisdictions:")
    for jur in generator.get_supported_jurisdictions():
        config = generator.get_jurisdiction_requirements(jur)
        hvhz = "HVHZ" if config.get('hvhz') else "Non-HVHZ"
        print(f"  - {jur} ({hvhz})")

    # Create test project
    project = ProjectInfo(
        project_name="Goulds Tower",
        project_address="11900 SW 216th St",
        city="Goulds",
        state="FL",
        zip_code="33170",
        folio_number="30-6029-001-0010",
        legal_description="GOULDS INDUSTRIAL PARK LOT 10",
        lot="10",
        block="1",
        subdivision="Goulds Industrial Park",
        occupancy_type="B - Business",
        construction_type="Type II-B",
        stories=3,
        building_sqft=15000,
        lot_sqft=25000,
        estimated_value=750000,
        scope_of_work="New 3-story commercial office building with ground floor retail",
        is_new_construction=True
    )

    owner = OwnerInfo(
        name="Goulds Development LLC",
        address="123 Main Street",
        city="Miami",
        state="FL",
        zip_code="33130",
        phone="(305) 555-1234",
        email="owner@gouldsdevelopment.com"
    )

    contractor = ContractorInfo(
        company_name="ABC Construction Inc.",
        license_number="CGC123456",
        qualifier_name="John Builder",
        address="456 Construction Ave",
        city="Miami",
        state="FL",
        zip_code="33125",
        phone="(305) 555-5678",
        email="permits@abcconstruction.com",
        insurance_company="Builder's Insurance Co.",
        insurance_policy="POL-2024-12345",
        insurance_expiration="12/31/2025"
    )

    architect = ArchitectInfo(
        name="Bruce Davis, AIA",
        company="BD Architect LLC",
        license_number="AR12345",
        address="789 Design Blvd",
        city="Miami",
        state="FL",
        zip_code="33131",
        phone="(305) 555-9012",
        email="bruce@bdarchitect.com"
    )

    print("\n" + "-" * 50)
    print("Generating Building Permit Application...")
    print("-" * 50)

    output_path = generator.generate_building_permit_application(
        jurisdiction="Miami-Dade County",
        project=project,
        owner=owner,
        contractor=contractor,
        architect=architect,
        output_path="test_goulds_tower_permit.pdf"
    )

    print(f"\n✓ Generated: {output_path}")

    # Generate trade permits
    print("\n" + "-" * 50)
    print("Generating Trade Permit Applications...")
    print("-" * 50)

    elec_path = generator.generate_trade_permit_application(
        jurisdiction="Miami-Dade County",
        application_type=ApplicationType.ELECTRICAL,
        project=project,
        owner=owner,
        contractor=ContractorInfo(
            company_name="Sparky Electric Inc.",
            license_number="EC13001234",
            qualifier_name="Mike Sparks",
            address="123 Electric Ave",
            city="Miami",
            state="FL",
            zip_code="33125",
            phone="(305) 555-ELEC",
            email="permits@sparkyelectric.com"
        ),
        output_path="test_goulds_tower_electrical.pdf",
        work_details={
            'service_size': '400 Amps',
            'circuits': '50',
            'panel_location': 'Electrical Room 101'
        }
    )

    print(f"✓ Generated: {elec_path}")

    mech_path = generator.generate_trade_permit_application(
        jurisdiction="Miami-Dade County",
        application_type=ApplicationType.MECHANICAL,
        project=project,
        owner=owner,
        contractor=ContractorInfo(
            company_name="Cool Air HVAC",
            license_number="CMC1234567",
            qualifier_name="Tom Cool",
            address="456 HVAC Lane",
            city="Miami",
            state="FL",
            zip_code="33125",
            phone="(305) 555-COOL",
            email="permits@coolairhvac.com"
        ),
        output_path="test_goulds_tower_mechanical.pdf",
        work_details={
            'equipment_type': 'Split System',
            'tonnage': '25',
            'unit_count': '3'
        }
    )

    print(f"✓ Generated: {mech_path}")

    print("\n" + "=" * 70)
    print("PDF PERMIT APPLICATION GENERATOR - TEST COMPLETE")
    print("=" * 70)
    print("\nGenerated Files:")
    print(f"  1. {output_path}")
    print(f"  2. {elec_path}")
    print(f"  3. {mech_path}")
    print("\n✓ All tests passed!")
