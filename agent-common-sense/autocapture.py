"""
Auto-capture corrections from conversation text.

Parses conversation transcripts for correction patterns, extracts
what-was-wrong and what-to-do-instead, and stores them through
the Common Sense Engine with validation and deduplication.

Supports:
  - Real-time mode: called from a Claude Code hook on each user message
  - Batch mode: scan a full conversation transcript for corrections
  - Pattern-based extraction: regex patterns for common correction phrases
  - Structured extraction: handles "Wrong: X / Right: Y" format

Usage:
    from autocapture import CorrectionCapture

    cap = CorrectionCapture(db_path)

    # Real-time: check a single user message
    result = cap.check_message("No, that's wrong. The path is /opt/app-v2")

    # Batch: scan a full transcript
    results = cap.scan_transcript(transcript_text)

CLI:
    echo '{"user_prompt": "No that is wrong..."}' | python autocapture.py
    python autocapture.py --scan /path/to/transcript.txt
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CapturedCorrection:
    """A correction extracted from conversation text."""
    what_wrong: str
    correct_approach: str
    confidence: float  # 0-1 how confident we are this is a real correction
    source_text: str
    domain: str = "general"
    severity: str = "medium"
    patterns_matched: list = field(default_factory=list)


# ─── DETECTION PATTERNS ─────────────────────────────────────────

# Patterns that indicate a correction is being made
CORRECTION_INDICATORS = [
    # Direct corrections
    (r"no[,.]?\s*that'?s\s*(wrong|incorrect|not\s*right)", 0.9),
    (r"actually[,.]?\s+(.+)", 0.6),
    (r"no[,.]?\s*i\s*meant\s+(.+)", 0.8),
    (r"i\s*told\s*you\s+(.+)", 0.7),
    (r"not\s*what\s*i\s*(asked|wanted|said)", 0.7),
    (r"you\s*(forgot|missed)\s+(.+)", 0.7),
    (r"that'?s\s*not\s*(right|correct|how)", 0.85),
    (r"wrong\s*(approach|way|path|file|method|tool)", 0.9),
    (r"you\s*should\s*have\s+(.+)", 0.8),
    (r"the\s*correct\s*(way|approach|path|method)\s*(is|was)\s+(.+)", 0.9),
    (r"you\s*made\s*a\s*mistake", 0.85),
    (r"you\s*misunderstood", 0.7),
    (r"don'?t\s*(do|use|call|open|send|deploy)\s+(.+)", 0.8),
    (r"stop\s*(doing|using)\s+(.+)", 0.8),
    (r"you'?re\s*(wrong|mistaken|confused)", 0.85),
    (r"no[,!]+\s*no[,!]*", 0.6),
    (r"never\s+(use|do|call|send|deploy)\s+(.+)", 0.85),
    (r"always\s+(use|do|call|check)\s+(.+)", 0.7),
    (r"instead\s*(of|,)\s+(.+)", 0.7),
    (r"not\s+(\w+)[,.]?\s*(use|it'?s|the)\s+(.+)", 0.7),
]

# Patterns for extracting the correction content
EXTRACTION_PATTERNS = [
    # "Not X, use Y" or "Not X. Use Y instead"
    (r"(?:not|don'?t\s+use)\s+(.+?)[,.]?\s*(?:use|it'?s|the\s+correct\s+\w+\s+is)\s+(.+?)\.?$",
     "what_wrong", "correct"),
    # "Wrong: X / Right: Y" or "Wrong: X. Correct: Y"
    (r"wrong:\s*(.+?)\s*(?:[/\|]|right:|correct:)\s*(.+)",
     "what_wrong", "correct"),
    # "should have X instead of Y"
    (r"should\s+have\s+(.+?)\s+instead\s+of\s+(.+?)\.?$",
     "correct", "what_wrong"),
    # "X is wrong, Y is correct"
    (r"(.+?)\s+is\s+wrong[,.]?\s*(.+?)\s+is\s+(?:correct|right)",
     "what_wrong", "correct"),
    # "instead of X, do Y" or "instead of X do Y"
    (r"instead\s+of\s+(.+?)[,]?\s*(?:do|use|try)\s+(.+?)\.?$",
     "what_wrong", "correct"),
    # "The correct X is Y" (extract Y as the correction)
    (r"the\s+correct\s+(\w+)\s+is\s+(.+?)\.?$",
     None, "correct"),
    # "Use X not Y" or "Use X, not Y"
    (r"use\s+(.+?)[,]?\s*not\s+(.+?)\.?$",
     "correct_first", "what_wrong"),
]

# Domain detection keywords
DOMAIN_SIGNALS = {
    "revit": ["revit", "bim", "wall", "floor", "level", "family", "viewport",
              "sheet", "mcp bridge", "createwall", "getelements"],
    "git": ["git", "commit", "push", "branch", "merge", "rebase"],
    "filesystem": ["path", "file", "folder", "directory", "deploy", "dll"],
    "email": ["email", "gmail", "outlook", "send", "recipient"],
    "window": ["window", "monitor", "screen", "display", "dpi"],
    "excel": ["excel", "cell", "chart", "worksheet", "formula"],
    "identity": ["name", "user", "weber", "rick"],
}


# ─── MAIN CAPTURE ENGINE ────────────────────────────────────────

class CorrectionCapture:
    """Extracts corrections from conversation text."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._sense = None

    def _get_sense(self):
        """Lazy-load CommonSense engine."""
        if self._sense is None and self.db_path:
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from sense import CommonSense
                self._sense = CommonSense(db_path=self.db_path)
            except Exception:
                pass
        return self._sense

    def check_message(self, message: str) -> Optional[CapturedCorrection]:
        """Check a single user message for correction intent.

        Returns a CapturedCorrection if one is detected, None otherwise.
        """
        if not message or len(message) < 10:
            return None

        # Score the message against correction indicators
        total_confidence = 0.0
        matched_patterns = []
        message_lower = message.lower()

        for pattern, weight in CORRECTION_INDICATORS:
            if re.search(pattern, message_lower):
                total_confidence = max(total_confidence, weight)
                matched_patterns.append(pattern)

        if total_confidence < 0.5:
            return None  # Not confident enough

        # Try to extract structured correction content
        what_wrong, correct_approach = self._extract_correction(message)

        if not what_wrong and not correct_approach:
            # Couldn't extract structured content — use the whole message
            correct_approach = message.strip()
            what_wrong = "(detected from conversation context)"

        # Detect domain
        domain = self._detect_domain(message)

        # Severity heuristic
        severity = "medium"
        if any(w in message_lower for w in ["never", "critical", "always", "important", "wrong"]):
            severity = "high"
        if any(w in message_lower for w in ["crash", "broke", "lost data", "destroyed"]):
            severity = "critical"

        return CapturedCorrection(
            what_wrong=what_wrong,
            correct_approach=correct_approach,
            confidence=total_confidence,
            source_text=message[:500],
            domain=domain,
            severity=severity,
            patterns_matched=matched_patterns[:3],
        )

    def capture_and_store(self, message: str) -> Optional[dict]:
        """Check a message, and if it's a correction, store it.

        Returns the stored correction dict or None.
        """
        captured = self.check_message(message)
        if not captured:
            return None

        # Only store high-confidence corrections
        if captured.confidence < 0.6:
            return None

        sense = self._get_sense()
        if sense:
            result = sense.learn(
                action=captured.what_wrong,
                what_went_wrong=captured.what_wrong,
                correct_approach=captured.correct_approach,
                category=captured.domain,
                severity=captured.severity,
            )
            if result:
                return {
                    "stored": True,
                    "correction": result,
                    "confidence": captured.confidence,
                    "domain": captured.domain,
                }

        return {
            "stored": False,
            "captured": {
                "what_wrong": captured.what_wrong,
                "correct_approach": captured.correct_approach,
                "confidence": captured.confidence,
                "domain": captured.domain,
            },
            "reason": "No database configured",
        }

    def scan_transcript(self, transcript: str) -> list[CapturedCorrection]:
        """Scan a full conversation transcript for corrections.

        Splits by message boundaries and checks each user message.
        """
        corrections = []

        # Split by common message boundaries
        # Look for "User:", "Human:", or similar prefixes
        message_patterns = [
            r'(?:^|\n)(?:User|Human|Weber):\s*(.+?)(?=\n(?:Assistant|Claude|AI):|$)',
            r'(?:^|\n)>\s*(.+?)(?=\n[^>]|$)',  # Quoted messages
        ]

        messages = []
        for pattern in message_patterns:
            found = re.findall(pattern, transcript, re.DOTALL | re.IGNORECASE)
            messages.extend(found)

        # If no structured messages found, split by paragraphs
        if not messages:
            messages = [p.strip() for p in transcript.split('\n\n') if p.strip()]

        for msg in messages:
            captured = self.check_message(msg.strip())
            if captured and captured.confidence >= 0.5:
                corrections.append(captured)

        return corrections

    def _extract_correction(self, text: str) -> tuple[str, str]:
        """Extract what-was-wrong and correct-approach from text.

        Returns (what_wrong, correct_approach) or ("", "") if not extractable.
        """
        text_clean = text.strip()

        for pattern, first_group, second_group in EXTRACTION_PATTERNS:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    if first_group == "correct_first":
                        return groups[1].strip(), groups[0].strip()
                    elif first_group == "what_wrong":
                        return groups[0].strip(), groups[1].strip()
                    elif first_group == "correct":
                        return groups[1].strip(), groups[0].strip()
                    elif first_group is None:
                        return "", groups[-1].strip()

        # Try sentence-level extraction
        # If there's a sentence with "wrong/incorrect" and one with "should/instead/correct"
        sentences = re.split(r'[.!?]\s+', text_clean)
        wrong_sentence = ""
        correct_sentence = ""

        for s in sentences:
            s_lower = s.lower()
            if any(w in s_lower for w in ["wrong", "incorrect", "mistake", "shouldn't"]):
                wrong_sentence = s.strip()
            if any(w in s_lower for w in ["should", "instead", "correct", "right way", "use "]):
                correct_sentence = s.strip()

        if wrong_sentence or correct_sentence:
            return wrong_sentence, correct_sentence

        return "", ""

    def _detect_domain(self, text: str) -> str:
        """Detect the domain of a correction from its text."""
        text_lower = text.lower()
        scores = {}

        for domain, keywords in DOMAIN_SIGNALS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"


