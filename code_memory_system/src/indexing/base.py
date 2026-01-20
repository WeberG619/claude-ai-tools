"""Base classes for code indexing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from ..core.models import FileInfo, CodeEntityInfo, FileType


class CodeParser(ABC):
    """Abstract base class for language-specific parsers."""
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> List[CodeEntityInfo]:
        """Parse a file and extract code entities."""
        pass
        
    @abstractmethod
    def get_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from a file."""
        pass
        
    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    @staticmethod
    def detect_file_type(file_path: Path) -> FileType:
        """Detect the file type based on extension."""
        extension_map = {
            '.py': FileType.PYTHON,
            '.js': FileType.JAVASCRIPT,
            '.jsx': FileType.JAVASCRIPT,
            '.ts': FileType.TYPESCRIPT,
            '.tsx': FileType.TYPESCRIPT,
            '.java': FileType.JAVA,
            '.cpp': FileType.CPP,
            '.cc': FileType.CPP,
            '.cxx': FileType.CPP,
            '.h': FileType.CPP,
            '.hpp': FileType.CPP,
            '.go': FileType.GO,
            '.rs': FileType.RUST,
        }
        
        suffix = file_path.suffix.lower()
        return extension_map.get(suffix, FileType.OTHER)


class IndexingStrategy(ABC):
    """Abstract base class for indexing strategies."""
    
    @abstractmethod
    def should_index_file(self, file_path: Path) -> bool:
        """Determine if a file should be indexed."""
        pass
        
    @abstractmethod
    def should_reindex_file(self, file_path: Path, last_hash: str) -> bool:
        """Determine if a file should be re-indexed."""
        pass