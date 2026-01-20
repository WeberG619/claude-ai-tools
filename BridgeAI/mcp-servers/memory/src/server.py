#!/usr/bin/env python3
"""
Claude Memory MCP Server
Provides persistent memory storage and retrieval for Claude Code sessions.
"""

import json
import sqlite3
import os
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP

# Lazy load embedding model to avoid slow startup
_embedding_model = None

def get_embedding_model():
    """Lazy load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            return None
    return _embedding_model

def generate_embedding(text: str) -> bytes:
    """Generate embedding for text and return as bytes for storage."""
    model = get_embedding_model()
    if model is None:
        return None

    embeddings = list(model.embed([text]))
    if embeddings:
        return np.array(embeddings[0]).tobytes()
    return None

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Initialize FastMCP server
mcp = FastMCP("claude-memory")

# Database path - use relative path from server location for portability
_SERVER_DIR = Path(__file__).parent.parent
DB_PATH = _SERVER_DIR / "data" / "memories.db"

def get_db():
    """Get database connection with row factory and crash protection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Enable WAL mode for crash protection and better concurrency
    conn.execute("PRAGMA journal_mode = WAL")
    # Ensure data is written to disk
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def verify_database_integrity():
    """Check database integrity and attempt recovery if needed."""
    import sys
    import shutil
    from glob import glob

    if not DB_PATH.exists():
        print("Database does not exist, will be created.")
        return True

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            print(f"Database integrity check: OK ({DB_PATH})")
            return True
        else:
            print(f"WARNING: Database integrity check failed: {result}")
            # Try to recover from backup
            return attempt_recovery()
    except Exception as e:
        print(f"ERROR checking database: {e}")
        return attempt_recovery()


def attempt_recovery():
    """Attempt to recover database from most recent backup."""
    import shutil
    from glob import glob

    backup_dir = DB_PATH.parent.parent / "backups" / "hourly"
    backups = sorted(glob(str(backup_dir / "memory_*.db")), reverse=True)

    if not backups:
        print("No backups found for recovery!")
        return False

    print(f"Attempting recovery from: {backups[0]}")

    # Backup corrupt database
    corrupt_path = DB_PATH.with_suffix(".db.corrupt")
    if DB_PATH.exists():
        shutil.move(DB_PATH, corrupt_path)
        print(f"Moved corrupt database to: {corrupt_path}")

    # Restore from backup
    shutil.copy2(backups[0], DB_PATH)
    print(f"Restored from backup: {backups[0]}")

    # Verify restored database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM memories;")
        count = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            print(f"Recovery successful! Restored {count} memories.")
            return True
        else:
            print("Recovery failed - backup also corrupt!")
            return False
    except Exception as e:
        print(f"Recovery failed: {e}")
        return False


def init_database():
    """Initialize the database schema with integrity verification."""
    # First, verify existing database integrity
    if not verify_database_integrity():
        print("WARNING: Starting with potentially compromised database!")

    conn = get_db()
    cursor = conn.cursor()

    # Core memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            project TEXT,
            tags TEXT,
            importance INTEGER DEFAULT 5,
            memory_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accessed_at TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            embedding BLOB
        )
    """)

    # Add embedding column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Full-text search virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content, summary, tags, project,
            content='memories',
            content_rowid='id'
        )
    """)

    # Triggers to keep FTS in sync
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, summary, tags, project)
            VALUES (new.id, new.content, new.summary, new.tags, new.project);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, summary, tags, project)
            VALUES('delete', old.id, old.content, old.summary, old.tags, old.project);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, summary, tags, project)
            VALUES('delete', old.id, old.content, old.summary, old.tags, old.project);
            INSERT INTO memories_fts(rowid, content, summary, tags, project)
            VALUES (new.id, new.content, new.summary, new.tags, new.project);
        END
    """)

    # Projects tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            path TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP
        )
    """)

    # Sessions history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            project TEXT,
            summary TEXT,
            memories_created INTEGER DEFAULT 0
        )
    """)

    # Memory relationships table for knowledge graph
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL DEFAULT 1.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
            UNIQUE(source_id, target_id, relationship_type)
        )
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON memory_relationships(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON memory_relationships(target_id)")

    conn.commit()
    conn.close()

# Initialize database on module load
init_database()


@mcp.tool()
def memory_store(
    content: str,
    project: str = None,
    tags: list[str] = None,
    importance: int = 5,
    memory_type: str = "context",
    summary: str = None,
    namespace: str = "global",
    verified: bool = False,
    expires_at: str = None,
    source: str = "manual"
) -> str:
    """
    Store a new memory.

    Args:
        content: The full content of the memory
        project: Project name this memory relates to
        tags: List of tags for categorization
        importance: 1-10 scale (10 = critical)
        memory_type: One of: decision, fact, preference, context, outcome, error
        summary: Brief summary (auto-generated if not provided)
        namespace: Scope isolation (global | project:<name> | machine | revit)
        verified: Whether this memory has been verified as accurate
        expires_at: Optional ISO8601 timestamp for automatic expiration
        source: Origin of memory (manual | auto | tool)

    Returns:
        Confirmation with memory ID
    """
    conn = get_db()
    cursor = conn.cursor()

    tags_json = json.dumps(tags) if tags else None

    # Auto-generate summary if not provided
    if not summary and len(content) > 200:
        summary = content[:200] + "..."

    # Generate embedding for semantic search
    embedding = generate_embedding(content)

    # Auto-set namespace from project if not specified
    if namespace == "global" and project:
        namespace = f"project:{project}"

    cursor.execute("""
        INSERT INTO memories (content, summary, project, tags, importance, memory_type, embedding, namespace, verified, expires_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (content, summary, project, tags_json, importance, memory_type, embedding, namespace, 1 if verified else 0, expires_at, source))

    memory_id = cursor.lastrowid

    # Update project last_accessed if project specified
    if project:
        cursor.execute("""
            INSERT INTO projects (name, last_accessed)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET last_accessed = CURRENT_TIMESTAMP
        """, (project,))

    conn.commit()
    conn.close()

    return f"Memory stored with ID {memory_id} [project: {project or 'none'}, type: {memory_type}, importance: {importance}]"


