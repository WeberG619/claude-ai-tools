"""CLI interface for the code memory system."""

import click
import logging
from pathlib import Path
from typing import Optional
import json
import time

from ..core.config import Config
from ..core.database import DatabaseManager
from ..core.models import QueryRequest
from ..indexing.indexer import CodeIndexer
from ..indexing.embeddings import CodeEmbeddingGenerator
from ..retrieval.vector_store import VectorStore
from ..retrieval.context_retriever import ContextRetriever
from ..memory.cache_manager import ThreeTierMemoryCache
from ..session.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """Code Memory System - Intelligent caching for AI-assisted development."""
    # Initialize configuration
    if config:
        # Load from file if provided
        ctx.obj = Config.from_file(Path(config))
    else:
        ctx.obj = Config.from_env()
        
    ctx.obj.ensure_directories()


@cli.command()
@click.argument('project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--name', '-n', help='Project name')
@click.pass_context
def init(ctx, project_path, name):
    """Initialize a new project for indexing."""
    config = ctx.obj
    project_path = Path(project_path).resolve()
    
    click.echo(f"Initializing project at: {project_path}")
    
    # Initialize components
    db_manager = DatabaseManager(config)
    embedding_generator = CodeEmbeddingGenerator(
        embedding_dim=config.performance.embedding_dimension,
        use_openai=bool(config.openai_api_key),
        api_key=config.openai_api_key
    )
    
    # Initialize vector store
    vector_store = VectorStore(config.database.vector_db_path, embedding_generator)
    
    # Create indexer
    indexer = CodeIndexer(config, db_manager)
    
    # Index the project
    with click.progressbar(length=100, label='Indexing project') as bar:
        project = indexer.index_project(project_path, name)
        bar.update(100)
        
    click.echo(f"✓ Project indexed successfully!")
    click.echo(f"  - Total files: {project.total_files}")
    click.echo(f"  - Indexed files: {project.indexed_files}")
    click.echo(f"  - Project ID: {project.id}")
    
    # Create initial session
    session_manager = SessionManager(db_manager)
    session = session_manager.create_session(project.id)
    click.echo(f"✓ Created session: {session.name}")


@cli.command()
@click.argument('query_text')
@click.option('--project-id', '-p', type=int, help='Project ID to query')
@click.option('--max-results', '-m', default=10, help='Maximum results to return')
@click.option('--include-tests', is_flag=True, help='Include test files in results')
@click.option('--json-output', is_flag=True, help='Output as JSON')
@click.pass_context
def query(ctx, query_text, project_id, max_results, include_tests, json_output):
    """Query the code memory system."""
    config = ctx.obj
    
    # Initialize components
    db_manager = DatabaseManager(config)
    embedding_generator = CodeEmbeddingGenerator(
        embedding_dim=config.performance.embedding_dimension,
        use_openai=bool(config.openai_api_key),
        api_key=config.openai_api_key
    )
    vector_store = VectorStore(config.database.vector_db_path, embedding_generator)
    cache = ThreeTierMemoryCache(config)
    retriever = ContextRetriever(db_manager, vector_store)
    
    # Check cache first
    cache_key = f"query:{project_id}:{query_text}"
    cached_result, tier = cache.get(cache_key)
    
    if cached_result:
        click.echo(f"✓ Retrieved from {tier} cache")
        result = cached_result
    else:
        # Perform query
        start_time = time.time()
        
        query_request = QueryRequest(
            text=query_text,
            max_results=max_results,
            include_tests=include_tests
        )
        
        result = retriever.retrieve_context(query_request, project_id)
        result.response_time = time.time() - start_time
        
        # Cache the result
        cache.put(cache_key, result.dict(), "warm")
        
    # Output results
    if json_output:
        click.echo(json.dumps(result.dict(), indent=2))
    else:
        click.echo(f"\n🔍 Query: {query_text}")
        click.echo(f"📊 Type: {result.query_type}")
        click.echo(f"⏱️  Time: {result.response_time:.3f}s")
        
        click.echo(f"\n📄 Relevant Files ({len(result.files)}):")
        for file_info in result.files[:5]:
            click.echo(f"  - {file_info.relative_path}")
            
        click.echo(f"\n🔧 Code Entities ({len(result.entities)}):")
        for entity in result.entities[:10]:
            score = result.relevance_scores.get(entity.name, 0)
            click.echo(f"  - {entity.entity_type} {entity.name} ({entity.file_path}:{entity.start_line}) [score: {score:.2f}]")


