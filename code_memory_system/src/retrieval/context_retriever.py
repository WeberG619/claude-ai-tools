"""Smart context retrieval system for intelligent code fetching."""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy.orm import Session

from ..core.models import (
    File, CodeEntity, QueryRequest, QueryResult,
    CodeEntityInfo, FileInfo, QueryType
)
from ..core.database import DatabaseManager
from .vector_store import VectorStore
from .query_classifier import QueryClassifier, QueryIntent

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """Context retrieved for a query."""
    primary_entities: List[CodeEntity]
    related_entities: List[CodeEntity]
    files: List[File]
    relevance_scores: Dict[int, float]
    query_intent: QueryIntent
    

class ContextRetriever:
    """Smart context retrieval system that intelligently fetches relevant code."""
    
    def __init__(self, db_manager: DatabaseManager, vector_store: VectorStore):
        self.db_manager = db_manager
        self.vector_store = vector_store
        self.query_classifier = QueryClassifier()
        
    def retrieve_context(self, query_request: QueryRequest, 
                        project_id: int) -> QueryResult:
        """Retrieve relevant context for a query."""
        # Classify the query
        intent = self.query_classifier.classify(query_request.text)
        
        # Get retrieval strategy
        strategy = self.query_classifier.get_retrieval_strategy(intent)
        
        # Perform semantic search
        search_results = self.vector_store.search(
            query=query_request.text,
            project_id=project_id,
            n_results=query_request.max_results * 2  # Get more for filtering
        )
        
        with self.db_manager.session() as session:
            # Fetch primary entities
            primary_entities, relevance_scores = self._fetch_primary_entities(
                session, search_results, intent, query_request.max_results
            )
            
            # Expand context based on strategy
            context = self._expand_context(
                session, primary_entities, strategy, relevance_scores
            )
            
            # Filter based on intent
            if not query_request.include_tests and intent.query_type != QueryType.TESTING:
                context = self._filter_test_files(context)
                
            # Convert to result format
            result = self._format_result(
                context, intent, relevance_scores
            )
            
        return result
        
    def _fetch_primary_entities(self, session: Session, 
                              search_results: List[Dict],
                              intent: QueryIntent,
                              limit: int) -> Tuple[List[CodeEntity], Dict[int, float]]:
        """Fetch primary entities from search results."""
        entities = []
        relevance_scores = {}
        
        for result in search_results[:limit]:
            entity_id = result['metadata']['entity_id']
            entity = session.query(CodeEntity).get(entity_id)
            
            if entity:
                entities.append(entity)
                relevance_scores[entity_id] = result['relevance_score']
                
        return entities, relevance_scores
        
    def _expand_context(self, session: Session,
                       primary_entities: List[CodeEntity],
                       strategy: Dict[str, Any],
                       relevance_scores: Dict[int, float]) -> RetrievalContext:
        """Expand context based on retrieval strategy."""
        # Track all entities and files
        all_entities = set(primary_entities)
        all_files = set()
        
        # Get files for primary entities
        for entity in primary_entities:
            if entity.file:
                all_files.add(entity.file)
                
        # Expand dependencies if needed
        if strategy['expand_dependencies']:
            expanded = self._expand_dependencies(
                session, primary_entities, strategy['max_depth']
            )
            all_entities.update(expanded)
            
            # Get files for expanded entities
            for entity in expanded:
                if entity.file:
                    all_files.add(entity.file)
                    
        # Get related entities from same files
        for file in list(all_files):
            # Add other entities from the same file
            for entity in file.entities:
                if entity not in all_entities:
                    # Give lower relevance score
                    relevance_scores[entity.id] = relevance_scores.get(
                        entity.id, 0.3
                    )
                    all_entities.add(entity)
                    
        # Separate primary and related entities
        primary_set = set(primary_entities)
        related_entities = [e for e in all_entities if e not in primary_set]
        
        return RetrievalContext(
            primary_entities=primary_entities,
            related_entities=related_entities,
            files=list(all_files),
            relevance_scores=relevance_scores,
            query_intent=intent
        )
        
    def _expand_dependencies(self, session: Session,
                           entities: List[CodeEntity],
                           max_depth: int) -> Set[CodeEntity]:
        """Expand entities by following dependencies."""
        expanded = set()
        to_process = list(entities)
        processed = set()
        current_depth = 0
        
        while to_process and current_depth < max_depth:
            next_level = []
            
            for entity in to_process:
                if entity.id in processed:
                    continue
                    
                processed.add(entity.id)
                
                # Get dependencies
                if entity.dependencies:
                    for dep in entity.dependencies:
                        # Search for entities with matching names
                        dep_entities = session.query(CodeEntity).filter(
                            CodeEntity.name == dep
                        ).all()
                        
                        for dep_entity in dep_entities:
                            if dep_entity not in expanded:
                                expanded.add(dep_entity)
                                next_level.append(dep_entity)
                                
            to_process = next_level
            current_depth += 1
            
        return expanded
        
    def _filter_test_files(self, context: RetrievalContext) -> RetrievalContext:
        """Filter out test files from context."""
        # Common test file patterns
        test_patterns = ['test_', '_test.', 'tests/', '/test/', 'spec.']
        
        # Filter files
        filtered_files = []
        for file in context.files:
            is_test = any(pattern in file.relative_path.lower() 
                         for pattern in test_patterns)
            if not is_test:
                filtered_files.append(file)
                
        # Filter entities
        test_file_ids = {f.id for f in context.files if f not in filtered_files}
        
        filtered_primary = [e for e in context.primary_entities 
                          if e.file_id not in test_file_ids]
        filtered_related = [e for e in context.related_entities 
                          if e.file_id not in test_file_ids]
        
        context.files = filtered_files
        context.primary_entities = filtered_primary
        context.related_entities = filtered_related
        
        return context
        
    def _format_result(self, context: RetrievalContext,
                      intent: QueryIntent,
                      relevance_scores: Dict[int, float]) -> QueryResult:
        """Format retrieval context as query result."""
        # Convert entities to info objects
        entity_infos = []
        
        for entity in context.primary_entities + context.related_entities:
            if entity.file:
                file_path = entity.file.relative_path
            else:
                file_path = "unknown"
                
            entity_infos.append(CodeEntityInfo(
                name=entity.name,
                entity_type=entity.entity_type,
                file_path=file_path,
                start_line=entity.start_line,
                end_line=entity.end_line,
                signature=entity.signature,
                docstring=entity.docstring,
                dependencies=entity.dependencies or []
            ))
            
        # Convert files to info objects
        file_infos = []
        for file in context.files:
            file_infos.append(FileInfo(
                path=Path(file.path),
                relative_path=file.relative_path,
                file_type=file.file_type,
                size=file.size,
                last_modified=file.last_modified
            ))
            
        # Calculate average response time (mock for now)
        response_time = 0.1  # seconds
        
        return QueryResult(
            query_type=intent.query_type,
            entities=entity_infos,
            files=file_infos,
            relevance_scores=relevance_scores,
            response_time=response_time
        )
        
    def get_file_contents(self, file_path: Path, 
                         start_line: Optional[int] = None,
                         end_line: Optional[int] = None) -> str:
        """Get file contents, optionally for specific line range."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if start_line is not None and end_line is not None:
                # Adjust for 0-based indexing
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                return ''.join(lines[start_idx:end_idx])
            else:
                return ''.join(lines)
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""
            
    def jump_to_location(self, project_id: int, 
                        target: str) -> Optional[CodeEntity]:
        """Jump directly to a specific code location without loading intermediate context."""
        with self.db_manager.session() as session:
            # First try exact match
            entity = session.query(CodeEntity).join(File).filter(
                File.project_id == project_id,
                CodeEntity.name == target
            ).first()
            
            if entity:
                return entity
                
            # Try semantic search
            search_results = self.vector_store.search(
                query=target,
                project_id=project_id,
                n_results=1
            )
            
            if search_results:
                entity_id = search_results[0]['metadata']['entity_id']
                return session.query(CodeEntity).get(entity_id)
                
        return None