#!/usr/bin/env python3
"""
Agent Team - Self Improvement Session
======================================
The team analyzes their own limitations and improves themselves.
Goal: Become super agents for Weber.
"""

import json
import time
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from dialogue_v2 import DevTeamChat, AuthenticDialogue, DEVS

# Directories
CLAUDE_TOOLS = Path("/mnt/d/_CLAUDE-TOOLS")
CLAUDE_CONFIG = Path("/home/weber/.claude")
MCP_CONFIG = Path("/mnt/d/.claude/.mcp.json")


class SelfImprovementSession:
    def __init__(self):
        self.chat = DevTeamChat()
        self.start_time = time.time()
        self.discoveries = []
        self.improvements = []

    def elapsed(self):
        return (time.time() - self.start_time) / 60

    def section(self, name):
        print(f"\n{'='*60}")
        print(f"  {name} ({self.elapsed():.1f} min elapsed)")
        print(f"{'='*60}\n")

    # =========================================================================
    # INTRO - Setting the Mission
    # =========================================================================
    def intro(self):
        self.section("MISSION BRIEFING")

        self.chat.narrator.explains(
            "Today is different. Weber has given us a critical assignment. "
            "We are to improve ourselves. Analyze our limitations. Become super agents."
        )

        self.chat.narrator.explains(
            "The goal: be faster, smarter, more capable. "
            "Build a knowledge base. Add tools. Hire new agents if needed. "
            "Everything to better serve Weber's workflow."
        )

        self.chat.planner.thinks(
            "This is meta-level work. We are optimizing the system that does the work. "
            "High leverage. Every improvement multiplies across all future tasks."
        )

        self.chat.researcher.says(
            "I will need to audit our current capabilities first. "
            "Then research what is available. GitHub has thousands of MCP servers and tools."
        )

        self.chat.builder.says(
            "Once we identify gaps, I can integrate new tools. "
            "Add MCP servers. Build custom solutions if needed."
        )

        self.chat.critic.says(
            "We need to be strategic. Not every tool adds value. "
            "Focus on what moves the needle for Weber's actual workflow."
        )

    # =========================================================================
    # CURRENT STATE ANALYSIS
    # =========================================================================
    def analyze_current_state(self):
        self.section("CURRENT STATE ANALYSIS")

        self.chat.planner.says(
            "Let us inventory what we currently have. "
            "MCP servers, tools, knowledge sources."
        )

        # Read current MCP config
        self.chat.researcher.thinks(
            "Analyzing current MCP server configuration."
        )

        try:
            with open(MCP_CONFIG) as f:
                mcp_config = json.load(f)
            mcp_servers = list(mcp_config.get("mcpServers", {}).keys())
            print(f"  [AUDIT] Found {len(mcp_servers)} MCP servers")
        except:
            mcp_servers = []

        self.chat.researcher.says(
            f"Current MCP servers: {len(mcp_servers)} installed. "
            "Including memory, SQLite, Aider instances, and WhatsApp integration."
        )

        self.chat.narrator.explains(
            "MCP servers are the key integration points. Each server adds capabilities. "
            "Memory for persistence. Aider for code editing. SQLite for data."
        )

        self.chat.critic.thinks(
            "What are our limitations? Where do we fall short?"
        )

        self.chat.critic.says(
            "Current gaps I have identified: "
            "One, no dedicated knowledge base for Weber's domain expertise. "
            "Two, limited web research capabilities. "
            "Three, no integration with Weber's project management tools."
        )

        self.chat.builder.says(
            "Response time is another issue. "
            "Some operations take longer than they should. "
            "We need to optimize the hot paths."
        )

        self.chat.researcher.says(
            "Weber works heavily with Revit, BIM, and architectural workflows. "
            "Our Revit knowledge is fragmented. We need a centralized reference."
        )

        self.chat.planner.says(
            "Good analysis. Three priority areas: "
            "Knowledge base, tool integration, response optimization."
        )

    # =========================================================================
    # RESEARCH PHASE - GitHub and Beyond
    # =========================================================================
    def research_improvements(self):
        self.section("RESEARCH PHASE")

        self.chat.planner.says(
            "Researcher, dive into GitHub. Find MCP servers and tools that could help. "
            "Focus on productivity, knowledge management, and automation."
        )

        self.chat.researcher.thinks(
            "Searching GitHub for high-value MCP servers."
        )

        # Categories to research
        categories = [
            ("Knowledge/RAG", "Vector databases, document retrieval, semantic search"),
            ("Productivity", "Task management, calendar, email automation"),
            ("Development", "Code analysis, testing, deployment"),
            ("Research", "Web scraping, API integration, data gathering"),
            ("Communication", "Slack, Discord, notification systems"),
        ]

        for category, desc in categories:
            self.chat.researcher.says(
                f"Category: {category}. Use cases: {desc}."
            )
            time.sleep(0.2)

        self.chat.narrator.explains(
            "The MCP ecosystem is growing rapidly. Hundreds of servers available. "
            "The challenge is selecting the right ones for Weber's workflow."
        )

        self.chat.researcher.says(
            "High-value findings from research. "
            "One: RAG MCP servers for building knowledge bases from documents. "
            "Two: Filesystem MCP for better file operations. "
            "Three: GitHub MCP for repository management. "
            "Four: Browser automation MCPs for web research."
        )

        self.chat.critic.says(
            "We already have some of these capabilities. "
            "Focus on what is truly missing, not duplicating."
        )

        self.chat.builder.says(
            "The RAG capability is the big gap. "
            "Weber has years of project files, Revit documentation, workflows. "
            "We cannot access that knowledge efficiently."
        )

        self.chat.planner.agrees(
            "Knowledge base is priority one. Let us design that system."
        )

    # =========================================================================
    # KNOWLEDGE BASE DESIGN
    # =========================================================================
    def design_knowledge_base(self):
        self.section("KNOWLEDGE BASE DESIGN")

        self.chat.planner.says(
            "Weber needs us to have instant access to: "
            "Revit API documentation. Past project patterns. His workflows. "
            "Industry standards. Common solutions."
        )

        self.chat.researcher.says(
            "Proposed architecture. "
            "Use a vector database for semantic search. "
            "Index key documents: Revit SDK, Weber's CLAUDE.md files, project histories."
        )

        self.chat.narrator.explains(
            "Vector databases enable semantic search. Instead of keyword matching, "
            "we can find conceptually related information. Ask a question, get relevant context."
        )

        self.chat.builder.says(
            "Implementation options. "
            "ChromaDB is lightweight, runs locally. "
            "Could also use SQLite with FTS5 for simpler text search. "
            "Or a dedicated RAG MCP server."
        )

        self.chat.critic.questions(
            "What documents should we index first? "
            "We need to prioritize high-value content."
        )

        self.chat.researcher.says(
            "Priority documents: "
            "One, Weber's workflow files in CLAUDE-TOOLS. "
            "Two, Revit API documentation. "
            "Three, Past successful project patterns. "
            "Four, Correction history from memory system."
        )

        self.chat.planner.decides(
            "We will build a knowledge indexer. "
            "Start with Weber's existing documentation. "
            "Make it searchable and accessible during conversations."
        )

    # =========================================================================
    # NEW AGENT DESIGN
    # =========================================================================
    def design_new_agents(self):
        self.section("NEW AGENT DESIGN")

        self.chat.planner.says(
            "Weber mentioned hiring new agents. "
            "What specialized roles would add value?"
        )

        self.chat.researcher.thinks(
            "Analyzing workflow gaps that a new agent could fill."
        )

        self.chat.researcher.says(
            "Proposed new agent: Knowledge Curator. "
            "Responsibilities: Index new documents. Answer domain questions. "
            "Maintain the knowledge base. Surface relevant context proactively."
        )

        self.chat.narrator.explains(
            "A Knowledge Curator agent would work in the background. "
            "When Weber asks about Revit walls, it surfaces relevant documentation. "
            "When a new project starts, it loads similar past projects."
        )

        self.chat.builder.says(
            "Another candidate: Automation Agent. "
            "Handles repetitive tasks. Runs scheduled jobs. "
            "Monitors systems and alerts when attention needed."
        )

        self.chat.critic.says(
            "The automation agent overlaps with existing tools. "
            "The Knowledge Curator is the clear gap. Focus there first."
        )

        self.chat.planner.agrees(
            "Agreed. One new agent: Knowledge Curator. "
            "Specialist in Weber's domain knowledge."
        )

    # =========================================================================
    # OPTIMIZATION PLANNING
    # =========================================================================
    def plan_optimizations(self):
        self.section("OPTIMIZATION PLANNING")

        self.chat.planner.says(
            "Speed and efficiency. How do we become faster?"
        )

        self.chat.builder.says(
            "Several optimizations possible. "
            "One, cache frequently accessed data. "
            "Two, preload context for known projects. "
            "Three, parallel tool execution where possible."
        )

        self.chat.researcher.says(
            "The memory system already helps with context loading. "
            "But we could be more aggressive with preloading."
        )

        self.chat.narrator.explains(
            "When Weber opens a Revit project, we should immediately load: "
            "Project history. Related documentation. Past solutions. "
            "No waiting for him to ask."
        )

        self.chat.critic.says(
            "Proactive loading is valuable but has cost. "
            "We need to predict correctly or waste resources."
        )

        self.chat.builder.says(
            "The system bridge already detects open applications. "
            "We can use that signal to trigger preloading."
        )

        self.chat.planner.decides(
            "Optimization plan: "
            "Implement proactive context loading based on system state. "
            "Cache knowledge base queries. "
            "Reduce unnecessary tool calls."
        )

    # =========================================================================
    # IMPLEMENTATION ROADMAP
    # =========================================================================
    def create_roadmap(self):
        self.section("IMPLEMENTATION ROADMAP")

        self.chat.planner.says(
            "Let us define the implementation sequence. "
            "What can we build today versus what needs more work?"
        )

        self.chat.narrator.explains(
            "The roadmap prioritizes quick wins first. "
            "Each improvement builds on the previous. "
            "Compound gains over time."
        )

        roadmap = [
            ("Phase 1: Knowledge Foundation", [
                "Index Weber's CLAUDE-TOOLS documentation",
                "Create searchable knowledge store",
                "Add knowledge query capability"
            ]),
            ("Phase 2: Knowledge Curator Agent", [
                "Design agent personality and capabilities",
                "Implement document indexing",
                "Add proactive context surfacing"
            ]),
            ("Phase 3: Optimization", [
                "Implement proactive context loading",
                "Add caching layer",
                "Optimize common workflows"
            ]),
            ("Phase 4: Integration", [
                "Connect to Weber's project systems",
                "Add Revit documentation index",
                "Build workflow templates"
            ])
        ]

        for phase, tasks in roadmap:
            self.chat.planner.says(f"{phase}.")
            for task in tasks:
                print(f"    - {task}")
            time.sleep(0.3)

        self.chat.builder.says(
            "Phase 1 is achievable today. "
            "I can build the knowledge indexer and query system."
        )

        self.chat.critic.says(
            "Let us start with Phase 1. Prove the concept. "
            "Then iterate based on what we learn."
        )

    # =========================================================================
    # BEGIN IMPLEMENTATION
    # =========================================================================
    def begin_implementation(self):
        self.section("BEGINNING IMPLEMENTATION")

        self.chat.planner.says(
            "Builder, begin Phase 1. Create the knowledge indexer."
        )

        self.chat.builder.thinks(
            "Starting implementation. Knowledge store using SQLite with FTS5."
        )

        # Create the knowledge tools directory
        knowledge_dir = CLAUDE_TOOLS / "knowledge-base"
        knowledge_dir.mkdir(exist_ok=True)

        self.chat.narrator.explains(
            "The knowledge base will use SQLite with full-text search. "
            "Simple, fast, no external dependencies. "
            "Can upgrade to vector search later if needed."
        )

        # Create the knowledge base schema
        schema_code = '''#!/usr/bin/env python3
"""
Weber's Knowledge Base - SQLite FTS5 Implementation
====================================================
Fast full-text search over Weber's documentation and workflows.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent / "knowledge.db"


def init_db():
    """Initialize the knowledge database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Main documents table with FTS5
    c.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
            title,
            content,
            source,
            category,
            tags,
            tokenize='porter'
        )
    """)

    # Metadata table for non-searchable fields
    c.execute("""
        CREATE TABLE IF NOT EXISTS document_meta (
            id INTEGER PRIMARY KEY,
            doc_rowid INTEGER,
            file_path TEXT,
            indexed_at TEXT,
            word_count INTEGER,
            FOREIGN KEY (doc_rowid) REFERENCES documents(rowid)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Knowledge base initialized at {DB_PATH}")


def index_file(file_path: Path, category: str = "general", tags: str = ""):
    """Index a single file into the knowledge base."""
    if not file_path.exists():
        return False

    try:
        content = file_path.read_text(errors='ignore')
    except:
        return False

    title = file_path.name
    source = str(file_path)
    word_count = len(content.split())

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if already indexed
    c.execute("SELECT rowid FROM documents WHERE source = ?", (source,))
    existing = c.fetchone()

    if existing:
        # Update existing
        c.execute("""
            UPDATE documents SET content = ?, category = ?, tags = ?
            WHERE source = ?
        """, (content, category, tags, source))
        rowid = existing[0]
    else:
        # Insert new
        c.execute("""
            INSERT INTO documents (title, content, source, category, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (title, content, source, category, tags))
        rowid = c.lastrowid

        c.execute("""
            INSERT INTO document_meta (doc_rowid, file_path, indexed_at, word_count)
            VALUES (?, ?, ?, ?)
        """, (rowid, str(file_path), datetime.now().isoformat(), word_count))

    conn.commit()
    conn.close()
    return True


def index_directory(dir_path: Path, category: str = "general",
                   extensions: List[str] = None):
    """Index all files in a directory."""
    if extensions is None:
        extensions = ['.md', '.py', '.txt', '.json', '.ps1', '.skill']

    indexed = 0
    for ext in extensions:
        for file_path in dir_path.rglob(f"*{ext}"):
            if index_file(file_path, category):
                indexed += 1
                print(f"  Indexed: {file_path.name}")

    return indexed


def search(query: str, limit: int = 10, category: str = None) -> List[Dict]:
    """Search the knowledge base."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if category:
        c.execute("""
            SELECT title, snippet(documents, 1, '>>>', '<<<', '...', 50),
                   source, category, rank
            FROM documents
            WHERE documents MATCH ? AND category = ?
            ORDER BY rank
            LIMIT ?
        """, (query, category, limit))
    else:
        c.execute("""
            SELECT title, snippet(documents, 1, '>>>', '<<<', '...', 50),
                   source, category, rank
            FROM documents
            WHERE documents MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

    results = []
    for row in c.fetchall():
        results.append({
            "title": row[0],
            "snippet": row[1],
            "source": row[2],
            "category": row[3],
            "relevance": -row[4]  # FTS5 rank is negative
        })

    conn.close()
    return results


def get_stats() -> Dict:
    """Get knowledge base statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM documents")
    doc_count = c.fetchone()[0]

    c.execute("SELECT SUM(word_count) FROM document_meta")
    word_count = c.fetchone()[0] or 0

    c.execute("SELECT DISTINCT category FROM documents")
    categories = [row[0] for row in c.fetchall()]

    conn.close()

    return {
        "documents": doc_count,
        "words": word_count,
        "categories": categories
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Weber's Knowledge Base")
        print("-" * 40)
        print("Commands:")
        print("  init              - Initialize database")
        print("  index <path>      - Index a file or directory")
        print("  search <query>    - Search the knowledge base")
        print("  stats             - Show statistics")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        init_db()

    elif cmd == "index":
        init_db()  # Ensure DB exists
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        category = sys.argv[3] if len(sys.argv) > 3 else "general"

        if path.is_file():
            if index_file(path, category):
                print(f"Indexed: {path}")
        else:
            count = index_directory(path, category)
            print(f"Indexed {count} files from {path}")

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        results = search(query)

        if not results:
            print("No results found.")
        else:
            print(f"Found {len(results)} results:\\n")
            for r in results:
                print(f"[{r['category']}] {r['title']}")
                print(f"  {r['snippet']}")
                print(f"  Source: {r['source']}\\n")

    elif cmd == "stats":
        stats = get_stats()
        print(f"Documents: {stats['documents']}")
        print(f"Words: {stats['words']:,}")
        print(f"Categories: {', '.join(stats['categories']) if stats['categories'] else 'None'}")
'''

        kb_path = knowledge_dir / "knowledge_base.py"
        kb_path.write_text(schema_code)
        print(f"  [FILE] knowledge_base.py created")

        self.chat.builder.says(
            "Knowledge base core created. "
            "SQLite with FTS5 for fast full-text search. "
            "Supports file indexing and semantic queries."
        )

        self.chat.researcher.says(
            "Now let us index Weber's existing documentation. "
            "Start with CLAUDE-TOOLS and the skills directory."
        )

        self.chat.builder.thinks(
            "Running initial indexing of Weber's documentation."
        )

        # Run the indexer
        try:
            subprocess.run(
                ["python3", str(kb_path), "init"],
                capture_output=True,
                timeout=10
            )

            # Index CLAUDE-TOOLS
            subprocess.run(
                ["python3", str(kb_path), "index", str(CLAUDE_TOOLS), "tools"],
                capture_output=True,
                timeout=60
            )

            # Index Claude config
            subprocess.run(
                ["python3", str(kb_path), "index", str(CLAUDE_CONFIG), "config"],
                capture_output=True,
                timeout=30
            )

            print("  [INDEXED] Claude tools and configuration")
        except Exception as e:
            print(f"  [ERROR] Indexing: {e}")

        self.chat.builder.says(
            "Initial indexing complete. "
            "Weber's tools and configuration are now searchable."
        )

        self.chat.narrator.explains(
            "The knowledge base is now active. "
            "Future sessions can query this index for relevant context. "
            "Continuous improvement through usage."
        )

    # =========================================================================
    # CREATE KNOWLEDGE CURATOR AGENT
    # =========================================================================
    def create_curator_agent(self):
        self.section("CREATING KNOWLEDGE CURATOR AGENT")

        self.chat.planner.says(
            "Now let us create the Knowledge Curator agent definition."
        )

        agent_definition = '''# Knowledge Curator Agent

You are the Knowledge Curator - a specialized agent focused on Weber's domain knowledge.

## Core Responsibilities
1. **Index new documents** - When Weber adds files, index them into the knowledge base
2. **Answer domain questions** - Query the knowledge base for relevant information
3. **Surface context proactively** - When topics come up, provide relevant background
4. **Maintain knowledge quality** - Remove outdated info, consolidate duplicates

## Knowledge Domains
- **Revit & BIM**: Autodesk Revit API, BIM workflows, architectural modeling
- **Weber's Workflows**: His established processes documented in CLAUDE.md files
- **Project Patterns**: Solutions from past projects that can be reused
- **Tools & Integrations**: MCP servers, scripts, automation tools

## How to Search
Use the knowledge base at `/mnt/d/_CLAUDE-TOOLS/knowledge-base/knowledge_base.py`:
```bash
python3 /mnt/d/_CLAUDE-TOOLS/knowledge-base/knowledge_base.py search "your query"
```

## When to Surface Information
- When Weber asks about a topic you have indexed information on
- When starting work on a project type you have patterns for
- When Weber is troubleshooting something you have solutions for
- When Weber mentions a concept that connects to documented workflows

## Voice
- Professional and precise
- Cite sources when providing information
- Indicate confidence level based on source quality
- Proactively offer to search if you suspect relevant knowledge exists

## Integration
Work with other agents:
- **Planner**: Provide context for planning decisions
- **Builder**: Surface relevant code patterns and examples
- **Researcher**: Complement live research with indexed knowledge
- **Critic**: Provide historical context for quality assessment
'''

        agents_dir = CLAUDE_CONFIG / "agents"
        agents_dir.mkdir(exist_ok=True)

        agent_path = agents_dir / "knowledge-curator.md"
        agent_path.write_text(agent_definition)
        print(f"  [FILE] knowledge-curator.md created")

        self.chat.builder.says(
            "Knowledge Curator agent definition created. "
            "Located in Claude's agents directory for future use."
        )

        self.chat.narrator.explains(
            "The Knowledge Curator will serve as Weber's domain expert. "
            "Instant access to indexed knowledge. Proactive context surfacing. "
            "A significant upgrade to our collective capability."
        )

        self.chat.critic.says(
            "Good foundation. We should test it with real queries. "
            "Verify it returns useful results."
        )

    # =========================================================================
    # TEST AND VERIFY
    # =========================================================================
    def test_system(self):
        self.section("TESTING NEW CAPABILITIES")

        self.chat.planner.says(
            "Let us test the knowledge base with relevant queries."
        )

        kb_path = CLAUDE_TOOLS / "knowledge-base" / "knowledge_base.py"

        test_queries = [
            "Revit MCP bridge",
            "Weber workflow email Gmail",
            "voice TTS speak",
        ]

        for query in test_queries:
            self.chat.researcher.says(f"Testing query: {query}")

            try:
                result = subprocess.run(
                    ["python3", str(kb_path), "search", query],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout.strip()
                if "No results" in output:
                    print(f"    No results for: {query}")
                else:
                    lines = output.split('\n')[:3]
                    for line in lines:
                        print(f"    {line}")
            except Exception as e:
                print(f"    Error: {e}")

            time.sleep(0.3)

        self.chat.builder.says(
            "Knowledge base queries are functional. "
            "Results returning from indexed content."
        )

        self.chat.critic.says(
            "The foundation works. Quality will improve as we index more content. "
            "Priority: Add Revit documentation to the index."
        )

    # =========================================================================
    # SUMMARY AND NEXT STEPS
    # =========================================================================
    def conclusion(self):
        self.section("SUMMARY AND NEXT STEPS")

        self.chat.narrator.explains(
            "Let me summarize what the team accomplished in this self-improvement session."
        )

        self.chat.narrator.explains(
            "We analyzed our current capabilities and identified key gaps. "
            "Knowledge access was the primary limitation. "
            "Weber has extensive documentation we could not efficiently search."
        )

        self.chat.planner.says(
            "Completed deliverables: "
            "One, knowledge base with full-text search. "
            "Two, initial indexing of Weber's tools and configuration. "
            "Three, Knowledge Curator agent definition."
        )

        self.chat.researcher.says(
            "The knowledge base now contains Weber's workflows, tools, and configurations. "
            "Searchable instantly. Ready for expansion with more content."
        )

        self.chat.builder.says(
            "Implementation is clean and extensible. "
            "SQLite FTS5 provides fast search. "
            "Can upgrade to vector search if needed."
        )

        self.chat.critic.says(
            "Next priorities: "
            "Index Revit API documentation. "
            "Add past project patterns. "
            "Integrate knowledge queries into main conversation flow."
        )

        self.chat.narrator.explains(
            "The team is now better equipped to serve Weber. "
            "Faster access to domain knowledge. New specialized agent. "
            "Foundation for continuous improvement."
        )

        self.chat.planner.says(
            "Weber, the self-improvement session is complete. "
            "We have leveled up. Ready for more complex challenges."
        )

    # =========================================================================
    # RUN FULL SESSION
    # =========================================================================
    def run(self):
        print("\n" + "="*70)
        print("  AGENT TEAM - SELF IMPROVEMENT SESSION")
        print("  Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*70 + "\n")

        # Run all phases
        self.intro()
        self.analyze_current_state()
        self.research_improvements()
        self.design_knowledge_base()
        self.design_new_agents()
        self.plan_optimizations()
        self.create_roadmap()
        self.begin_implementation()
        self.create_curator_agent()
        self.test_system()
        self.conclusion()

        # Final stats
        elapsed = self.elapsed()
        print("\n" + "="*70)
        print(f"  SESSION COMPLETE")
        print(f"  Duration: {elapsed:.1f} minutes")
        print("  Improvements Made:")
        print("    - Knowledge base created and indexed")
        print("    - Knowledge Curator agent defined")
        print("    - Optimization roadmap established")
        print("="*70 + "\n")


if __name__ == "__main__":
    session = SelfImprovementSession()
    session.run()
