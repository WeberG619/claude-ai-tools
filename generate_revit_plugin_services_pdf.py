#!/usr/bin/env python3
"""
Generate a professional multi-page PDF for Upwork Project Catalog:
"Custom Revit Plugin Development Services" by Weber Gouin / BIM Ops Studio
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.units import mm
import os

# ── Color Palette ──────────────────────────────────────────────────────────
DARK_BLUE   = HexColor("#1a1a3e")
MED_BLUE    = HexColor("#2d4a7a")
LIGHT_BLUE  = HexColor("#3a7bd5")
ACCENT_BLUE = HexColor("#4a90d9")
SOFT_BG     = HexColor("#f4f6fa")
BORDER_GRAY = HexColor("#d0d5dd")
TEXT_DARK    = HexColor("#1a1a2e")
TEXT_MED     = HexColor("#3a3a5c")
TEXT_LIGHT   = HexColor("#5a5a7a")
WHITE        = white
TIER_GREEN   = HexColor("#27ae60")
TIER_BLUE    = HexColor("#2980b9")
TIER_PURPLE  = HexColor("#8e44ad")
CHECK_COLOR  = HexColor("#2d4a7a")

OUTPUT_PATH = "/mnt/d/_CLAUDE-TOOLS/revit-plugin-services.pdf"

# ── Custom Flowables ───────────────────────────────────────────────────────

class ColorBlock(Flowable):
    """A colored rectangle block used for header backgrounds."""
    def __init__(self, width, height, color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


class TierBox(Flowable):
    """A styled tier/pricing box."""
    def __init__(self, width, height, title, price, duration, subtitle, features, accent_color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.title = title
        self.price = price
        self.duration = duration
        self.subtitle = subtitle
        self.features = features
        self.accent_color = accent_color

    def draw(self):
        c = self.canv
        w, h = self.width, self.height

        # Outer rounded rect with border
        c.setStrokeColor(BORDER_GRAY)
        c.setLineWidth(1)
        c.setFillColor(WHITE)
        c.roundRect(0, 0, w, h, 8, fill=1, stroke=1)

        # Top accent bar
        c.setFillColor(self.accent_color)
        c.roundRect(0, h - 50, w, 50, 8, fill=1, stroke=0)
        # Cover bottom corners of accent bar
        c.rect(0, h - 50, w, 10, fill=1, stroke=0)

        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 32, self.title)

        # Price
        c.setFillColor(self.accent_color)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(w / 2, h - 80, self.price)

        # Duration
        c.setFillColor(TEXT_LIGHT)
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h - 96, self.duration)

        # Divider
        c.setStrokeColor(BORDER_GRAY)
        c.setLineWidth(0.5)
        c.line(15, h - 108, w - 15, h - 108)

        # Subtitle
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-BoldOblique", 11)
        c.drawCentredString(w / 2, h - 125, self.subtitle)

        # Features
        c.setFont("Helvetica", 9.5)
        c.setFillColor(TEXT_MED)
        y_pos = h - 148
        for feat in self.features:
            # Checkmark
            c.setFillColor(self.accent_color)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(18, y_pos, "\u2713")
            c.setFillColor(TEXT_MED)
            c.setFont("Helvetica", 9.5)
            c.drawString(34, y_pos, feat)
            y_pos -= 17


# ── Build Styles ───────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=32,
        leading=38,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName='Helvetica',
        fontSize=15,
        leading=20,
        textColor=HexColor("#a0b4d0"),
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='CoverAuthor',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=18,
        textColor=HexColor("#c0d0e8"),
        alignment=TA_CENTER,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='CoverBody',
        fontName='Helvetica',
        fontSize=11.5,
        leading=17,
        textColor=TEXT_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leftIndent=30,
        rightIndent=30,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=26,
        textColor=DARK_BLUE,
        spaceBefore=16,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name='SubHeader',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=19,
        textColor=MED_BLUE,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='BodyText2',
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='BulletItem',
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=TEXT_MED,
        leftIndent=28,
        bulletIndent=12,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name='BulletItemBold',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=15,
        textColor=TEXT_DARK,
        leftIndent=28,
        bulletIndent=12,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name='TechTag',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=MED_BLUE,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='SmallNote',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='ProcessStep',
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=TEXT_MED,
        leftIndent=36,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='ContactCTA',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=20,
        textColor=DARK_BLUE,
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='FooterText',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
    ))
    return styles


# ── Page Templates ─────────────────────────────────────────────────────────

def footer_template(canvas, doc):
    """Draw footer on every page."""
    canvas.saveState()
    canvas.setFillColor(BORDER_GRAY)
    canvas.rect(0, 0, letter[0], 28, fill=1, stroke=0)
    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(
        letter[0] / 2, 10,
        "Weber Gouin  |  BIM Ops Studio  |  Custom Revit Plugin Development  |  Upwork"
    )
    # Page number
    canvas.drawRightString(letter[0] - 40, 10, f"Page {doc.page}")
    canvas.restoreState()


# ── Page Builders ──────────────────────────────────────────────────────────

def build_cover_page(story, styles, page_width):
    """Page 1: Cover / Overview"""

    # Dark blue header block simulated via a table with background
    header_content = []
    header_content.append(Spacer(1, 30))
    header_content.append(Paragraph(
        "Custom Revit Plugin<br/>Development Services",
        styles['CoverTitle']
    ))
    header_content.append(Spacer(1, 8))
    header_content.append(Paragraph(
        "C# / .NET  |  Revit API  |  BIM Automation",
        styles['CoverSubtitle']
    ))
    header_content.append(Spacer(1, 12))

    # Thin decorative line
    header_content.append(HRFlowable(
        width="40%", thickness=1.5, color=HexColor("#4a6a9a"),
        spaceAfter=12, spaceBefore=4, hAlign='CENTER'
    ))

    header_content.append(Paragraph(
        "Weber Gouin  \u2014  BIM Ops Studio",
        styles['CoverAuthor']
    ))
    header_content.append(Spacer(1, 20))

    # Use a single-cell table with inner flowables for the dark header block
    header_table2 = Table([[header_content]], colWidths=[page_width])
    header_table2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))

    story.append(header_table2)
    story.append(Spacer(1, 28))

    # Intro paragraph
    intro_text = (
        "I specialize in building custom Revit C# plugins that streamline BIM workflows "
        "and eliminate repetitive manual tasks. Whether you need a simple single-button add-in "
        "or a complex multi-feature solution with custom WPF interfaces, I deliver production-ready "
        "plugins built on the official Revit API with clean, maintainable code."
    )
    story.append(Paragraph(intro_text, styles['CoverBody']))
    story.append(Spacer(1, 10))

    intro_text2 = (
        "With hands-on experience across Revit 2024 through 2026, I build tools that integrate "
        "seamlessly into the Revit ribbon and follow Autodesk's best practices. From automated "
        "data extraction and batch processing to AI-powered BIM assistants using named pipes IPC, "
        "I bring deep technical expertise to every project."
    )
    story.append(Paragraph(intro_text2, styles['CoverBody']))
    story.append(Spacer(1, 16))

    # Key highlights in a styled table
    highlights = [
        ["\u2022  Production-Ready C# Code", "\u2022  Revit 2024 / 2025 / 2026"],
        ["\u2022  Custom WPF/XAML Interfaces", "\u2022  Complete Source Code Included"],
        ["\u2022  Named Pipes IPC & AI Integration", "\u2022  Post-Delivery Support"],
    ]

    hl_style = ParagraphStyle(
        'HLStyle', fontName='Helvetica', fontSize=10.5,
        leading=14, textColor=TEXT_DARK
    )

    hl_data = []
    for row in highlights:
        hl_data.append([
            Paragraph(row[0], hl_style),
            Paragraph(row[1], hl_style),
        ])

    hl_table = Table(hl_data, colWidths=[page_width * 0.48, page_width * 0.48])
    hl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SOFT_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 1, ACCENT_BLUE),
        ('LINEBELOW', (0, -1), (-1, -1), 1, ACCENT_BLUE),
    ]))
    story.append(hl_table)

    story.append(PageBreak())


def build_services_page(story, styles, page_width):
    """Page 2: Services & Capabilities"""

    # Page header bar
    hdr = Table(
        [[Paragraph("Services & Capabilities", ParagraphStyle(
            'P2Hdr', fontName='Helvetica-Bold', fontSize=22, textColor=WHITE,
            leading=28, alignment=TA_LEFT
        ))]],
        colWidths=[page_width],
    )
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 16))

    # "What I Build" section
    story.append(Paragraph("What I Build", styles['SectionHeader']))
    story.append(HRFlowable(
        width="100%", thickness=1.5, color=ACCENT_BLUE,
        spaceAfter=10, spaceBefore=2
    ))

    services = [
        ("Custom Revit Add-ins",
         "Ribbon buttons, external commands, and custom panels integrated "
         "into the Revit interface following Autodesk best practices."),
        ("Workflow Automation",
         "Batch processing, automated data extraction, report generation, "
         "and repetitive task elimination."),
        ("Family & Parameter Management",
         "Shared parameter tools, family templates, batch family editing, "
         "and parameter management utilities."),
        ("AI Integration",
         "LLM-powered BIM assistants using named pipes IPC for real-time "
         "communication between AI models and Revit."),
        ("Dynamo Scripts & Custom Nodes",
         "Visual programming solutions and custom Python/C# nodes for "
         "complex computational design workflows."),
        ("WPF/XAML Dialogs & Custom UI",
         "Modern, polished user interfaces with data binding, validation, "
         "and intuitive user experiences."),
    ]

    svc_title_style = ParagraphStyle(
        'SvcTitle', fontName='Helvetica-Bold', fontSize=11,
        leading=14, textColor=DARK_BLUE
    )
    svc_desc_style = ParagraphStyle(
        'SvcDesc', fontName='Helvetica', fontSize=9.5,
        leading=13, textColor=TEXT_MED
    )

    svc_data = []
    for i, (title, desc) in enumerate(services):
        bullet = Paragraph(
            f'<font color="{ACCENT_BLUE.hexval()}">\u25A0</font>',
            ParagraphStyle('Bul', fontSize=12, leading=14, alignment=TA_CENTER)
        )
        content = [
            Paragraph(title, svc_title_style),
            Paragraph(desc, svc_desc_style),
        ]
        svc_data.append([bullet, content])

    svc_table = Table(svc_data, colWidths=[28, page_width - 40])
    svc_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 6),
        ('LEFTPADDING', (1, 0), (1, -1), 4),
        # Subtle row separators
        ('LINEBELOW', (1, 0), (1, -2), 0.3, BORDER_GRAY),
    ]))
    story.append(svc_table)
    story.append(Spacer(1, 20))

    # "Tech Stack" section
    story.append(Paragraph("Tech Stack", styles['SectionHeader']))
    story.append(HRFlowable(
        width="100%", thickness=1.5, color=ACCENT_BLUE,
        spaceAfter=12, spaceBefore=2
    ))

    tech_items = [
        "C#", ".NET Framework / .NET Core", "Revit API 2024\u20132026",
        "WPF / XAML", "Python", "Dynamo", "Named Pipes IPC", "Git / GitHub"
    ]

    tag_style = ParagraphStyle(
        'Tag', fontName='Helvetica-Bold', fontSize=10,
        textColor=MED_BLUE, alignment=TA_CENTER, leading=13,
    )

    # Build tag-like boxes in a table (2 rows x 4 cols)
    tag_rows = []
    row = []
    for i, tech in enumerate(tech_items):
        row.append(Paragraph(tech, tag_style))
        if len(row) == 4:
            tag_rows.append(row)
            row = []
    if row:
        while len(row) < 4:
            row.append("")
        tag_rows.append(row)

    col_w = (page_width - 20) / 4
    tag_table = Table(tag_rows, colWidths=[col_w] * 4)
    tag_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SOFT_BG),
        ('BOX', (0, 0), (-1, -1), 1, ACCENT_BLUE),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tag_table)

    story.append(PageBreak())


def build_tiers_page(story, styles, page_width):
    """Page 3: Service Tiers"""

    # Page header bar
    hdr = Table(
        [[Paragraph("Service Tiers", ParagraphStyle(
            'P3Hdr', fontName='Helvetica-Bold', fontSize=22, textColor=WHITE,
            leading=28, alignment=TA_LEFT
        ))]],
        colWidths=[page_width],
    )
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Choose the package that fits your needs. All tiers include source code and documentation.",
        ParagraphStyle('TierIntro', fontName='Helvetica', fontSize=11,
                       leading=15, textColor=TEXT_MED, alignment=TA_CENTER,
                       spaceAfter=16)
    ))

    # Draw three tier boxes side by side using a table with custom flowables
    box_w = (page_width - 24) / 3
    box_h = 310

    starter = TierBox(
        box_w, box_h,
        title="STARTER",
        price="$300",
        duration="5-day delivery",
        subtitle="Simple Add-in",
        features=[
            "Single-function Revit add-in",
            "Ribbon button integration",
            "Basic WPF dialog or form",
            "Source code + compiled DLL",
            ".addin manifest file",
            "Installation guide",
            "1 revision included",
        ],
        accent_color=TIER_GREEN,
    )

    standard = TierBox(
        box_w, box_h,
        title="STANDARD",
        price="$750",
        duration="14-day delivery",
        subtitle="Custom Plugin",
        features=[
            "Multi-feature Revit plugin",
            "Custom WPF dialog with MVVM",
            "Error handling & logging",
            "Source code + compiled DLL",
            "Technical documentation",
            "Revit 2024/2025/2026 support",
            "2 revisions included",
        ],
        accent_color=TIER_BLUE,
    )

    advanced = TierBox(
        box_w, box_h,
        title="ADVANCED",
        price="$1,500",
        duration="30-day delivery",
        subtitle="Full Solution",
        features=[
            "Complex plugin suite",
            "Custom UI with advanced UX",
            "API / service integration",
            "Named Pipes IPC support",
            "Comprehensive documentation",
            "30 days post-delivery support",
            "3 revisions included",
        ],
        accent_color=TIER_PURPLE,
    )

    tier_table = Table(
        [[starter, standard, advanced]],
        colWidths=[box_w + 4, box_w + 4, box_w + 4],
        rowHeights=[box_h + 10],
    )
    tier_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tier_table)

    story.append(Spacer(1, 20))

    # Note below tiers
    story.append(Paragraph(
        "Need something different? Custom quotes available for unique requirements. "
        "All prices are starting points \u2014 final pricing depends on project complexity.",
        ParagraphStyle('TierNote', fontName='Helvetica-Oblique', fontSize=9.5,
                       leading=14, textColor=TEXT_LIGHT, alignment=TA_CENTER,
                       leftIndent=30, rightIndent=30)
    ))

    # "Most Popular" badge-like indicator for Standard
    story.append(Spacer(1, 8))
    pop_table = Table(
        [[Paragraph(
            '\u2605  Standard tier is most popular for Revit automation projects  \u2605',
            ParagraphStyle('Pop', fontName='Helvetica-Bold', fontSize=10,
                           textColor=TIER_BLUE, alignment=TA_CENTER, leading=14)
        )]],
        colWidths=[page_width * 0.7],
    )
    pop_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#e8f0fe")),
        ('BOX', (0, 0), (-1, -1), 1, TIER_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    pop_table.hAlign = 'CENTER'
    story.append(pop_table)

    story.append(PageBreak())


def build_deliverables_page(story, styles, page_width):
    """Page 4: Deliverables, Process & Contact"""

    # Page header bar
    hdr = Table(
        [[Paragraph("What You Get & Process", ParagraphStyle(
            'P4Hdr', fontName='Helvetica-Bold', fontSize=22, textColor=WHITE,
            leading=28, alignment=TA_LEFT
        ))]],
        colWidths=[page_width],
    )
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 14))

    # Two-column layout: Deliverables | Process
    # -- Deliverables --
    del_title = Paragraph("Deliverables", ParagraphStyle(
        'DelTitle', fontName='Helvetica-Bold', fontSize=16,
        textColor=DARK_BLUE, leading=20, spaceAfter=8
    ))

    del_style = ParagraphStyle(
        'DelItem', fontName='Helvetica', fontSize=10.5,
        leading=15, textColor=TEXT_MED, leftIndent=14
    )
    del_bold = ParagraphStyle(
        'DelBold', fontName='Helvetica-Bold', fontSize=10.5,
        leading=15, textColor=TEXT_DARK, leftIndent=14
    )

    deliverables = [
        "Complete Visual Studio solution with source code",
        "Compiled DLL + .addin manifest file",
        "Installation guide and documentation",
        "Revit 2024 / 2025 / 2026 compatibility",
        "Post-delivery support and bug fixes",
        "Clean, well-commented, maintainable code",
    ]

    del_items = [del_title]
    del_items.append(HRFlowable(
        width="100%", thickness=1, color=ACCENT_BLUE,
        spaceAfter=10, spaceBefore=2
    ))
    for d in deliverables:
        del_items.append(Paragraph(
            f'<font color="{CHECK_COLOR.hexval()}">\u2713</font>  {d}',
            del_style
        ))
        del_items.append(Spacer(1, 3))

    # -- Process --
    proc_title = Paragraph("My Process", ParagraphStyle(
        'ProcTitle', fontName='Helvetica-Bold', fontSize=16,
        textColor=DARK_BLUE, leading=20, spaceAfter=8
    ))

    process_steps = [
        ("1", "Requirements Discussion",
         "Understand your workflow, pain points, and goals"),
        ("2", "Technical Design & Architecture",
         "Plan the solution structure and approach"),
        ("3", "Development with Regular Updates",
         "Build iteratively with progress check-ins"),
        ("4", "Testing in Target Revit Version",
         "Thorough testing in your Revit environment"),
        ("5", "Delivery with Documentation",
         "Compiled plugin, source code, and guides"),
        ("6", "Post-Delivery Support",
         "Bug fixes and assistance after handoff"),
    ]

    step_num_style = ParagraphStyle(
        'StepNum', fontName='Helvetica-Bold', fontSize=14,
        textColor=WHITE, alignment=TA_CENTER, leading=18
    )
    step_title_style = ParagraphStyle(
        'StepTitle', fontName='Helvetica-Bold', fontSize=10.5,
        textColor=TEXT_DARK, leading=14
    )
    step_desc_style = ParagraphStyle(
        'StepDesc', fontName='Helvetica', fontSize=9,
        textColor=TEXT_LIGHT, leading=12
    )

    proc_items = [proc_title]
    proc_items.append(HRFlowable(
        width="100%", thickness=1, color=ACCENT_BLUE,
        spaceAfter=10, spaceBefore=2
    ))

    step_rows = []
    for num, title, desc in process_steps:
        step_rows.append([
            Paragraph(num, step_num_style),
            [Paragraph(title, step_title_style),
             Paragraph(desc, step_desc_style)],
        ])

    step_table = Table(step_rows, colWidths=[30, page_width * 0.38])
    step_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), ACCENT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (0, -1), 2),
        ('LEFTPADDING', (1, 0), (1, -1), 8),
        ('LINEBELOW', (1, 0), (1, -2), 0.3, BORDER_GRAY),
    ]))
    proc_items.append(step_table)

    # Combine into two-column table
    two_col = Table(
        [[del_items, proc_items]],
        colWidths=[page_width * 0.50, page_width * 0.50],
    )
    two_col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LINEAFTER', (0, 0), (0, -1), 0.5, BORDER_GRAY),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 24))

    # Divider
    story.append(HRFlowable(
        width="80%", thickness=1, color=BORDER_GRAY,
        spaceAfter=16, spaceBefore=4, hAlign='CENTER'
    ))

    # Contact CTA
    cta_content = [
        [Paragraph(
            "Ready to automate your Revit workflow?",
            ParagraphStyle('CTA1', fontName='Helvetica-Bold', fontSize=16,
                           textColor=DARK_BLUE, alignment=TA_CENTER, leading=22)
        )],
        [Paragraph(
            "Let's discuss your project!",
            ParagraphStyle('CTA2', fontName='Helvetica', fontSize=13,
                           textColor=ACCENT_BLUE, alignment=TA_CENTER, leading=18)
        )],
        [Spacer(1, 8)],
        [Paragraph(
            "Message me on Upwork with your project details and I'll respond within 24 hours.",
            ParagraphStyle('CTA3', fontName='Helvetica', fontSize=10.5,
                           textColor=TEXT_MED, alignment=TA_CENTER, leading=15)
        )],
    ]

    cta_table = Table(cta_content, colWidths=[page_width * 0.75])
    cta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SOFT_BG),
        ('BOX', (0, 0), (-1, -1), 1.5, ACCENT_BLUE),
        ('TOPPADDING', (0, 0), (-1, 0), 16),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    cta_table.hAlign = 'CENTER'
    story.append(cta_table)

    story.append(Spacer(1, 16))

    # Bottom tagline
    story.append(Paragraph(
        "Weber Gouin  |  BIM Ops Studio  |  Custom Revit C# Plugin Development",
        ParagraphStyle('BottomTag', fontName='Helvetica-Bold', fontSize=9,
                       textColor=TEXT_LIGHT, alignment=TA_CENTER, leading=13)
    ))


# ── Main Build ─────────────────────────────────────────────────────────────

def main():
    page_w, page_h = letter
    margin = 36  # 0.5 inch margins

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=30,
        bottomMargin=36,
        title="Custom Revit Plugin Development Services",
        author="Weber Gouin - BIM Ops Studio",
        subject="Upwork Project Catalog - Revit C# Plugin Development",
    )

    usable_width = page_w - 2 * margin
    styles = build_styles()
    story = []

    build_cover_page(story, styles, usable_width)
    build_services_page(story, styles, usable_width)
    build_tiers_page(story, styles, usable_width)
    build_deliverables_page(story, styles, usable_width)

    doc.build(story, onFirstPage=footer_template, onLaterPages=footer_template)
    print(f"PDF generated successfully: {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH):,} bytes")


if __name__ == "__main__":
    main()
