"""Core data models for the code memory system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, Float, JSON, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class FileType(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    OTHER = "other"


class QueryType(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    EXPLORATION = "exploration"
    

class CodeEntity(Base):
    """Represents a code entity (function, class, module) in the database."""
    __tablename__ = "code_entities"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # function, class, module
    start_line = Column(Integer)
    end_line = Column(Integer)
    signature = Column(Text)
    docstring = Column(Text)
    embedding = Column(JSON)  # Store as JSON for simplicity
    dependencies = Column(JSON)  # List of dependencies
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    file = relationship("File", back_populates="entities")
    

class File(Base):
    """Represents a file in the codebase."""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    path = Column(String, nullable=False)
    relative_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    hash = Column(String, nullable=False)
    size = Column(Integer)
    last_modified = Column(DateTime)
    last_indexed = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="files")
    entities = relationship("CodeEntity", back_populates="file", cascade="all, delete-orphan")
    

class Project(Base):
    """Represents a project/codebase."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    root_path = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_indexed = Column(DateTime)
    total_files = Column(Integer, default=0)
    indexed_files = Column(Integer, default=0)
    
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    

class Session(Base):
    """Represents a working session."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    state = Column(JSON)  # Store session state as JSON
    active = Column(Boolean, default=True)
    
    project = relationship("Project", back_populates="sessions")
    queries = relationship("Query", back_populates="session", cascade="all, delete-orphan")
    

class Query(Base):
    """Represents a query made to the system."""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    text = Column(Text, nullable=False)
    query_type = Column(String)
    retrieved_context = Column(JSON)
    response_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="queries")


# Pydantic models for API/CLI interaction

class FileInfo(BaseModel):
    path: Path
    relative_path: str
    file_type: FileType
    size: int
    last_modified: datetime
    

class CodeEntityInfo(BaseModel):
    name: str
    entity_type: str
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    

class QueryRequest(BaseModel):
    text: str
    session_id: Optional[int] = None
    max_results: int = Field(default=10, ge=1, le=100)
    include_tests: bool = Field(default=False)
    

class QueryResult(BaseModel):
    query_type: QueryType
    entities: List[CodeEntityInfo]
    files: List[FileInfo]
    relevance_scores: Dict[str, float]
    response_time: float
    

class ProjectInfo(BaseModel):
    name: str
    root_path: Path
    total_files: int
    indexed_files: int
    last_indexed: Optional[datetime] = None
    

class SessionInfo(BaseModel):
    id: int
    name: str
    project_name: str
    created_at: datetime
    last_accessed: datetime
    active: bool