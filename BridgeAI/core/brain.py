#!/usr/bin/env python3
"""
BridgeAI Core Intelligence System
==================================
A distributed AI brain that can observe, learn, decide, and act.

This is not just automation - this is an AI that:
- Understands context and learns from interactions
- Makes intelligent decisions based on patterns
- Controls any connected device or system
- Remembers everything and gets smarter over time
- Can delegate to local AI models for quick responses
- Connects to Claude for complex reasoning

Architecture:
- Brain: Central decision engine
- Memory: Persistent learning and recall
- Sensors: System observation and monitoring
- Actions: Execution of commands and controls
- Communication: Multi-channel interface
"""

import os
import sys
import json
import time
import sqlite3
import socket
import threading
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import re

# ============================================================
# CONFIGURATION
# ============================================================

class Config:
    """Central configuration"""
    BASE_DIR = Path(os.getenv('BRIDGEAI_HOME', 'C:/BridgeAI'))
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    MEMORY_DB = DATA_DIR / 'brain_memory.db'

    # Network
    MAIN_PC_IP = '192.168.1.51'
    DELL_PC_IP = '192.168.1.31'
    HUB_PORT = 5000
    BRAIN_PORT = 5001

    # Devices
    SAMSUNG_TV_IP = '192.168.1.150'
    SAMSUNG_TV_MAC = '68:72:c3:36:93:96'
    LG_TV_IP = '192.168.1.46'

    # AI
    LOCAL_MODEL = 'llama3.2:1b'  # Fast local model
    OLLAMA_URL = 'http://localhost:11434'

# Create directories
Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# MEMORY SYSTEM - The Brain's Long-Term Storage
# ============================================================

class MemoryType(Enum):
    FACT = "fact"           # Something learned
    EVENT = "event"         # Something that happened
    PATTERN = "pattern"     # A recognized pattern
    PREFERENCE = "preference"  # User preference
    SKILL = "skill"         # Learned capability
    ERROR = "error"         # Mistakes to avoid
    CONVERSATION = "conversation"  # Chat history

@dataclass
class Memory:
    """A single memory unit"""
    id: Optional[int] = None
    type: str = "fact"
    content: str = ""
    context: str = ""
    importance: float = 0.5  # 0-1 scale
    tags: List[str] = None
    created_at: str = None
    accessed_at: str = None
    access_count: int = 0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.accessed_at is None:
            self.accessed_at = self.created_at

