"""File scanner for discovering and tracking files in a codebase."""

import logging
from pathlib import Path
from typing import List, Set, Generator, Optional
import fnmatch
import os

from ..core.models import FileInfo, FileType
from .base import CodeParser

logger = logging.getLogger(__name__)


class FileScanner:
    """Scans directories for code files."""
    
    # Default patterns to ignore
    DEFAULT_IGNORE_PATTERNS = {
        # Version control
        '.git', '.svn', '.hg',
        # Dependencies
        'node_modules', 'venv', 'env', '__pycache__',
        '.venv', '.env', 'vendor', 'dist', 'build',
        # IDE
        '.idea', '.vscode', '*.swp', '*.swo',
        # OS
        '.DS_Store', 'Thumbs.db',
        # Compiled
        '*.pyc', '*.pyo', '*.class', '*.o', '*.so',
        # Archives
        '*.zip', '*.tar', '*.gz', '*.rar',
        # Media
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.mp3', '*.mp4',
        # Data
        '*.db', '*.sqlite', '*.log'
    }
    
    # File extensions to include
    CODE_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx',
        '.java', '.cpp', '.cc', '.cxx', '.h', '.hpp',
        '.go', '.rs', '.rb', '.php', '.cs', '.swift',
        '.kt', '.scala', '.r', '.m', '.mm'
    }
    
    def __init__(self, ignore_patterns: Optional[Set[str]] = None,
                 include_extensions: Optional[Set[str]] = None):
        self.ignore_patterns = ignore_patterns or self.DEFAULT_IGNORE_PATTERNS
        self.include_extensions = include_extensions or self.CODE_EXTENSIONS
        
    def scan_directory(self, root_path: Path) -> Generator[FileInfo, None, None]:
        """Scan a directory recursively for code files."""
        root_path = root_path.resolve()
        
        for file_path in self._walk_directory(root_path):
            if self._should_process_file(file_path, root_path):
                try:
                    stat = file_path.stat()
                    yield FileInfo(
                        path=file_path,
                        relative_path=str(file_path.relative_to(root_path)),
                        file_type=CodeParser.detect_file_type(file_path),
                        size=stat.st_size,
                        last_modified=stat.st_mtime
                    )
                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")
                    
    def _walk_directory(self, root_path: Path) -> Generator[Path, None, None]:
        """Walk directory tree, respecting ignore patterns."""
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Modify dirnames in-place to skip ignored directories
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore(Path(dirpath) / d, root_path)
            ]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if not self._should_ignore(file_path, root_path):
                    yield file_path
                    
    def _should_ignore(self, path: Path, root_path: Path) -> bool:
        """Check if a path should be ignored."""
        try:
            relative_path = path.relative_to(root_path)
        except ValueError:
            return True
            
        # Check against ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(str(relative_path), pattern):
                return True
            if fnmatch.fnmatch(path.name, pattern):
                return True
                
        return False
        
    def _should_process_file(self, file_path: Path, root_path: Path) -> bool:
        """Check if a file should be processed."""
        # Check file extension
        if file_path.suffix.lower() not in self.include_extensions:
            return False
            
        # Additional checks
        if file_path.is_symlink():
            return False
            
        return True
        
    def get_gitignore_patterns(self, root_path: Path) -> Set[str]:
        """Read .gitignore file if it exists."""
        gitignore_path = root_path / '.gitignore'
        patterns = set()
        
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.add(line)
            except Exception as e:
                logger.warning(f"Error reading .gitignore: {e}")
                
        return patterns