"""
Pluggable search backends for the Common Sense Engine.

Supports:
  - KeywordSearch: SQLite LIKE with keyword decomposition (no deps)
  - TFIDFSearch: TF-IDF cosine similarity (requires scikit-learn)
  - EmbeddingSearch: Sentence-transformer embeddings (requires sentence-transformers)
  - HybridSearch: Combines keyword + semantic for best recall

Usage:
    backend = get_best_backend(db_path)
    results = backend.search("deploy to wrong path", memory_type="correction", limit=10)
"""

import json
import sqlite3
import hashlib
import math
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SearchResult:
    """A single search result with scoring metadata."""
    id: int
    content: str
    score: float
    memory_type: str = ""
    project: str = ""
    importance: int = 5
    tags: str = "[]"
    created_at: str = ""
    domain: str = ""
    status: str = "active"
    helped_count: int = 0
    not_helped_count: int = 0

    @property
    def effectiveness(self) -> float:
        total = self.helped_count + self.not_helped_count
        if total == 0:
            return 0.5  # Unknown effectiveness = neutral
        return self.helped_count / total

    @property
    def parsed_tags(self) -> list:
        try:
            return json.loads(self.tags) if self.tags else []
        except (json.JSONDecodeError, TypeError):
            return []


STOP_WORDS = frozenset({
    "a", "an", "the", "to", "in", "on", "at", "is", "it", "of",
    "and", "or", "all", "for", "be", "was", "were", "been", "are",
    "this", "that", "with", "from", "but", "not", "by", "as", "do",
    "if", "so", "no", "up", "out", "has", "had", "have", "will",
    "can", "may", "should", "would", "could", "their", "they",
    "its", "my", "your", "his", "her", "our", "we", "you", "i",
})


def extract_keywords(text: str, min_length: int = 2) -> list[str]:
    """Extract meaningful keywords from text, removing stop words."""
    words = re.findall(r'[a-z0-9_\-]+', text.lower())
    return [w for w in words if len(w) >= min_length and w not in STOP_WORDS]


def _row_to_result(row: dict, score: float = 1.0) -> SearchResult:
    """Convert a database row dict to a SearchResult."""
    return SearchResult(
        id=row.get("id", 0),
        content=row.get("content", ""),
        score=score,
        memory_type=row.get("memory_type", ""),
        project=row.get("project", ""),
        importance=row.get("importance", 5),
        tags=row.get("tags", "[]"),
        created_at=row.get("created_at", ""),
        domain=row.get("domain", ""),
        status=row.get("status", "active"),
        helped_count=row.get("helped_count", 0),
        not_helped_count=row.get("not_helped_count", 0),
    )


# ─── BASE CLASS ──────────────────────────────────────────────────