class MemorySystem:
    """
    Long-term memory storage with semantic search and learning.
    The brain remembers everything and gets smarter over time.
    """

    def __init__(self, db_path: Path = Config.MEMORY_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the memory database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    importance REAL DEFAULT 0.5,
                    tags TEXT,
                    created_at TEXT,
                    accessed_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    embedding TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id_1 INTEGER,
                    memory_id_2 INTEGER,
                    strength REAL DEFAULT 0.5,
                    FOREIGN KEY (memory_id_1) REFERENCES memories(id),
                    FOREIGN KEY (memory_id_2) REFERENCES memories(id)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)
            ''')
            conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, context, tags)')

    def store(self, memory: Memory) -> int:
        """Store a new memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO memories (type, content, context, importance, tags, created_at, accessed_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.type,
                memory.content,
                memory.context,
                memory.importance,
                json.dumps(memory.tags),
                memory.created_at,
                memory.accessed_at,
                memory.access_count
            ))
            memory_id = cursor.lastrowid

            # Add to full-text search
            conn.execute('''
                INSERT INTO memories_fts (rowid, content, context, tags)
                VALUES (?, ?, ?, ?)
            ''', (memory_id, memory.content, memory.context, ' '.join(memory.tags)))

            return memory_id

    def recall(self, query: str, limit: int = 10, memory_type: str = None) -> List[Memory]:
        """Recall memories matching a query"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Escape special FTS5 characters by wrapping in quotes
            # This treats the query as a phrase search
            safe_query = '"' + query.replace('"', '""') + '"'

            # Full-text search
            try:
                if memory_type:
                    rows = conn.execute('''
                        SELECT m.* FROM memories m
                        JOIN memories_fts fts ON m.id = fts.rowid
                        WHERE memories_fts MATCH ? AND m.type = ?
                        ORDER BY m.importance DESC, m.access_count DESC
                        LIMIT ?
                    ''', (safe_query, memory_type, limit)).fetchall()
                else:
                    rows = conn.execute('''
                        SELECT m.* FROM memories m
                        JOIN memories_fts fts ON m.id = fts.rowid
                        WHERE memories_fts MATCH ?
                        ORDER BY m.importance DESC, m.access_count DESC
                        LIMIT ?
                    ''', (safe_query, limit)).fetchall()
            except sqlite3.OperationalError:
                # If FTS query fails, fall back to LIKE search
                if memory_type:
                    rows = conn.execute('''
                        SELECT * FROM memories
                        WHERE content LIKE ? AND type = ?
                        ORDER BY importance DESC, access_count DESC
                        LIMIT ?
                    ''', (f'%{query}%', memory_type, limit)).fetchall()
                else:
                    rows = conn.execute('''
                        SELECT * FROM memories
                        WHERE content LIKE ?
                        ORDER BY importance DESC, access_count DESC
                        LIMIT ?
                    ''', (f'%{query}%', limit)).fetchall()

            memories = []
            for row in rows:
                # Update access stats
                conn.execute('''
                    UPDATE memories SET accessed_at = ?, access_count = access_count + 1
                    WHERE id = ?
                ''', (datetime.now().isoformat(), row['id']))

                memories.append(Memory(
                    id=row['id'],
                    type=row['type'],
                    content=row['content'],
                    context=row['context'],
                    importance=row['importance'],
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    created_at=row['created_at'],
                    accessed_at=row['accessed_at'],
                    access_count=row['access_count']
                ))

            return memories

    def get_recent(self, limit: int = 20, memory_type: str = None) -> List[Memory]:
        """Get recent memories"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if memory_type:
                rows = conn.execute('''
                    SELECT * FROM memories WHERE type = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (memory_type, limit)).fetchall()
            else:
                rows = conn.execute('''
                    SELECT * FROM memories ORDER BY created_at DESC LIMIT ?
                ''', (limit,)).fetchall()

            return [Memory(
                id=row['id'],
                type=row['type'],
                content=row['content'],
                context=row['context'],
                importance=row['importance'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                created_at=row['created_at'],
                accessed_at=row['accessed_at'],
                access_count=row['access_count']
            ) for row in rows]

    def learn_pattern(self, pattern: str, context: str, importance: float = 0.7):
        """Learn a new pattern from observations"""
        self.store(Memory(
            type=MemoryType.PATTERN.value,
            content=pattern,
            context=context,
            importance=importance,
            tags=['learned', 'pattern', 'auto']
        ))

    def remember_error(self, error: str, solution: str, importance: float = 0.9):
        """Remember an error and its solution"""
        self.store(Memory(
            type=MemoryType.ERROR.value,
            content=f"Error: {error}\nSolution: {solution}",
            context="error_learning",
            importance=importance,
            tags=['error', 'solution', 'learned']
        ))

# ============================================================
# SENSOR SYSTEM - Observing the World
# ============================================================

class SensorType(Enum):
    NETWORK = "network"
    SYSTEM = "system"
    FILE = "file"
    DEVICE = "device"
    TIME = "time"

@dataclass
class SensorReading:
    """A single sensor observation"""
    sensor_type: str
    name: str
    value: Any
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class SensorSystem:
    """
    Observes the environment - network, system, files, devices.
    The eyes and ears of the AI.
    """

    def __init__(self):
        self.readings: Dict[str, SensorReading] = {}
        self.callbacks: List[Callable] = []

    def read_all(self) -> Dict[str, SensorReading]:
        """Read all sensors"""
        readings = {}

        # System sensors
        readings['hostname'] = SensorReading(SensorType.SYSTEM.value, 'hostname', socket.gethostname())
        readings['time'] = SensorReading(SensorType.TIME.value, 'current_time', datetime.now().isoformat())
        readings['day_of_week'] = SensorReading(SensorType.TIME.value, 'day_of_week', datetime.now().strftime('%A'))
        readings['hour'] = SensorReading(SensorType.TIME.value, 'hour', datetime.now().hour)

        # Network sensors - check devices
        readings['samsung_tv'] = SensorReading(
            SensorType.DEVICE.value, 'samsung_tv',
            self._check_port(Config.SAMSUNG_TV_IP, 8001)
        )
        readings['lg_tv'] = SensorReading(
            SensorType.DEVICE.value, 'lg_tv',
            self._check_port(Config.LG_TV_IP, 3001)
        )
        readings['main_pc'] = SensorReading(
            SensorType.DEVICE.value, 'main_pc',
            self._check_port(Config.MAIN_PC_IP, 445)
        )

        # Disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage('C:/')
            readings['disk_free_gb'] = SensorReading(
                SensorType.SYSTEM.value, 'disk_free_gb',
                round(free / (1024**3), 1)
            )
        except:
            pass

        self.readings = readings
        return readings

    def _check_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def watch(self, callback: Callable):
        """Register a callback for sensor changes"""
        self.callbacks.append(callback)

    def get(self, name: str) -> Optional[Any]:
        """Get a specific sensor reading"""
        if name in self.readings:
            return self.readings[name].value
        return None

# ============================================================
# ACTION SYSTEM - Affecting the World
# ============================================================

class ActionType(Enum):
    SHELL = "shell"
    PYTHON = "python"
    HTTP = "http"
    DEVICE = "device"
    FILE = "file"
    NOTIFY = "notify"

@dataclass
class ActionResult:
    """Result of an action"""
    success: bool
    output: Any = None
    error: str = None
    duration: float = 0

class ActionSystem:
    """
    Executes actions on the system and connected devices.
    The hands of the AI.
    """

    def __init__(self):
        self.history: List[Dict] = []

    def execute(self, action_type: str, **kwargs) -> ActionResult:
        """Execute an action"""
        start_time = time.time()
        result = ActionResult(success=False)

        try:
            if action_type == ActionType.SHELL.value:
                result = self._run_shell(kwargs.get('command', ''))
            elif action_type == ActionType.PYTHON.value:
                result = self._run_python(kwargs.get('code', ''))
            elif action_type == ActionType.HTTP.value:
                result = self._make_request(
                    kwargs.get('url', ''),
                    kwargs.get('method', 'GET'),
                    kwargs.get('data')
                )
            elif action_type == ActionType.DEVICE.value:
                result = self._control_device(
                    kwargs.get('device', ''),
                    kwargs.get('command', '')
                )
            elif action_type == ActionType.FILE.value:
                result = self._file_operation(
                    kwargs.get('operation', ''),
                    kwargs.get('path', ''),
                    kwargs.get('content')
                )
            else:
                result.error = f"Unknown action type: {action_type}"
        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start_time

        # Log action
        self.history.append({
            'type': action_type,
            'kwargs': kwargs,
            'result': asdict(result),
            'timestamp': datetime.now().isoformat()
        })

        return result

    def _run_shell(self, command: str) -> ActionResult:
        """Run a shell command"""
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            return ActionResult(
                success=proc.returncode == 0,
                output=proc.stdout,
                error=proc.stderr if proc.returncode != 0 else None
            )
        except subprocess.TimeoutExpired:
            return ActionResult(success=False, error="Command timed out")
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def _run_python(self, code: str) -> ActionResult:
        """Run Python code"""
        try:
            result = {}
            exec(code, {'result': result, 'Config': Config})
            return ActionResult(success=True, output=result)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def _make_request(self, url: str, method: str = 'GET', data: Any = None) -> ActionResult:
        """Make an HTTP request"""
        try:
            import urllib.request
            import urllib.parse

            if method == 'POST' and data:
                data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data, method=method)
                req.add_header('Content-Type', 'application/json')
            else:
                req = urllib.request.Request(url, method=method)

            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode('utf-8')
                try:
                    body = json.loads(body)
                except:
                    pass
                return ActionResult(success=True, output=body)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def _control_device(self, device: str, command: str) -> ActionResult:
        """Control a smart device"""
        hub_url = f"http://{Config.DELL_PC_IP}:{Config.HUB_PORT}/api/{device}/{command}"
        return self._make_request(hub_url, method='POST')

    def _file_operation(self, operation: str, path: str, content: Any = None) -> ActionResult:
        """Perform file operations"""
        try:
            path = Path(path)

            if operation == 'read':
                return ActionResult(success=True, output=path.read_text())
            elif operation == 'write':
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(content))
                return ActionResult(success=True, output=f"Written to {path}")
            elif operation == 'exists':
                return ActionResult(success=True, output=path.exists())
            elif operation == 'list':
                files = [str(f) for f in path.iterdir()] if path.is_dir() else []
                return ActionResult(success=True, output=files)
            elif operation == 'delete':
                if path.exists():
                    path.unlink()
                return ActionResult(success=True, output=f"Deleted {path}")
            else:
                return ActionResult(success=False, error=f"Unknown file operation: {operation}")
        except Exception as e:
            return ActionResult(success=False, error=str(e))

