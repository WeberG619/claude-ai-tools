#!/usr/bin/env python3
"""
Graph Memory — Lightweight entity-relationship memory with vector search.

Uses fastembed for vector embeddings + SQLite for entity/relationship graph.
No external LLM or API keys required. Complements the existing memories.db.

Usage:
    from graph_memory import GraphMemory
    gm = GraphMemory()
    gm.add("Weber prefers named pipes for Revit", entities=["Weber", "Revit"], tags=["preference"])
    results = gm.search("How does Weber connect to Revit?")
    related = gm.get_related("Revit")
    corrections = gm.get_corrections_for_tool("mcp__revit")
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

DATA_DIR = Path("/mnt/d/_CLAUDE-TOOLS/graph-memory/data")
DB_PATH = DATA_DIR / "graph.db"
EXISTING_MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")

# Try to use fastembed for vector search (already installed for mem0)
try:
    from fastembed import TextEmbedding
    _EMBEDDER = None

    def _get_embedder():
        global _EMBEDDER
        if _EMBEDDER is None:
            _EMBEDDER = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return _EMBEDDER

    def _embed(text: str) -> List[float]:
        embedder = _get_embedder()
        return list(embedder.embed([text]))[0].tolist()

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

    def _embed(text: str) -> List[float]:
        return []


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_entities_simple(text: str) -> List[str]:
    """Simple entity extraction without LLM — uses capitalized words and known patterns."""
    entities = set()

    # Capitalized multi-word names (e.g., "Weber Gouin", "BIM Ops Studio")
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
        entities.add(match.group(1))

    # Known tool/system patterns
    for match in re.finditer(r'(mcp__\w+|Revit\w*|Bluebeam|AutoCAD|Excel|Chrome|RevitMCPBridge\d*)', text):
        entities.add(match.group(1))

    # Technical terms in backticks
    for match in re.finditer(r'`([^`]+)`', text):
        entities.add(match.group(1))

    # Filter out common words that aren't entities
    stop_words = {"The", "This", "That", "These", "Those", "When", "Where", "What",
                  "How", "Why", "Which", "After", "Before", "Always", "Never", "Should",
                  "Could", "Would", "Must", "True", "False", "None", "Not", "But", "And",
                  "For", "With", "From", "Into", "Also", "Only", "Just", "Still", "Each"}
    entities = {e for e in entities if e not in stop_words and len(e) > 1}

    return list(entities)


class GraphMemory:
    """Lightweight graph memory with vector search and entity relationships."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'fact',
                importance INTEGER DEFAULT 5,
                project TEXT DEFAULT 'General',
                tags TEXT DEFAULT '[]',
                entities TEXT DEFAULT '[]',
                embedding BLOB,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT DEFAULT 'unknown',
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity TEXT NOT NULL,
                target_entity TEXT NOT NULL,
                relationship_type TEXT DEFAULT 'related_to',
                context TEXT,
                memory_id INTEGER,
                created_at TEXT NOT NULL,
                strength INTEGER DEFAULT 1,
                FOREIGN KEY (memory_id) REFERENCES memories(id),
                UNIQUE(source_entity, target_entity, relationship_type)
            );

            CREATE TABLE IF NOT EXISTS entity_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                fact TEXT NOT NULL,
                fact_type TEXT DEFAULT 'state',
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                memory_id INTEGER,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity);
            CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entity);
            CREATE INDEX IF NOT EXISTS idx_timeline_entity ON entity_timeline(entity);
        """)
        conn.close()

    def add(self, content: str, memory_type: str = "fact", importance: int = 5,
            project: str = "General", tags: List[str] = None, entities: List[str] = None) -> int:
        """Add a memory with auto entity extraction and relationship building."""
        now = datetime.now().isoformat()
        tags = tags or []

        # Auto-extract entities if not provided
        if entities is None:
            entities = _extract_entities_simple(content)

        # Generate embedding
        embedding = None
        if VECTOR_AVAILABLE:
            try:
                embedding = json.dumps(_embed(content))
            except Exception:
                pass

        conn = sqlite3.connect(str(self.db_path))

        # Insert memory
        cursor = conn.execute(
            """INSERT INTO memories (content, memory_type, importance, project, tags, entities, embedding, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (content, memory_type, importance, project, json.dumps(tags),
             json.dumps(entities), embedding, now, now)
        )
        memory_id = cursor.lastrowid

        # Upsert entities
        for entity in entities:
            conn.execute(
                """INSERT INTO entities (name, first_seen, last_seen, mention_count)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(name) DO UPDATE SET
                     last_seen = ?, mention_count = mention_count + 1""",
                (entity, now, now, now)
            )

        # Create relationships between co-occurring entities
        for i, src in enumerate(entities):
            for tgt in entities[i + 1:]:
                conn.execute(
                    """INSERT INTO relationships (source_entity, target_entity, relationship_type, context, memory_id, created_at, strength)
                       VALUES (?, ?, 'co_occurs', ?, ?, ?, 1)
                       ON CONFLICT(source_entity, target_entity, relationship_type) DO UPDATE SET
                         strength = strength + 1, context = ?""",
                    (src, tgt, content[:200], memory_id, now, content[:200])
                )

        # Add to entity timeline
        for entity in entities:
            conn.execute(
                """INSERT INTO entity_timeline (entity, fact, fact_type, valid_from, memory_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (entity, content[:500], memory_type, now, memory_id)
            )

        conn.commit()
        conn.close()
        return memory_id

    def add_correction(self, what_wrong: str, correct_approach: str,
                       tool: str = None, project: str = "General") -> int:
        """Store a correction with entity links to the relevant tool/context."""
        content = f"CORRECTION: {what_wrong}\nCORRECT: {correct_approach}"
        entities = _extract_entities_simple(content)
        if tool:
            entities.append(tool)
        tags = ["correction"]
        if tool:
            tags.append(f"tool:{tool}")
        return self.add(content, memory_type="correction", importance=9,
                        project=project, tags=tags, entities=entities)

    def search(self, query: str, limit: int = 5, project: str = None) -> List[Dict]:
        """Hybrid search: vector similarity + keyword matching."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        results = []

        # Vector search
        if VECTOR_AVAILABLE:
            try:
                query_emb = _embed(query)
                cursor = conn.execute("SELECT id, content, memory_type, importance, project, tags, entities, embedding, created_at FROM memories WHERE embedding IS NOT NULL")
                scored = []
                for row in cursor:
                    mem_emb = json.loads(row["embedding"])
                    sim = _cosine_similarity(query_emb, mem_emb)
                    scored.append((sim, dict(row)))
                scored.sort(key=lambda x: x[0], reverse=True)
                for sim, row in scored[:limit * 2]:
                    if sim > 0.3:
                        row["score"] = round(sim, 3)
                        row.pop("embedding", None)
                        results.append(row)
            except Exception:
                pass

        # Keyword fallback/supplement
        query_words = set(query.lower().split())
        where_clauses = []
        params = []
        for word in query_words:
            if len(word) > 2:
                where_clauses.append("LOWER(content) LIKE ?")
                params.append(f"%{word}%")

        if where_clauses:
            sql = f"SELECT id, content, memory_type, importance, project, tags, entities, created_at FROM memories WHERE {' OR '.join(where_clauses)}"
            if project:
                sql += " AND project = ?"
                params.append(project)
            sql += " ORDER BY importance DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            existing_ids = {r["id"] for r in results}
            for row in cursor:
                if row["id"] not in existing_ids:
                    d = dict(row)
                    d["score"] = 0.1  # keyword match baseline
                    results.append(d)

        conn.close()

        # Sort by score, return top N
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    def get_related(self, entity: str, limit: int = 10) -> Dict[str, Any]:
        """Graph traversal from an entity — find all related entities and memories."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Get direct relationships
        cursor = conn.execute(
            """SELECT target_entity as related, relationship_type, strength, context
               FROM relationships WHERE source_entity = ?
               UNION
               SELECT source_entity as related, relationship_type, strength, context
               FROM relationships WHERE target_entity = ?
               ORDER BY strength DESC LIMIT ?""",
            (entity, entity, limit)
        )
        relationships = [dict(row) for row in cursor]

        # Get entity timeline
        cursor = conn.execute(
            """SELECT fact, fact_type, valid_from, valid_to
               FROM entity_timeline WHERE entity = ?
               ORDER BY valid_from DESC LIMIT 10""",
            (entity,)
        )
        timeline = [dict(row) for row in cursor]

        # Get entity info
        cursor = conn.execute("SELECT * FROM entities WHERE name = ?", (entity,))
        entity_info = None
        row = cursor.fetchone()
        if row:
            entity_info = dict(row)

        conn.close()

        return {
            "entity": entity,
            "info": entity_info,
            "relationships": relationships,
            "timeline": timeline
        }

    def get_corrections_for_tool(self, tool_name: str) -> List[Dict]:
        """Get all corrections related to a specific tool."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """SELECT id, content, project, created_at, tags
               FROM memories
               WHERE memory_type = 'correction'
                 AND (tags LIKE ? OR entities LIKE ? OR content LIKE ?)
               ORDER BY created_at DESC""",
            (f'%{tool_name}%', f'%{tool_name}%', f'%{tool_name}%')
        )
        results = [dict(row) for row in cursor]
        conn.close()
        return results

    def get_entity_timeline(self, entity: str) -> List[Dict]:
        """How facts about an entity changed over time."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """SELECT fact, fact_type, valid_from, valid_to
               FROM entity_timeline WHERE entity = ?
               ORDER BY valid_from ASC""",
            (entity,)
        )
        results = [dict(row) for row in cursor]
        conn.close()
        return results

    def sync_from_sqlite(self, sqlite_path: Path = EXISTING_MEMORY_DB) -> int:
        """One-time import from existing memories.db into graph memory."""
        if not sqlite_path.exists():
            print(f"Source DB not found: {sqlite_path}")
            return 0

        src = sqlite3.connect(str(sqlite_path))
        src.row_factory = sqlite3.Row

        cursor = src.execute(
            "SELECT content, memory_type, importance, project, created_at FROM memories ORDER BY created_at"
        )

        count = 0
        for row in cursor:
            content = row["content"] or ""
            if not content.strip():
                continue

            entities = _extract_entities_simple(content)
            memory_type = row["memory_type"] or "fact"
            if "CORRECTION" in content:
                memory_type = "correction"

            self.add(
                content=content,
                memory_type=memory_type,
                importance=row["importance"] or 5,
                project=row["project"] or "General",
                entities=entities
            )
            count += 1
            if count % 50 == 0:
                print(f"  Imported {count} memories...")

        src.close()
        print(f"Imported {count} total memories from {sqlite_path}")
        return count

    def stats(self) -> Dict:
        """Get graph memory statistics."""
        conn = sqlite3.connect(str(self.db_path))
        stats = {}
        stats["memories"] = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        stats["entities"] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        stats["relationships"] = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        stats["timeline_entries"] = conn.execute("SELECT COUNT(*) FROM entity_timeline").fetchone()[0]
        stats["corrections"] = conn.execute("SELECT COUNT(*) FROM memories WHERE memory_type='correction'").fetchone()[0]
        stats["vector_enabled"] = VECTOR_AVAILABLE

        # Top entities by mention count
        cursor = conn.execute("SELECT name, mention_count FROM entities ORDER BY mention_count DESC LIMIT 10")
        stats["top_entities"] = [(row[0], row[1]) for row in cursor]

        conn.close()
        return stats


# ============ CLI ============

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Graph Memory CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Show graph memory statistics")
    sub.add_parser("sync", help="Import from existing memories.db")

    search_p = sub.add_parser("search", help="Search memories")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5)

    related_p = sub.add_parser("related", help="Get related entities")
    related_p.add_argument("entity", help="Entity name")

    corr_p = sub.add_parser("corrections", help="Get corrections for a tool")
    corr_p.add_argument("tool", help="Tool name pattern")

    timeline_p = sub.add_parser("timeline", help="Entity timeline")
    timeline_p.add_argument("entity", help="Entity name")

    args = parser.parse_args()
    gm = GraphMemory()

    if args.command == "stats":
        s = gm.stats()
        print(f"Graph Memory Stats:")
        print(f"  Memories: {s['memories']}")
        print(f"  Entities: {s['entities']}")
        print(f"  Relationships: {s['relationships']}")
        print(f"  Timeline entries: {s['timeline_entries']}")
        print(f"  Corrections: {s['corrections']}")
        print(f"  Vector search: {'enabled' if s['vector_enabled'] else 'disabled'}")
        if s["top_entities"]:
            print(f"\n  Top entities:")
            for name, count in s["top_entities"]:
                print(f"    {name}: {count} mentions")

    elif args.command == "sync":
        count = gm.sync_from_sqlite()
        print(f"Done. Imported {count} memories.")

    elif args.command == "search":
        results = gm.search(args.query, limit=args.limit)
        for r in results:
            print(f"\n[{r.get('memory_type', '?')}] score={r.get('score', '?')} | {r.get('project', '?')}")
            print(f"  {r['content'][:200]}")

    elif args.command == "related":
        data = gm.get_related(args.entity)
        if data["info"]:
            print(f"Entity: {data['info']['name']} (seen {data['info']['mention_count']}x)")
        print(f"\nRelationships ({len(data['relationships'])}):")
        for rel in data["relationships"]:
            print(f"  → {rel['related']} ({rel['relationship_type']}, strength={rel['strength']})")
        print(f"\nTimeline ({len(data['timeline'])}):")
        for entry in data["timeline"]:
            print(f"  [{entry['valid_from'][:10]}] {entry['fact'][:100]}")

    elif args.command == "corrections":
        results = gm.get_corrections_for_tool(args.tool)
        print(f"Corrections for '{args.tool}': {len(results)}")
        for r in results:
            print(f"\n  [{r['created_at'][:10]}] {r['project']}")
            print(f"  {r['content'][:200]}")

    elif args.command == "timeline":
        entries = gm.get_entity_timeline(args.entity)
        print(f"Timeline for '{args.entity}': {len(entries)} entries")
        for e in entries:
            status = f" → ended {e['valid_to'][:10]}" if e.get("valid_to") else " (current)"
            print(f"  [{e['valid_from'][:10]}]{status} {e['fact'][:100]}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
