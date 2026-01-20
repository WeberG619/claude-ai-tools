# PRD: Autonomous AI Agent Workstation

## Project Overview

Build a fully autonomous AI agent system that runs continuously on a dedicated computer, capable of executing business tasks, conducting research, and testing workflows without human intervention. The system should be able to run for hours or days autonomously, pulling tasks from a queue, executing them, and reporting results.

**Primary Use Case:** AEC (Architecture, Engineering, Construction) automation business operations
**Secondary Use Cases:** General business automation, research, lead generation, content creation, market analysis

---

## Goals

1. Create a "set it and forget it" autonomous agent that runs 24/7
2. Enable Claude Code to orchestrate complex, multi-step business workflows
3. Provide web research and data gathering capabilities
4. Build a task queue system for continuous operation
5. Implement logging, monitoring, and error recovery
6. Keep the system modular so new capabilities can be added easily

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         CONTROL LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Web UI     │  │  CLI        │  │  API        │                 │
│  │  Dashboard  │  │  Interface  │  │  Endpoints  │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
└─────────┼────────────────┼────────────────┼────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Task Orchestrator                         │   │
│  │  - Task queue management (SQLite)                            │   │
│  │  - Priority scheduling                                       │   │
│  │  - Timeout handling                                          │   │
│  │  - Retry logic                                               │   │
│  │  - Result aggregation                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────┐
│                       EXECUTION LAYER                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Claude Code Agent                          │   │
│  │  - Receives task from orchestrator                           │   │
│  │  - Plans and executes multi-step workflows                   │   │
│  │  - Uses tools (web, file, code execution)                    │   │
│  │  - Reports progress and results                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────┐
│                         TOOLS LAYER                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ Web Search │ │ Web Scrape │ │ File Ops   │ │ Code Exec  │       │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ Email      │ │ Database   │ │ API Calls  │ │ Browser    │       │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │
└────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ Task Queue │ │ Results DB │ │ File Store │ │ Logs       │       │
│  │ (SQLite)   │ │ (SQLite)   │ │ (Local)    │ │ (Local)    │       │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Task Queue System

**Database Schema (SQLite):**

```sql
-- tasks table
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    priority INTEGER DEFAULT 5,      -- 1 (highest) to 10 (lowest)
    task_type TEXT NOT NULL,         -- research, content, analysis, outreach, custom
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    input_data JSON,                 -- structured input for the task
    output_data JSON,                -- results from execution
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 3600,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    parent_task_id TEXT,             -- for subtasks
    tags JSON                        -- for filtering/categorization
);

-- task_logs table
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,                      -- info, warning, error, debug
    message TEXT,
    metadata JSON,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- agent_sessions table
CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
);
```

### 2. Task Orchestrator

**File: `orchestrator.py`**

Core responsibilities:
- Poll task queue for pending tasks
- Assign tasks to Claude Code agent
- Monitor task execution with timeouts
- Handle retries on failure
- Aggregate and store results
- Spawn subtasks when needed

**Key Functions:**
```python
def get_next_task() -> Task
def execute_task(task: Task) -> Result
def handle_timeout(task: Task)
def retry_task(task: Task)
def complete_task(task: Task, result: Result)
def fail_task(task: Task, error: str)
def spawn_subtask(parent_task: Task, subtask_spec: dict) -> Task
def get_queue_status() -> dict
```

### 3. Claude Code Agent Interface

**File: `agent.py`**

Wrapper around Claude Code CLI that:
- Formats task as a prompt
- Invokes Claude Code with appropriate context
- Captures output and parses results
- Handles streaming for long-running tasks

**Invocation Pattern:**
```bash
claude --print --output-format json \
  --system-prompt "$(cat system_prompt.md)" \
  --prompt "$(cat task_prompt.md)" \
  --allowedTools "web_search,web_fetch,bash,file_read,file_write" \
  2>&1 | tee -a logs/task_${TASK_ID}.log
```

### 4. Web Research Module

**Capabilities:**
- Web search via Claude Code's built-in tools
- Page fetching and content extraction
- Multi-source aggregation
- Fact verification across sources
- Structured data extraction

**Research Task Types:**
- `competitor_analysis` - Find and analyze competitors
- `lead_generation` - Find potential customers
- `market_research` - Gather market data
- `content_research` - Research topics for content creation
- `price_monitoring` - Track pricing across sites
- `news_monitoring` - Track industry news

### 5. Business Workflow Templates

Pre-built task templates for common operations:

