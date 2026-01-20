"""Session management for persistent working context."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session as DBSession

from ..core.models import Session, Project, Query, File, CodeEntity
from ..core.database import DatabaseManager

logger = logging.getLogger(__name__)


class SessionState:
    """Represents the current state of a working session."""
    
    def __init__(self):
        self.open_files: List[str] = []
        self.cursor_positions: Dict[str, Dict[str, int]] = {}  # file_path -> {line, column}
        self.recent_queries: List[str] = []
        self.working_context: Dict[str, Any] = {}
        self.bookmarks: List[Dict[str, Any]] = []
        self.last_activity: datetime = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for storage."""
        return {
            'open_files': self.open_files,
            'cursor_positions': self.cursor_positions,
            'recent_queries': self.recent_queries,
            'working_context': self.working_context,
            'bookmarks': self.bookmarks,
            'last_activity': self.last_activity.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create state from dictionary."""
        state = cls()
        state.open_files = data.get('open_files', [])
        state.cursor_positions = data.get('cursor_positions', {})
        state.recent_queries = data.get('recent_queries', [])
        state.working_context = data.get('working_context', {})
        state.bookmarks = data.get('bookmarks', [])
        
        if 'last_activity' in data:
            state.last_activity = datetime.fromisoformat(data['last_activity'])
            
        return state


class SessionManager:
    """Manages working sessions with persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_session: Optional[Session] = None
        self.current_state: Optional[SessionState] = None
        
    def create_session(self, project_id: int, name: Optional[str] = None) -> Session:
        """Create a new working session."""
        with self.db_manager.session() as db_session:
            # Deactivate other sessions for this project
            db_session.query(Session).filter_by(
                project_id=project_id,
                active=True
            ).update({'active': False})
            
            # Create new session
            session = Session(
                project_id=project_id,
                name=name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                active=True
            )
            
            db_session.add(session)
            db_session.commit()
            
            self.current_session = session
            self.current_state = SessionState()
            
            logger.info(f"Created new session: {session.name}")
            
            return session
            
    def load_session(self, session_id: int) -> bool:
        """Load an existing session."""
        with self.db_manager.session() as db_session:
            session = db_session.query(Session).get(session_id)
            
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
                
            # Update last accessed
            session.last_accessed = datetime.utcnow()
            session.active = True
            
            # Load state
            if session.state:
                self.current_state = SessionState.from_dict(session.state)
            else:
                self.current_state = SessionState()
                
            self.current_session = session
            db_session.commit()
            
            logger.info(f"Loaded session: {session.name}")
            
            return True
            
    def save_session(self) -> bool:
        """Save current session state."""
        if not self.current_session or not self.current_state:
            return False
            
        with self.db_manager.session() as db_session:
            session = db_session.query(Session).get(self.current_session.id)
            
            if session:
                session.state = self.current_state.to_dict()
                session.last_accessed = datetime.utcnow()
                db_session.commit()
                
                logger.debug(f"Saved session state for: {session.name}")
                return True
                
        return False
        
    def continue_last_session(self, project_id: int) -> Optional[Session]:
        """Continue the last active session for a project."""
        with self.db_manager.session() as db_session:
            # Find most recent active session
            session = db_session.query(Session).filter_by(
                project_id=project_id
            ).order_by(Session.last_accessed.desc()).first()
            
            if session:
                self.load_session(session.id)
                return session
                
        # No existing session, create new one
        return self.create_session(project_id)
        
    def add_open_file(self, file_path: str, cursor_position: Optional[Dict[str, int]] = None):
        """Add a file to the open files list."""
        if not self.current_state:
            return
            
        if file_path not in self.current_state.open_files:
            self.current_state.open_files.append(file_path)
            
        if cursor_position:
            self.current_state.cursor_positions[file_path] = cursor_position
            
        self.current_state.last_activity = datetime.utcnow()
        self.save_session()
        
    def remove_open_file(self, file_path: str):
        """Remove a file from the open files list."""
        if not self.current_state:
            return
            
        if file_path in self.current_state.open_files:
            self.current_state.open_files.remove(file_path)
            
        if file_path in self.current_state.cursor_positions:
            del self.current_state.cursor_positions[file_path]
            
        self.current_state.last_activity = datetime.utcnow()
        self.save_session()
        
    def update_cursor_position(self, file_path: str, line: int, column: int):
        """Update cursor position for a file."""
        if not self.current_state:
            return
            
        self.current_state.cursor_positions[file_path] = {
            'line': line,
            'column': column
        }
        
        self.current_state.last_activity = datetime.utcnow()
        
    def add_query(self, query_text: str):
        """Add a query to the session history."""
        if not self.current_state:
            return
            
        self.current_state.recent_queries.append(query_text)
        
        # Keep only last 50 queries
        if len(self.current_state.recent_queries) > 50:
            self.current_state.recent_queries = self.current_state.recent_queries[-50:]
            
        self.current_state.last_activity = datetime.utcnow()
        self.save_session()
        
    def add_bookmark(self, file_path: str, line: int, description: str = ""):
        """Add a bookmark to the session."""
        if not self.current_state:
            return
            
        bookmark = {
            'file_path': file_path,
            'line': line,
            'description': description,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.current_state.bookmarks.append(bookmark)
        self.current_state.last_activity = datetime.utcnow()
        self.save_session()
        
    def get_working_context(self, key: str) -> Any:
        """Get a value from working context."""
        if not self.current_state:
            return None
            
        return self.current_state.working_context.get(key)
        
    def set_working_context(self, key: str, value: Any):
        """Set a value in working context."""
        if not self.current_state:
            return
            
        self.current_state.working_context[key] = value
        self.current_state.last_activity = datetime.utcnow()
        self.save_session()
        
    def list_sessions(self, project_id: int) -> List[Dict[str, Any]]:
        """List all sessions for a project."""
        with self.db_manager.session() as db_session:
            sessions = db_session.query(Session).filter_by(
                project_id=project_id
            ).order_by(Session.last_accessed.desc()).all()
            
            return [
                {
                    'id': s.id,
                    'name': s.name,
                    'created_at': s.created_at,
                    'last_accessed': s.last_accessed,
                    'active': s.active,
                    'query_count': len(s.queries)
                }
                for s in sessions
            ]
            
    def delete_session(self, session_id: int) -> bool:
        """Delete a session."""
        with self.db_manager.session() as db_session:
            session = db_session.query(Session).get(session_id)
            
            if session:
                # Clear current session if it's being deleted
                if self.current_session and self.current_session.id == session_id:
                    self.current_session = None
                    self.current_state = None
                    
                db_session.delete(session)
                db_session.commit()
                
                logger.info(f"Deleted session: {session.name}")
                return True
                
        return False
        
    def export_session(self, session_id: int, export_path: Path) -> bool:
        """Export session data to a file."""
        with self.db_manager.session() as db_session:
            session = db_session.query(Session).get(session_id)
            
            if not session:
                return False
                
            export_data = {
                'session': {
                    'name': session.name,
                    'created_at': session.created_at.isoformat(),
                    'last_accessed': session.last_accessed.isoformat()
                },
                'state': session.state,
                'queries': [
                    {
                        'text': q.text,
                        'query_type': q.query_type,
                        'created_at': q.created_at.isoformat()
                    }
                    for q in session.queries
                ]
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            logger.info(f"Exported session to: {export_path}")
            return True
            
    def import_session(self, project_id: int, import_path: Path) -> Optional[Session]:
        """Import session data from a file."""
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)
                
            # Create new session
            session_name = f"Imported: {data['session']['name']}"
            session = self.create_session(project_id, session_name)
            
            # Import state
            if 'state' in data:
                self.current_state = SessionState.from_dict(data['state'])
                self.save_session()
                
            # Import queries
            with self.db_manager.session() as db_session:
                for query_data in data.get('queries', []):
                    query = Query(
                        session_id=session.id,
                        text=query_data['text'],
                        query_type=query_data.get('query_type'),
                        created_at=datetime.fromisoformat(query_data['created_at'])
                    )
                    db_session.add(query)
                    
                db_session.commit()
                
            logger.info(f"Imported session from: {import_path}")
            return session
            
        except Exception as e:
            logger.error(f"Error importing session: {e}")
            return None