@cli.command()
@click.option('--project-id', '-p', type=int, help='Continue session for specific project')
@click.pass_context
def continue_session(ctx, project_id):
    """Continue the last working session."""
    config = ctx.obj
    
    db_manager = DatabaseManager(config)
    session_manager = SessionManager(db_manager)
    
    if project_id:
        session = session_manager.continue_last_session(project_id)
        if session:
            click.echo(f"✓ Continuing session: {session.name}")
            
            # Show session state
            if session_manager.current_state:
                state = session_manager.current_state
                click.echo(f"\n📂 Open files ({len(state.open_files)}):")
                for file_path in state.open_files[:5]:
                    click.echo(f"  - {file_path}")
                    
                if state.recent_queries:
                    click.echo(f"\n🔍 Recent queries:")
                    for query in state.recent_queries[-5:]:
                        click.echo(f"  - {query}")
        else:
            click.echo("❌ No session found for this project")
    else:
        click.echo("❌ Please specify a project ID with -p")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show system statistics."""
    config = ctx.obj
    
    # Initialize components
    db_manager = DatabaseManager(config)
    vector_store = VectorStore(config.database.vector_db_path, 
                             CodeEmbeddingGenerator(config.performance.embedding_dimension))
    cache = ThreeTierMemoryCache(config)
    
    click.echo("\n📊 Code Memory System Statistics\n")
    
    # Database stats
    db_size = db_manager.get_db_size()
    click.echo(f"💾 Database:")
    click.echo(f"  - Size: {db_size / (1024 * 1024):.2f} MB")
    
    # Vector store stats
    vector_stats = vector_store.get_statistics()
    click.echo(f"\n🔍 Vector Store:")
    click.echo(f"  - Total entities: {vector_stats['total_entities']}")
    click.echo(f"  - Embedding dimension: {vector_stats['embedding_dimension']}")
    
    # Cache stats
    cache_stats = cache.get_statistics()
    click.echo(f"\n💨 Cache:")
    click.echo(f"  - Hit rate: {cache_stats['hit_rate']:.2%}")
    click.echo(f"  - Hot tier: {cache_stats['tiers']['hot']['entries']} entries, {cache_stats['tiers']['hot']['size_mb']:.2f} MB")
    click.echo(f"  - Warm tier: {cache_stats['tiers']['warm']['entries']} entries, {cache_stats['tiers']['warm']['size_mb']:.2f} MB")
    click.echo(f"  - Cold tier: {cache_stats['tiers']['cold']['entries']} entries, {cache_stats['tiers']['cold']['size_mb']:.2f} MB")


@cli.command()
@click.argument('project_id', type=int)
@click.pass_context
def update(ctx, project_id):
    """Update an existing project's index."""
    config = ctx.obj
    
    db_manager = DatabaseManager(config)
    indexer = CodeIndexer(config, db_manager)
    
    click.echo(f"Updating project {project_id}...")
    
    with click.progressbar(length=100, label='Updating index') as bar:
        indexed_count = indexer.update_project(project_id)
        bar.update(100)
        
    click.echo(f"✓ Updated {indexed_count} files")


@cli.command()
@click.option('--list', 'list_sessions', is_flag=True, help='List all sessions')
@click.option('--export', type=int, help='Export session ID')
@click.option('--import-file', type=click.Path(exists=True), help='Import session from file')
@click.option('--project-id', '-p', type=int, help='Project ID for import')
@click.pass_context
def session(ctx, list_sessions, export, import_file, project_id):
    """Manage sessions."""
    config = ctx.obj
    
    db_manager = DatabaseManager(config)
    session_manager = SessionManager(db_manager)
    
    if list_sessions and project_id:
        sessions = session_manager.list_sessions(project_id)
        click.echo(f"\n📋 Sessions for project {project_id}:\n")
        
        for s in sessions:
            status = "🟢" if s['active'] else "⚪"
            click.echo(f"{status} [{s['id']}] {s['name']}")
            click.echo(f"   Created: {s['created_at']}")
            click.echo(f"   Last accessed: {s['last_accessed']}")
            click.echo(f"   Queries: {s['query_count']}\n")
            
    elif export:
        export_path = Path(f"session_{export}_export.json")
        if session_manager.export_session(export, export_path):
            click.echo(f"✓ Exported session to: {export_path}")
        else:
            click.echo("❌ Failed to export session")
            
    elif import_file and project_id:
        session = session_manager.import_session(project_id, Path(import_file))
        if session:
            click.echo(f"✓ Imported session: {session.name}")
        else:
            click.echo("❌ Failed to import session")


if __name__ == '__main__':
    cli()