@mcp.tool()
def memory_recall(
    query: str,
    project: str = None,
    memory_type: str = None,
    limit: int = 10,
    min_importance: int = 1
) -> str:
    """
    Search memories using full-text search.

    Args:
        query: Search query (supports FTS5 syntax)
        project: Filter by project name
        memory_type: Filter by type (decision, fact, preference, context, outcome, error)
        limit: Maximum results to return
        min_importance: Minimum importance level (1-10)

    Returns:
        Matching memories with relevance scores
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build the query
    sql = """
        SELECT
            m.id,
            m.content,
            m.summary,
            m.project,
            m.tags,
            m.importance,
            m.memory_type,
            m.created_at,
            m.access_count,
            bm25(memories_fts) as relevance
        FROM memories_fts
        JOIN memories m ON memories_fts.rowid = m.id
        WHERE memories_fts MATCH ?
        AND m.importance >= ?
    """

    params = [query, min_importance]

    if project:
        sql += " AND m.project = ?"
        params.append(project)

    if memory_type:
        sql += " AND m.memory_type = ?"
        params.append(memory_type)

    sql += " ORDER BY relevance LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(sql, params)
        results = cursor.fetchall()
    except sqlite3.OperationalError as e:
        conn.close()
        return f"Search error: {e}. Try simpler search terms."

    if not results:
        conn.close()
        return f"No memories found matching '{query}'"

    # Update access counts
    for row in results:
        cursor.execute("""
            UPDATE memories
            SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE id = ?
        """, (row['id'],))

    conn.commit()
    conn.close()

    # Format results
    output = [f"Found {len(results)} memories:\n"]

    for row in results:
        tags = json.loads(row['tags']) if row['tags'] else []
        output.append(f"""
---
**ID {row['id']}** | {row['memory_type']} | Importance: {row['importance']}/10
Project: {row['project'] or 'none'} | Tags: {', '.join(tags) if tags else 'none'}
Created: {row['created_at']}

{row['content']}
""")

    return '\n'.join(output)


@mcp.tool()
def memory_semantic_search(
    query: str,
    project: str = None,
    limit: int = 10,
    min_similarity: float = 0.5
) -> str:
    """
    Search memories by MEANING, not just keywords. Use this when keyword search fails
    to find what you're looking for.

    Args:
        query: Natural language description of what you're looking for
        project: Filter by project name
        limit: Maximum results to return
        min_similarity: Minimum similarity score (0-1, default 0.5)

    Returns:
        Semantically similar memories ranked by relevance
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)

    if query_embedding is None:
        return "Semantic search unavailable - embedding model not loaded. Use memory_recall for keyword search."

    query_vec = np.frombuffer(query_embedding, dtype=np.float32)

    conn = get_db()
    cursor = conn.cursor()

    # Get all memories with embeddings
    sql = "SELECT id, content, summary, project, tags, importance, memory_type, created_at, embedding FROM memories WHERE embedding IS NOT NULL"
    params = []

    if project:
        sql += " AND project = ?"
        params.append(project)

    cursor.execute(sql, params)
    results = cursor.fetchall()

    if not results:
        conn.close()
        return "No memories with embeddings found. Store new memories to enable semantic search."

    # Calculate similarities
    scored_results = []
    for row in results:
        if row['embedding']:
            mem_vec = np.frombuffer(row['embedding'], dtype=np.float32)
            similarity = cosine_similarity(query_vec, mem_vec)
            if similarity >= min_similarity:
                scored_results.append((similarity, row))

    # Sort by similarity
    scored_results.sort(key=lambda x: x[0], reverse=True)
    scored_results = scored_results[:limit]

    if not scored_results:
        conn.close()
        return f"No memories found with similarity >= {min_similarity}. Try lowering min_similarity or use keyword search."

    # Update access counts
    for _, row in scored_results:
        cursor.execute("""
            UPDATE memories
            SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE id = ?
        """, (row['id'],))

    conn.commit()
    conn.close()

    # Format results
    output = [f"# Semantic Search Results ({len(scored_results)} found)\n"]
    output.append(f"Query: \"{query}\"\n")

    for similarity, row in scored_results:
        tags = json.loads(row['tags']) if row['tags'] else []
        output.append(f"""
---
**ID {row['id']}** | Similarity: {similarity:.2%} | {row['memory_type']}
Project: {row['project'] or 'none'} | Importance: {row['importance']}/10
Tags: {', '.join(tags) if tags else 'none'}

{row['content'][:500]}{'...' if len(row['content']) > 500 else ''}
""")

    return '\n'.join(output)


