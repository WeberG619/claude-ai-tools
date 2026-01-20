"""
Spine Passive Learner - Learn BIM patterns from your Revit projects.

This system extracts patterns from your Revit projects overnight,
building a knowledge base that Claude can query to understand your
workflow standards.
"""

__version__ = "1.0.0"
__author__ = "Weber"

from .database import Database
from .extractor import RevitExtractor
from .analyzer import PatternAnalyzer
from .recommender import ProjectRecommender
