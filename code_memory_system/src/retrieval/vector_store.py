"""Vector store for semantic search using ChromaDB."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import numpy as np

from ..core.models import CodeEntity
from ..indexing.embeddings import CodeEmbeddingGenerator

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector storage and retrieval for semantic search."""
    
    def __init__(self, store_path: Path, embedding_generator: CodeEmbeddingGenerator):
        self.store_path = store_path
        self.embedding_generator = embedding_generator
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(store_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="code_entities",
            metadata={"description": "Code entities with embeddings"}
        )
        
    def add_entity(self, entity: CodeEntity, project_id: int):
        """Add a single code entity to the vector store."""
        # Create embedding
        entity_data = {
            'name': entity.name,
            'entity_type': entity.entity_type,
            'signature': entity.signature,
            'docstring': entity.docstring,
            'dependencies': entity.dependencies or []
        }
        
        embedding = self.embedding_generator.create_code_embedding(entity_data)
        
        # Prepare metadata
        metadata = {
            'entity_id': entity.id,
            'file_id': entity.file_id,
            'project_id': project_id,
            'name': entity.name,
            'entity_type': entity.entity_type,
            'start_line': entity.start_line,
            'end_line': entity.end_line
        }
        
        # Add to collection
        self.collection.add(
            embeddings=[embedding],
            documents=[entity.docstring or entity.signature or entity.name],
            metadatas=[metadata],
            ids=[f"entity_{entity.id}"]
        )
        
    def add_entities_batch(self, entities: List[Tuple[CodeEntity, int]]):
        """Add multiple entities to the vector store efficiently."""
        if not entities:
            return
            
        embeddings = []
        documents = []
        metadatas = []
        ids = []
        
        # Process in batches
        for entity, project_id in entities:
            # Create embedding
            entity_data = {
                'name': entity.name,
                'entity_type': entity.entity_type,
                'signature': entity.signature,
                'docstring': entity.docstring,
                'dependencies': entity.dependencies or []
            }
            
            embedding = self.embedding_generator.create_code_embedding(entity_data)
            embeddings.append(embedding)
            
            # Document for full-text search
            doc = entity.docstring or entity.signature or entity.name
            documents.append(doc)
            
            # Metadata
            metadata = {
                'entity_id': entity.id,
                'file_id': entity.file_id,
                'project_id': project_id,
                'name': entity.name,
                'entity_type': entity.entity_type,
                'start_line': entity.start_line,
                'end_line': entity.end_line
            }
            metadatas.append(metadata)
            
            # ID
            ids.append(f"entity_{entity.id}")
            
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
    def search(self, query: str, project_id: Optional[int] = None, 
              n_results: int = 10, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar code entities."""
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Build filter
        where_filter = {}
        if project_id is not None:
            where_filter['project_id'] = project_id
        if filter_type:
            where_filter['entity_type'] = filter_type
            
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None,
            include=['metadatas', 'documents', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['metadatas'] and results['metadatas'][0]:
            for i, metadata in enumerate(results['metadatas'][0]):
                formatted_results.append({
                    'metadata': metadata,
                    'document': results['documents'][0][i] if results['documents'] else None,
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'relevance_score': 1.0 - results['distances'][0][i] if results['distances'] else 0
                })
                
        return formatted_results
        
    def search_similar_entities(self, entity_id: int, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find entities similar to a given entity."""
        # Get the entity's embedding
        try:
            result = self.collection.get(
                ids=[f"entity_{entity_id}"],
                include=['embeddings']
            )
            
            if not result['embeddings']:
                return []
                
            embedding = result['embeddings'][0]
            
            # Search for similar
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results + 1,  # +1 because it will include itself
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format and exclude self
            formatted_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    if metadata.get('entity_id') != entity_id:
                        formatted_results.append({
                            'metadata': metadata,
                            'document': results['documents'][0][i] if results['documents'] else None,
                            'distance': results['distances'][0][i] if results['distances'] else None,
                            'relevance_score': 1.0 - results['distances'][0][i] if results['distances'] else 0
                        })
                        
            return formatted_results[:n_results]
            
        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return []
            
    def delete_project_entities(self, project_id: int):
        """Delete all entities for a project."""
        # ChromaDB doesn't support efficient bulk delete by metadata
        # So we need to query all IDs first
        all_results = self.collection.get(
            where={'project_id': project_id}
        )
        
        if all_results['ids']:
            self.collection.delete(ids=all_results['ids'])
            
    def update_entity(self, entity: CodeEntity, project_id: int):
        """Update an existing entity."""
        # Delete old version
        self.collection.delete(ids=[f"entity_{entity.id}"])
        
        # Add new version
        self.add_entity(entity, project_id)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        count = self.collection.count()
        
        # Get sample to check dimensionality
        sample = self.collection.peek(limit=1)
        embedding_dim = len(sample['embeddings'][0]) if sample['embeddings'] else 0
        
        return {
            'total_entities': count,
            'embedding_dimension': embedding_dim,
            'store_path': str(self.store_path)
        }
        
    def clear(self):
        """Clear all data from the vector store."""
        self.client.delete_collection("code_entities")
        self.collection = self.client.create_collection(
            name="code_entities",
            metadata={"description": "Code entities with embeddings"}
        )