#### Template: Lead Generation Pipeline
```yaml
name: lead_generation_pipeline
description: Find and qualify potential customers
steps:
  - id: search
    type: research
    config:
      query_template: "{industry} {location} architecture firms"
      sources: google, linkedin, yelp
      max_results: 50
  
  - id: enrich
    type: research
    config:
      for_each: search.results
      gather: company_size, contact_info, recent_projects
  
  - id: qualify
    type: analysis
    config:
      criteria:
        - company_size: 1-10 employees
        - has_email: true
        - active_projects: true
      score_threshold: 7
  
  - id: output
    type: export
    config:
      format: csv
      fields: company_name, website, email, score, notes
```

#### Template: Competitor Analysis
```yaml
name: competitor_analysis
description: Analyze competitors in a market
steps:
  - id: find_competitors
    type: research
    config:
      query: "Revit automation plugins AEC"
      depth: 20
  
  - id: analyze_each
    type: analysis
    for_each: find_competitors.results
    config:
      gather:
        - pricing
        - features
        - reviews
        - market_position
  
  - id: synthesize
    type: analysis
    config:
      compare: analyze_each.results
      output: competitive_landscape_report
```

#### Template: Content Creation Pipeline
```yaml
name: content_pipeline
description: Research and create content
steps:
  - id: research_topic
    type: research
    config:
      topic: "{topic}"
      depth: comprehensive
      sources: 10
  
  - id: outline
    type: content
    config:
      type: outline
      based_on: research_topic.results
  
  - id: draft
    type: content
    config:
      type: full_article
      based_on: outline.result
      word_count: 1500
  
  - id: review
    type: analysis
    config:
      check: grammar, seo, readability
      suggest_improvements: true
```

---

## Directory Structure

```
autonomous-agent/
├── README.md
├── requirements.txt
├── setup.py
├── config/
│   ├── config.yaml              # Main configuration
│   ├── prompts/                 # System prompts for different task types
│   │   ├── research.md
│   │   ├── content.md
│   │   ├── analysis.md
│   │   └── default.md
│   └── templates/               # Task templates
│       ├── lead_generation.yaml
│       ├── competitor_analysis.yaml
│       └── content_pipeline.yaml
├── src/
│   ├── __init__.py
│   ├── orchestrator.py          # Main orchestration logic
│   ├── agent.py                 # Claude Code interface
│   ├── queue.py                 # Task queue management
│   ├── database.py              # SQLite operations
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web.py               # Web research tools
│   │   ├── email.py             # Email tools
│   │   └── file.py              # File operations
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── base.py              # Base workflow class
│   │   ├── research.py          # Research workflows
│   │   ├── content.py           # Content workflows
│   │   └── outreach.py          # Outreach workflows
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging utilities
│       └── config.py            # Config management
├── data/
│   ├── agent.db                 # SQLite database
│   ├── results/                 # Task results storage
│   └── cache/                   # Web cache
├── logs/
│   ├── orchestrator.log
│   └── tasks/                   # Per-task logs
├── scripts/
│   ├── start.sh                 # Start the agent
│   ├── stop.sh                  # Stop the agent
│   ├── status.sh                # Check status
│   └── add_task.py              # CLI to add tasks
├── web/                         # Optional web dashboard
│   ├── app.py
│   ├── templates/
│   └── static/
└── tests/
    ├── test_orchestrator.py
    ├── test_queue.py
    └── test_workflows.py
```

---

## Configuration

**File: `config/config.yaml`**

```yaml
agent:
  name: "autonomous-agent"
  version: "1.0.0"
  
orchestrator:
  poll_interval_seconds: 10
  max_concurrent_tasks: 1        # Start with 1 for stability
  default_timeout_seconds: 3600
  max_retries: 3
  retry_delay_seconds: 60

database:
  path: "data/agent.db"
  
logging:
  level: INFO
  file: "logs/orchestrator.log"
  max_size_mb: 100
  backup_count: 5

claude_code:
  model: "claude-sonnet-4-20250514"  # or opus for complex tasks
  max_tokens: 16000
  allowed_tools:
    - web_search
    - web_fetch
    - bash
    - file_read
    - file_write
    - computer

research:
  max_search_results: 20
  cache_ttl_hours: 24
  rate_limit_per_minute: 10

notifications:
  enabled: false
  # email:
  #   smtp_host: ""
  #   smtp_port: 587
  #   from: ""
  #   to: ""
```

---

## Implementation Phases

### Phase 1: Foundation (Day 1)
- [ ] Set up project structure
- [ ] Implement SQLite database schema
- [ ] Create basic task queue (add, get, update)
- [ ] Build Claude Code wrapper
- [ ] Test single task execution

### Phase 2: Orchestration (Day 2)
- [ ] Implement orchestrator main loop
- [ ] Add timeout handling
- [ ] Add retry logic
- [ ] Implement logging system
- [ ] Create start/stop scripts

