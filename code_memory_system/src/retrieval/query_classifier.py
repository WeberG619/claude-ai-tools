"""Query classifier for determining task types and intent."""

import re
import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.models import QueryType

logger = logging.getLogger(__name__)


@dataclass
class QueryIntent:
    """Represents the classified intent of a query."""
    query_type: QueryType
    confidence: float
    keywords: List[str]
    entities_mentioned: List[str]
    scope_indicators: List[str]
    

class QueryClassifier:
    """Classifies queries to determine task type and retrieval strategy."""
    
    # Keywords for each query type
    QUERY_TYPE_KEYWORDS = {
        QueryType.BUG_FIX: [
            'bug', 'fix', 'error', 'issue', 'problem', 'crash', 'exception',
            'broken', 'failing', 'failed', 'not working', 'doesn\'t work',
            'debug', 'troubleshoot', 'resolve', 'patch'
        ],
        QueryType.FEATURE: [
            'add', 'implement', 'create', 'new', 'feature', 'functionality',
            'enhancement', 'extend', 'build', 'develop', 'introduce',
            'support for', 'integrate'
        ],
        QueryType.REFACTORING: [
            'refactor', 'improve', 'optimize', 'clean', 'reorganize',
            'restructure', 'simplify', 'extract', 'rename', 'move',
            'reduce complexity', 'better', 'cleaner'
        ],
        QueryType.DOCUMENTATION: [
            'document', 'documentation', 'explain', 'describe', 'comment',
            'docstring', 'readme', 'guide', 'tutorial', 'how does',
            'what does', 'understanding'
        ],
        QueryType.TESTING: [
            'test', 'testing', 'unit test', 'integration test', 'coverage',
            'assert', 'verify', 'validate', 'check', 'ensure'
        ],
        QueryType.EXPLORATION: [
            'find', 'search', 'locate', 'where', 'show', 'list',
            'explore', 'analyze', 'understand', 'investigate'
        ]
    }
    
    # Scope indicators
    SCOPE_INDICATORS = {
        'file_level': ['file', 'module', 'script'],
        'function_level': ['function', 'method', 'procedure', 'func'],
        'class_level': ['class', 'object', 'type'],
        'project_level': ['project', 'codebase', 'repository', 'entire', 'all']
    }
    
    def classify(self, query: str) -> QueryIntent:
        """Classify a query and determine its intent."""
        query_lower = query.lower()
        
        # Extract mentioned entities (functions, classes, etc.)
        entities = self._extract_entities(query)
        
        # Find scope indicators
        scope_indicators = self._extract_scope_indicators(query_lower)
        
        # Score each query type
        type_scores = {}
        matched_keywords = {}
        
        for query_type, keywords in self.QUERY_TYPE_KEYWORDS.items():
            score = 0
            matches = []
            
            for keyword in keywords:
                if keyword in query_lower:
                    # Weight by keyword length (longer = more specific)
                    weight = len(keyword) / 10.0
                    score += weight
                    matches.append(keyword)
                    
            type_scores[query_type] = score
            matched_keywords[query_type] = matches
            
        # Determine the best match
        if not any(type_scores.values()):
            # Default to exploration if no clear match
            best_type = QueryType.EXPLORATION
            confidence = 0.3
            keywords = []
        else:
            best_type = max(type_scores, key=type_scores.get)
            confidence = min(type_scores[best_type] / 3.0, 1.0)  # Normalize confidence
            keywords = matched_keywords[best_type]
            
        # Adjust confidence based on query structure
        confidence = self._adjust_confidence(query, best_type, confidence)
        
        return QueryIntent(
            query_type=best_type,
            confidence=confidence,
            keywords=keywords,
            entities_mentioned=entities,
            scope_indicators=scope_indicators
        )
        
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential code entity names from query."""
        entities = []
        
        # Look for quoted strings
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        entities.extend(quoted)
        
        # Look for PascalCase or camelCase identifiers
        # PascalCase
        pascal_case = re.findall(r'\b[A-Z][a-zA-Z]*(?:[A-Z][a-zA-Z]*)*\b', query)
        entities.extend(pascal_case)
        
        # camelCase
        camel_case = re.findall(r'\b[a-z]+(?:[A-Z][a-z]*)*\b', query)
        # Filter out common words
        common_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        camel_case = [word for word in camel_case if word not in common_words and len(word) > 2]
        entities.extend(camel_case)
        
        # Look for function calls pattern
        function_calls = re.findall(r'(\w+)\s*\(', query)
        entities.extend(function_calls)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)
                
        return unique_entities
        
    def _extract_scope_indicators(self, query_lower: str) -> List[str]:
        """Extract scope indicators from query."""
        indicators = []
        
        for scope, keywords in self.SCOPE_INDICATORS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    indicators.append(scope)
                    break
                    
        return indicators
        
    def _adjust_confidence(self, query: str, query_type: QueryType, initial_confidence: float) -> float:
        """Adjust confidence based on query characteristics."""
        confidence = initial_confidence
        
        # Boost confidence for queries with code entities
        if re.search(r'["\']([^"\']+)["\']', query):
            confidence = min(confidence + 0.1, 1.0)
            
        # Boost confidence for specific patterns
        if query_type == QueryType.BUG_FIX:
            if re.search(r'error\s+(message|code)|\bfix\s+\w+|exception', query, re.I):
                confidence = min(confidence + 0.2, 1.0)
                
        elif query_type == QueryType.FEATURE:
            if re.search(r'(implement|add|create)\s+\w+\s+(feature|functionality)', query, re.I):
                confidence = min(confidence + 0.2, 1.0)
                
        return confidence
        
    def get_retrieval_strategy(self, intent: QueryIntent) -> Dict[str, any]:
        """Determine retrieval strategy based on query intent."""
        strategy = {
            'include_tests': False,
            'prioritize_recent': False,
            'expand_dependencies': False,
            'include_documentation': False,
            'max_depth': 1
        }
        
        if intent.query_type == QueryType.BUG_FIX:
            # For bug fixes, include tests and recent changes
            strategy['include_tests'] = True
            strategy['prioritize_recent'] = True
            strategy['expand_dependencies'] = True
            
        elif intent.query_type == QueryType.FEATURE:
            # For features, look at similar functionality
            strategy['expand_dependencies'] = True
            strategy['max_depth'] = 2
            
        elif intent.query_type == QueryType.TESTING:
            # For testing, prioritize test files
            strategy['include_tests'] = True
            
        elif intent.query_type == QueryType.DOCUMENTATION:
            # For documentation, include all docstrings
            strategy['include_documentation'] = True
            
        elif intent.query_type == QueryType.REFACTORING:
            # For refactoring, need to see full context
            strategy['expand_dependencies'] = True
            strategy['max_depth'] = 2
            
        return strategy