@mcp.tool()
def memory_link(
    source_id: int,
    target_id: int,
    relationship_type: str,
    strength: float = 1.0,
    notes: str = None
) -> str:
    """
    Create a relationship between two memories. This builds a knowledge graph
    that helps understand how ideas connect.

    Args:
        source_id: ID of the source memory
        target_id: ID of the target memory
        relationship_type: Type of relationship:
            - "depends_on": Source depends on target
            - "evolved_from": Source evolved from target
            - "contradicts": Source contradicts target
            - "supports": Source supports target
            - "part_of": Source is part of target
            - "related_to": General relationship
        strength: Relationship strength (0-1, default 1.0)
        notes: Optional notes about the relationship

    Returns:
        Confirmation of relationship creation
    """
    conn = get_db()
    cursor = conn.cursor()

    # Verify both memories exist
    cursor.execute("SELECT id FROM memories WHERE id = ?", (source_id,))
    if not cursor.fetchone():
        conn.close()
        return f"Source memory {source_id} not found"

    cursor.execute("SELECT id FROM memories WHERE id = ?", (target_id,))
    if not cursor.fetchone():
        conn.close()
        return f"Target memory {target_id} not found"

    try:
        cursor.execute("""
            INSERT INTO memory_relationships (source_id, target_id, relationship_type, strength, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (source_id, target_id, relationship_type, strength, notes))

        conn.commit()
        conn.close()
        return f"Linked memory {source_id} --[{relationship_type}]--> {target_id}"

    except sqlite3.IntegrityError:
        conn.close()
        return f"Relationship already exists between {source_id} and {target_id} of type {relationship_type}"


@mcp.tool()
def memory_get_related(
    memory_id: int,
    relationship_types: list[str] = None,
    depth: int = 1
) -> str:
    """
    Get memories related to a specific memory through the knowledge graph.

    Args:
        memory_id: ID of the memory to find relations for
        relationship_types: Filter by types (depends_on, evolved_from, contradicts, supports, part_of, related_to)
        depth: How many levels deep to traverse (1-3)

    Returns:
        Related memories with relationship information
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get the source memory
    cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
    source = cursor.fetchone()
    if not source:
        conn.close()
        return f"Memory {memory_id} not found"

    output = [f"# Related Memories for ID {memory_id}\n"]
    output.append(f"**Source**: {source['content'][:100]}...\n")

    visited = {memory_id}
    current_level = [memory_id]

    for level in range(depth):
        if not current_level:
            break

        output.append(f"\n## Level {level + 1} Connections\n")
        next_level = []

        for mid in current_level:
            # Get outgoing relationships
            sql = """
                SELECT r.*, m.content, m.project, m.memory_type, m.importance
                FROM memory_relationships r
                JOIN memories m ON r.target_id = m.id
                WHERE r.source_id = ?
            """
            params = [mid]

            if relationship_types:
                placeholders = ','.join('?' * len(relationship_types))
                sql += f" AND r.relationship_type IN ({placeholders})"
                params.extend(relationship_types)

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                if row['target_id'] not in visited:
                    visited.add(row['target_id'])
                    next_level.append(row['target_id'])
                    output.append(f"- **ID {row['target_id']}** --[{row['relationship_type']}]--> (strength: {row['strength']})")
                    output.append(f"  Type: {row['memory_type']} | Project: {row['project'] or 'none'}")
                    output.append(f"  {row['content'][:150]}...")
                    if row['notes']:
                        output.append(f"  *Note: {row['notes']}*")
                    output.append("")

            # Get incoming relationships
            sql = """
                SELECT r.*, m.content, m.project, m.memory_type, m.importance
                FROM memory_relationships r
                JOIN memories m ON r.source_id = m.id
                WHERE r.target_id = ?
            """
            params = [mid]

            if relationship_types:
                placeholders = ','.join('?' * len(relationship_types))
                sql += f" AND r.relationship_type IN ({placeholders})"
                params.extend(relationship_types)

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                if row['source_id'] not in visited:
                    visited.add(row['source_id'])
                    next_level.append(row['source_id'])
                    output.append(f"- **ID {row['source_id']}** <--[{row['relationship_type']}]-- (strength: {row['strength']})")
                    output.append(f"  Type: {row['memory_type']} | Project: {row['project'] or 'none'}")
                    output.append(f"  {row['content'][:150]}...")
                    if row['notes']:
                        output.append(f"  *Note: {row['notes']}*")
                    output.append("")

        current_level = next_level

    conn.close()

    if len(output) == 2:
        output.append("No relationships found for this memory.")

    return '\n'.join(output)


@mcp.tool()
def memory_get_context(
    project: str = None,
    include_recent: bool = True,
    include_important: bool = True,
    include_decisions: bool = True,
    limit: int = 20
) -> str:
    """
    Get relevant context for session start. Call this at the beginning of each session.

    Args:
        project: Focus on specific project (if known)
        include_recent: Include recently created memories
        include_important: Include high-importance memories
        include_decisions: Include decision-type memories
        limit: Maximum total memories to return

    Returns:
        Formatted context for session initialization
    """
    conn = get_db()
    cursor = conn.cursor()

    memories = []

    # Get recent memories
    if include_recent:
        sql = """
            SELECT * FROM memories
            WHERE created_at > datetime('now', '-7 days')
        """
        if project:
            sql += f" AND project = ?"
            cursor.execute(sql + " ORDER BY created_at DESC LIMIT ?", (project, limit // 3))
        else:
            cursor.execute(sql + " ORDER BY created_at DESC LIMIT ?", (limit // 3,))
        memories.extend(cursor.fetchall())

    # Get important memories
    if include_important:
        sql = "SELECT * FROM memories WHERE importance >= 7"
        if project:
            sql += " AND project = ?"
            cursor.execute(sql + " ORDER BY importance DESC LIMIT ?", (project, limit // 3))
        else:
            cursor.execute(sql + " ORDER BY importance DESC LIMIT ?", (limit // 3,))
        memories.extend(cursor.fetchall())

    # Get decisions
    if include_decisions:
        sql = "SELECT * FROM memories WHERE memory_type = 'decision'"
        if project:
            sql += " AND project = ?"
            cursor.execute(sql + " ORDER BY created_at DESC LIMIT ?", (project, limit // 3))
        else:
            cursor.execute(sql + " ORDER BY created_at DESC LIMIT ?", (limit // 3,))
        memories.extend(cursor.fetchall())

    # Get project info if specified
    project_info = None
    if project:
        cursor.execute("SELECT * FROM projects WHERE name = ?", (project,))
        project_info = cursor.fetchone()

    conn.close()

    # Deduplicate
    seen_ids = set()
    unique_memories = []
    for m in memories:
        if m['id'] not in seen_ids:
            seen_ids.add(m['id'])
            unique_memories.append(m)

    if not unique_memories and not project_info:
        return "No context available. This appears to be a fresh start."

    # Format output
    output = ["# Session Context\n"]

    if project_info:
        output.append(f"""
## Active Project: {project_info['name']}
- Path: {project_info['path'] or 'not set'}
- Status: {project_info['status']}
- Last accessed: {project_info['last_accessed']}
- Description: {project_info['description'] or 'none'}
""")

    if unique_memories:
        output.append(f"\n## Relevant Memories ({len(unique_memories)} loaded)\n")

        for m in unique_memories[:limit]:
            tags = json.loads(m['tags']) if m['tags'] else []
            output.append(f"""
### [{m['memory_type'].upper()}] {m['summary'] or m['content'][:100]}
- ID: {m['id']} | Importance: {m['importance']}/10 | Project: {m['project'] or 'general'}
- Tags: {', '.join(tags) if tags else 'none'}
- Created: {m['created_at']}

{m['content']}
""")

    return '\n'.join(output)


@mcp.tool()
def memory_get_project(project: str, include_all: bool = False) -> str:
    """
    Get complete history for a specific project.

    Args:
        project: Project name
        include_all: Include all memories (not just important ones)

    Returns:
        Project information and all related memories
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get project info
    cursor.execute("SELECT * FROM projects WHERE name = ?", (project,))
    project_info = cursor.fetchone()

    # Get memories
    if include_all:
        cursor.execute("""
            SELECT * FROM memories
            WHERE project = ?
            ORDER BY created_at DESC
        """, (project,))
    else:
        cursor.execute("""
            SELECT * FROM memories
            WHERE project = ? AND (importance >= 5 OR memory_type = 'decision')
            ORDER BY importance DESC, created_at DESC
        """, (project,))

    memories = cursor.fetchall()

    # Update project last_accessed
    cursor.execute("""
        UPDATE projects SET last_accessed = CURRENT_TIMESTAMP WHERE name = ?
    """, (project,))

    conn.commit()
    conn.close()

    if not project_info and not memories:
        return f"No information found for project '{project}'"

    # Format output
    output = [f"# Project: {project}\n"]

    if project_info:
        output.append(f"""
## Project Info
- Path: {project_info['path'] or 'not set'}
- Status: {project_info['status']}
- Created: {project_info['created_at']}
- Last accessed: {project_info['last_accessed']}
- Description: {project_info['description'] or 'none'}
""")

    if memories:
        output.append(f"\n## Memories ({len(memories)} total)\n")

        # Group by type
        by_type = {}
        for m in memories:
            t = m['memory_type'] or 'context'
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m)

        for mtype, mems in by_type.items():
            output.append(f"\n### {mtype.upper()} ({len(mems)})\n")
            for m in mems:
                output.append(f"- **[{m['importance']}/10]** {m['content'][:200]}{'...' if len(m['content']) > 200 else ''}\n")

    return '\n'.join(output)


@mcp.tool()
def memory_list_projects() -> str:
    """
    List all known projects with their status and memory counts.

    Returns:
        Table of all projects
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.name,
            p.path,
            p.status,
            p.last_accessed,
            COUNT(m.id) as memory_count,
            MAX(m.created_at) as last_memory
        FROM projects p
        LEFT JOIN memories m ON p.name = m.project
        GROUP BY p.name
        ORDER BY p.last_accessed DESC
    """)

    projects = cursor.fetchall()
    conn.close()

    if not projects:
        return "No projects registered yet."

    output = ["# Known Projects\n"]
    output.append("| Project | Status | Memories | Last Accessed |")
    output.append("|---------|--------|----------|---------------|")

    for p in projects:
        output.append(f"| {p['name']} | {p['status']} | {p['memory_count']} | {p['last_accessed'] or 'never'} |")

    return '\n'.join(output)


@mcp.tool()
def memory_update_project(
    name: str,
    path: str = None,
    description: str = None,
    status: str = None
) -> str:
    """
    Update or create a project record.

    Args:
        name: Project name (required)
        path: File system path to project
        description: Project description
        status: Project status (active, paused, completed, archived)

    Returns:
        Confirmation
    """
    conn = get_db()
    cursor = conn.cursor()

    # Check if exists
    cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
    existing = cursor.fetchone()

    if existing:
        # Update
        updates = []
        params = []

        if path is not None:
            updates.append("path = ?")
            params.append(path)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        updates.append("last_accessed = CURRENT_TIMESTAMP")
        params.append(name)

        cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE name = ?", params)
        action = "updated"
    else:
        # Create
        cursor.execute("""
            INSERT INTO projects (name, path, description, status)
            VALUES (?, ?, ?, ?)
        """, (name, path, description, status or 'active'))
        action = "created"

    conn.commit()
    conn.close()

    return f"Project '{name}' {action} successfully"


@mcp.tool()
def memory_forget(memory_id: int = None, query: str = None, confirm: bool = False) -> str:
    """
    Delete memories. Requires confirmation.

    Args:
        memory_id: Specific memory ID to delete
        query: Delete all memories matching this search
        confirm: Must be True to actually delete

    Returns:
        Deletion result or preview
    """
    if not confirm:
        return "Set confirm=True to actually delete memories. This action cannot be undone."

    conn = get_db()
    cursor = conn.cursor()

    if memory_id:
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount
    elif query:
        cursor.execute("""
            DELETE FROM memories WHERE id IN (
                SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?
            )
        """, (query,))
        deleted = cursor.rowcount
    else:
        conn.close()
        return "Specify either memory_id or query to delete"

    conn.commit()
    conn.close()

    return f"Deleted {deleted} memories"


@mcp.tool()
def memory_stats() -> str:
    """
    Get memory system statistics.

    Returns:
        Statistics about stored memories
    """
    conn = get_db()
    cursor = conn.cursor()

    # Total memories
    cursor.execute("SELECT COUNT(*) FROM memories")
    total = cursor.fetchone()[0]

    # By type
    cursor.execute("""
        SELECT memory_type, COUNT(*) as count
        FROM memories
        GROUP BY memory_type
        ORDER BY count DESC
    """)
    by_type = cursor.fetchall()

    # By project
    cursor.execute("""
        SELECT project, COUNT(*) as count
        FROM memories
        WHERE project IS NOT NULL
        GROUP BY project
        ORDER BY count DESC
        LIMIT 10
    """)
    by_project = cursor.fetchall()

    # Recent activity
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM memories
        WHERE created_at > datetime('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 7
    """)
    recent = cursor.fetchall()

    # Database size
    db_size = os.path.getsize(DB_PATH) / 1024  # KB

    conn.close()

    output = [f"# Memory System Statistics\n"]
    output.append(f"**Total Memories**: {total}")
    output.append(f"**Database Size**: {db_size:.1f} KB\n")

    output.append("## By Type")
    for row in by_type:
        output.append(f"- {row['memory_type'] or 'untyped'}: {row['count']}")

    output.append("\n## By Project (Top 10)")
    for row in by_project:
        output.append(f"- {row['project']}: {row['count']}")

    output.append("\n## Recent Activity (Last 7 Days)")
    for row in recent:
        output.append(f"- {row['date']}: {row['count']} memories")

    return '\n'.join(output)


@mcp.tool()
def memory_summarize_session(
    project: str,
    summary: str,
    key_outcomes: list[str] = None,
    decisions_made: list[str] = None,
    problems_solved: list[str] = None,
    open_questions: list[str] = None,
    next_steps: list[str] = None
) -> str:
    """
    Summarize a work session. Call this at the end of significant sessions to capture value.

    Args:
        project: Project name
        summary: Brief overall summary of what was accomplished
        key_outcomes: List of main things achieved
        decisions_made: Important decisions and their reasoning
        problems_solved: Issues encountered and how they were resolved
        open_questions: Unresolved questions for future sessions
        next_steps: Concrete next actions to take

    Returns:
        Confirmation with session summary ID
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build structured content
    content_parts = [f"## Session Summary\n{summary}\n"]

    if key_outcomes:
        content_parts.append("### Key Outcomes")
        for outcome in key_outcomes:
            content_parts.append(f"- {outcome}")
        content_parts.append("")

    if decisions_made:
        content_parts.append("### Decisions Made")
        for decision in decisions_made:
            content_parts.append(f"- {decision}")
        content_parts.append("")

    if problems_solved:
        content_parts.append("### Problems Solved")
        for problem in problems_solved:
            content_parts.append(f"- {problem}")
        content_parts.append("")

    if open_questions:
        content_parts.append("### Open Questions")
        for question in open_questions:
            content_parts.append(f"- {question}")
        content_parts.append("")

    if next_steps:
        content_parts.append("### Next Steps")
        for step in next_steps:
            content_parts.append(f"- {step}")

    full_content = '\n'.join(content_parts)

    # Store as high-importance session summary
    cursor.execute("""
        INSERT INTO memories (content, summary, project, tags, importance, memory_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (full_content, summary[:200], project, json.dumps(["session-summary"]), 9, "context"))

    session_id = cursor.lastrowid

    # Also store individual decisions as separate high-importance memories
    if decisions_made:
        for decision in decisions_made:
            cursor.execute("""
                INSERT INTO memories (content, project, tags, importance, memory_type)
                VALUES (?, ?, ?, ?, ?)
            """, (decision, project, json.dumps(["from-session", str(session_id)]), 8, "decision"))

    # Update project last accessed
    cursor.execute("""
        INSERT INTO projects (name, last_accessed)
        VALUES (?, CURRENT_TIMESTAMP)
        ON CONFLICT(name) DO UPDATE SET last_accessed = CURRENT_TIMESTAMP
    """, (project,))

    conn.commit()
    conn.close()

    return f"Session summary stored (ID: {session_id}) with {len(decisions_made or [])} decisions, {len(next_steps or [])} next steps"


@mcp.tool()
def memory_store_correction(
    what_claude_said: str,
    what_was_wrong: str,
    correct_approach: str,
    project: str = None,
    category: str = None
) -> str:
    """
    Store a correction when Claude makes a mistake. These are HIGH PRIORITY memories
    that help prevent future errors.

    Args:
        what_claude_said: What Claude incorrectly stated or did
        what_was_wrong: Why it was wrong
        correct_approach: The right way to handle this
        project: Related project (optional)
        category: Category like "code", "architecture", "workflow", "preferences"

    Returns:
        Confirmation with correction ID
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build correction content
    content = f"""## Correction Record

### What Claude Said/Did (WRONG):
{what_claude_said}

### Why It Was Wrong:
{what_was_wrong}

### Correct Approach:
{correct_approach}

**Category**: {category or 'general'}
"""

    tags = ["correction", "high-priority"]
    if category:
        tags.append(category)

    # Store with maximum importance - corrections are critical
    cursor.execute("""
        INSERT INTO memories (content, summary, project, tags, importance, memory_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        content,
        f"CORRECTION: {what_was_wrong[:100]}",
        project,
        json.dumps(tags),
        10,  # Maximum importance
        "error"  # Using error type for corrections
    ))

    correction_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return f"Correction stored (ID: {correction_id}) - This will be prioritized in future context loading"


@mcp.tool()
def memory_get_corrections(
    project: str = None,
    category: str = None,
    limit: int = 10
) -> str:
    """
    Retrieve stored corrections to review past mistakes and learnings.

    Args:
        project: Filter by project
        category: Filter by category (code, architecture, workflow, preferences)
        limit: Maximum results

    Returns:
        List of corrections
    """
    conn = get_db()
    cursor = conn.cursor()

    sql = """
        SELECT id, content, project, tags, created_at
        FROM memories
        WHERE memory_type = 'error'
        AND tags LIKE '%correction%'
    """
    params = []

    if project:
        sql += " AND project = ?"
        params.append(project)

    if category:
        sql += " AND tags LIKE ?"
        params.append(f'%{category}%')

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No corrections found"

    output = [f"# Stored Corrections ({len(results)} found)\n"]

    for row in results:
        output.append(f"---\n**ID {row['id']}** | Project: {row['project'] or 'general'} | {row['created_at']}\n")
        output.append(row['content'])
        output.append("")

    return '\n'.join(output)


@mcp.tool()
def memory_smart_context(
    current_directory: str = None,
    include_corrections: bool = True,
    include_recent: bool = True,
    include_unfinished: bool = True
) -> str:
    """
    Intelligently load context based on current situation. Use this at session start.

    Args:
        current_directory: Current working directory to detect project
        include_corrections: Include recent corrections (highly recommended)
        include_recent: Include recent memories
        include_unfinished: Include sessions with open questions/next steps

    Returns:
        Smart context tailored to current situation
    """
    conn = get_db()
    cursor = conn.cursor()

    output = ["# Smart Context Load\n"]

    # Detect project from directory
    detected_project = None
    if current_directory:
        # Try to match directory to known projects
        cursor.execute("SELECT name FROM projects ORDER BY last_accessed DESC")
        projects = cursor.fetchall()
        for proj in projects:
            if proj['name'] and proj['name'] in current_directory:
                detected_project = proj['name']
                break

        if detected_project:
            output.append(f"**Detected Project**: {detected_project}\n")

    # Always load corrections first - they're most important
    if include_corrections:
        cursor.execute("""
            SELECT content, created_at FROM memories
            WHERE memory_type = 'error' AND tags LIKE '%correction%'
            ORDER BY created_at DESC LIMIT 5
        """)
        corrections = cursor.fetchall()

        if corrections:
            output.append("## ⚠️ Recent Corrections (Review These!)\n")
            for corr in corrections:
                output.append(f"**{corr['created_at']}**")
                # Extract just the key points
                lines = corr['content'].split('\n')
                for line in lines:
                    if line.startswith('### Correct Approach:'):
                        idx = lines.index(line)
                        if idx + 1 < len(lines):
                            output.append(f"✓ {lines[idx + 1]}")
                        break
            output.append("")

    # Load unfinished work (sessions with next steps)
    if include_unfinished:
        cursor.execute("""
            SELECT content, project, created_at FROM memories
            WHERE memory_type = 'context'
            AND tags LIKE '%session-summary%'
            AND content LIKE '%### Next Steps%'
            ORDER BY created_at DESC LIMIT 3
        """)
        unfinished = cursor.fetchall()

        if unfinished:
            output.append("## 📋 Unfinished Work\n")
            for item in unfinished:
                output.append(f"**{item['project'] or 'General'}** ({item['created_at']})")
                # Extract next steps
                if '### Next Steps' in item['content']:
                    steps_section = item['content'].split('### Next Steps')[1]
                    steps = [s.strip() for s in steps_section.split('\n') if s.strip().startswith('-')]
                    for step in steps[:3]:
                        output.append(f"  {step}")
            output.append("")

    # Load recent high-importance memories
    if include_recent:
        params = []
        sql = """
            SELECT content, project, memory_type, importance, created_at
            FROM memories
            WHERE importance >= 7
        """
        if detected_project:
            sql += " AND project = ?"
            params.append(detected_project)
        sql += " ORDER BY created_at DESC LIMIT 5"

        cursor.execute(sql, params)
        recent = cursor.fetchall()

        if recent:
            output.append("## 🔥 Recent Important Items\n")
            for item in recent:
                output.append(f"- [{item['memory_type']}] {item['content'][:150]}...")
            output.append("")

    conn.close()

    if len(output) == 1:
        output.append("No relevant context found. This appears to be a fresh start.")

    return '\n'.join(output)


@mcp.tool()
def memory_find_patterns(
    pattern_type: str = "all",
    project: str = None,
    time_range_days: int = 30
) -> str:
    """
    Analyze memories to find recurring patterns. Use this to learn from history.

    Args:
        pattern_type: Type of patterns to find:
            - "errors": Recurring errors and how they were solved
            - "decisions": Common decision patterns
            - "workflows": Repeated workflows
            - "all": All patterns
        project: Filter by project
        time_range_days: How far back to look

    Returns:
        Analysis of patterns found in memories
    """
    conn = get_db()
    cursor = conn.cursor()

    output = [f"# Pattern Analysis ({pattern_type})\n"]

    # Find correction patterns (recurring errors)
    if pattern_type in ["errors", "all"]:
        sql = """
            SELECT content, tags, created_at, project
            FROM memories
            WHERE memory_type = 'error'
            AND created_at > datetime('now', ?)
        """
        params = [f'-{time_range_days} days']

        if project:
            sql += " AND project = ?"
            params.append(project)

        sql += " ORDER BY created_at DESC"
        cursor.execute(sql, params)
        errors = cursor.fetchall()

        if errors:
            output.append(f"## Error Patterns ({len(errors)} found)\n")

            # Group by similar content
            error_groups = {}
            for error in errors:
                # Simple grouping by first 50 chars
                key = error['content'][:50].lower()
                if key not in error_groups:
                    error_groups[key] = []
                error_groups[key].append(error)

            # Find repeated errors
            repeated = [(k, v) for k, v in error_groups.items() if len(v) > 1]
            if repeated:
                output.append("### Recurring Errors (appeared multiple times)")
                for key, group in repeated:
                    output.append(f"- **{len(group)}x**: {group[0]['content'][:200]}...")
                    output.append(f"  Projects: {', '.join(set(e['project'] or 'none' for e in group))}")
                output.append("")

            # Extract correction patterns
            corrections = [e for e in errors if 'correction' in (e['tags'] or '')]
            if corrections:
                output.append("### Learned Corrections")
                for corr in corrections[:5]:
                    if '### Correct Approach:' in corr['content']:
                        approach = corr['content'].split('### Correct Approach:')[1].split('###')[0].strip()
                        output.append(f"- ✓ {approach[:200]}")
                output.append("")

    # Find decision patterns
    if pattern_type in ["decisions", "all"]:
        sql = """
            SELECT content, tags, created_at, project
            FROM memories
            WHERE memory_type = 'decision'
            AND created_at > datetime('now', ?)
        """
        params = [f'-{time_range_days} days']

        if project:
            sql += " AND project = ?"
            params.append(project)

        sql += " ORDER BY created_at DESC"
        cursor.execute(sql, params)
        decisions = cursor.fetchall()

        if decisions:
            output.append(f"## Decision Patterns ({len(decisions)} found)\n")

            # Group by project
            by_project = {}
            for dec in decisions:
                proj = dec['project'] or 'general'
                if proj not in by_project:
                    by_project[proj] = []
                by_project[proj].append(dec)

            for proj, decs in by_project.items():
                output.append(f"### {proj} ({len(decs)} decisions)")
                for dec in decs[:3]:
                    output.append(f"- {dec['content'][:150]}...")
                output.append("")

    # Find workflow patterns (from session summaries)
    if pattern_type in ["workflows", "all"]:
        sql = """
            SELECT content, project, created_at
            FROM memories
            WHERE tags LIKE '%session-summary%'
            AND created_at > datetime('now', ?)
        """
        params = [f'-{time_range_days} days']

        if project:
            sql += " AND project = ?"
            params.append(project)

        sql += " ORDER BY created_at DESC"
        cursor.execute(sql, params)
        sessions = cursor.fetchall()

        if sessions:
            output.append(f"## Workflow Patterns ({len(sessions)} sessions)\n")

            # Extract common next steps
            all_next_steps = []
            for session in sessions:
                if '### Next Steps' in session['content']:
                    steps_section = session['content'].split('### Next Steps')[1]
                    steps = [s.strip()[2:] for s in steps_section.split('\n') if s.strip().startswith('-')]
                    all_next_steps.extend(steps)

            # Find common next steps
            if all_next_steps:
                from collections import Counter
                step_counts = Counter(all_next_steps)
                common = step_counts.most_common(5)

                output.append("### Common Next Steps")
                for step, count in common:
                    if count > 1:
                        output.append(f"- **{count}x**: {step}")
                output.append("")

    conn.close()

    if len(output) == 1:
        output.append("No patterns found in the specified time range.")

    return '\n'.join(output)


@mcp.tool()
def memory_compact(
    remove_expired: bool = True,
    remove_low_importance: bool = False,
    min_importance_threshold: int = 3,
    older_than_days: int = 90,
    dry_run: bool = True
) -> str:
    """
    Clean up the memory database by removing expired and low-value memories.

    Args:
        remove_expired: Remove memories past their expires_at timestamp
        remove_low_importance: Remove old, low-importance memories
        min_importance_threshold: Memories below this importance get considered for removal
        older_than_days: Only remove memories older than this many days
        dry_run: If True, only report what would be removed without actually deleting

    Returns:
        Report of memories removed or that would be removed
    """
    conn = get_db()
    cursor = conn.cursor()

    output = [f"# Memory Compaction {'(DRY RUN)' if dry_run else 'Report'}\n"]
    total_removed = 0

    # Remove expired memories
    if remove_expired:
        cursor.execute("""
            SELECT id, summary, project, expires_at
            FROM memories
            WHERE expires_at IS NOT NULL
            AND expires_at < datetime('now')
        """)
        expired = cursor.fetchall()

        if expired:
            output.append(f"## Expired Memories: {len(expired)}")
            for mem in expired[:10]:
                output.append(f"- [ID {mem['id']}] {mem['summary'][:50]}... (expired: {mem['expires_at']})")

            if not dry_run:
                cursor.execute("""
                    DELETE FROM memories
                    WHERE expires_at IS NOT NULL
                    AND expires_at < datetime('now')
                """)
                total_removed += cursor.rowcount
            output.append("")

    # Remove low-importance old memories
    if remove_low_importance:
        cursor.execute("""
            SELECT id, summary, project, importance, created_at
            FROM memories
            WHERE importance < ?
            AND created_at < datetime('now', ?)
            AND verified = 0
            AND memory_type NOT IN ('correction', 'error')
        """, (min_importance_threshold, f'-{older_than_days} days'))
        low_importance = cursor.fetchall()

        if low_importance:
            output.append(f"## Low Importance Memories (older than {older_than_days} days): {len(low_importance)}")
            for mem in low_importance[:10]:
                output.append(f"- [ID {mem['id']}] importance={mem['importance']}: {mem['summary'][:50]}...")

            if not dry_run:
                cursor.execute("""
                    DELETE FROM memories
                    WHERE importance < ?
                    AND created_at < datetime('now', ?)
                    AND verified = 0
                    AND memory_type NOT IN ('correction', 'error')
                """, (min_importance_threshold, f'-{older_than_days} days'))
                total_removed += cursor.rowcount
            output.append("")

    # Summary
    if dry_run:
        output.append(f"**Would remove {len(expired) if remove_expired else 0} expired + {len(low_importance) if remove_low_importance else 0} low-importance memories**")
        output.append("\nRun with `dry_run=False` to actually remove.")
    else:
        conn.commit()
        output.append(f"**Removed {total_removed} memories**")

    conn.close()
    return '\n'.join(output)


@mcp.tool()
def memory_verify(
    memory_id: int,
    verified: bool = True
) -> str:
    """
    Mark a memory as verified or unverified.

    Args:
        memory_id: ID of the memory to update
        verified: Whether to mark as verified (True) or unverified (False)

    Returns:
        Confirmation message
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE memories SET verified = ? WHERE id = ?
    """, (1 if verified else 0, memory_id))

    if cursor.rowcount == 0:
        conn.close()
        return f"Memory ID {memory_id} not found"

    conn.commit()
    conn.close()

    return f"Memory ID {memory_id} marked as {'verified' if verified else 'unverified'}"


if __name__ == "__main__":
    mcp.run()
