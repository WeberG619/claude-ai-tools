"""Embedding generation for code entities."""

import logging
from typing import List, Optional, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeEmbeddingGenerator:
    """Generates embeddings for code entities using various techniques."""
    
    def __init__(self, embedding_dim: int = 768, use_openai: bool = False, api_key: Optional[str] = None):
        self.embedding_dim = embedding_dim
        self.use_openai = use_openai
        self.api_key = api_key
        
        # TF-IDF vectorizer for fallback
        self.tfidf_vectorizer = None
        self.tfidf_fitted = False
        
        if use_openai and api_key:
            try:
                import openai
                self.openai_client = openai.Client(api_key=api_key)
            except ImportError:
                logger.warning("OpenAI not installed, falling back to TF-IDF")
                self.use_openai = False
                
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.use_openai and hasattr(self, 'openai_client'):
            return self._generate_openai_embedding(text)
        else:
            return self._generate_tfidf_embedding(text)
            
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        if self.use_openai and hasattr(self, 'openai_client'):
            return [self._generate_openai_embedding(text) for text in texts]
        else:
            return self._generate_tfidf_embeddings_batch(texts)
            
    def create_code_embedding(self, entity: Dict[str, Any]) -> List[float]:
        """Create embedding for a code entity combining multiple signals."""
        # Combine different parts of the entity
        text_parts = []
        
        # Name is most important
        if entity.get('name'):
            text_parts.append(f"name: {entity['name']}")
            
        # Entity type
        if entity.get('entity_type'):
            text_parts.append(f"type: {entity['entity_type']}")
            
        # Signature provides context
        if entity.get('signature'):
            text_parts.append(f"signature: {entity['signature']}")
            
        # Docstring for semantic meaning
        if entity.get('docstring'):
            text_parts.append(f"description: {entity['docstring']}")
            
        # Dependencies for relationships
        if entity.get('dependencies'):
            deps = ', '.join(entity['dependencies'][:10])  # Limit dependencies
            text_parts.append(f"uses: {deps}")
            
        combined_text = " | ".join(text_parts)
        return self.generate_embedding(combined_text)
        
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=self.embedding_dim
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            # Fall back to TF-IDF
            return self._generate_tfidf_embedding(text)
            
    def _generate_tfidf_embedding(self, text: str) -> List[float]:
        """Generate embedding using TF-IDF."""
        if not self.tfidf_fitted:
            # Initialize with a simple vocabulary if not fitted
            self._fit_tfidf_on_programming_vocabulary()
            
        # Transform text
        try:
            vector = self.tfidf_vectorizer.transform([text]).toarray()[0]
            # Pad or truncate to match embedding dimension
            if len(vector) < self.embedding_dim:
                vector = np.pad(vector, (0, self.embedding_dim - len(vector)))
            else:
                vector = vector[:self.embedding_dim]
            return vector.tolist()
        except Exception as e:
            logger.error(f"Error generating TF-IDF embedding: {e}")
            # Return random embedding as last resort
            return np.random.rand(self.embedding_dim).tolist()
            
    def _generate_tfidf_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate TF-IDF embeddings for multiple texts."""
        if not self.tfidf_fitted:
            self._fit_tfidf_on_texts(texts)
            
        vectors = self.tfidf_vectorizer.transform(texts).toarray()
        
        # Adjust dimensions
        result = []
        for vector in vectors:
            if len(vector) < self.embedding_dim:
                vector = np.pad(vector, (0, self.embedding_dim - len(vector)))
            else:
                vector = vector[:self.embedding_dim]
            result.append(vector.tolist())
            
        return result
        
    def _fit_tfidf_on_texts(self, texts: List[str]):
        """Fit TF-IDF vectorizer on provided texts."""
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.embedding_dim,
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.tfidf_vectorizer.fit(texts)
        self.tfidf_fitted = True
        
    def _fit_tfidf_on_programming_vocabulary(self):
        """Fit TF-IDF on common programming terms."""
        # Common programming vocabulary
        vocab = [
            "function", "class", "method", "variable", "constant",
            "import", "export", "return", "if", "else", "for", "while",
            "try", "catch", "except", "finally", "async", "await",
            "public", "private", "protected", "static", "abstract",
            "interface", "extends", "implements", "constructor",
            "get", "set", "post", "put", "delete", "update", "create",
            "read", "write", "open", "close", "connect", "disconnect",
            "initialize", "setup", "teardown", "test", "assert",
            "error", "exception", "warning", "info", "debug",
            "array", "list", "dict", "map", "set", "tuple",
            "string", "number", "boolean", "null", "undefined"
        ]
        
        # Create combinations
        texts = []
        for i in range(100):
            # Random combinations of terms
            sample = np.random.choice(vocab, size=5, replace=False)
            texts.append(" ".join(sample))
            
        self._fit_tfidf_on_texts(texts)
        
    def save_vectorizer(self, path: Path):
        """Save the TF-IDF vectorizer to disk."""
        if self.tfidf_vectorizer and self.tfidf_fitted:
            with open(path, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
                
    def load_vectorizer(self, path: Path):
        """Load TF-IDF vectorizer from disk."""
        if path.exists():
            with open(path, 'rb') as f:
                self.tfidf_vectorizer = pickle.load(f)
                self.tfidf_fitted = True