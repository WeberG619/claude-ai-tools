from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=20)

# Title
pdf.set_font("Helvetica", "B", 18)
pdf.cell(0, 10, "WEBER GOUIN", new_x="LMARGIN", new_y="NEXT", align="C")
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 6, "Sandpoint, ID | weber@bimopsstudio.com | (786) 587-9726", new_x="LMARGIN", new_y="NEXT", align="C")
pdf.ln(8)

def section_header(title):
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(0, 0, 0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

def bullet(text):
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "  -  " + text, new_x="LMARGIN", new_y="NEXT")

def bullet_long(text):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(15)
    pdf.multi_cell(180, 5, "- " + text)

# Professional Summary
section_header("PROFESSIONAL SUMMARY")
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 5, "Detail-oriented professional with expertise in BIM/Revit architecture, technical writing, data management, and AI-assisted content creation. Skilled in translating complex technical concepts into clear documentation. Proficient with AI tools including Claude, ChatGPT, and automation workflows. Strong analytical and problem-solving abilities with experience in construction documentation, data entry, and content production.")
pdf.ln(4)

# Skills
section_header("SKILLS")
skills = [
    "Technical Writing and Documentation",
    "Content Writing and Editing",
    "Proofreading and Quality Assurance",
    "Data Entry and Spreadsheet Management (Excel, Google Sheets)",
    "AI Tools: Claude, ChatGPT, Prompt Engineering",
    "BIM/Revit Architecture and Construction Documents",
    "Research and Analysis",
    "PDF/CAD Conversion and Document Processing",
    "Python Scripting and Automation",
    "Project Coordination"
]
for skill in skills:
    bullet(skill)
pdf.ln(4)

# Experience
section_header("EXPERIENCE")

pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "BIM Ops Studio | Principal / BIM Specialist", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 5, "2024 - Present", new_x="LMARGIN", new_y="NEXT")
for item in [
    "Develop and manage Building Information Models (BIM) for architectural projects using Autodesk Revit",
    "Produce construction document sets including floor plans, elevations, sections, and details",
    "Coordinate with architects and engineers on multi-discipline projects",
    "Create technical documentation and project specifications",
    "Automate workflows using Python scripting and AI integration"
]:
    bullet_long(item)
pdf.ln(2)

pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Architectural Drafter / Technical Professional", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 5, "2020 - 2024", new_x="LMARGIN", new_y="NEXT")
for item in [
    "Prepared architectural drawings and construction documents",
    "Performed quality assurance reviews on document sets",
    "Managed project data and maintained organized file systems",
    "Wrote technical reports and project documentation"
]:
    bullet_long(item)
pdf.ln(2)

pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Content and Data Professional | Freelance", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 5, "2018 - Present", new_x="LMARGIN", new_y="NEXT")
for item in [
    "Create professional content using AI-assisted workflows",
    "Perform data entry, spreadsheet management, and document formatting",
    "Proofread and edit documents for accuracy and clarity",
    "Research and compile information for various projects",
    "Write scripts, articles, and marketing content"
]:
    bullet_long(item)
pdf.ln(4)

# Education
section_header("EDUCATION")
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Architecture and Building Technology", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 5, "Professional Development in BIM, Revit, and Construction Documentation", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# Tools
section_header("TOOLS AND TECHNOLOGY")
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 5, "Autodesk Revit | AutoCAD | Microsoft Office Suite | Google Workspace | Python | AI/ML Tools (Claude, ChatGPT) | Adobe Acrobat | Bluebeam Revu | Project Management Software")

output_path = "/mnt/d/_CLAUDE-TOOLS/Weber_Gouin_Resume.pdf"
pdf.output(output_path)
print(f"PDF created: {output_path}")
