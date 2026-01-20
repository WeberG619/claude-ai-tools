#!/usr/bin/env python3
"""
Create a professional PDF whitepaper about the MCP Bridge technology.
Universal AI-to-software integration platform by BIM Ops Studio.
"""

from fpdf import FPDF
from pathlib import Path

class BridgePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'MCP Bridge Technology - Universal AI Integration', align='C', new_x='LMARGIN', new_y='NEXT')
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def add_title(self, title, size=16):
        self.set_font('Helvetica', 'B', size)
        self.set_text_color(0, 82, 147)
        self.cell(0, 12, title, new_x='LMARGIN', new_y='NEXT')
        self.ln(4)

    def add_section(self, title):
        self.set_x(self.l_margin)  # Reset to left margin
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 10, title)  # Use multi_cell to handle long titles
        self.ln(2)

    def add_text(self, text):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def add_bullet(self, text):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        bullet = '  ' + chr(149) + ' ' + text
        self.multi_cell(0, 6, bullet)

    def add_code(self, text):
        self.set_x(self.l_margin)
        self.set_font('Courier', '', 9)
        self.set_fill_color(245, 245, 245)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(5)

    def add_qa(self, question, answer):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 82, 147)
        self.multi_cell(0, 6, 'Q: ' + question)
        self.set_x(self.l_margin)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, 'A: ' + answer)
        self.ln(3)


