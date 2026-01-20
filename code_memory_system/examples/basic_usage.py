"""Basic usage example for the Code Memory System."""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.code_memory import CodeMemory
from src.core.config import Config


def main():
    # Initialize the system
    config = Config.from_env()
    code_memory = CodeMemory(config)
    
    # Example 1: Index a project
    print("=== Indexing Project ===")
    project_path = Path("/path/to/your/project")  # Change this to your project path
    
    if project_path.exists():
        project_info = code_memory.index_project(project_path, "My Project")
        print(f"Indexed {project_info.indexed_files}/{project_info.total_files} files")
    
    # Example 2: Query for bug fixes
    print("\n=== Querying for Authentication Bugs ===")
    result = code_memory.query(
        "fix the authentication bug in login function",
        project_id=1,  # Use actual project ID
        max_results=5
    )
    
    print(f"Query type detected: {result.query_type}")
    print(f"Found {len(result.entities)} relevant code entities:")
    
    for entity in result.entities:
        print(f"  - {entity.entity_type} {entity.name} in {entity.file_path}:{entity.start_line}")
    
    # Example 3: Jump directly to a location
    print("\n=== Jumping to Location ===")
    location = code_memory.jump_to("authenticate_user", project_id=1)
    
    if location:
        entity = location['entity']
        print(f"Found: {entity['type']} {entity['name']} at line {entity['start_line']}")
        print(f"File: {entity['file']}")
    
    # Example 4: Session management
    print("\n=== Session Management ===")
    session = code_memory.start_session(project_id=1, name="Bug fixing session")
    print(f"Started session: {session.name}")
    
    # Add some context to the session
    code_memory.session_manager.add_open_file("/path/to/file.py", {"line": 42, "column": 10})
    code_memory.session_manager.add_bookmark("/path/to/file.py", 42, "Bug location")
    
    # Example 5: Get statistics
    print("\n=== System Statistics ===")
    stats = code_memory.get_statistics()
    cache_stats = stats['cache']
    
    print(f"Cache hit rate: {cache_stats['hit_rate']:.2%}")
    print(f"Vector store entities: {stats['vector_store']['total_entities']}")
    
    # Clean up
    code_memory.close()


if __name__ == "__main__":
    main()