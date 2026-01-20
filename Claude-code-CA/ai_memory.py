#!/usr/bin/env python3
"""
AI Memory and Learning System
Enables the orchestrator to learn from past experiences and improve over time
"""

import os
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import logging
import pickle
import numpy as np
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class Experience:
    """Represents a single experience/interaction"""
    id: str
    timestamp: datetime
    request: str
    intent: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    outcome: str  # success, failure, partial
    error_details: Optional[str] = None
    recovery_attempts: List[Dict[str, Any]] = field(default_factory=list)
    user_feedback: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class Pattern:
    """Represents a learned pattern"""
    pattern_type: str  # error_recovery, successful_sequence, optimization
    context: Dict[str, Any]
    solution: Dict[str, Any]
    success_rate: float
    usage_count: int
    last_used: datetime
    confidence: float

class AIMemory:
    """Memory system for storing and retrieving experiences"""
    
    def __init__(self, db_path: str = "ai_memory.db"):
        self.db_path = db_path
        self.connection = None
        self.patterns = {}
        self.short_term_memory = []  # Recent experiences
        self.working_memory = {}  # Current context
        self._initialize_database()
        self._load_patterns()
    
    def _initialize_database(self):
        """Initialize the database schema"""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()
        
        # Experiences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                request TEXT NOT NULL,
                intent TEXT NOT NULL,
                actions_taken TEXT NOT NULL,
                outcome TEXT NOT NULL,
                error_details TEXT,
                recovery_attempts TEXT,
                user_feedback TEXT,
                performance_metrics TEXT,
                embedding BLOB
            )
        """)
        
        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                context TEXT NOT NULL,
                solution TEXT NOT NULL,
                success_rate REAL NOT NULL,
                usage_count INTEGER NOT NULL,
                last_used TEXT NOT NULL,
                confidence REAL NOT NULL
            )
        """)
        
        # Solutions table (for quick lookup)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solutions (
                problem_hash TEXT PRIMARY KEY,
                solution TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_timestamp ON experiences(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_outcome ON experiences(outcome)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON patterns(pattern_type)")
        
        self.connection.commit()
    
    def _load_patterns(self):
        """Load patterns from database"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM patterns")
        
        for row in cursor.fetchall():
            pattern = Pattern(
                pattern_type=row[1],
                context=json.loads(row[2]),
                solution=json.loads(row[3]),
                success_rate=row[4],
                usage_count=row[5],
                last_used=datetime.fromisoformat(row[6]),
                confidence=row[7]
            )
            
            pattern_key = self._generate_pattern_key(pattern.pattern_type, pattern.context)
            self.patterns[pattern_key] = pattern
    
    def _generate_pattern_key(self, pattern_type: str, context: Dict[str, Any]) -> str:
        """Generate a unique key for a pattern"""
        context_str = json.dumps(context, sort_keys=True)
        return f"{pattern_type}:{hashlib.md5(context_str.encode()).hexdigest()}"
    
    async def store_experience(self, experience: Experience):
        """Store an experience in memory"""
        # Add to short-term memory
        self.short_term_memory.append(experience)
        if len(self.short_term_memory) > 100:  # Keep last 100 experiences
            self.short_term_memory.pop(0)
        
        # Store in database
        cursor = self.connection.cursor()
        
        # Generate embedding (simplified - in production, use proper embeddings)
        embedding = self._generate_embedding(experience.request)
        
        cursor.execute("""
            INSERT INTO experiences 
            (id, timestamp, request, intent, actions_taken, outcome, 
             error_details, recovery_attempts, user_feedback, performance_metrics, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experience.id,
            experience.timestamp.isoformat(),
            experience.request,
            json.dumps(experience.intent),
            json.dumps(experience.actions_taken),
            experience.outcome,
            experience.error_details,
            json.dumps(experience.recovery_attempts),
            experience.user_feedback,
            json.dumps(experience.performance_metrics),
            pickle.dumps(embedding)
        ))
        
        self.connection.commit()
        
        # Learn from experience
        await self._learn_from_experience(experience)
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate a simple embedding for text (placeholder for real embedding model)"""
        # In production, use a proper embedding model
        # For now, create a simple hash-based vector
        hash_val = hashlib.md5(text.encode()).hexdigest()
        vector = np.array([int(hash_val[i:i+2], 16) / 255.0 for i in range(0, 32, 2)])
        return vector
    
    async def _learn_from_experience(self, experience: Experience):
        """Learn patterns from an experience"""
        
        # Learn error recovery patterns
        if experience.outcome == 'failure' and experience.recovery_attempts:
            for recovery in experience.recovery_attempts:
                if recovery.get('success'):
                    await self._store_recovery_pattern(experience, recovery)
        
        # Learn successful action sequences
        if experience.outcome == 'success':
            await self._store_success_pattern(experience)
        
        # Update solution effectiveness
        if experience.intent:
            problem_hash = self._hash_problem(experience.intent)
            await self._update_solution_stats(problem_hash, experience)
    
    async def _store_recovery_pattern(self, experience: Experience, recovery: Dict[str, Any]):
        """Store a successful recovery pattern"""
        pattern = Pattern(
            pattern_type='error_recovery',
            context={
                'error': experience.error_details,
                'action_before_error': experience.actions_taken[-1] if experience.actions_taken else None
            },
            solution=recovery,
            success_rate=1.0,
            usage_count=1,
            last_used=datetime.now(),
            confidence=0.8
        )
        
        pattern_key = self._generate_pattern_key(pattern.pattern_type, pattern.context)
        
        if pattern_key in self.patterns:
            # Update existing pattern
            existing = self.patterns[pattern_key]
            existing.usage_count += 1
            existing.last_used = datetime.now()
            existing.success_rate = (existing.success_rate * (existing.usage_count - 1) + 1) / existing.usage_count
        else:
            # Store new pattern
            self.patterns[pattern_key] = pattern
            await self._save_pattern(pattern)
    
    async def _store_success_pattern(self, experience: Experience):
        """Store a successful action sequence"""
        pattern = Pattern(
            pattern_type='successful_sequence',
            context={
                'task_type': experience.intent.get('task_type'),
                'application': experience.intent.get('application')
            },
            solution={
                'actions': experience.actions_taken,
                'performance': experience.performance_metrics
            },
            success_rate=1.0,
            usage_count=1,
            last_used=datetime.now(),
            confidence=0.9
        )
        
        pattern_key = self._generate_pattern_key(pattern.pattern_type, pattern.context)
        
        if pattern_key in self.patterns:
            # Update existing pattern
            existing = self.patterns[pattern_key]
            existing.usage_count += 1
            existing.last_used = datetime.now()
            
            # Update solution if this one was faster
            if experience.performance_metrics.get('duration', float('inf')) < \
               existing.solution.get('performance', {}).get('duration', float('inf')):
                existing.solution = pattern.solution
        else:
            # Store new pattern
            self.patterns[pattern_key] = pattern
            await self._save_pattern(pattern)
    
    async def _save_pattern(self, pattern: Pattern):
        """Save pattern to database"""
        cursor = self.connection.cursor()
        pattern_id = self._generate_pattern_key(pattern.pattern_type, pattern.context)
        
        cursor.execute("""
            INSERT OR REPLACE INTO patterns 
            (id, pattern_type, context, solution, success_rate, usage_count, last_used, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_id,
            pattern.pattern_type,
            json.dumps(pattern.context),
            json.dumps(pattern.solution),
            pattern.success_rate,
            pattern.usage_count,
            pattern.last_used.isoformat(),
            pattern.confidence
        ))
        
        self.connection.commit()
    
    def _hash_problem(self, intent: Dict[str, Any]) -> str:
        """Generate hash for a problem/intent"""
        # Create a normalized representation
        normalized = {
            'task_type': intent.get('task_type'),
            'action': intent.get('action'),
            'target': intent.get('target'),
            'application': intent.get('application')
        }
        return hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    
    async def _update_solution_stats(self, problem_hash: str, experience: Experience):
        """Update solution statistics"""
        cursor = self.connection.cursor()
        
        if experience.outcome == 'success':
            cursor.execute("""
                INSERT INTO solutions (problem_hash, solution, success_count, failure_count, last_used)
                VALUES (?, ?, 1, 0, ?)
                ON CONFLICT(problem_hash) DO UPDATE SET
                    success_count = success_count + 1,
                    last_used = ?
            """, (
                problem_hash,
                json.dumps(experience.actions_taken),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        else:
            cursor.execute("""
                UPDATE solutions 
                SET failure_count = failure_count + 1, last_used = ?
                WHERE problem_hash = ?
            """, (datetime.now().isoformat(), problem_hash))
        
        self.connection.commit()
    
    async def recall_similar_experiences(self, request: str, intent: Dict[str, Any], limit: int = 5) -> List[Experience]:
        """Recall similar past experiences"""
        # Generate embedding for current request
        current_embedding = self._generate_embedding(request)
        
        # Query database for similar experiences
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM experiences 
            WHERE outcome = 'success'
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        similar_experiences = []
        
        for row in cursor.fetchall():
            exp_data = {
                'id': row[0],
                'timestamp': row[1],
                'request': row[2],
                'intent': json.loads(row[3]),
                'actions_taken': json.loads(row[4]),
                'outcome': row[5],
                'error_details': row[6],
                'recovery_attempts': json.loads(row[7]) if row[7] else [],
                'user_feedback': row[8],
                'performance_metrics': json.loads(row[9]) if row[9] else {}
            }
            
            # Calculate similarity (simplified)
            if row[10]:  # embedding
                stored_embedding = pickle.loads(row[10])
                similarity = np.dot(current_embedding, stored_embedding)
                
                if similarity > 0.7:  # Threshold
                    experience = Experience.from_dict(exp_data)
                    similar_experiences.append((similarity, experience))
        
        # Sort by similarity and return top matches
        similar_experiences.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in similar_experiences[:limit]]
    
    async def get_best_solution(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the best known solution for a problem"""
        problem_hash = self._hash_problem(intent)
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT solution, success_count, failure_count 
            FROM solutions 
            WHERE problem_hash = ?
        """, (problem_hash,))
        
        row = cursor.fetchone()
        if row and row[1] > row[2]:  # More successes than failures
            return {
                'solution': json.loads(row[0]),
                'confidence': row[1] / (row[1] + row[2])
            }
        
        # Check patterns
        pattern_key = self._generate_pattern_key('successful_sequence', {
            'task_type': intent.get('task_type'),
            'application': intent.get('application')
        })
        
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            if pattern.success_rate > 0.7:
                return {
                    'solution': pattern.solution.get('actions', []),
                    'confidence': pattern.confidence
                }
        
        return None
    
    async def get_recovery_strategy(self, error: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get recovery strategy for an error"""
        pattern_key = self._generate_pattern_key('error_recovery', {
            'error': error,
            'action_before_error': context.get('last_action')
        })
        
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            return pattern.solution
        
        # Try partial match
        for key, pattern in self.patterns.items():
            if pattern.pattern_type == 'error_recovery' and error in str(pattern.context.get('error', '')):
                return pattern.solution
        
        return None
    
    def update_working_memory(self, key: str, value: Any):
        """Update working memory (current context)"""
        self.working_memory[key] = value
    
    def get_working_memory(self, key: str) -> Any:
        """Get from working memory"""
        return self.working_memory.get(key)
    
    async def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        cursor = self.connection.cursor()
        
        # Success rate over time
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes
            FROM experiences
            WHERE timestamp > datetime('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)
        
        daily_stats = []
        for row in cursor.fetchall():
            daily_stats.append({
                'date': row[0],
                'total': row[1],
                'success_rate': row[2] / row[1] if row[1] > 0 else 0
            })
        
        # Most common errors
        cursor.execute("""
            SELECT error_details, COUNT(*) as count
            FROM experiences
            WHERE outcome = 'failure' AND error_details IS NOT NULL
            GROUP BY error_details
            ORDER BY count DESC
            LIMIT 10
        """)
        
        common_errors = [{'error': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Best performing patterns
        best_patterns = sorted(
            [p for p in self.patterns.values() if p.usage_count > 5],
            key=lambda p: p.success_rate * p.confidence,
            reverse=True
        )[:5]
        
        return {
            'daily_performance': daily_stats,
            'common_errors': common_errors,
            'best_patterns': [
                {
                    'type': p.pattern_type,
                    'success_rate': p.success_rate,
                    'usage_count': p.usage_count,
                    'confidence': p.confidence
                }
                for p in best_patterns
            ],
            'total_experiences': len(self.short_term_memory),
            'total_patterns': len(self.patterns)
        }
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

# Test function
async def test_ai_memory():
    """Test the AI memory system"""
    memory = AIMemory("test_memory.db")
    
    print("AI Memory System Test")
    print("====================")
    
    # Create test experience
    experience = Experience(
        id="test_001",
        timestamp=datetime.now(),
        request="Close the Copilot dialog in PowerPoint",
        intent={
            'task_type': 'ui_automation',
            'action': 'close',
            'target': 'dialog',
            'application': 'powerpoint'
        },
        actions_taken=[
            {'action': 'click', 'position': {'x': 1271, 'y': 497}},
            {'action': 'send_keys', 'keys': '{ESC}'}
        ],
        outcome='success',
        performance_metrics={'duration': 2.5}
    )
    
    # Store experience
    print("\nStoring experience...")
    await memory.store_experience(experience)
    
    # Recall similar
    print("\nRecalling similar experiences...")
    similar = await memory.recall_similar_experiences(
        "Close dialog in PowerPoint",
        {'task_type': 'ui_automation', 'application': 'powerpoint'}
    )
    print(f"Found {len(similar)} similar experiences")
    
    # Get best solution
    print("\nGetting best solution...")
    solution = await memory.get_best_solution({
        'task_type': 'ui_automation',
        'action': 'close',
        'target': 'dialog',
        'application': 'powerpoint'
    })
    if solution:
        print(f"Best solution found with confidence: {solution['confidence']}")
    
    # Analyze trends
    print("\nAnalyzing performance trends...")
    trends = await memory.analyze_performance_trends()
    print(f"Total patterns learned: {trends['total_patterns']}")
    
    memory.close()

if __name__ == "__main__":
    asyncio.run(test_ai_memory())