class SearchBackend(ABC):
    """Abstract search backend."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    @abstractmethod
    def search(self, query: str, memory_type: str = None,
               project: str = None, limit: int = 10,
               status: str = "active") -> list[SearchResult]:
        """Search corrections by relevance."""
        ...

    @abstractmethod
    def index(self):
        """Rebuild the search index from current database state."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def _get_rows(self, memory_type: str = None, project: str = None,
                  status: str = "active") -> list[dict]:
        """Fetch rows from the database with optional filters."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM memories WHERE 1=1"
            params = []

            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)

            if project and project != "general":
                sql += " AND (project = ? OR project IS NULL OR project = 'general')"
                params.append(project)

            if status:
                # Handle databases that don't have status column yet
                sql += " AND (status = ? OR status IS NULL)"
                params.append(status)

            sql += " ORDER BY importance DESC, created_at DESC"

            cursor = conn.execute(sql, params)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(f"DB read failed: {e}", file=sys.stderr)
            return []


# ─── KEYWORD SEARCH ──────────────────────────────────────────────

class KeywordSearch(SearchBackend):
    """Keyword-decomposed search using SQLite LIKE with OR matching and scoring."""

    @property
    def name(self) -> str:
        return "keyword"

    def search(self, query: str, memory_type: str = None,
               project: str = None, limit: int = 10,
               status: str = "active") -> list[SearchResult]:
        keywords = extract_keywords(query)
        if not keywords:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Build scoring: count how many keywords match
            score_expr = " + ".join(
                ["(CASE WHEN LOWER(content) LIKE ? THEN 1 ELSE 0 END)"]
                * len(keywords)
            )
            where_clauses = " OR ".join(
                ["LOWER(content) LIKE ?"] * len(keywords)
            )

            sql = f"""
                SELECT *, ({score_expr}) as match_score
                FROM memories
                WHERE ({where_clauses})
            """
            # Score params + WHERE params
            params = [f"%{kw}%" for kw in keywords] * 2

            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)

            if project and project != "general":
                sql += " AND (project = ? OR project IS NULL OR project = 'general')"
                params.append(project)

            if status:
                sql += " AND (status = ? OR status IS NULL)"
                params.append(status)

            sql += " ORDER BY match_score DESC, importance DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                score = row_dict.pop("match_score", 1) / max(len(keywords), 1)
                results.append(_row_to_result(row_dict, score=score))

            conn.close()
            return results
        except Exception as e:
            print(f"Keyword search failed: {e}", file=sys.stderr)
            return []

    def index(self):
        pass  # No indexing needed for keyword search


# ─── TF-IDF SEARCH ───────────────────────────────────────────────

class TFIDFSearch(SearchBackend):
    """TF-IDF cosine similarity search. Requires scikit-learn."""

    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._vectorizer = None
        self._matrix = None
        self._row_ids = []
        self._row_data = []
        self._indexed = False

    @property
    def name(self) -> str:
        return "tfidf"

    def index(self):
        """Build TF-IDF matrix from all corrections in the database."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        rows = self._get_rows(status=None)  # Index everything
        if not rows:
            self._indexed = True
            return

        self._row_ids = [r["id"] for r in rows]
        self._row_data = rows
        texts = [r.get("content", "") for r in rows]

        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        self._indexed = True

    def search(self, query: str, memory_type: str = None,
               project: str = None, limit: int = 10,
               status: str = "active") -> list[SearchResult]:
        from sklearn.metrics.pairwise import cosine_similarity

        if not self._indexed:
            self.index()

        if self._matrix is None or self._matrix.shape[0] == 0:
            return []

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._matrix).flatten()

        # Get top-k indices
        top_indices = similarities.argsort()[::-1]

        results = []
        for idx in top_indices:
            if len(results) >= limit:
                break
            score = float(similarities[idx])
            if score < 0.01:
                break  # Below relevance threshold

            row = self._row_data[idx]

            # Apply filters
            if memory_type and row.get("memory_type") != memory_type:
                continue
            if project and project != "general":
                row_project = row.get("project", "")
                if row_project and row_project != project and row_project != "general":
                    continue
            if status:
                row_status = row.get("status", "active")
                if row_status and row_status != status:
                    continue

            results.append(_row_to_result(row, score=score))

        return results

    def invalidate(self):
        """Mark index as stale so it rebuilds on next search."""
        self._indexed = False


# ─── EMBEDDING SEARCH ────────────────────────────────────────────

class EmbeddingSearch(SearchBackend):
    """Sentence-transformer embedding search. Best quality, requires sentence-transformers."""

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, db_path: str, model_name: str = None):
        super().__init__(db_path)
        self._model = None
        self._model_name = model_name or self.MODEL_NAME
        self._embeddings = None
        self._row_ids = []
        self._row_data = []
        self._indexed = False

    @property
    def name(self) -> str:
        return "embedding"

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    def index(self):
        """Build embedding index from all corrections."""
        self._load_model()

        rows = self._get_rows(status=None)
        if not rows:
            self._indexed = True
            return

        self._row_ids = [r["id"] for r in rows]
        self._row_data = rows
        texts = [r.get("content", "") for r in rows]

        self._embeddings = self._model.encode(texts, convert_to_numpy=True,
                                               show_progress_bar=False)
        self._indexed = True

    def search(self, query: str, memory_type: str = None,
               project: str = None, limit: int = 10,
               status: str = "active") -> list[SearchResult]:
        import numpy as np

        if not self._indexed:
            self.index()

        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        self._load_model()
        query_embedding = self._model.encode([query], convert_to_numpy=True)

        # Cosine similarity
        similarities = np.dot(self._embeddings, query_embedding.T).flatten()
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_embedding)
        norms = np.maximum(norms, 1e-10)
        similarities = similarities / norms

        top_indices = similarities.argsort()[::-1]

        results = []
        for idx in top_indices:
            if len(results) >= limit:
                break
            score = float(similarities[idx])
            if score < 0.1:
                break

            row = self._row_data[idx]

            if memory_type and row.get("memory_type") != memory_type:
                continue
            if project and project != "general":
                row_project = row.get("project", "")
                if row_project and row_project != project and row_project != "general":
                    continue
            if status:
                row_status = row.get("status", "active")
                if row_status and row_status != status:
                    continue

            results.append(_row_to_result(row, score=score))

        return results

    def invalidate(self):
        self._indexed = False


