"""
Client Matcher - Identifies client from filename or content.
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClientMatch:
    client_name: str
    confidence: float
    matched_pattern: str
    source: str  # filename, content, path


class ClientMatcher:
    """Matches files to clients based on patterns in filenames and paths."""

    def __init__(self, client_config: Dict[str, Dict] = None):
        """
        Initialize with client configuration.

        client_config format:
        {
            "Client Name": {
                "patterns": ["pattern1", "pattern2"],
                "aliases": ["alias1"],
                "project_prefix": "CLT"
            }
        }
        """
        self.clients = client_config or {}
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        for client, config in self.clients.items():
            patterns = config.get("patterns", [client])
            aliases = config.get("aliases", [])
            all_patterns = patterns + aliases

            self._compiled_patterns[client] = [
                re.compile(p, re.IGNORECASE) for p in all_patterns
            ]

    def add_client(self, name: str, patterns: List[str] = None,
                   aliases: List[str] = None, project_prefix: str = None):
        """Add a new client to the matcher."""
        self.clients[name] = {
            "patterns": patterns or [name],
            "aliases": aliases or [],
            "project_prefix": project_prefix
        }
        self._compiled_patterns[name] = [
            re.compile(p, re.IGNORECASE) for p in (patterns or [name]) + (aliases or [])
        ]

    def match_filename(self, filename: str) -> Optional[ClientMatch]:
        """Match client from filename."""
        best_match = None
        best_confidence = 0.0

        for client, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if match := pattern.search(filename):
                    # Calculate confidence based on match quality
                    match_len = len(match.group())
                    name_len = len(filename)
                    confidence = min(1.0, match_len / max(name_len * 0.3, 1))

                    # Boost confidence for exact matches
                    if match.group().lower() == client.lower():
                        confidence = min(1.0, confidence + 0.3)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ClientMatch(
                            client_name=client,
                            confidence=confidence,
                            matched_pattern=pattern.pattern,
                            source="filename"
                        )

        return best_match

    def match_path(self, filepath: str) -> Optional[ClientMatch]:
        """Match client from full file path."""
        path = Path(filepath)
        parts = path.parts

        # Check each path component
        for part in parts:
            if match := self.match_filename(part):
                # Boost confidence for directory matches
                match.confidence = min(1.0, match.confidence + 0.1)
                match.source = "path"
                return match

        return None

    def match_file(self, filepath: str) -> Optional[ClientMatch]:
        """
        Match client from file using all available methods.

        Returns the highest confidence match.
        """
        matches = []

        # Try filename
        if filename_match := self.match_filename(Path(filepath).name):
            matches.append(filename_match)

        # Try path
        if path_match := self.match_path(filepath):
            matches.append(path_match)

        if not matches:
            return None

        # Return highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def get_client_folder(self, client_name: str) -> Optional[str]:
        """Get the folder name for a client."""
        if client_name in self.clients:
            return self.clients[client_name].get("folder", client_name)
        return client_name

    def list_clients(self) -> List[str]:
        """List all configured clients."""
        return list(self.clients.keys())
