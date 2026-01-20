"""Main indexing engine for the code memory system."""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from tqdm import tqdm

from sqlalchemy.orm import Session

from .base import CodeParser
from .python_parser import PythonParser
from .scanner import FileScanner
from ..core.models import Project, File, CodeEntity, FileType
from ..core.database import DatabaseManager
from ..core.config import Config

logger = logging.getLogger(__name__)


class CodeIndexer:
    """Main indexing engine that orchestrates file scanning and parsing."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.scanner = FileScanner()
        self.parsers: Dict[FileType, CodeParser] = {
            FileType.PYTHON: PythonParser(),
        }
        
    def index_project(self, project_path: Path, project_name: Optional[str] = None) -> Project:
        """Index a complete project."""
        project_path = project_path.resolve()
        project_name = project_name or project_path.name
        
        logger.info(f"Starting indexing of project: {project_name} at {project_path}")
        
        with self.db_manager.session() as session:
            # Create or update project
            project = self._get_or_create_project(session, project_name, project_path)
            
            # Scan for files
            files_to_index = list(self.scanner.scan_directory(project_path))
            project.total_files = len(files_to_index)
            
            # Index files in parallel
            indexed_count = self._index_files_parallel(session, project, files_to_index)
            
            # Update project stats
            project.indexed_files = indexed_count
            project.last_indexed = datetime.utcnow()
            session.commit()
            
            logger.info(f"Indexing complete: {indexed_count}/{len(files_to_index)} files indexed")
            
        return project
        
    def update_project(self, project_id: int) -> int:
        """Update an existing project's index."""
        with self.db_manager.session() as session:
            project = session.query(Project).get(project_id)
            if not project:
                raise ValueError(f"Project with id {project_id} not found")
                
            project_path = Path(project.root_path)
            
            # Get current files in database
            existing_files = {f.relative_path: f for f in project.files}
            
            # Scan for current files
            current_files = list(self.scanner.scan_directory(project_path))
            current_paths = {f.relative_path for f in current_files}
            
            # Find deleted files
            deleted_paths = set(existing_files.keys()) - current_paths
            for path in deleted_paths:
                session.delete(existing_files[path])
                
            # Index new and modified files
            files_to_index = []
            for file_info in current_files:
                existing = existing_files.get(file_info.relative_path)
                if not existing or self._should_reindex(file_info, existing):
                    files_to_index.append(file_info)
                    
            indexed_count = self._index_files_parallel(session, project, files_to_index)
            
            # Update project stats
            project.total_files = len(current_files)
            project.indexed_files = session.query(File).filter_by(project_id=project.id).count()
            project.last_indexed = datetime.utcnow()
            session.commit()
            
            return indexed_count
            
    def _get_or_create_project(self, session: Session, name: str, path: Path) -> Project:
        """Get existing project or create new one."""
        project = session.query(Project).filter_by(
            root_path=str(path)
        ).first()
        
        if not project:
            project = Project(
                name=name,
                root_path=str(path),
                created_at=datetime.utcnow()
            )
            session.add(project)
            session.flush()
            
        return project
        
    def _index_files_parallel(self, session: Session, project: Project, 
                            files: List) -> int:
        """Index multiple files in parallel."""
        indexed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.config.performance.max_workers) as executor:
            # Submit indexing tasks
            future_to_file = {
                executor.submit(self._index_single_file, file_info): file_info
                for file_info in files
            }
            
            # Process results as they complete
            with tqdm(total=len(files), desc="Indexing files") as pbar:
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            self._save_indexed_file(session, project, file_info, result)
                            indexed_count += 1
                    except Exception as e:
                        logger.error(f"Error indexing {file_info.path}: {e}")
                    finally:
                        pbar.update(1)
                        
        session.commit()
        return indexed_count
        
    def _index_single_file(self, file_info) -> Optional[Dict]:
        """Index a single file and extract entities."""
        try:
            # Get appropriate parser
            parser = self.parsers.get(file_info.file_type)
            if not parser:
                return None
                
            # Parse file
            entities = parser.parse_file(file_info.path)
            dependencies = parser.get_dependencies(file_info.path)
            file_hash = parser.get_file_hash(file_info.path)
            
            return {
                'entities': entities,
                'dependencies': dependencies,
                'hash': file_hash
            }
        except Exception as e:
            logger.error(f"Error parsing {file_info.path}: {e}")
            return None
            
    def _save_indexed_file(self, session: Session, project: Project,
                          file_info, index_result: Dict):
        """Save indexed file data to database."""
        # Check if file exists
        file_obj = session.query(File).filter_by(
            project_id=project.id,
            relative_path=file_info.relative_path
        ).first()
        
        if not file_obj:
            file_obj = File(
                project_id=project.id,
                path=str(file_info.path),
                relative_path=file_info.relative_path,
                file_type=file_info.file_type.value
            )
            session.add(file_obj)
            
        # Update file metadata
        file_obj.hash = index_result['hash']
        file_obj.size = file_info.size
        file_obj.last_modified = datetime.fromtimestamp(file_info.last_modified)
        file_obj.last_indexed = datetime.utcnow()
        
        # Remove old entities
        session.query(CodeEntity).filter_by(file_id=file_obj.id).delete()
        
        # Add new entities
        for entity_info in index_result['entities']:
            entity = CodeEntity(
                file_id=file_obj.id,
                name=entity_info.name,
                entity_type=entity_info.entity_type,
                start_line=entity_info.start_line,
                end_line=entity_info.end_line,
                signature=entity_info.signature,
                docstring=entity_info.docstring,
                dependencies=entity_info.dependencies
            )
            session.add(entity)
            
        session.flush()
        
    def _should_reindex(self, file_info, existing_file: File) -> bool:
        """Check if a file should be re-indexed."""
        # Check modification time
        if file_info.last_modified > existing_file.last_modified.timestamp():
            return True
            
        # Could also check hash if needed
        return False