# ─── HYBRID SEARCH ───────────────────────────────────────────────

class HybridSearch(SearchBackend):
    """Combines keyword search with semantic search for best recall.

    Runs both backends, merges results, and re-ranks by combined score.
    """

    def __init__(self, db_path: str, keyword_weight: float = 0.3,
                 semantic_weight: float = 0.7,
                 semantic_backend: SearchBackend = None):
        super().__init__(db_path)
        self.keyword = KeywordSearch(db_path)
        self.semantic = semantic_backend or _detect_semantic_backend(db_path)
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight

    @property
    def name(self) -> str:
        return f"hybrid(keyword+{self.semantic.name})"

    def search(self, query: str, memory_type: str = None,
               project: str = None, limit: int = 10,
               status: str = "active") -> list[SearchResult]:

        # Run both searches with expanded limit
        kw_results = self.keyword.search(query, memory_type, project,
                                          limit=limit * 2, status=status)
        sem_results = self.semantic.search(query, memory_type, project,
                                            limit=limit * 2, status=status)

        # Merge by ID, combine scores
        merged: dict[int, SearchResult] = {}

        for r in kw_results:
            merged[r.id] = SearchResult(
                id=r.id, content=r.content,
                score=r.score * self.keyword_weight,
                memory_type=r.memory_type, project=r.project,
                importance=r.importance, tags=r.tags,
                created_at=r.created_at, domain=r.domain,
                status=r.status, helped_count=r.helped_count,
                not_helped_count=r.not_helped_count,
            )

        for r in sem_results:
            if r.id in merged:
                merged[r.id].score += r.score * self.semantic_weight
            else:
                merged[r.id] = SearchResult(
                    id=r.id, content=r.content,
                    score=r.score * self.semantic_weight,
                    memory_type=r.memory_type, project=r.project,
                    importance=r.importance, tags=r.tags,
                    created_at=r.created_at, domain=r.domain,
                    status=r.status, helped_count=r.helped_count,
                    not_helped_count=r.not_helped_count,
                )

        # Sort by combined score, apply importance boost
        ranked = sorted(merged.values(),
                        key=lambda r: r.score * (1 + r.importance / 20),
                        reverse=True)

        return ranked[:limit]

    def index(self):
        self.keyword.index()
        self.semantic.index()

    def invalidate(self):
        if hasattr(self.semantic, 'invalidate'):
            self.semantic.invalidate()


# ─── BACKEND DETECTION ───────────────────────────────────────────

def _detect_semantic_backend(db_path: str) -> SearchBackend:
    """Auto-detect the best available semantic search backend."""
    # Try sentence-transformers first (best quality)
    # Use Exception (not just ImportError) to catch broken installs
    try:
        import sentence_transformers  # noqa: F401
        return EmbeddingSearch(db_path)
    except Exception:
        pass

    # Try scikit-learn (good quality, lighter weight)
    try:
        import sklearn  # noqa: F401
        return TFIDFSearch(db_path)
    except Exception:
        pass

    # Fallback to keyword (always available)
    return KeywordSearch(db_path)


def get_best_backend(db_path: str) -> SearchBackend:
    """Get the best available search backend, preferring hybrid when possible.

    Returns:
        HybridSearch if a semantic backend is available,
        KeywordSearch otherwise.
    """
    semantic = _detect_semantic_backend(db_path)

    # If the semantic backend IS keyword, no point in hybrid
    if isinstance(semantic, KeywordSearch):
        return semantic

    return HybridSearch(db_path, semantic_backend=semantic)


def get_backend_by_name(name: str, db_path: str) -> SearchBackend:
    """Get a specific search backend by name."""
    backends = {
        "keyword": KeywordSearch,
        "tfidf": TFIDFSearch,
        "embedding": EmbeddingSearch,
    }
    cls = backends.get(name)
    if cls is None:
        raise ValueError(f"Unknown backend: {name}. Available: {list(backends.keys())}")
    return cls(db_path)
