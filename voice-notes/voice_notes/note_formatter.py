"""
Note formatting and extraction module.

Extracts key points, action items, and attendees from transcribed text.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class NoteFormatter:
    """Formats transcriptions into structured meeting notes."""

    # Patterns for detecting action items
    ACTION_PATTERNS = [
        r"(?:i'?ll|we'?ll|i\s+will|we\s+will|going\s+to)\s+(.+?)(?:\.|$)",
        r"(?:need\s+to|have\s+to|should|must)\s+(.+?)(?:\.|$)",
        r"(?:action\s+item[s]?[:;]?)\s*(.+?)(?:\.|$)",
        r"(?:todo[:;]?|to[\-\s]do[:;]?)\s*(.+?)(?:\.|$)",
        r"(?:please|can\s+you|could\s+you)\s+(.+?)(?:\.|$)",
        r"(?:follow[\-\s]?up\s+(?:on|with)?[:;]?)\s*(.+?)(?:\.|$)",
        r"(?:assigned\s+to\s+\w+[:;]?)\s*(.+?)(?:\.|$)",
    ]

    # Patterns for detecting key discussion points
    KEY_POINT_PATTERNS = [
        r"(?:important(?:ly)?|key\s+(?:point|takeaway)|main\s+(?:point|thing)|notably)[:;,]?\s*(.+?)(?:\.|$)",
        r"(?:the\s+(?:main|key|critical|important)\s+(?:issue|point|thing)\s+is)\s+(.+?)(?:\.|$)",
        r"(?:we\s+(?:decided|agreed|concluded)\s+(?:that|to)?)\s*(.+?)(?:\.|$)",
        r"(?:in\s+summary|to\s+summarize|overall)[:;,]?\s*(.+?)(?:\.|$)",
    ]

    # Common name patterns (for attendee detection)
    NAME_PATTERNS = [
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|mentioned|asked|suggested|noted|pointed\s+out)",
        r"(?:according\s+to|as\s+per)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"\b([A-Z][a-z]+)\s*(?:'s\s+(?:point|suggestion|idea|comment))",
        r"(?:^|\.\s+)([A-Z][a-z]+)[:;,]?\s+(?:i\s+think|we\s+should|let'?s)",
    ]

    # Words to exclude from name detection
    NAME_EXCLUSIONS = {
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
        'September', 'October', 'November', 'December',
        'The', 'This', 'That', 'These', 'Those', 'There', 'Here',
        'What', 'When', 'Where', 'Which', 'Who', 'Why', 'How',
        'And', 'But', 'Or', 'So', 'Yet', 'For', 'Nor',
        'However', 'Therefore', 'Furthermore', 'Moreover', 'Also',
        'First', 'Second', 'Third', 'Next', 'Finally', 'Lastly',
        'Please', 'Thanks', 'Thank', 'Okay', 'Alright',
    }

    def __init__(self, audio_filename: Optional[str] = None):
        """
        Initialize the formatter.

        Args:
            audio_filename: Original audio filename (for context in notes)
        """
        self.audio_filename = audio_filename
        self.timestamp = datetime.now()

    def extract_action_items(self, text: str) -> List[str]:
        """
        Extract action items from transcribed text.

        Args:
            text: The transcribed text

        Returns:
            List of identified action items
        """
        actions = []
        text_lower = text.lower()

        for pattern in self.ACTION_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_extracted_text(match)
                if cleaned and len(cleaned) > 10:  # Filter out very short matches
                    actions.append(cleaned)

        # Deduplicate while preserving order
        seen = set()
        unique_actions = []
        for action in actions:
            action_normalized = action.lower().strip()
            if action_normalized not in seen:
                seen.add(action_normalized)
                unique_actions.append(action.capitalize())

        return unique_actions[:15]  # Limit to top 15 action items

    def extract_key_points(self, text: str) -> List[str]:
        """
        Extract key discussion points from transcribed text.

        Uses sentence analysis to identify important statements.

        Args:
            text: The transcribed text

        Returns:
            List of key points
        """
        points = []

        # First, try explicit key point patterns
        for pattern in self.KEY_POINT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_extracted_text(match)
                if cleaned and len(cleaned) > 15:
                    points.append(cleaned)

        # If we don't have many points, extract from sentences
        if len(points) < 5:
            sentences = self._split_sentences(text)
            scored_sentences = self._score_sentences(sentences)

            # Get top sentences by importance
            for sentence, score in sorted(scored_sentences, key=lambda x: x[1], reverse=True)[:10]:
                if len(sentence) > 20 and sentence not in points:
                    points.append(sentence)

        # Deduplicate
        seen = set()
        unique_points = []
        for point in points:
            point_normalized = point.lower().strip()
            if point_normalized not in seen:
                seen.add(point_normalized)
                unique_points.append(point)

        return unique_points[:10]  # Limit to top 10 key points

    def extract_attendees(self, text: str) -> List[str]:
        """
        Extract mentioned names/attendees from transcribed text.

        Args:
            text: The transcribed text

        Returns:
            List of potential attendee names
        """
        names = set()

        for pattern in self.NAME_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                cleaned = match.strip()
                if (
                    cleaned
                    and cleaned not in self.NAME_EXCLUSIONS
                    and len(cleaned) > 1
                    and not cleaned.isupper()  # Exclude acronyms
                ):
                    names.add(cleaned)

        return sorted(list(names))

    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove extra whitespace
        cleaned = ' '.join(text.split())
        # Remove leading/trailing punctuation
        cleaned = cleaned.strip('.,;:!?"\' ')
        return cleaned

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _score_sentences(self, sentences: List[str]) -> List[Tuple[str, float]]:
        """
        Score sentences by importance.

        Uses keyword presence and position heuristics.
        """
        importance_keywords = {
            'important', 'key', 'critical', 'main', 'primary', 'essential',
            'decided', 'agreed', 'concluded', 'resolved', 'approved',
            'deadline', 'budget', 'goal', 'objective', 'target',
            'problem', 'issue', 'challenge', 'solution', 'recommendation',
            'next', 'step', 'action', 'follow-up', 'update',
        }

        scored = []
        for i, sentence in enumerate(sentences):
            score = 0.0
            words = sentence.lower().split()

            # Score based on keywords
            for word in words:
                if word in importance_keywords:
                    score += 2.0

            # Boost first and last few sentences (often contain summaries)
            if i < 3 or i >= len(sentences) - 3:
                score += 1.0

            # Penalize very short sentences
            if len(words) < 5:
                score -= 1.0

            # Boost sentences with numbers (often contain specifics)
            if re.search(r'\d+', sentence):
                score += 0.5

            scored.append((sentence, score))

        return scored

    def format_markdown(
        self,
        transcription: str,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        attendees: Optional[List[str]] = None,
        include_full_transcript: bool = True
    ) -> str:
        """
        Format the transcription into structured markdown notes.

        Args:
            transcription: The full transcribed text
            key_points: Extracted key points (auto-extracted if None)
            action_items: Extracted action items (auto-extracted if None)
            attendees: Extracted attendees (auto-extracted if None)
            include_full_transcript: Whether to include full transcript at end

        Returns:
            Formatted markdown string
        """
        # Auto-extract if not provided
        if key_points is None:
            key_points = self.extract_key_points(transcription)
        if action_items is None:
            action_items = self.extract_action_items(transcription)
        if attendees is None:
            attendees = self.extract_attendees(transcription)

        # Build markdown document
        lines = []

        # Header
        lines.append("# Meeting Notes")
        lines.append("")

        # Metadata
        lines.append(f"**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M')}")
        if self.audio_filename:
            lines.append(f"**Source:** {self.audio_filename}")
        lines.append("")

        # Attendees
        if attendees:
            lines.append("## Attendees")
            lines.append("")
            for name in attendees:
                lines.append(f"- {name}")
            lines.append("")

        # Key Points
        lines.append("## Key Points")
        lines.append("")
        if key_points:
            for point in key_points:
                lines.append(f"- {point}")
        else:
            lines.append("- No specific key points identified")
        lines.append("")

        # Action Items
        lines.append("## Action Items")
        lines.append("")
        if action_items:
            for item in action_items:
                lines.append(f"- [ ] {item}")
        else:
            lines.append("- No action items identified")
        lines.append("")

        # Full Transcript
        if include_full_transcript:
            lines.append("## Full Transcript")
            lines.append("")
            lines.append(transcription)
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by voice-notes on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def generate_summary(
        self,
        transcription: str,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None
    ) -> str:
        """
        Generate a brief spoken summary of the notes.

        Args:
            transcription: The full transcribed text
            key_points: Extracted key points
            action_items: Extracted action items

        Returns:
            Summary text suitable for text-to-speech
        """
        if key_points is None:
            key_points = self.extract_key_points(transcription)
        if action_items is None:
            action_items = self.extract_action_items(transcription)

        parts = ["Meeting notes processed."]

        # Word count
        word_count = len(transcription.split())
        parts.append(f"Transcribed {word_count} words.")

        # Key points summary
        if key_points:
            parts.append(f"Found {len(key_points)} key points.")
            if len(key_points) >= 1:
                parts.append(f"Main point: {key_points[0][:100]}")

        # Action items summary
        if action_items:
            parts.append(f"Identified {len(action_items)} action items.")
            if len(action_items) >= 1:
                parts.append(f"First action: {action_items[0][:100]}")

        parts.append("Notes saved to markdown file.")

        return " ".join(parts)
