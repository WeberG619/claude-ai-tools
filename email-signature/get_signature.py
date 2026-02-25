"""
Email signature helper for Weber Gouin.

Usage:
    python get_signature.py [plain|html|gmail_js]

If no argument is given, all three formats are printed.
"""

import json
import sys
from pathlib import Path


SIGNATURE_FILE = Path(__file__).parent / "signature.json"


def load_signature() -> dict:
    return json.loads(SIGNATURE_FILE.read_text())


def get_plain_text_signature(sig: dict | None = None) -> str:
    """Return a clean plain-text signature block."""
    if sig is None:
        sig = load_signature()

    lines = [
        sig["name"],
        f"{sig['title']} | {sig['company']}",
        sig["phone"],
        sig["emails"]["business"],
        sig["location"],
    ]

    if sig.get("website"):
        lines.append(sig["website"])

    return "\n".join(lines)


def get_html_signature(sig: dict | None = None) -> str:
    """Return a professional HTML signature for Gmail."""
    if sig is None:
        sig = load_signature()

    emails = sig["emails"]
    website_line = ""
    if sig.get("website"):
        website_line = f'<br><a href="{sig["website"]}" style="color:#1a73e8;text-decoration:none;">{sig["website"]}</a>'

    html = f"""<div style="font-family:Arial,sans-serif;font-size:13px;color:#333;line-height:1.5;max-width:480px;">
  <strong style="font-size:14px;color:#111;">{sig["name"]}</strong><br>
  <span style="color:#555;">{sig["title"]}</span>
  <span style="color:#999;"> &nbsp;|&nbsp; </span>
  <span style="color:#555;">{sig["company"]}</span><br>
  <br>
  <table style="border-collapse:collapse;font-size:12px;color:#555;">
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Phone</td>
      <td style="padding:1px 0;">{sig["phone"]}</td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Business</td>
      <td style="padding:1px 0;"><a href="mailto:{emails["business"]}" style="color:#1a73e8;text-decoration:none;">{emails["business"]}</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">BD Architect</td>
      <td style="padding:1px 0;"><a href="mailto:{emails["bdarchitect"]}" style="color:#1a73e8;text-decoration:none;">{emails["bdarchitect"]}</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">WG Design</td>
      <td style="padding:1px 0;"><a href="mailto:{emails["wgdesign"]}" style="color:#1a73e8;text-decoration:none;">{emails["wgdesign"]}</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Location</td>
      <td style="padding:1px 0;">{sig["location"]}</td>
    </tr>
  </table>{website_line}
</div>"""

    return html


def get_gmail_js_signature(sig: dict | None = None) -> str:
    """
    Return JavaScript that can be evaluated via CDP in a Gmail compose window
    to insert the HTML signature into the compose body.

    Targets the active compose window's editable body div.
    """
    if sig is None:
        sig = load_signature()

    html = get_html_signature(sig)

    # Escape backticks and backslashes for JS template literal
    html_escaped = html.replace("\\", "\\\\").replace("`", "\\`")

    js = f"""(function() {{
  // Find the active compose body (contenteditable div inside compose window)
  const composeBody = document.querySelector(
    '.aO7 .Am.Al.editable, ' +       // compose in window
    '.M9 .Am.Al.editable, ' +         // compose in tab
    '[contenteditable="true"][aria-label]'  // fallback
  );

  if (!composeBody) {{
    return 'ERROR: No compose body found. Open a compose window first.';
  }}

  const sigHtml = `<br><br>-- <br>{html_escaped}`;

  // Append to existing content, or set fresh
  if (composeBody.innerHTML.trim() === '' || composeBody.innerHTML === '<br>') {{
    composeBody.innerHTML = sigHtml;
  }} else {{
    composeBody.innerHTML += sigHtml;
  }}

  // Move cursor to top so user types above signature
  const range = document.createRange();
  const sel = window.getSelection();
  range.setStart(composeBody, 0);
  range.collapse(true);
  sel.removeAllRanges();
  sel.addRange(range);

  return 'Signature inserted successfully.';
}})();"""

    return js


def main():
    formats = {"plain", "html", "gmail_js"}
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if arg not in formats and arg != "all":
        print(f"Usage: python get_signature.py [plain|html|gmail_js]")
        print(f"       (no argument prints all formats)")
        sys.exit(1)

    sig = load_signature()

    if arg in ("plain", "all"):
        print("=" * 60)
        print("PLAIN TEXT")
        print("=" * 60)
        print(get_plain_text_signature(sig))
        print()

    if arg in ("html", "all"):
        print("=" * 60)
        print("HTML")
        print("=" * 60)
        print(get_html_signature(sig))
        print()

    if arg in ("gmail_js", "all"):
        print("=" * 60)
        print("GMAIL JS (CDP inject)")
        print("=" * 60)
        print(get_gmail_js_signature(sig))
        print()


if __name__ == "__main__":
    main()
