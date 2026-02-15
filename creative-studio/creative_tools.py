"""
Creative Tools - Integrations for the Creative Studio
======================================================
Tools for creating presentations, documents, and content:
- Slide deck generation
- Document creation
- Content export (HTML, Markdown, PDF-ready)
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# Output directory for creative work
OUTPUT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/creative-studio/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SlideBuilder:
    """Build presentation slides in various formats."""

    def __init__(self, title: str = "Untitled Presentation"):
        self.title = title
        self.slides = []
        self.theme = {
            "primary_color": "#2C3E50",
            "accent_color": "#3498DB",
            "background": "#FFFFFF",
            "font_title": "Arial Black",
            "font_body": "Arial"
        }

    def add_slide(self, title: str, content: List[str] = None,
                  layout: str = "title-content", notes: str = "",
                  image_desc: str = None):
        """Add a slide to the deck."""
        slide = {
            "number": len(self.slides) + 1,
            "title": title,
            "content": content or [],
            "layout": layout,  # title-only, title-content, two-column, image-focus
            "notes": notes,
            "image_description": image_desc
        }
        self.slides.append(slide)
        return slide

    def set_theme(self, primary: str = None, accent: str = None,
                  background: str = None):
        """Set presentation theme colors."""
        if primary:
            self.theme["primary_color"] = primary
        if accent:
            self.theme["accent_color"] = accent
        if background:
            self.theme["background"] = background

    def to_html(self) -> str:
        """Export as HTML presentation."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: {self.theme['font_body']}, sans-serif; background: #1a1a2e; }}
        .slide {{
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 80px;
            background: {self.theme['background']};
            page-break-after: always;
        }}
        .slide h1 {{
            font-family: {self.theme['font_title']}, sans-serif;
            font-size: 3em;
            color: {self.theme['primary_color']};
            margin-bottom: 40px;
        }}
        .slide ul {{
            font-size: 1.5em;
            line-height: 1.8;
            color: #333;
        }}
        .slide li {{
            margin-bottom: 15px;
            padding-left: 20px;
        }}
        .slide li::marker {{
            color: {self.theme['accent_color']};
        }}
        .slide-number {{
            position: absolute;
            bottom: 20px;
            right: 40px;
            font-size: 0.9em;
            color: #999;
        }}
        .image-placeholder {{
            background: linear-gradient(135deg, {self.theme['accent_color']}22, {self.theme['primary_color']}22);
            border: 2px dashed {self.theme['accent_color']};
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            color: {self.theme['accent_color']};
            margin-top: 30px;
        }}
    </style>
</head>
<body>
"""
        for slide in self.slides:
            html += f"""
    <div class="slide">
        <h1>{slide['title']}</h1>
"""
            if slide['content']:
                html += "        <ul>\n"
                for item in slide['content']:
                    html += f"            <li>{item}</li>\n"
                html += "        </ul>\n"

            if slide['image_description']:
                html += f"""        <div class="image-placeholder">
            📷 {slide['image_description']}
        </div>
"""
            html += f"""        <div class="slide-number">{slide['number']}</div>
    </div>
"""
        html += """</body>