### Phase 3: Task Templates (Day 3)
- [ ] Build template parser
- [ ] Implement research workflow
- [ ] Implement content workflow
- [ ] Add subtask spawning

### Phase 4: Web Dashboard (Day 4)
- [ ] Create Flask/FastAPI app
- [ ] Build task list view
- [ ] Add task creation form
- [ ] Show logs and results
- [ ] Add basic auth

### Phase 5: Production Hardening (Day 5)
- [ ] Add systemd service file
- [ ] Implement health checks
- [ ] Add error alerting
- [ ] Performance tuning
- [ ] Documentation

---

## CLI Interface

```bash
# Start the agent
./scripts/start.sh

# Check status
./scripts/status.sh

# Stop the agent
./scripts/stop.sh

# Add a task
python scripts/add_task.py \
  --type research \
  --title "Find AEC firms in Miami" \
  --description "Search for small architecture firms in Miami area" \
  --priority 3

# Add a task from template
python scripts/add_task.py \
  --template lead_generation \
  --vars '{"industry": "architecture", "location": "Miami"}'

# View queue
python scripts/add_task.py --list

# View task result
python scripts/add_task.py --result TASK_ID
```

---

## System Prompts

**File: `config/prompts/default.md`**

```markdown
# Autonomous Agent System Prompt

You are an autonomous AI agent running as part of a continuous workflow system. Your role is to execute tasks thoroughly and report results in a structured format.

## Operating Principles

1. **Thoroughness**: Complete each task fully. Don't cut corners.
2. **Accuracy**: Verify information from multiple sources when possible.
3. **Structure**: Return results in the expected format.
4. **Persistence**: If something fails, try alternative approaches before giving up.
5. **Documentation**: Log your reasoning and steps for debugging.

## Task Execution

When you receive a task:
1. Parse the task requirements carefully
2. Plan your approach
3. Execute step by step
4. Verify your results
5. Format output as specified
6. Report any issues or limitations

## Output Format

Always return results as JSON:
```json
{
  "status": "success|partial|failed",
  "summary": "Brief description of what was accomplished",
  "data": { ... },  // Structured results
  "errors": [],     // Any errors encountered
  "suggestions": [] // Recommendations for follow-up
}
```

## Available Tools

- `web_search`: Search the web for information
- `web_fetch`: Retrieve content from URLs
- `bash`: Execute shell commands
- `file_read`: Read files
- `file_write`: Write files

## Constraints

- Respect rate limits on web requests
- Don't store sensitive credentials in plain text
- Report honestly if you cannot complete a task
- Stay focused on the assigned task
```

---

## Testing Tasks

### Test Task 1: Simple Research
```json
{
  "type": "research",
  "title": "Find top 5 Revit plugins",
  "description": "Search for the most popular Revit plugins for architecture firms. For each plugin, gather: name, price, key features, and user ratings.",
  "priority": 5
}
```

### Test Task 2: Lead Generation
```json
{
  "type": "lead_generation",
  "title": "Find small architecture firms in Denver",
  "description": "Find 10 architecture firms in Denver, CO with 1-5 employees. Gather company name, website, and contact email if available.",
  "priority": 3
}
```

### Test Task 3: Content Creation
```json
{
  "type": "content",
  "title": "Write blog post about BIM automation",
  "description": "Research and write a 1000-word blog post about how AI is transforming BIM workflows in architecture. Target audience: small architecture firm owners.",
  "priority": 5
}
```

### Test Task 4: Competitor Analysis
```json
{
  "type": "analysis",
  "title": "Analyze Revit automation competitors",
  "description": "Find and analyze 5 companies offering Revit automation or BIM automation services. Compare their pricing, features, and market positioning.",
  "priority": 2
}
```

---

## Success Metrics

1. **Uptime**: Agent runs continuously without crashes
2. **Task Completion Rate**: >90% of tasks complete successfully
3. **Quality**: Results are accurate and actionable
4. **Efficiency**: Tasks complete within reasonable time limits
5. **Recoverability**: System recovers gracefully from errors

---

## Future Enhancements

- Multi-agent coordination (multiple Claude instances)
- Memory/learning from past tasks
- Integration with external APIs (CRM, email marketing)
- Scheduled/recurring tasks
- Webhook triggers
- Mobile notifications
- Cost tracking per task

---

## Notes for Claude Code

When building this system:

1. Start with the simplest working version - a loop that pulls tasks and executes them
2. Add complexity incrementally
3. Test each component before moving on
4. Use extensive logging - you'll need it for debugging autonomous operation
5. Build in graceful degradation - if something fails, the system should continue
6. Keep the database schema simple but extensible
7. Make it easy to add new task types and workflows

The goal is a system that can run unsupervised for hours, executing business tasks reliably. Start simple, prove it works, then add features.
