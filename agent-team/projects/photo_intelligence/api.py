"""
Photo Intelligence API - FastAPI web service.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import load_config
from photo_analyzer import PhotoAnalyzer
from database import Database


# Initialize
config = load_config()
app = FastAPI(
    title="Photo Intelligence",
    description="AI-powered construction photo organization",
    version="1.0.0"
)

# Ensure upload directory exists
os.makedirs(config.storage.upload_dir, exist_ok=True)

# Database
db = Database()

# Photo analyzer (lazy loaded when API key available)
analyzer = None


def get_analyzer():
    """Get or create photo analyzer."""
    global analyzer
    if analyzer is None and config.openai.api_key:
        analyzer = PhotoAnalyzer(config.openai)
    return analyzer


# Pydantic models for API
class ProjectCreate(BaseModel):
    name: str
    client: Optional[str] = None
    address: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    client: Optional[str]
    address: Optional[str]
    created_at: str


class PhotoResponse(BaseModel):
    id: int
    filename: str
    description: Optional[str]
    room_type: Optional[str]
    floor_level: Optional[str]
    trade: Optional[str]
    work_stage: Optional[str]
    issue_count: int
    tags: List[dict]


# API Endpoints

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "Photo Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "analyzer_ready": get_analyzer() is not None
    }


# Project endpoints
@app.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    project_id = db.create_project(
        name=project.name,
        client=project.client,
        address=project.address
    )
    return db.get_project(project_id)


@app.get("/projects")
async def list_projects():
    """List all projects."""
    return db.list_projects()


@app.get("/projects/{project_id}")
async def get_project(project_id: int):
    """Get project details."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/projects/{project_id}/stats")
async def get_project_stats(project_id: int):
    """Get project statistics."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.get_project_stats(project_id)


# Photo endpoints
@app.post("/projects/{project_id}/photos")
async def upload_photo(
    project_id: int,
    file: UploadFile = File(...),
    analyze: bool = True
):
    """Upload and optionally analyze a photo."""
    # Validate project exists
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in config.storage.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed"
        )

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = Path(config.storage.upload_dir) / str(project_id) / safe_filename

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = {
        "filename": safe_filename,
        "path": str(file_path),
        "analyzed": False
    }

    # Analyze if requested and API key available
    if analyze:
        photo_analyzer = get_analyzer()
        if photo_analyzer:
            try:
                analysis = photo_analyzer.analyze_photo(str(file_path))
                photo_id = db.save_photo_analysis(project_id, str(file_path), analysis)
                result["analyzed"] = True
                result["photo_id"] = photo_id
                result["analysis"] = {
                    "description": analysis.description,
                    "room_type": analysis.room_type,
                    "floor_level": analysis.floor_level,
                    "trade": analysis.trade,
                    "work_stage": analysis.work_stage,
                    "issue_count": analysis.issue_count,
                    "tags": [{"category": t.category, "value": t.value} for t in analysis.tags]
                }
            except Exception as e:
                result["error"] = str(e)
        else:
            result["error"] = "Analyzer not available (API key not set)"

    return result


@app.get("/projects/{project_id}/photos")
async def list_photos(
    project_id: int,
    room_type: Optional[str] = None,
    trade: Optional[str] = None,
    has_issues: Optional[bool] = None,
    search: Optional[str] = None
):
    """List and filter photos for a project."""
    photos = db.search_photos(
        project_id=project_id,
        room_type=room_type,
        trade=trade,
        has_issues=has_issues,
        tag_value=search
    )
    return photos


@app.get("/photos/{photo_id}")
async def get_photo(photo_id: int):
    """Get photo details with tags and issues."""
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "analyzer": "ready" if get_analyzer() else "unavailable"
    }


# Run with: uvicorn api:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
