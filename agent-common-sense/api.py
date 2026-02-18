"""
REST API for the Common Sense Engine.

Makes the engine accessible to any agent in any language via HTTP.

Endpoints:
    POST /check          - Check an action before executing
    POST /learn          - Store a correction from a mistake
    POST /avoided        - Log an avoided mistake
    POST /succeeded      - Log a successful pattern
    POST /feedback       - Record correction outcome
    GET  /feedback/summary - Get feedback statistics
    GET  /domains        - List available domains
    GET  /stale          - Get stale corrections
    POST /cleanup        - Run quality cleanup
    POST /synthesize     - Find correction patterns
    GET  /health         - Health check

Usage:
    # Start the server
    python api.py                           # Default port 8377
    python api.py --port 9000               # Custom port
    python api.py --db /path/to/memories.db # Custom DB

    # Or with uvicorn
    uvicorn api:app --port 8377

    # Client examples (any language)
    curl -X POST http://localhost:8377/check \\
         -H "Content-Type: application/json" \\
         -d '{"action": "git push --force origin main"}'

    curl -X POST http://localhost:8377/learn \\
         -H "Content-Type: application/json" \\
         -d '{"action": "deployed to wrong path", "what_went_wrong": "used system addins", "correct_approach": "use user addins path"}'
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from sense import CommonSense

# ─── REQUEST/RESPONSE MODELS ────────────────────────────────────

if HAS_FASTAPI:

    class CheckRequest(BaseModel):
        action: str = Field(..., description="The action to check before executing")
        context: str = Field("", description="Additional context about the action")
        project: str = Field("general", description="Project scope")

    class CheckResponse(BaseModel):
        blocked: bool
        reason: str
        warnings: list[str]
        confidence: float
        corrections: list[dict]
        safe: bool

    class LearnRequest(BaseModel):
        action: str = Field(..., description="What was attempted")
        what_went_wrong: str = Field(..., description="What went wrong")
        correct_approach: str = Field(..., description="The correct way to do it")
        category: str = Field("execution", description="Domain category")
        severity: str = Field("medium", description="critical/high/medium/low")
        tags: list[str] = Field(default_factory=list)
        project: str = Field("general", description="Project scope")

    class FeedbackRequest(BaseModel):
        correction_id: int = Field(..., description="ID of the correction")
        helped: bool = Field(..., description="Whether the correction helped")
        notes: str = Field("", description="Brief explanation")

    class AvoidedRequest(BaseModel):
        description: str = Field(..., description="What was avoided")
        project: str = Field("general")

    class SucceededRequest(BaseModel):
        action: str = Field(..., description="What succeeded")
        context: str = Field("", description="Additional context")
        project: str = Field("general")

    class CleanupRequest(BaseModel):
        dry_run: bool = Field(True, description="Preview without making changes")

    class SynthesizeRequest(BaseModel):
        project: str = Field("general")

    # ─── APP SETUP ───────────────────────────────────────────────

    app = FastAPI(
        title="Common Sense Engine API",
        description="Experiential judgment for AI agents. Check actions against accumulated corrections, learn from mistakes, track outcomes.",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instance cache keyed by (db_path, project)
    _instances: dict[tuple, CommonSense] = {}
    _db_path: Optional[str] = None

    def _get_cs(project: str = "general") -> CommonSense:
        key = (_db_path, project)
        if key not in _instances:
            _instances[key] = CommonSense(project=project, db_path=_db_path)
        return _instances[key]

    # ─── ENDPOINTS ───────────────────────────────────────────────

    @app.get("/health")
    def health():
        cs = _get_cs()
        return {
            "status": "ok",
            "version": "2.0.0",
            "db_path": cs.db_path,
            "search_backend": cs._search.name if cs._search else "none",
        }

    @app.post("/check", response_model=CheckResponse)
    def check_action(req: CheckRequest):
        """Check an action against accumulated experience before executing it."""
        cs = _get_cs(req.project)
        result = cs.before(req.action, req.context)
        return CheckResponse(
            blocked=result.blocked,
            reason=result.reason,
            warnings=result.warnings,
            confidence=result.confidence,
            corrections=result.corrections,
            safe=result.safe,
        )

    @app.post("/learn")
    def learn(req: LearnRequest):
        """Store a correction from a mistake or user feedback."""
        cs = _get_cs(req.project)
        stored = cs.learn(
            action=req.action,
            what_went_wrong=req.what_went_wrong,
            correct_approach=req.correct_approach,
            category=req.category,
            severity=req.severity,
            tags=req.tags,
        )
        if stored is None:
            raise HTTPException(400, "Correction rejected (invalid or duplicate)")
        return {"status": "stored", "correction": stored}

    @app.post("/feedback")
    def feedback(req: FeedbackRequest):
        """Record whether a correction actually helped."""
        cs = _get_cs()
        success = cs.correction_helped(req.correction_id, req.helped, req.notes)
        if not success:
            raise HTTPException(500, "Failed to record feedback")
        return {"status": "recorded", "correction_id": req.correction_id, "helped": req.helped}

    @app.get("/feedback/summary")
    def feedback_summary():
        """Get overall feedback statistics."""
        cs = _get_cs()
        return cs.get_feedback_summary()

    @app.post("/avoided")
    def avoided(req: AvoidedRequest):
        """Log that a known mistake was successfully avoided."""
        cs = _get_cs(req.project)
        cs.avoided(req.description)
        return {"status": "logged"}

    @app.post("/succeeded")
    def succeeded(req: SucceededRequest):
        """Log a successful action as a known-good pattern."""
        cs = _get_cs(req.project)
        cs.succeeded(req.action, req.context)
        return {"status": "logged"}

    @app.get("/domains")
    def list_domains():
        """List available domain modules."""
        try:
            from domains import DomainLoader
            loader = DomainLoader()
            return {"domains": loader.list_domains()}
        except ImportError:
            return {"domains": [], "note": "domains module not available"}

    @app.get("/stale")
    def stale_corrections(days: int = 90):
        """Get corrections that are old and never been validated."""
        cs = _get_cs()
        return {"stale": cs.get_stale(days=days)}

    @app.post("/cleanup")
    def cleanup(req: CleanupRequest):
        """Run quality cleanup on the correction database."""
        cs = _get_cs()
        return cs.cleanup(dry_run=req.dry_run)

    @app.post("/synthesize")
    def synthesize(req: SynthesizeRequest):
        """Analyze corrections for recurring patterns."""
        cs = _get_cs(req.project)
        patterns = cs.synthesize()
        return {"patterns": patterns}


# ─── MAIN ────────────────────────────────────────────────────────

def main():
    if not HAS_FASTAPI:
        print("FastAPI not installed. Install with: pip install fastapi uvicorn")
        print("Or use the Python API directly: from sense import CommonSense")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description="Common Sense Engine REST API")
    parser.add_argument("--port", type=int, default=8377, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--db", help="Path to memory SQLite database")
    args = parser.parse_args()

    global _db_path
    _db_path = args.db

    import uvicorn
    print(f"Starting Common Sense Engine API on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