def create_whitepaper():
    pdf = BridgePDF()
    pdf.set_margins(25, 25, 25)

    # ===== COVER PAGE =====
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(0, 82, 147)
    pdf.cell(0, 15, 'MCP Bridge', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.set_font('Helvetica', '', 18)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, 'Universal AI Integration Platform', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(15)

    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7, (
        'Connect Claude AI to any software with an API. Real-time bidirectional '
        'communication enables autonomous workflows, intelligent automation, '
        'and voice-driven control across your entire software ecosystem.'
    ), align='C')

    pdf.ln(30)

    # Key stats
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 82, 147)
    pdf.cell(0, 10, 'Any Software  |  Any API  |  One AI Assistant', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(50)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, 'Technical Whitepaper', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, 'BIM Ops Studio', align='C', new_x='LMARGIN', new_y='NEXT')

    # ===== PAGE 2: EXECUTIVE SUMMARY =====
    pdf.add_page()
    pdf.add_title('Executive Summary')

    pdf.add_text(
        'MCP Bridge is a universal integration platform that connects Claude AI to any '
        'software application through its API. Using the Model Context Protocol (MCP), '
        'this technology creates a real-time bidirectional communication channel between '
        'AI and your existing software tools.')

    pdf.add_text(
        'The platform is application-agnostic. If a software has an API, MCP Bridge can '
        'connect to it. This means the same AI assistant that controls your CAD software '
        'can also manage your project management tools, communicate with your databases, '
        'automate your document workflows, and integrate with any custom applications.')

    pdf.add_section('Proven at Scale')
    pdf.add_text(
        'This is not theoretical. MCP Bridge currently connects 13+ applications including '
        'Revit (705 methods), AutoCAD, Bluebeam, PostgreSQL, browser automation, voice '
        'synthesis, AI rendering, and more. Over 850 methods are in production use.')

    pdf.add_section('Key Capabilities')
    pdf.add_bullet('Universal Connectivity: Works with any software that has an API')
    pdf.add_bullet('Real-Time Control: Bidirectional communication for instant response')
    pdf.add_bullet('Domain Knowledge: Embed industry expertise into AI workflows')
    pdf.add_bullet('Progressive Autonomy: From simple queries to full automation')
    pdf.add_bullet('Voice-Driven Workflow: Hands-free operation via voice commands')
    pdf.add_bullet('Persistent Memory: AI remembers context across sessions')

    pdf.add_section('The Problem We Solve')
    pdf.add_text(
        'Software automation today is fragmented. Each application needs separate scripts, '
        'different programming languages, and specialized knowledge. Teams spend more time '
        'maintaining automation than benefiting from it. MCP Bridge changes this - one AI '
        'assistant handles all your software, speaking natural language instead of code.')

    # ===== PAGE 3: HOW IT WORKS =====
    pdf.add_page()
    pdf.add_title('How It Works')

    pdf.add_section('The Bridge Architecture')
    pdf.add_text('MCP Bridge creates a communication layer between AI and software:')

    pdf.add_code(
        '  +------------------+\n'
        '  |    Claude AI     |  <- Natural Language Understanding\n'
        '  +--------+---------+\n'
        '           |\n'
        '           | Model Context Protocol (MCP)\n'
        '           v\n'
        '  +------------------+\n'
        '  |   MCP Bridge     |  <- Translation Layer\n'
        '  +--------+---------+\n'
        '           |\n'
        '           | Native API Calls\n'
        '           v\n'
        '  +------------------+\n'
        '  | Target Software  |  <- Any Application with API\n'
        '  +------------------+')

    pdf.add_section('Communication Methods')
    pdf.add_text('The bridge supports multiple communication protocols:')
    pdf.add_bullet('Named Pipes: For local Windows applications (fastest, sub-millisecond)')
    pdf.add_bullet('REST API: For web services and cloud applications')
    pdf.add_bullet('WebSocket: For real-time bidirectional communication')
    pdf.add_bullet('gRPC: For high-performance service-to-service calls')

    pdf.add_section('How Translation Works')
    pdf.add_text(
        'When you say "create a report from last week\'s data," the bridge:')
    pdf.add_bullet('1. Parses your natural language request')
    pdf.add_bullet('2. Identifies which applications are needed')
    pdf.add_bullet('3. Converts to specific API calls for each application')
    pdf.add_bullet('4. Executes calls in the correct sequence')
    pdf.add_bullet('5. Aggregates results and reports back in plain language')

    # ===== PAGE 4: TECHNICAL DEEP DIVE =====
    pdf.add_page()
    pdf.add_title('Technical Deep Dive')

    pdf.add_section('What is MCP?')
    pdf.add_text(
        'Model Context Protocol (MCP) is an open standard developed by Anthropic for '
        'connecting AI models to external tools and data sources. It provides a '
        'standardized way for AI to discover available tools, understand their '
        'capabilities, and invoke them with proper parameters.')

    pdf.add_section('Bridge Components')
    pdf.add_text('Each bridge implementation consists of three parts:')

    pdf.add_bullet('Method Registry: Catalog of all available operations (e.g., "createDocument", '
                   '"queryDatabase", "sendEmail"). Each method has defined parameters and return types.')

    pdf.add_bullet('API Translator: Converts method calls into native API format. For a CAD '
                   'application, this might convert "drawLine(0,0,10,10)" into the specific '
                   'API syntax that application expects.')

    pdf.add_bullet('Response Handler: Processes results from the target application, handles '
                   'errors gracefully, and formats responses for AI understanding.')

    pdf.add_section('Transaction Safety')
    pdf.add_text(
        'All operations that modify data are wrapped in transactions. This means:')
    pdf.add_bullet('Atomic Operations: Changes either complete fully or not at all')
    pdf.add_bullet('Rollback Support: Failed operations can be undone automatically')
    pdf.add_bullet('Conflict Prevention: Only one modification operation runs at a time')
    pdf.add_bullet('Undo Integration: AI-made changes appear in application undo history')

    # ===== PAGE 5: PROVEN INTEGRATIONS =====
    pdf.add_page()
    pdf.add_title('Proven Integrations')

    pdf.add_text(
        'These integrations are not theoretical - they are built, tested, and working '
        'in production environments. Each represents a complete MCP bridge with full '
        'API coverage.')

    pdf.add_section('Active Production Bridges')

    proven_apps = [
        ('Autodesk Revit', '705 methods', 'Full BIM automation - walls, doors, rooms, schedules, sheets, views, families, parameters, MEP, structural, annotations'),
        ('Autodesk AutoCAD', '50+ methods', 'Drawing automation, layer management, block operations, coordinate extraction'),
        ('Bluebeam Revu', '15+ methods', 'PDF markup, document control, screenshot capture, navigation'),
        ('PostgreSQL', '20+ methods', 'Database queries, schema inspection, data import/export with PostGIS support'),
        ('SQLite', '10+ methods', 'Local database operations, query execution, table management'),
        ('Browser Control', '30+ methods', 'Chrome/Edge automation via Playwright - navigation, screenshots, form filling'),
    ]

    for app_name, method_count, description in proven_apps:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 82, 147)
        pdf.cell(0, 6, f'{app_name} ({method_count})', new_x='LMARGIN', new_y='NEXT')
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, description)
        pdf.ln(1)

    pdf.add_section('Supporting Services')
    support_services = [
        ('Voice Synthesis', 'Text-to-speech with multiple voices for hands-free feedback'),
        ('AI Rendering', 'Stable Diffusion integration for architectural visualization'),
        ('PDF Processing', 'Extract text, analyze floor plans, generate summaries'),
        ('Email Automation', 'Send notifications, process incoming messages'),
        ('Git/GitHub', 'Version control, commit automation, PR management'),
        ('Local LLMs', 'Ollama orchestration for offline AI processing'),
        ('Persistent Memory', 'Cross-session context, corrections, learned preferences'),
    ]

    for service, desc in support_services:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(0, 82, 147)
        pdf.cell(42, 5, service + ':', new_x='RIGHT')
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(80, 80, 80)
        remaining_width = pdf.w - pdf.get_x() - pdf.r_margin
        pdf.multi_cell(remaining_width, 5, desc)

    # ===== PAGE 6: ADDING MORE =====
    pdf.add_page()
    pdf.add_title('Expanding the Ecosystem')

    pdf.add_text(
        'The bridge architecture makes adding new applications straightforward. '
        'Once you understand the pattern, new integrations follow the same structure.')

    pdf.add_section('Ready to Connect')
    pdf.add_text('These applications have documented APIs and can be integrated:')

    ready_apps = [
        ('Microsoft Office', 'COM Interop - Word, Excel, PowerPoint automation'),
        ('Docker', 'REST API - container management, deployment orchestration'),
        ('OBS Studio', 'WebSocket API - streaming control, scene switching'),
        ('LM Studio', 'OpenAI-compatible REST - local model inference'),
        ('Procore', 'REST API - construction project management'),
        ('Asana/Monday', 'REST API - task and project tracking'),
    ]

    for app, api_desc in ready_apps:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(38, 5, app + ':', new_x='RIGHT')
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(80, 80, 80)
        remaining_width = pdf.w - pdf.get_x() - pdf.r_margin
        pdf.multi_cell(remaining_width, 5, api_desc)

    pdf.add_section('Adding New Applications')
    pdf.add_text('To connect a new application, you need:')
    pdf.add_bullet('API Documentation: Understanding of available endpoints')
    pdf.add_bullet('Authentication Setup: API keys, OAuth tokens, or credentials')
    pdf.add_bullet('Method Definitions: List of operations you want to expose')
    pdf.add_bullet('Knowledge Files: Domain expertise for intelligent operation')

    pdf.add_text(
        'Once configured, the new application becomes part of your AI-powered workflow '
        'immediately. No retraining required - Claude understands new capabilities as '
        'soon as they are registered.')

    pdf.add_section('Integration Timeline')
    pdf.add_bullet('Simple REST API: 1-2 days (well-documented endpoints)')
    pdf.add_bullet('Desktop application SDK: 1-2 weeks (COM/native API)')
    pdf.add_bullet('Complex enterprise system: 2-4 weeks (authentication, workflows)')

    # ===== PAGE 6: AUTONOMY LEVELS =====
    pdf.add_page()
    pdf.add_title('5 Levels of Autonomy')

    pdf.add_text('Choose how much control to delegate to AI. Start conservative, '
                 'increase autonomy as trust builds.')

    levels = [
        ('Level 1: Query Only',
         'AI reads data but cannot modify anything. Safe for exploring capabilities.',
         'Example: "What projects are overdue?" "Show me all invoices over $10,000"'),

        ('Level 2: Confirm Each Action',
         'AI proposes actions one at a time. You approve or reject each.',
         'Example: "Update this record?" -> You click Approve -> AI executes'),

        ('Level 3: Batch with Approval',
         'AI plans multiple actions, shows you the full plan, you approve once.',
         'Example: "Here are 47 records to update. Approve all?" -> One click'),

        ('Level 4: Rules-Based Automation',
         'AI follows defined rules without asking. Good for routine tasks.',
         'Example: "Every Monday, generate and email the weekly report"'),

        ('Level 5: Full Autonomy',
         'AI makes judgment calls based on domain knowledge and learned patterns.',
         'Example: "Keep the project on track" -> AI handles issues as they arise'),
    ]

    for level_name, description, example in levels:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 82, 147)
        pdf.cell(0, 7, level_name, new_x='LMARGIN', new_y='NEXT')
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 5, description)
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, example)
        pdf.ln(2)

    # ===== PAGE 7: DOMAIN KNOWLEDGE =====
    pdf.add_page()
    pdf.add_title('Domain Knowledge System')

    pdf.add_text(
        'Generic AI knows general information. MCP Bridge includes specialized '
        'knowledge files that make AI an expert in YOUR industry.')

    pdf.add_section('How Knowledge Files Work')
    pdf.add_text(
        'Knowledge files are structured documents (typically Markdown) that contain:')
    pdf.add_bullet('Industry standards and codes (building codes, regulations, compliance)')
    pdf.add_bullet('Best practices and proven workflows')
    pdf.add_bullet('Terminology definitions and context')
    pdf.add_bullet('Common errors and how to avoid them')
    pdf.add_bullet('Organization-specific preferences and standards')

    pdf.add_section('Example: Architecture Knowledge')
    pdf.add_text('For an architecture firm, knowledge files might include:')
    pdf.add_bullet('Building code requirements by jurisdiction')
    pdf.add_bullet('Standard room sizes and clearances')
    pdf.add_bullet('ADA accessibility requirements')
    pdf.add_bullet('Construction document standards')
    pdf.add_bullet('Typical wall assemblies and their applications')

    pdf.add_section('Continuous Learning')
    pdf.add_text(
        'The memory system captures corrections and new information over time:')
    pdf.add_bullet('When you correct AI, the correction is stored permanently')
    pdf.add_bullet('Future sessions automatically load relevant corrections')
    pdf.add_bullet('AI learns your preferences and working style')
    pdf.add_bullet('Patterns from your projects become part of the knowledge base')

    # ===== PAGE 8: VOICE WORKFLOW =====
    pdf.add_page()
    pdf.add_title('Voice-Driven Workflow')

    pdf.add_text(
        'Control your entire software ecosystem by speaking naturally. No memorizing '
        'commands, no typing, no switching between applications.')

    pdf.add_section('Voice Input Capabilities')
    pdf.add_bullet('Natural language understanding - speak as you would to a colleague')
    pdf.add_bullet('Industry vocabulary recognition - technical terms understood correctly')
    pdf.add_bullet('Context awareness - AI remembers what you were working on')
    pdf.add_bullet('Multi-step requests - complex workflows from single sentences')
    pdf.add_bullet('Clarification requests - AI asks for details when needed')

    pdf.add_section('Audio Feedback')
    pdf.add_bullet('Spoken summaries after completing tasks')
    pdf.add_bullet('Progress updates during long operations')
    pdf.add_bullet('Error notifications with suggested solutions')
    pdf.add_bullet('Confirmation requests before major changes')

    pdf.add_section('Real-World Use Cases')
    pdf.add_text('Voice control is ideal when:')
    pdf.add_bullet('Hands are occupied (reviewing drawings, site visits, driving)')
    pdf.add_bullet('Eyes are on other work (reviewing documents, in meetings)')
    pdf.add_bullet('Speed matters (quick queries faster than typing)')
    pdf.add_bullet('Accessibility needs (users who benefit from voice interaction)')

    # ===== PAGE 9: ECOSYSTEM =====
    pdf.add_page()
    pdf.add_title('Complete Ecosystem')

    pdf.add_text('MCP Bridge is part of a larger automation platform:')

    integrations = [
        ('Persistent Memory', 'Every decision, correction, and preference is stored. '
         'AI maintains context across sessions, days, even months.'),
        ('System Awareness', 'AI knows what applications you have open, what files '
         'you are working on, and can proactively offer assistance.'),
        ('Document Vision', 'AI can see and understand documents - PDFs, images, '
         'screenshots. Extract data visually, not just from structured files.'),
        ('Multi-App Workflows', 'Chain operations across applications. Pull data '
         'from one system, transform it, push to another - all in one request.'),
    ]

    for name, description in integrations:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 82, 147)
        pdf.cell(0, 7, name, new_x='LMARGIN', new_y='NEXT')
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, description)
        pdf.ln(2)

    pdf.add_section('Extensibility')
    pdf.add_text(
        'The architecture is designed for growth. Adding new applications follows '
        'a consistent pattern - create the API translation layer, add domain '
        'knowledge, and register the methods. The new capabilities immediately '
        'become available to AI.')

    # ===== PAGE 10: EXAMPLES =====
    pdf.add_page()
    pdf.add_title('Real-World Examples')

    pdf.add_section('Example 1: Cross-Application Workflow')
    pdf.add_code(
        'User: "Generate the monthly client report for Project Alpha"\n\n'
        'AI Actions:\n'
        '  1. Query project management system for task completion rates\n'
        '  2. Pull budget data from accounting system\n'
        '  3. Get recent changes from CAD/BIM model\n'
        '  4. Compile into report template\n'
        '  5. Generate PDF and email to client contacts\n\n'
        'Time: 2 minutes (vs 45 minutes manually)')

    pdf.add_section('Example 2: Document Processing')
    pdf.add_code(
        'User: "Extract all dimensions from this floor plan PDF and \n'
        '       create a takeoff spreadsheet"\n\n'
        'AI Actions:\n'
        '  1. Analyze PDF visually to identify dimension annotations\n'
        '  2. Extract dimension values and their associated elements\n'
        '  3. Create spreadsheet with columns for item, dimension, area\n'
        '  4. Calculate totals and summary statistics\n'
        '  5. Format and save to project folder\n\n'
        'Time: 3 minutes (vs 2 hours manually)')

    pdf.add_section('Example 3: Quality Control')
    pdf.add_code(
        'User: "Check the model for code compliance issues"\n\n'
        'AI Actions:\n'
        '  1. Query all doors and check clearances against ADA requirements\n'
        '  2. Verify corridor widths meet egress requirements\n'
        '  3. Check stair dimensions against building code\n'
        '  4. Generate report listing all issues with element IDs\n'
        '  5. Suggest corrections for each issue found\n\n'
        'Result: 23 issues identified, 18 auto-correctable')

    # ===== PAGE 11: FAQ =====
    pdf.add_page()
    pdf.add_title('Frequently Asked Questions')

    pdf.add_qa(
        'What applications can MCP Bridge connect to?',
        'Any application with an API. This includes desktop software with SDK/API access, '
        'web applications with REST APIs, databases with query interfaces, and cloud '
        'services. If it has documented programmatic access, we can connect to it.')

    pdf.add_qa(
        'Is my data sent to the cloud?',
        'Communication between AI and your applications happens locally on your machine. '
        'Your data stays within your network. The AI model (Claude) processes requests, '
        'but sensitive data can be configured to stay local.')

    pdf.add_qa(
        'How long does it take to set up a new integration?',
        'Simple integrations (REST APIs with good documentation) can be set up in a day. '
        'Complex integrations (desktop applications with SDK) take 1-2 weeks. Once set up, '
        'maintenance is minimal.')

    pdf.add_qa(
        'What happens if AI makes a mistake?',
        'All modifications are transactional and can be undone. The system maintains '
        'full audit trails. AI operations appear in application undo history. For '
        'critical operations, you can require approval before execution.')

    pdf.add_qa(
        'Can I customize what AI is allowed to do?',
        'Yes. Autonomy levels are configurable per application and per operation type. '
        'You can allow read-only access to some systems while enabling full automation '
        'on others. Permissions are granular.')

    pdf.add_qa(
        'How does voice control work?',
        'Voice input uses speech recognition to convert your words to text, which AI '
        'then interprets. Voice output uses text-to-speech to read responses aloud. '
        'Both work with standard microphones and speakers.')

    # ===== PAGE 13: SUMMARY =====
    pdf.add_page()
    pdf.add_title('Summary')

    pdf.add_text(
        'MCP Bridge technology enables a new way of working with software. Instead of '
        'learning each application\'s interface, maintaining separate automation scripts, '
        'and context-switching between tools, you have one AI assistant that understands '
        'them all.')

    pdf.add_section('Current Scale')
    scale_stats = [
        ('Connected Apps', '13+ applications in production'),
        ('Total Methods', '850+ API methods available'),
        ('Revit Coverage', '705 methods across 25 categories'),
        ('Knowledge Base', '113 domain expertise files'),
    ]
    for stat_label, stat_value in scale_stats:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 82, 147)
        pdf.cell(40, 6, stat_label + ':')
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 6, stat_value, new_x='LMARGIN', new_y='NEXT')

    pdf.ln(3)
    pdf.add_section('Key Benefits')
    pdf.add_bullet('Universal Connectivity: One integration approach for all applications')
    pdf.add_bullet('Natural Language: Speak or type requests in plain English')
    pdf.add_bullet('Domain Expertise: AI understands your industry, not just generic tasks')
    pdf.add_bullet('Progressive Trust: Start conservative, increase autonomy over time')
    pdf.add_bullet('Continuous Learning: System improves from corrections and patterns')
    pdf.add_bullet('Voice Control: Hands-free operation for maximum productivity')

    pdf.add_section('Technical Foundation')
    specs = [
        ('Protocol', 'Model Context Protocol (MCP) - Open Standard'),
        ('Communication', 'Named Pipes, REST, WebSocket, gRPC'),
        ('AI Model', 'Claude by Anthropic'),
        ('Extensibility', 'Any application with API access'),
    ]

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(60, 60, 60)
    for label, value in specs:
        pdf.cell(40, 6, label + ':')
        pdf.cell(0, 6, value, new_x='LMARGIN', new_y='NEXT')

    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 82, 147)
    pdf.cell(0, 8, 'If it has an API, we can connect to it.', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(10)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'BIM Ops Studio', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, 'www.bimopsstudio.com', align='C', new_x='LMARGIN', new_y='NEXT')

    # Save
    output_path = Path('/mnt/d/_CLAUDE-TOOLS/heygen-mcp/MCP_Bridge_Whitepaper.pdf')
    pdf.output(str(output_path))
    return output_path


if __name__ == '__main__':
    output = create_whitepaper()
    print(f"Created: {output}")
    print(f"Size: {output.stat().st_size / 1024:.1f} KB")