# ─── HOOK ENTRY POINT ───────────────────────────────────────────

def hook_main():
    """Entry point when called as a Claude Code UserPromptSubmit hook.

    Reads hook JSON from stdin, checks for correction patterns,
    outputs structured guidance for Claude.
    """
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            sys.exit(0)
        hook_input = json.loads(stdin_data)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    user_prompt = hook_input.get('user_prompt', '')
    if not user_prompt:
        sys.exit(0)

    # Find database
    db_path = None
    candidates = [
        Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
        Path.home() / ".claude-memory" / "memories.db",
    ]
    for p in candidates:
        if p.exists():
            db_path = str(p)
            break

    capture = CorrectionCapture(db_path=db_path)
    captured = capture.check_message(user_prompt)

    if captured and captured.confidence >= 0.6:
        output = {
            "type": "correction_autocaptured",
            "message": "CORRECTION DETECTED — auto-extracted from user message",
            "what_wrong": captured.what_wrong[:200],
            "correct_approach": captured.correct_approach[:200],
            "confidence": f"{captured.confidence:.0%}",
            "domain": captured.domain,
            "severity": captured.severity,
            "instruction": (
                "A correction was detected. If this IS a correction:\n"
                "1. Acknowledge the mistake\n"
                "2. Use memory_store_correction() to save it permanently\n"
                "3. Apply the correct approach going forward"
            ),
        }
        print(json.dumps(output))

    sys.exit(0)


