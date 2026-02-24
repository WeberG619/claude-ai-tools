"""
Cognitive Core — The thinking layer for Weber's Claude Code system.

Provides autonomous reasoning, self-evaluation, goal decomposition,
learning compilation, task routing, and cross-session reflection.

Usage:
    from cognitive_core import CognitiveCore
    brain = CognitiveCore()

    # Self-evaluate after an action
    evaluation = brain.evaluate("created walls in Revit", result_summary, goal)

    # Decompose a high-level goal into tasks
    tree = brain.decompose("Set up CD sheets for residential project")

    # Route a task to the right framework
    decision = brain.route("Fix wall join at grid intersection B-3")

    # End-of-session reflection
    reflection = brain.reflect(session_data)

    # Compile learnings into enforced rules
    rules = brain.compile()
"""

from .core import CognitiveCore
from .evaluator import Evaluator, Evaluation
from .decomposer import GoalDecomposer, TaskNode
from .compiler import LearningCompiler, CompiledRules
from .meta_router import MetaRouter, RoutingDecision
from .reflector import SessionReflector, Reflection
from .dispatcher import CognitiveDispatcher, DispatchResult, Event
from .watcher import CognitiveWatcher

__version__ = "1.0.0"
__all__ = [
    "CognitiveCore",
    "Evaluator", "Evaluation",
    "GoalDecomposer", "TaskNode",
    "LearningCompiler", "CompiledRules",
    "MetaRouter", "RoutingDecision",
    "SessionReflector", "Reflection",
    "CognitiveDispatcher", "DispatchResult", "Event",
    "CognitiveWatcher",
]
