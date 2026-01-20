"""Main CodeMemory class that ties everything together."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from .config import Config
from .database import DatabaseManager
from .models import QueryRequest, QueryResult, ProjectInfo
from ..indexing.indexer import CodeIndexer
from ..indexing.embeddings import CodeEmbeddingGenerator
from ..retrieval.vector_store import VectorStore
from ..retrieval.context_retriever import ContextRetriever
from ..memory.cache_manager import ThreeTierMemoryCache
from ..session.session_manager import SessionManager

logger = logging.getLogger(__name__)


class CodeMemory:
    """Main interface for the code memory system."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the code memory system."""
        self.config = config or Config.from_env()
        self.config.ensure_directories()
        
        # Initialize components
        self.db_manager = DatabaseManager(self.config)
        
        self.embedding_generator = CodeEmbeddingGenerator(
            embedding_dim=self.config.performance.embedding_dimension,
            use_openai=bool(self.config.openai_api_key),
            api_key=self.config.openai_api_key
        )
        
        self.vector_store = VectorStore(
            self.config.database.vector_db_path,
            self.embedding_generator
        )
        
        self.indexer = CodeIndexer(self.config, self.db_manager)
        self.cache = ThreeTierMemoryCache(self.config)
        self.retriever = ContextRetriever(self.db_manager, self.vector_store)
        self.session_manager = SessionManager(self.db_manager)
        
        logger.info("Code Memory system initialized")
        
    def index_project(self, project_path: Path, name: Optional[str] = None) -> ProjectInfo:
        """Index a new project."""
        project = self.indexer.index_project(project_path, name)
        
        # Index embeddings
        with self.db_manager.session() as session:
            entities = []
            for file in project.files:
                for entity in file.entities:
                    entities.append((entity, project.id))
                    
            # Batch add to vector store
            if entities:
                self.vector_store.add_entities_batch(entities)
                
        return ProjectInfo(
            name=project.name,
            root_path=Path(project.root_path),
            total_files=project.total_files,
            indexed_files=project.indexed_files,
            last_indexed=project.last_indexed
        )
        
    def query(self, text: str, project_id: int, 
              max_results: int = 10,
              include_tests: bool = False) -> QueryResult:
        """Query the code memory system."""
        # Check cache
        cache_key = f"query:{project_id}:{text}:{max_results}:{include_tests}"
        cached_result, tier = self.cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"Cache hit from {tier} tier")
            return QueryResult(**cached_result)
            
        # Create query request
        request = QueryRequest(
            text=text,
            max_results=max_results,
            include_tests=include_tests
        )
        
        # Retrieve context
        result = self.retriever.retrieve_context(request, project_id)
        
        # Cache result
        self.cache.put(cache_key, result.dict(), "warm")
        
        # Update session
        if self.session_manager.current_session:
            self.session_manager.add_query(text)
            
        return result
        
    def start_session(self, project_id: int, name: Optional[str] = None):
        """Start a new working session."""
        return self.session_manager.create_session(project_id, name)
        
    def continue_session(self, project_id: int):
        """Continue the last session for a project."""
        return self.session_manager.continue_last_session(project_id)
        
    def get_file_context(self, file_path: Path, project_id: int) -> Dict[str, Any]:
        """Get context for a specific file."""
        cache_key = f"file:{project_id}:{file_path}"
        cached_result, _ = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
            
        with self.db_manager.session() as session:
            from ..core.models import File, CodeEntity
            
            file = session.query(File).filter_by(
                project_id=project_id,
                path=str(file_path)
            ).first()
            
            if not file:
                return {}
                
            context = {
                'file': {
                    'path': file.path,
                    'type': file.file_type,
                    'size': file.size
                },
                'entities': [
                    {
                        'name': e.name,
                        'type': e.entity_type,
                        'start_line': e.start_line,
                        'end_line': e.end_line,
                        'signature': e.signature
                    }
                    for e in file.entities
                ]
            }
            
            self.cache.put(cache_key, context, "hot")
            return context
            
    def jump_to(self, target: str, project_id: int) -> Optional[Dict[str, Any]]:
        """Jump directly to a code location."""
        entity = self.retriever.jump_to_location(project_id, target)
        
        if entity:
            return {
                'entity': {
                    'name': entity.name,
                    'type': entity.entity_type,
                    'file': entity.file.relative_path if entity.file else None,
                    'start_line': entity.start_line,
                    'end_line': entity.end_line,
                    'signature': entity.signature
                },
                'content': self.retriever.get_file_contents(
                    Path(entity.file.path),
                    entity.start_line,
                    entity.end_line
                ) if entity.file else None
            }
            
        return None
        
    def update_project(self, project_id: int) -> int:
        """Update an existing project's index."""
        return self.indexer.update_project(project_id)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            'database': {
                'size_bytes': self.db_manager.get_db_size()
            },
            'vector_store': self.vector_store.get_statistics(),
            'cache': self.cache.get_statistics()
        }
        
    def close(self):
        """Clean up resources."""
        if self.session_manager.current_session:
            self.session_manager.save_session()
            
        self.db_manager.close()
        logger.info("Code Memory system closed")