# ============================================================
# LOCAL AI - Quick Thinking with Ollama
# ============================================================

class LocalAI:
    """
    Interface to local Ollama model for quick decisions.
    Fast responses without network latency.
    """

    def __init__(self, model: str = Config.LOCAL_MODEL):
        self.model = model
        self.available = False
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama is running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 11434))
            sock.close()
            self.available = result == 0
        except:
            self.available = False

    def think(self, prompt: str, context: str = "") -> str:
        """Quick thinking with local model"""
        if not self.available:
            return "[Local AI not available]"

        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            proc = subprocess.run(
                ['ollama', 'run', self.model, full_prompt],
                capture_output=True, text=True, timeout=30
            )
            return proc.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[Thinking timed out]"
        except Exception as e:
            return f"[Error: {e}]"

    def classify(self, text: str, categories: List[str]) -> str:
        """Classify text into one of the categories"""
        prompt = f"""Classify this text into exactly one category.
Categories: {', '.join(categories)}
Text: {text}
Reply with just the category name, nothing else."""

        result = self.think(prompt)
        # Find best matching category
        for cat in categories:
            if cat.lower() in result.lower():
                return cat
        return categories[0]  # Default to first

    def extract_intent(self, text: str) -> Dict[str, Any]:
        """Extract intent from natural language"""
        prompt = f"""Extract the intent from this text.
Return JSON with: action (what to do), target (what/who), parameters (any specifics)
Text: {text}
JSON:"""

        result = self.think(prompt)
        try:
            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {'action': 'unknown', 'target': None, 'parameters': {}}