</html>"""
        return html

    def to_markdown(self) -> str:
        """Export as Markdown."""
        md = f"# {self.title}\n\n"
        for slide in self.slides:
            md += f"---\n\n## {slide['title']}\n\n"
            if slide['content']:
                for item in slide['content']:
                    md += f"- {item}\n"
                md += "\n"
            if slide['image_description']:
                md += f"*[Image: {slide['image_description']}]*\n\n"
            if slide['notes']:
                md += f"> Speaker notes: {slide['notes']}\n\n"
        return md

    def save(self, name: str = None) -> Dict[str, str]:
        """Save presentation in multiple formats."""
        name = name or self.title.lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{name}_{timestamp}"

        paths = {}

        # Save HTML
        html_path = OUTPUT_DIR / f"{base_name}.html"
        with open(html_path, 'w') as f:
            f.write(self.to_html())
        paths['html'] = str(html_path)

        # Save Markdown
        md_path = OUTPUT_DIR / f"{base_name}.md"
        with open(md_path, 'w') as f:
            f.write(self.to_markdown())
        paths['markdown'] = str(md_path)

        # Save JSON (for editing)
        json_path = OUTPUT_DIR / f"{base_name}.json"
        with open(json_path, 'w') as f:
            json.dump({
                "title": self.title,
                "theme": self.theme,
                "slides": self.slides
            }, f, indent=2)
        paths['json'] = str(json_path)

        return paths


class ContentGenerator:
    """Generate various content types."""

    @staticmethod
    def create_outline(topic: str, sections: int = 5) -> Dict:
        """Create a content outline structure."""
        return {
            "topic": topic,
            "sections": [{"number": i+1, "title": "", "points": []} for i in range(sections)],
            "created": datetime.now().isoformat()
        }

    @staticmethod
    def create_script(title: str, duration_minutes: int = 5) -> Dict:
        """Create a presentation script structure."""
        return {
            "title": title,
            "duration": duration_minutes,
            "sections": [],
            "word_count_target": duration_minutes * 150,  # ~150 words per minute
            "created": datetime.now().isoformat()
        }

    @staticmethod
    def save_content(content: str, filename: str, format: str = "md") -> str:
        """Save content to file."""
        path = OUTPUT_DIR / f"{filename}.{format}"
        with open(path, 'w') as f:
            f.write(content)
        return str(path)


class CreativeBridge:
    """Main bridge connecting agents to creative tools."""

    def __init__(self):
        self.current_presentation = None
        self.action_log = []

    def start_presentation(self, title: str) -> Dict:
        """Start a new presentation."""
        self.current_presentation = SlideBuilder(title)
        self._log_action("start_presentation", {"title": title})
        return {"success": True, "title": title}

    def add_slide(self, title: str, content: List[str] = None,
                  layout: str = "title-content", notes: str = "",
                  image_desc: str = None) -> Dict:
        """Add a slide to current presentation."""
        if not self.current_presentation:
            return {"success": False, "error": "No presentation started"}

        slide = self.current_presentation.add_slide(
            title, content, layout, notes, image_desc
        )
        self._log_action("add_slide", slide)
        return {"success": True, "slide": slide}

    def set_theme(self, primary: str = None, accent: str = None,
                  background: str = None) -> Dict:
        """Set presentation theme."""
        if not self.current_presentation:
            return {"success": False, "error": "No presentation started"}

        self.current_presentation.set_theme(primary, accent, background)
        self._log_action("set_theme", {"primary": primary, "accent": accent})
        return {"success": True, "theme": self.current_presentation.theme}

    def save_presentation(self, name: str = None) -> Dict:
        """Save the current presentation."""
        if not self.current_presentation:
            return {"success": False, "error": "No presentation started"}

        paths = self.current_presentation.save(name)
        self._log_action("save_presentation", paths)
        return {"success": True, "paths": paths}

    def get_presentation_preview(self) -> Dict:
        """Get preview of current presentation."""
        if not self.current_presentation:
            return {"success": False, "error": "No presentation started"}

        return {
            "success": True,
            "title": self.current_presentation.title,
            "slide_count": len(self.current_presentation.slides),
            "slides": self.current_presentation.slides,
            "theme": self.current_presentation.theme
        }

    def open_in_browser(self) -> Dict:
        """Open the presentation in browser."""
        if not self.current_presentation:
            return {"success": False, "error": "No presentation started"}

        paths = self.current_presentation.save()
        html_path = paths['html']

        try:
            # Open in Chrome
            cmd = f'Start-Process "chrome.exe" -ArgumentList "{html_path}"'
            if _HAS_BRIDGE:
                _ps_bridge(cmd, timeout=10)
            else:
                subprocess.run(
                    ["powershell.exe", "-Command", cmd],
                    timeout=10
                )
            return {"success": True, "path": html_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_action(self, action: str, details: Dict):
        """Log an action."""
        self.action_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        })

    def get_action_log(self, limit: int = 10) -> List[Dict]:
        """Get recent actions."""
        return self.action_log[-limit:]


# Quick test
if __name__ == "__main__":
    bridge = CreativeBridge()

    # Create a sample presentation
    bridge.start_presentation("AI Automation for Architecture")

    bridge.add_slide(
        "The Future of BIM",
        ["AI-powered model generation", "Automated documentation", "Real-time collaboration"],
        notes="Start with the vision"
    )

    bridge.add_slide(
        "Current Challenges",
        ["Manual data entry", "Repetitive tasks", "Coordination overhead"],
        image_desc="Frustrated architect at computer"
    )

    bridge.add_slide(
        "Our Solution",
        ["Intelligent automation", "Voice-controlled workflows", "AI agent teams"],
        notes="This is the hook"
    )

    result = bridge.save_presentation("bim_automation_pitch")
    print(f"Presentation saved: {result}")