# ─── BATCH CLI ───────────────────────────────────────────────────

def main():
    """CLI entry point for batch processing."""
    import argparse
    parser = argparse.ArgumentParser(description="Auto-capture corrections")
    parser.add_argument("--scan", help="Scan a transcript file")
    parser.add_argument("--message", help="Check a single message")
    parser.add_argument("--store", action="store_true",
                        help="Store detected corrections in DB")
    parser.add_argument("--db", help="Path to memory database")
    parser.add_argument("--hook", action="store_true",
                        help="Run as Claude Code hook (reads stdin)")
    args = parser.parse_args()

    if args.hook:
        hook_main()
        return

    db_path = args.db
    if not db_path:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                db_path = str(p)
                break

    capture = CorrectionCapture(db_path=db_path)

    if args.message:
        result = capture.check_message(args.message)
        if result:
            print(f"Correction detected (confidence: {result.confidence:.0%})")
            print(f"  What wrong: {result.what_wrong}")
            print(f"  Correct:    {result.correct_approach}")
            print(f"  Domain:     {result.domain}")
            print(f"  Severity:   {result.severity}")

            if args.store:
                stored = capture.capture_and_store(args.message)
                print(f"  Stored:     {stored.get('stored', False) if stored else False}")
        else:
            print("No correction detected.")

    elif args.scan:
        transcript = Path(args.scan).read_text()
        results = capture.scan_transcript(transcript)
        print(f"Found {len(results)} corrections in transcript:")
        for i, c in enumerate(results, 1):
            print(f"\n  [{i}] (confidence: {c.confidence:.0%}, domain: {c.domain})")
            print(f"      Wrong: {c.what_wrong[:100]}")
            print(f"      Right: {c.correct_approach[:100]}")

            if args.store:
                stored = capture.capture_and_store(c.source_text)
                print(f"      Stored: {stored.get('stored', False) if stored else False}")

    else:
        # Default: run as hook
        hook_main()


if __name__ == "__main__":
    main()
