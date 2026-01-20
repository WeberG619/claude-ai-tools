"""Database management for the code memory system."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base
from .config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, config: Config):
        self.config = config
        self.config.ensure_directories()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
    @property
    def engine(self) -> Engine:
        """Get or create the database engine."""
        if self._engine is None:
            db_path = self.config.database.path
            db_url = f"sqlite:///{db_path}"
            
            # Use StaticPool for better performance with SQLite
            self._engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
            
            # Create tables if they don't exist
            Base.metadata.create_all(self._engine)
            
            logger.info(f"Database initialized at {db_path}")
            
        return self._engine
        
    @property
    def session_factory(self) -> sessionmaker:
        """Get the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory
        
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a new database session."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            
    def close(self):
        """Close the database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            
    def reset(self):
        """Reset the database (delete all data)."""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.warning("Database reset completed")
        
    def get_db_size(self) -> int:
        """Get the database file size in bytes."""
        if self.config.database.path.exists():
            return self.config.database.path.stat().st_size
        return 0