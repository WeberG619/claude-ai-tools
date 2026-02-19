try:
    from .sense import CommonSense, ActionCheck
except ImportError:
    from sense import CommonSense, ActionCheck

try:
    from .search import (
        SearchBackend, KeywordSearch, TFIDFSearch, EmbeddingSearch,
        HybridSearch, SearchResult, get_best_backend, get_backend_by_name,
    )
except ImportError:
    pass

try:
    from .quality import (
        CorrectionStatus, validate_correction, content_hash,
        find_duplicates, deduplicate_database, decay_score,
        cleanup_database,
    )
except ImportError:
    pass

try:
    from .feedback import FeedbackTracker
except ImportError:
    pass

try:
    from .domains import DomainLoader, DomainPack
except ImportError:
    pass

try:
    from .autocapture import CorrectionCapture
except ImportError:
    pass

try:
    from .summarizer import CorrectionSummarizer
except ImportError:
    pass

try:
    from .context import ContextEngine
except ImportError:
    pass

try:
    from .workflows import WorkflowRecorder, Workflow
except ImportError:
    pass

# Autonomy Engine v1.0
try:
    from .goals import GoalEngine, Goal, GoalEvent
except ImportError:
    pass

try:
    from .planner import Planner, Plan, PlanStep, PlanTemplate
except ImportError:
    pass

try:
    from .alignment import AlignmentCore, AlignmentPrinciple, AlignmentProfile, InjectionResult
except ImportError:
    pass

try:
    from .coordinator import AgentCoordinator, AgentSession, ResourceLock, WorkflowState
except ImportError:
    pass

# Execution verification (grades D+ → B+)
try:
    from .aggregator import Aggregator, AggregatedContext
except ImportError:
    pass

try:
    from .coherence import CoherenceMonitor, CoherenceCheck
except ImportError:
    pass

# Permission scoping + self-check (A+ upgrades)
try:
    from .permissions import PermissionScope, ComplianceResult, get_scope_for_agent, compile_permission_prompt, verify_output_compliance
except ImportError:
    pass

try:
    from .selfcheck import SelfChecker, SelfCheckResult
except ImportError:
    pass

__all__ = [
    "CommonSense", "ActionCheck",
    "SearchBackend", "KeywordSearch", "TFIDFSearch", "EmbeddingSearch",
    "HybridSearch", "SearchResult", "get_best_backend", "get_backend_by_name",
    "CorrectionStatus", "validate_correction", "content_hash",
    "find_duplicates", "deduplicate_database", "decay_score", "cleanup_database",
    "FeedbackTracker",
    "DomainLoader", "DomainPack",
    "CorrectionCapture",
    "CorrectionSummarizer",
    "ContextEngine",
    "WorkflowRecorder", "Workflow",
    # Autonomy Engine v1.0
    "GoalEngine", "Goal", "GoalEvent",
    "Planner", "Plan", "PlanStep", "PlanTemplate",
    "AlignmentCore", "AlignmentPrinciple", "AlignmentProfile", "InjectionResult",
    "AgentCoordinator", "AgentSession", "ResourceLock", "WorkflowState",
    # Execution verification
    "Aggregator", "AggregatedContext",
    "CoherenceMonitor", "CoherenceCheck",
    # Permission scoping + self-check
    "PermissionScope", "ComplianceResult",
    "get_scope_for_agent", "compile_permission_prompt", "verify_output_compliance",
    "SelfChecker", "SelfCheckResult",
]
__version__ = "3.3.0"