# ============================================================
# THE BRAIN - Central Intelligence
# ============================================================

class Brain:
    """
    The central intelligence that coordinates everything.

    It can:
    - Understand natural language requests
    - Remember and learn from interactions
    - Make decisions based on context
    - Execute actions on systems and devices
    - Get smarter over time
    """

    def __init__(self):
        self.memory = MemorySystem()
        self.sensors = SensorSystem()
        self.actions = ActionSystem()
        self.local_ai = LocalAI()

        self.running = False
        self.task_queue = queue.Queue()
        self.results = {}

        # Initialize with core knowledge
        self._bootstrap_knowledge()

    def _bootstrap_knowledge(self):
        """Initialize the brain with core knowledge"""
        core_facts = [
            ("I am BridgeAI, an intelligent assistant running on a Dell PC", "identity", 1.0),
            ("I can control Samsung TV at 192.168.1.150", "capability", 0.9),
            ("I can control LG TV at 192.168.1.46", "capability", 0.9),
            ("I can run shell commands and Python code", "capability", 0.9),
            ("I can read and write files on the system", "capability", 0.9),
            ("I learn from every interaction", "behavior", 0.8),
            ("I should be helpful, accurate, and proactive", "behavior", 1.0),
        ]

        for content, context, importance in core_facts:
            # Check if already exists
            existing = self.memory.recall(content[:50], limit=1)
            if not existing:
                self.memory.store(Memory(
                    type=MemoryType.FACT.value,
                    content=content,
                    context=context,
                    importance=importance,
                    tags=['core', 'bootstrap']
                ))

    def process(self, input_text: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process an input and generate a response/action.
        This is the main thinking function.
        """
        context = context or {}

        # 1. Understand the input
        intent = self._understand(input_text)

        # 2. Recall relevant memories
        memories = self.memory.recall(input_text, limit=5)

        # 3. Read current sensor state
        sensors = self.sensors.read_all()

        # 4. Decide what to do
        decision = self._decide(intent, memories, sensors, context)

        # 5. Execute actions
        results = []
        for action in decision.get('actions', []):
            result = self.actions.execute(action['type'], **action.get('params', {}))
            results.append(result)

        # 6. Learn from this interaction
        self._learn(input_text, intent, decision, results)

        # 7. Generate response
        response = {
            'input': input_text,
            'intent': intent,
            'decision': decision,
            'results': [asdict(r) for r in results],
            'response': decision.get('response', 'Done'),
            'timestamp': datetime.now().isoformat()
        }

        return response

    def _understand(self, text: str) -> Dict[str, Any]:
        """Understand the input text"""
        # Use local AI if available
        if self.local_ai.available:
            intent = self.local_ai.extract_intent(text)
        else:
            # Simple keyword-based understanding
            intent = {'action': 'unknown', 'target': None, 'parameters': {}}

            text_lower = text.lower()

            # Detect action
            if any(w in text_lower for w in ['turn on', 'start', 'enable', 'activate']):
                intent['action'] = 'turn_on'
            elif any(w in text_lower for w in ['turn off', 'stop', 'disable', 'deactivate']):
                intent['action'] = 'turn_off'
            elif any(w in text_lower for w in ['volume up', 'louder']):
                intent['action'] = 'volume_up'
            elif any(w in text_lower for w in ['volume down', 'quieter', 'lower']):
                intent['action'] = 'volume_down'
            elif any(w in text_lower for w in ['status', 'check', "what's", 'is it']):
                intent['action'] = 'status'
            elif any(w in text_lower for w in ['run', 'execute', 'do']):
                intent['action'] = 'execute'
            elif any(w in text_lower for w in ['remember', 'learn', 'note']):
                intent['action'] = 'remember'
            elif any(w in text_lower for w in ['what do you know', 'recall', 'tell me about']):
                intent['action'] = 'recall'

            # Detect target
            if 'samsung' in text_lower or 'living room tv' in text_lower:
                intent['target'] = 'samsung_tv'
            elif 'lg' in text_lower:
                intent['target'] = 'lg_tv'
            elif 'tv' in text_lower:
                intent['target'] = 'tv'  # Generic TV

        return intent

    def _decide(self, intent: Dict, memories: List[Memory], sensors: Dict, context: Dict) -> Dict:
        """Decide what actions to take"""
        decision = {
            'actions': [],
            'response': '',
            'confidence': 0.5
        }

        action = intent.get('action', 'unknown')
        target = intent.get('target')

        if action == 'turn_on':
            if target in ['samsung_tv', 'tv']:
                decision['actions'].append({
                    'type': ActionType.DEVICE.value,
                    'params': {'device': 'samsung', 'command': 'power'}
                })
                decision['response'] = 'Turning on Samsung TV'
            elif target == 'lg_tv':
                decision['actions'].append({
                    'type': ActionType.DEVICE.value,
                    'params': {'device': 'lg', 'command': 'power'}
                })
                decision['response'] = 'Turning on LG TV'

        elif action == 'turn_off':
            if target in ['samsung_tv', 'tv']:
                decision['actions'].append({
                    'type': ActionType.DEVICE.value,
                    'params': {'device': 'samsung', 'command': 'power'}
                })
                decision['response'] = 'Turning off Samsung TV'
            elif target == 'lg_tv':
                decision['actions'].append({
                    'type': ActionType.DEVICE.value,
                    'params': {'device': 'lg', 'command': 'power'}
                })
                decision['response'] = 'Turning off LG TV'

        elif action == 'volume_up':
            device = 'samsung' if target in ['samsung_tv', 'tv', None] else 'lg'
            decision['actions'].append({
                'type': ActionType.DEVICE.value,
                'params': {'device': device, 'command': 'vol_up'}
            })
            decision['response'] = f'Increasing {device} volume'

        elif action == 'volume_down':
            device = 'samsung' if target in ['samsung_tv', 'tv', None] else 'lg'
            decision['actions'].append({
                'type': ActionType.DEVICE.value,
                'params': {'device': device, 'command': 'vol_down'}
            })
            decision['response'] = f'Decreasing {device} volume'

        elif action == 'status':
            # Check device status
            online_devices = []
            offline_devices = []

            for name, reading in sensors.items():
                if reading.sensor_type == SensorType.DEVICE.value:
                    if reading.value:
                        online_devices.append(name)
                    else:
                        offline_devices.append(name)

            decision['response'] = f"Online: {', '.join(online_devices) or 'none'}. Offline: {', '.join(offline_devices) or 'none'}"

        elif action == 'remember':
            # Store something in memory
            content = intent.get('parameters', {}).get('content', str(intent))
            self.memory.store(Memory(
                type=MemoryType.FACT.value,
                content=content,
                context='user_request',
                importance=0.7,
                tags=['user', 'manual']
            ))
            decision['response'] = f"I'll remember that."

        elif action == 'recall':
            # Recall from memory
            if memories:
                recalled = '\n'.join([f"- {m.content}" for m in memories[:3]])
                decision['response'] = f"Here's what I remember:\n{recalled}"
            else:
                decision['response'] = "I don't have any memories about that yet."

        elif action == 'execute':
            # Execute a command
            cmd = intent.get('parameters', {}).get('command', '')
            if cmd:
                decision['actions'].append({
                    'type': ActionType.SHELL.value,
                    'params': {'command': cmd}
                })
                decision['response'] = f'Executing: {cmd}'

        else:
            # Unknown action - try to be helpful
            decision['response'] = "I'm not sure what you want me to do. I can control TVs, run commands, and remember things."

        return decision

    def _learn(self, input_text: str, intent: Dict, decision: Dict, results: List[ActionResult]):
        """Learn from this interaction"""
        # Store the interaction
        self.memory.store(Memory(
            type=MemoryType.EVENT.value,
            content=f"User said: {input_text}\nI did: {decision.get('response', 'nothing')}",
            context='interaction',
            importance=0.3,
            tags=['interaction', 'auto']
        ))

        # Learn from errors
        for result in results:
            if not result.success and result.error:
                self.memory.remember_error(
                    error=result.error,
                    solution="Needs investigation",
                    importance=0.8
                )

    def status(self) -> Dict[str, Any]:
        """Get current brain status"""
        self.sensors.read_all()

        return {
            'name': 'BridgeAI Brain',
            'version': '1.0.0',
            'running': self.running,
            'local_ai': self.local_ai.available,
            'memory_count': len(self.memory.get_recent(limit=1000)),
            'sensors': {k: v.value for k, v in self.sensors.readings.items()},
            'timestamp': datetime.now().isoformat()
        }

# ============================================================
# WEB SERVER - Communication Interface
# ============================================================

def create_server(brain: Brain, port: int = Config.BRAIN_PORT):
    """Create a web server for the brain"""
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    @app.route('/')
    def home():
        return jsonify(brain.status())

    @app.route('/think', methods=['POST'])
    def think():
        data = request.get_json() or {}
        text = data.get('text', '')
        context = data.get('context', {})

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        result = brain.process(text, context)
        return jsonify(result)

    @app.route('/status')
    def status():
        return jsonify(brain.status())

    @app.route('/memory', methods=['GET', 'POST'])
    def memory():
        if request.method == 'POST':
            data = request.get_json() or {}
            memory = Memory(
                type=data.get('type', 'fact'),
                content=data.get('content', ''),
                context=data.get('context', ''),
                importance=data.get('importance', 0.5),
                tags=data.get('tags', [])
            )
            memory_id = brain.memory.store(memory)
            return jsonify({'id': memory_id, 'status': 'stored'})
        else:
            query = request.args.get('q', '')
            limit = int(request.args.get('limit', 10))

            if query:
                memories = brain.memory.recall(query, limit=limit)
            else:
                memories = brain.memory.get_recent(limit=limit)

            return jsonify([asdict(m) for m in memories])

    @app.route('/sensors')
    def sensors():
        readings = brain.sensors.read_all()
        return jsonify({k: asdict(v) for k, v in readings.items()})

    @app.route('/action', methods=['POST'])
    def action():
        data = request.get_json() or {}
        action_type = data.get('type', '')
        params = data.get('params', {})

        if not action_type:
            return jsonify({'error': 'No action type provided'}), 400

        result = brain.actions.execute(action_type, **params)
        return jsonify(asdict(result))

    return app

# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Start the BridgeAI Brain"""
    print()
    print("=" * 60)
    print("  BridgeAI Core Intelligence System")
    print("=" * 60)
    print()

    # Initialize the brain
    brain = Brain()

    # Show status
    status = brain.status()
    print(f"  Brain Status: {'Online' if status else 'Error'}")
    print(f"  Local AI: {'Available' if status.get('local_ai') else 'Not available'}")
    print(f"  Memories: {status.get('memory_count', 0)}")
    print()

    # Show sensor readings
    print("  Sensors:")
    for name, value in status.get('sensors', {}).items():
        print(f"    - {name}: {value}")
    print()

    # Start web server
    print(f"  Starting server on port {Config.BRAIN_PORT}...")
    print(f"  API: http://localhost:{Config.BRAIN_PORT}/")
    print(f"  Think: POST http://localhost:{Config.BRAIN_PORT}/think")
    print()
    print("=" * 60)
    print()

    app = create_server(brain)
    app.run(host='0.0.0.0', port=Config.BRAIN_PORT, debug=False)

if __name__ == '__main__':
    main()
