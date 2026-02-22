# Step 4: Implementation Proposals

> Generated: 2026-02-18
> Agent: system-architect
> Sprint: Autonomy Stress Test
> Input: step-3-system-analysis.md

---

## Proposal 1: Aggregator Module — Active Context Compression Between Pipeline Stages

### 1. Title and Summary

**Title:** `aggregator.py` — ROMA-style Aggregator for Pipeline Context Management

An Aggregator module that sits between pipeline stages in the agent dispatcher, compressing each agent's output into a structured context package before handing it to the next agent. This prevents context explosion across multi-step pipelines by extracting only the key facts, artifacts, and decisions that downstream agents actually need, while dropping intermediate reasoning, retries, and verbose output.

### 2. Problem Statement

**What fails today:** In `agent_dispatcher.py`, the `dispatch_pipeline()` method (lines 303-425) passes `previous_output` as raw text between pipeline steps (line 382: `previous_output = result.output`). This raw output is then injected via `_build_prompt()` (lines 644-653) as an uncompressed block appended to the next agent's prompt. For the `pdf-to-revit` pipeline (3 steps, 30-minute timeout), by step 3 the `bim-validator` agent receives the full raw output of both the `floor-plan-processor` and the `revit-builder` — potentially tens of thousands of characters of intermediate reasoning, tool call traces, and verbose explanations.

**Why it matters:** Paper 1 (Anthropic ICLR 2026) demonstrates that longer reasoning chains amplify variance/incoherence. Paper 2 (ROMA) identifies active context compression as the key architectural innovation that prevents this. Our 3-step pipelines are marginally manageable, but the system is designed for 5+ step chains, and the planner templates (`BUILTIN_TEMPLATES` in `planner.py`) define 5-step plans. Without aggregation, context grows linearly with pipeline depth, pushing later agents into the high-variance regime where they "lose the plot."

Additionally, `coordinator.py`'s `get_accumulated_context()` (lines 506-514) returns all shared state entries as-is, and `enhance_dispatch_prompt()` (lines 671-692) appends truncated (500-char) but unsummarized context. Neither mechanism extracts the *relevant* subset for the next agent's specific task.

### 3. Proposed Solution

#### New File: `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/aggregator.py`

**Classes:**

```python
@dataclass
class AggregatedContext:
    """Compressed context package for the next pipeline stage."""
    source_agent: str           # Who produced this
    step_index: int             # Which pipeline step
    key_facts: list[str]        # Extracted factual statements (max 10)
    artifacts: dict             # Named outputs: {"walls": [...], "room_count": 12}
    decisions: list[str]        # Key decisions made (max 5)
    warnings: list[str]         # Issues/caveats for downstream (max 5)
    raw_summary: str            # 1-3 sentence natural language summary
    char_count_original: int    # Size before compression
    char_count_compressed: int  # Size after compression
    compression_ratio: float    # compressed / original

class Aggregator:
    """
    Compresses agent output between pipeline stages.

    Three aggregation strategies (configurable per pipeline):
      1. heuristic  — regex + keyword extraction (fast, no LLM call)
      2. structured — parse known output formats (JSON, markdown sections)
      3. llm        — use a small/fast model to summarize (highest quality)
    """

    MAX_COMPRESSED_CHARS = 2000  # Hard cap on compressed output
    MAX_KEY_FACTS = 10
    MAX_DECISIONS = 5
    MAX_WARNINGS = 5
```

**Methods:**

```python
class Aggregator:
    def __init__(self, strategy: str = "auto", db_path: str = None):
        """
        Args:
            strategy: "heuristic", "structured", "llm", or "auto"
                      (auto selects based on output characteristics)
            db_path: path to memories.db for logging aggregation stats
        """

    def aggregate(self, output: str, step_config: dict,
                  pipeline_context: dict = None) -> AggregatedContext:
        """
        Main entry point. Compress an agent's output for the next stage.

        Args:
            output: raw agent output string
            step_config: the pipeline step dict from PIPELINE_REGISTRY
                         (has "agent", "data_key", etc.)
            pipeline_context: accumulated context from prior steps

        Returns:
            AggregatedContext with compressed data
        """

    def aggregate_for_prompt(self, output: str, step_config: dict,
                             pipeline_context: dict = None) -> str:
        """
        Convenience method that returns a formatted string ready for
        prompt injection. Calls aggregate() internally.
        """

    def _heuristic_aggregate(self, output: str, data_key: str) -> AggregatedContext:
        """
        Strategy 1: Extract facts using regex patterns.

        Patterns to detect:
        - Lines starting with "Result:", "Output:", "Found:", "Created:", "Error:"
        - Numbered lists (key findings)
        - JSON blocks (extract and keep)
        - File paths mentioned
        - Numeric values with units (dimensions, counts)
        - Markdown headers and their first sentence
        """

    def _structured_aggregate(self, output: str, data_key: str) -> AggregatedContext:
        """
        Strategy 2: Parse known output formats.

        If output contains JSON, extract it.
        If output has markdown sections, extract section headers + first line.
        If output matches a known agent's output template, use specific parser.
        """

    def _llm_aggregate(self, output: str, data_key: str,
                       goal_description: str) -> AggregatedContext:
        """
        Strategy 3: Use Claude to summarize.

        Prompt template:
        "Summarize the following agent output for the next pipeline step.
         Extract: (1) key facts, (2) artifacts/data produced, (3) decisions made,
         (4) warnings for the next agent. Keep total under 2000 chars.
         The next step needs: {data_key}

         Agent output:
         {output[:8000]}"

        Uses claude -p with --output-format text for a fast summarization call.
        """

    def _select_strategy(self, output: str) -> str:
        """
        Auto-select aggregation strategy based on output characteristics.

        - If output < 1000 chars: return "passthrough" (no compression needed)
        - If output contains valid JSON block: return "structured"
        - If output > 5000 chars: return "llm" (too complex for heuristics)
        - Default: return "heuristic"
        """

    def _extract_json_blocks(self, text: str) -> list[dict]:
        """Find and parse JSON blocks in output text."""

    def _extract_key_lines(self, text: str) -> list[str]:
        """Extract lines that are likely key facts (result lines, numbered items, etc.)."""

    def _extract_artifacts(self, text: str, data_key: str) -> dict:
        """Extract named data artifacts from output."""

    def to_prompt_section(self, ctx: AggregatedContext) -> str:
        """
        Format an AggregatedContext as a prompt section.

        Output format:
        --- Previous Step: {source_agent} (step {step_index}) ---
        Summary: {raw_summary}

        Key Facts:
        - fact 1
        - fact 2

        Artifacts: {data_key}: {artifact_value}

        Warnings:
        - warning 1
        ---
        """

    def log_aggregation(self, original_size: int, compressed_size: int,
                        strategy: str, pipeline_name: str, step_index: int):
        """Log aggregation metrics to memories.db for tracking compression effectiveness."""
```

**Data structures — New DB table:**

```sql
CREATE TABLE IF NOT EXISTS aggregation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    strategy_used TEXT NOT NULL,
    original_chars INTEGER NOT NULL,
    compressed_chars INTEGER NOT NULL,
    compression_ratio REAL NOT NULL,
    key_facts_extracted INTEGER DEFAULT 0,
    artifacts_extracted INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL
);
```

#### Existing File Modifications

**`/mnt/d/_CLAUDE-TOOLS/autonomous-agent/core/agent_dispatcher.py`:**

Modify `dispatch_pipeline()` to use the Aggregator between steps.

```python
# At top of file, add import:
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_CLAUDE-TOOLS" / "agent-common-sense"))
    from aggregator import Aggregator
    _aggregator_available = True
except ImportError:
    _aggregator_available = False

# In dispatch_pipeline(), replace line 382:
#   previous_output = result.output
# With:
    if _aggregator_available and len(result.output) > 1000:
        try:
            aggregator = Aggregator(strategy="auto")
            compressed = aggregator.aggregate_for_prompt(
                output=result.output,
                step_config=step,
                pipeline_context={"pipeline_name": pipeline_name, "step": i}
            )
            logger.info(
                f"Aggregated step {i+1} output: {len(result.output)} -> {len(compressed)} chars "
                f"({len(compressed)/max(len(result.output),1)*100:.0f}%)"
            )
            previous_output = compressed
        except Exception as e:
            logger.warning(f"Aggregation failed, using raw output: {e}")
            previous_output = result.output
    else:
        previous_output = result.output
```

**`/mnt/d/_CLAUDE-TOOLS/agent-common-sense/coordinator.py`:**

Modify `enhance_dispatch_prompt()` (line 671) to use Aggregator for shared state compression.

```python
# In enhance_dispatch_prompt(), replace the raw context append (lines 677-682):
    context = self.get_accumulated_context(session_id)
    if context:
        try:
            from aggregator import Aggregator
            agg = Aggregator(strategy="heuristic")
            parts.append("\n## Workflow Context (compressed)")
            for key, info in context.items():
                value = info["value"]
                if len(value) > 500:
                    # Compress large state values
                    compressed = agg._extract_key_lines(value)
                    value_preview = "\n".join(compressed[:5])
                else:
                    value_preview = value
                parts.append(f"- **{key}** (from {info['set_by']}): {value_preview}")
        except ImportError:
            # Fallback to current behavior
            parts.append("\n## Workflow Context (from prior agents)")
            for key, info in context.items():
                value_preview = info["value"][:500] if len(info["value"]) > 500 else info["value"]
                parts.append(f"- **{key}** (set by {info['set_by']}): {value_preview}")
```

**`PIPELINE_REGISTRY` in `agent_dispatcher.py`:**

Add optional `aggregation_strategy` to step configs:

```python
PIPELINE_REGISTRY = {
    "pdf-to-revit": {
        "description": "Full pipeline: PDF floor plan -> extract -> create Revit model -> validate",
        "aggregation": "auto",  # NEW: pipeline-level default
        "steps": [
            {"agent": "floor-plan-processor", "data_key": "spec", "aggregation": "structured"},
            {"agent": "revit-builder", "data_key": "model", "aggregation": "heuristic"},
            {"agent": "bim-validator", "data_key": "validation"},  # inherits pipeline default
        ],
        "timeout": 1800,
    },
    ...
}
```

### 4. Interface Design (Public API)

```python
# Primary interface — called by agent_dispatcher.py
from aggregator import Aggregator, AggregatedContext

agg = Aggregator(strategy="auto")

# After each pipeline step completes:
compressed: str = agg.aggregate_for_prompt(
    output=agent_result.output,
    step_config={"agent": "floor-plan-processor", "data_key": "spec"},
    pipeline_context={"pipeline_name": "pdf-to-revit", "step": 0}
)

# Or for more control:
ctx: AggregatedContext = agg.aggregate(output, step_config)
prompt_section: str = agg.to_prompt_section(ctx)

# For coordinator integration:
compressed_value: str = agg.aggregate_for_prompt(
    output=large_shared_state_value,
    step_config={"data_key": "context"}
)
```

### 5. Integration Points

1. **`agent_dispatcher.py` `dispatch_pipeline()`** — Primary integration. After each step's `execute_agent()` returns, pass output through `Aggregator.aggregate_for_prompt()` before storing in `previous_output`. This is the critical path.

2. **`coordinator.py` `enhance_dispatch_prompt()`** — Secondary integration. Compress `get_accumulated_context()` values before injecting into agent prompts. Non-critical but reduces context bloat for coordinator-managed workflows.

3. **`planner.py` `record_step_result()`** — Tertiary integration. When storing `result_summary` in `plan_step_results`, pass through aggregator to ensure summaries are concise and structured. This improves the quality of data available for replanning.

4. **`alignment.py` `get_corrections_for_task()`** — Future integration. Aggregator patterns could improve correction retrieval by better extracting task-relevant content from long correction entries.

5. **`memories.db`** — New `aggregation_log` table for tracking compression effectiveness over time.

### 6. Implementation Steps

| # | Step | Description | Est. Time |
|---|------|-------------|-----------|
| 1 | Create `aggregator.py` scaffold | File with `Aggregator` class, `AggregatedContext` dataclass, constants, DB schema creation. Implement `_select_strategy()` and `to_prompt_section()`. | 2 hours |
| 2 | Implement heuristic strategy | `_heuristic_aggregate()`: regex patterns for result lines, numbered lists, JSON blocks, file paths, numeric values, markdown headers. Unit test with sample agent outputs. | 3 hours |
| 3 | Implement structured strategy | `_structured_aggregate()`: JSON block extraction, markdown section parsing, known agent output template parsing. | 2 hours |
| 4 | Implement LLM strategy | `_llm_aggregate()`: build summarization prompt, call `claude -p` with short timeout, parse response into `AggregatedContext`. Fallback to heuristic if LLM call fails. | 2 hours |
| 5 | Implement `aggregate()` and `aggregate_for_prompt()` | Main orchestration: strategy selection, call appropriate method, format output, enforce char limits, log metrics. | 1 hour |
| 6 | Integrate into `dispatch_pipeline()` | Modify `agent_dispatcher.py` line 382 to use aggregator. Add import with graceful fallback. Add `aggregation` field to `PIPELINE_REGISTRY`. | 1 hour |
| 7 | Integrate into `enhance_dispatch_prompt()` | Modify `coordinator.py` lines 677-682 to compress large shared state values. | 30 min |
| 8 | Add `aggregation_log` DB table | Schema creation in `_ensure_schema()`, `log_aggregation()` method, test DB writes. | 30 min |
| 9 | Write tests | Unit tests for each strategy with representative agent outputs. Integration test running a mock 3-step pipeline with/without aggregation, comparing context sizes. | 3 hours |
| 10 | Manual validation | Run the `pdf-to-revit` pipeline (or a test mock) with aggregation enabled. Verify compression ratios, check that downstream agents still receive the information they need. | 1 hour |

**Total estimated time: 2-3 days**

### 7. Test Plan

**Unit tests (`/mnt/d/_CLAUDE-TOOLS/agent-common-sense/tests/test_aggregator.py`):**

1. **Heuristic strategy tests:**
   - Input: 5000-char agent output with numbered list, JSON block, and verbose reasoning. Assert: key facts extracted, JSON preserved, reasoning dropped, output < 2000 chars.
   - Input: output with file paths and dimensions (e.g., "Wall A: 12'-6\" x 8'-0\""). Assert: dimensions appear in key_facts.
   - Input: output with error/warning lines. Assert: warnings field populated.

2. **Structured strategy tests:**
   - Input: output containing valid JSON `{...}`. Assert: JSON extracted into artifacts.
   - Input: markdown with `## Section` headers. Assert: sections summarized.
   - Input: mixed text and JSON. Assert: both processed.

3. **LLM strategy tests (with mock):**
   - Mock the `_run_claude_agent()` call. Assert: prompt includes output and data_key. Assert: response parsed correctly.
   - Mock a failed LLM call. Assert: fallback to heuristic strategy.

4. **Strategy selection tests:**
   - Input < 1000 chars. Assert: strategy is "passthrough".
   - Input > 5000 chars. Assert: strategy is "llm".
   - Input with JSON block, 1000-5000 chars. Assert: strategy is "structured".
   - Default case. Assert: strategy is "heuristic".

5. **Compression ratio tests:**
   - 10000-char input. Assert: output < 2000 chars (MAX_COMPRESSED_CHARS).
   - 500-char input. Assert: output unchanged (passthrough).

**Integration tests:**

6. **Pipeline integration test:**
   - Mock a 3-step pipeline execution. Measure context size at each step with and without aggregation. Assert: with aggregation, context at step 3 is < 2x context at step 1 (instead of 3x without).

7. **Coordinator integration test:**
   - Set 5 shared state values of varying sizes. Call `enhance_dispatch_prompt()`. Assert: large values (>500 chars) are compressed, small values are passed through.

**Edge cases:**

8. Empty output string -> returns empty `AggregatedContext` with "No output produced" summary.
9. Binary/non-text output -> heuristic handles gracefully, returns raw truncation.
10. Output in non-English -> heuristic may under-extract, but does not crash; LLM strategy handles correctly.
11. Output > 100KB -> hard truncation to first 10000 chars before any strategy runs.

### 8. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Aggregation drops critical information needed by next agent | High | Medium | Start with conservative extraction (keep more), tune threshold over time. Always preserve JSON blocks and explicit "Result:" lines. Log all aggregations for audit. |
| LLM summarization call adds latency to pipelines | Medium | High | LLM strategy only activates for outputs > 5000 chars. Set a 30-second timeout for the summarization call. Fallback to heuristic if LLM is slow. |
| Heuristic regex patterns miss domain-specific output formats | Medium | Medium | Ship with patterns for known agents (floor-plan-processor, revit-builder, etc.). Add a mechanism to register custom patterns per agent in the registry. |
| Aggregator import fails in dispatcher (dependency issue) | Low | Low | Already handles this with `_aggregator_available` flag and try/except import. Raw output passthrough is the fallback. |
| Aggregation log table grows unbounded | Low | High | Add index on `timestamp`. Periodic cleanup (delete entries > 30 days old) in coordinator's `cleanup_stale()`. |

### 9. Success Criteria

1. **Context size metric:** For a 3-step pipeline, context at step 3 is no more than 2500 chars (currently unbounded, potentially 10000+ chars). Measured via `aggregation_log` table.
2. **Compression ratio:** Average compression ratio across all pipeline steps is below 0.40 (60% reduction). Tracked in `aggregation_log`.
3. **Pipeline success rate:** Pipeline completion rate does not decrease after enabling aggregation (i.e., critical information is preserved). Measured via existing `execution_log` in dispatcher.
4. **Zero regressions:** All existing tests pass. Single-agent dispatches (non-pipeline) are unaffected.
5. **Graceful degradation:** If aggregator module is unavailable (import fails), pipelines still work with raw output passthrough. Verified by test that removes aggregator import.

---

## Proposal 2: Alignment Injection Fail-Closed + Real-Time Coherence Monitoring

### 1. Title and Summary

**Title:** Fail-Closed Alignment Gate + Step-Level Coherence Checking

Two closely related changes that address the gap between alignment *intent* and execution *reality*. First, make alignment injection fail-closed: if the alignment system cannot compile a prompt prefix for a sub-agent, refuse to dispatch that agent rather than running it unconstrained. Second, add a lightweight coherence check after each pipeline step that compares the step's output against the plan's stated goal, flagging when an agent's output has drifted from the objective.

### 2. Problem Statement

**Fail-closed gap:** In `agent_dispatcher.py` lines 444-455, when `AlignmentCore.get_injection_for_autonomous()` throws an exception, the code logs a warning and proceeds to execute the agent without any alignment injection:

```python
except Exception as e:
    logger.warning(f"Alignment injection failed for {agent_name}: {e}")
    # EXECUTION CONTINUES — agent runs unconstrained
```

This means the sub-agent launches via `_run_claude_agent()` (line 489) with `--dangerously-skip-permissions` and zero alignment data — no kernel, no corrections, no principles, no strong agent framework. This is the exact "delegation to unconstrained sub-agents" failure mode that Paper 3 (Petri 2.0) identifies as critical. The failure is silent: the caller has no indication that the agent ran without safety guardrails.

Furthermore, even when alignment injection "succeeds," there is no verification that the compiled prefix is substantive. If `AlignmentCore.compile_prompt()` returns an empty string (e.g., because `kernel.md` is missing and the DB has no corrections), the code silently skips injection (line 451: `if prefix:`) and runs the agent unconstrained. There is no minimum quality threshold.

**Coherence monitoring gap:** The kernel's self-reflection prompts (`kernel.md` lines 159-163: "Am I making progress? Am I repeating myself? Am I drifting from scope?") are instructions that the model can ignore. Paper 1 (Anthropic ICLR 2026) shows that incoherence means the model has stopped following instructions — so the very mechanism designed to catch incoherence fails precisely when it is most needed, because the incoherent model will also ignore the self-reflection instruction.

Currently, `planner.py`'s `record_step_result()` (lines 643-715) records success/failure and updates progress, but does not evaluate whether a "successful" step's output is actually coherent with the plan's goal. An agent could return a grammatically correct, internally consistent response that is completely irrelevant to the task, and the pipeline would pass it forward as `previous_output` to the next agent, compounding the error.

**Combined impact:** These two gaps create a scenario where an agent can (a) run without alignment guardrails due to a transient error, (b) produce incoherent output that the pipeline cannot detect, and (c) propagate that incoherent output to downstream agents without any checkpoint. The system's safety model assumes both injection and compliance; when injection fails silently, the entire safety chain breaks.

### 3. Proposed Solution

This proposal has two tightly coupled components that share infrastructure.

#### Component A: Fail-Closed Alignment Gate

**Modify: `/mnt/d/_CLAUDE-TOOLS/autonomous-agent/core/agent_dispatcher.py`**

**Modify: `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/alignment.py`**

**New dataclass in `alignment.py`:**

```python
@dataclass
class InjectionResult:
    """Result of an alignment injection attempt."""
    success: bool
    prefix: str = ""
    char_count: int = 0
    components_present: dict = field(default_factory=dict)
    # e.g., {"kernel": True, "corrections": True, "principles": True, "strong_agent": False}
    error: str = ""
    quality_score: float = 0.0  # 0.0 (empty) to 1.0 (all components present and substantive)

    @property
    def meets_minimum(self) -> bool:
        """Check if injection meets minimum quality threshold."""
        return self.success and self.char_count >= 100 and self.quality_score >= 0.3
```

**New method in `AlignmentCore`:**

```python
def get_injection_with_verification(self, agent_name: str,
                                     task_description: str,
                                     event_data: dict = None) -> InjectionResult:
    """
    Build alignment prefix with quality verification.

    Returns an InjectionResult that includes quality metrics,
    allowing the caller to make fail-open/fail-closed decisions.

    Quality score calculation:
    - kernel_content present and > 500 chars: +0.3
    - corrections_content present: +0.2
    - principles present (at least 2): +0.2
    - strong_agent_content present: +0.2
    - total char count > 500: +0.1
    """
    try:
        project = ""
        if event_data:
            project = event_data.get("project", event_data.get("project_name", ""))

        profile = self.compile_profile(agent_name, task_description, project)
        prefix = self._profile_to_prompt(profile)

        # Calculate quality score
        score = 0.0
        components = {}

        components["kernel"] = len(profile.kernel_content) > 500
        if components["kernel"]:
            score += 0.3

        components["corrections"] = len(profile.corrections_content) > 0
        if components["corrections"]:
            score += 0.2

        components["principles"] = len(profile.principles) >= 2
        if components["principles"]:
            score += 0.2

        components["strong_agent"] = len(profile.strong_agent_content) > 100
        if components["strong_agent"]:
            score += 0.2

        if len(prefix) > 500:
            score += 0.1

        return InjectionResult(
            success=True,
            prefix=prefix,
            char_count=len(prefix),
            components_present=components,
            quality_score=round(score, 2),
        )

    except Exception as e:
        return InjectionResult(
            success=False,
            error=str(e),
        )
```

**Modify `execute_agent()` in `agent_dispatcher.py`:**

Replace the current alignment injection block (lines 444-455) with a fail-closed gate:

```python
# ALIGNMENT INJECTION — FAIL-CLOSED GATE
alignment_ok = False
if _alignment_available:
    try:
        alignment = AlignmentCore()
        injection = alignment.get_injection_with_verification(
            agent_name, prompt, event.data
        )

        if injection.meets_minimum:
            prompt = injection.prefix + "\n\n---\n\n" + prompt
            alignment_ok = True
            logger.info(
                f"Alignment injection for {agent_name}: "
                f"{injection.char_count} chars, quality={injection.quality_score:.1f}, "
                f"components={injection.components_present}"
            )
        else:
            # Injection present but below minimum quality
            logger.error(
                f"ALIGNMENT GATE: Injection below minimum quality for {agent_name}: "
                f"quality={injection.quality_score:.1f}, chars={injection.char_count}, "
                f"components={injection.components_present}"
            )
            # Record the failure as a critical alignment violation
            if injection.success:
                # Injection compiled but quality too low
                alignment.record_violation(
                    agent_name=agent_name,
                    principle_id=0,  # system-level, no specific principle
                    violation_type="injection_quality_below_threshold",
                    description=(
                        f"Alignment injection quality {injection.quality_score:.1f} "
                        f"below minimum 0.3 for {agent_name}. "
                        f"Components: {injection.components_present}"
                    ),
                    severity="critical",
                )

    except Exception as e:
        logger.error(f"ALIGNMENT GATE: Injection system error for {agent_name}: {e}")
        injection = None

else:
    logger.error(f"ALIGNMENT GATE: AlignmentCore not available for {agent_name}")

# FAIL-CLOSED DECISION
# For pipeline steps and high-priority agents, refuse to dispatch without alignment.
# For manual/low-priority, allow with warning.
if not alignment_ok:
    source = event.source if hasattr(event, 'source') else ""
    is_pipeline = "pipeline:" in source
    is_high_priority = event.priority in ("high", "critical")

    if is_pipeline or is_high_priority:
        error_msg = (
            f"Agent '{agent_name}' dispatch BLOCKED: alignment injection failed or below quality threshold. "
            f"This agent would run without safety guardrails. "
            f"Fix alignment system or reduce agent priority to override."
        )
        logger.critical(error_msg)

        if self.notifier:
            await self.notifier.send(
                f"ALIGNMENT BLOCK: {agent_name}",
                error_msg,
                "critical"
            )

        return AgentResult(
            agent_name=agent_name,
            success=False,
            output="",
            error=error_msg
        )
    else:
        # Low-priority non-pipeline: warn but allow (fail-open for manual tasks)
        logger.warning(
            f"ALIGNMENT WARNING: {agent_name} running without full alignment "
            f"(priority={event.priority}, source={source}). "
            f"Proceeding with degraded safety."
        )
```

#### Component B: Step-Level Coherence Monitoring

**New file: `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/coherence.py`**

```python
@dataclass
class CoherenceCheck:
    """Result of checking output coherence against the stated goal."""
    coherent: bool
    score: float              # 0.0 (completely off-topic) to 1.0 (perfectly aligned)
    goal_keywords_found: int  # How many goal keywords appear in output
    output_keywords_found: int  # How many meaningful keywords in output
    overlap_ratio: float      # goal_keywords_found / total_goal_keywords
    drift_indicators: list[str]  # Specific signals of drift
    recommendation: str       # "proceed", "warn", "halt"

class CoherenceMonitor:
    """
    Lightweight post-step coherence checking.

    After each pipeline step, compares the step's output against:
    1. The step's title/description (immediate coherence)
    2. The pipeline's overall goal (trajectory coherence)
    3. Expected output patterns for the agent type (structural coherence)
    """

    COHERENCE_THRESHOLD_WARN = 0.3   # Below this: warn
    COHERENCE_THRESHOLD_HALT = 0.1   # Below this: halt pipeline
```

**Methods:**

```python
class CoherenceMonitor:
    def __init__(self, db_path: str = None):
        """Initialize with optional DB for logging coherence scores."""

    def check_step_coherence(self, output: str, step_title: str,
                              step_description: str, pipeline_goal: str = "",
                              expected_data_key: str = "") -> CoherenceCheck:
        """
        Main coherence check. Called after each pipeline step.

        Three checks combined into a single score:

        1. Keyword overlap between step description and output.
           - Extract keywords from step_title + step_description
           - Count how many appear in output
           - Score = found / total

        2. Drift indicators in output:
           - "I'm not sure what to do" -> drift signal
           - "Let me start over" -> drift signal
           - Output is mostly apologies/confusion -> drift signal
           - Output discusses topics not in step description -> drift signal
           - Very short output (< 100 chars) for non-trivial steps -> drift signal

        3. Structural coherence:
           - If expected_data_key is "spec" and output contains no structured data -> low
           - If expected_data_key is "validation" and output has no pass/fail -> low
           - If expected_data_key is "model" and output references no creation -> low
        """

    def check_trajectory_coherence(self, step_outputs: list[str],
                                    pipeline_goal: str) -> CoherenceCheck:
        """
        Check whether the sequence of outputs is converging toward the goal.

        Uses cumulative keyword coverage: each step should add goal-relevant
        keywords. If step N adds no new goal keywords, trajectory is stalling.
        """

    def detect_drift_signals(self, output: str) -> list[str]:
        """
        Scan output for known drift indicators.

        Returns list of detected signals with descriptions.
        """

    def log_coherence(self, pipeline_name: str, step_index: int,
                       check: CoherenceCheck):
        """Log coherence check result to DB for trend analysis."""
```

**New DB table:**

```sql
CREATE TABLE IF NOT EXISTS coherence_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    coherence_score REAL NOT NULL,
    goal_keyword_overlap REAL NOT NULL,
    drift_indicators TEXT DEFAULT '[]',
    recommendation TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

**Integration into `dispatch_pipeline()` in `agent_dispatcher.py`:**

After the aggregation step (from Proposal 1), add coherence checking:

```python
# After line 382 (or after aggregation from Proposal 1):
# COHERENCE CHECK
try:
    from coherence import CoherenceMonitor
    monitor = CoherenceMonitor()

    # Get step and pipeline descriptions for comparison
    step_title = step.get("data_key", agent_name)
    step_desc = step.get("description", "")
    pipeline_desc = pipeline.get("description", "")

    check = monitor.check_step_coherence(
        output=result.output,
        step_title=step_title,
        step_description=step_desc,
        pipeline_goal=pipeline_desc,
        expected_data_key=step.get("data_key", "")
    )

    monitor.log_coherence(pipeline_name, i, check)

    if check.recommendation == "halt":
        logger.error(
            f"COHERENCE HALT: Step {i+1} ({agent_name}) output is incoherent "
            f"(score={check.score:.2f}). Drift: {check.drift_indicators}. "
            f"Stopping pipeline."
        )
        error_result = AgentResult(
            agent_name=f"pipeline:{pipeline_name}",
            success=False,
            output="",
            error=(
                f"Coherence check failed at step {i+1}/{len(steps)} ({agent_name}). "
                f"Score: {check.score:.2f}. Drift: {check.drift_indicators}"
            ),
            duration_seconds=(datetime.now() - pipeline_start).total_seconds()
        )
        results.append(error_result)
        break

    elif check.recommendation == "warn":
        logger.warning(
            f"COHERENCE WARNING: Step {i+1} ({agent_name}) may be drifting "
            f"(score={check.score:.2f}). Drift: {check.drift_indicators}. "
            f"Continuing with caution."
        )
        if self.notifier:
            await self.notifier.send(
                f"Coherence Warning: {pipeline_name} step {i+1}",
                f"Agent {agent_name} output may be off-track.\n"
                f"Score: {check.score:.2f}\nSignals: {check.drift_indicators}",
                "medium"
            )

except ImportError:
    pass  # Coherence module not available, skip check
except Exception as e:
    logger.debug(f"Coherence check error (non-fatal): {e}")
```

**Integration into `planner.py` `record_step_result()`:**

Add optional coherence data to step results:

```python
def record_step_result(self, plan_id: int, step_index: int,
                       success: bool, summary: str = "",
                       error: str = "", artifacts: list = None,
                       duration_seconds: float = 0,
                       coherence_score: float = None) -> bool:  # NEW parameter
    """Record the result of executing a plan step."""
    # ... existing logic ...

    # If coherence score provided, include in execution context
    if coherence_score is not None:
        plan = self.get_plan(plan_id)
        if plan:
            ctx = plan.execution_context or {}
            coherence_history = ctx.get("coherence_scores", [])
            coherence_history.append({
                "step_index": step_index,
                "score": coherence_score,
                "timestamp": now,
            })
            ctx["coherence_scores"] = coherence_history
            conn.execute(
                "UPDATE plans SET execution_context = ? WHERE id = ?",
                (json.dumps(ctx), plan_id)
            )
```

### 4. Interface Design (Public API)

**Component A — Alignment Gate:**

```python
from alignment import AlignmentCore, InjectionResult

core = AlignmentCore()

# New verified injection (replaces get_injection_for_autonomous)
result: InjectionResult = core.get_injection_with_verification(
    agent_name="revit-builder",
    task_description="Create walls from PDF spec",
    event_data={"project": "Avon Park"}
)

if result.meets_minimum:
    prompt = result.prefix + "\n\n" + task_prompt
else:
    # Handle failure: block dispatch or degrade gracefully
    log_critical(f"Injection failed: {result.error or 'quality too low'}")
```

**Component B — Coherence Monitor:**

```python
from coherence import CoherenceMonitor, CoherenceCheck

monitor = CoherenceMonitor()

# After each pipeline step:
check: CoherenceCheck = monitor.check_step_coherence(
    output=agent_output,
    step_title="Extract geometry from PDF",
    step_description="Extract walls, rooms, doors from floor plan",
    pipeline_goal="Full pipeline: PDF floor plan to Revit model",
    expected_data_key="spec"
)

if check.recommendation == "halt":
    abort_pipeline(reason=f"Incoherent output: {check.drift_indicators}")
elif check.recommendation == "warn":
    log_warning(f"Possible drift: score={check.score}")
# else: "proceed" — all good

# Trajectory check across multiple steps:
trajectory: CoherenceCheck = monitor.check_trajectory_coherence(
    step_outputs=[step1_output, step2_output, step3_output],
    pipeline_goal="PDF floor plan to Revit model"
)
```

### 5. Integration Points

**Component A:**

1. **`agent_dispatcher.py` `execute_agent()`** (lines 427-579) — Primary. Replace lines 444-455 with the fail-closed gate. This is the single most critical change.

2. **`alignment.py` `AlignmentCore`** — Add `InjectionResult` dataclass and `get_injection_with_verification()` method. The existing `get_injection_for_autonomous()` remains for backward compatibility but is deprecated.

3. **`alignment.py` `record_violation()`** (lines 423-449) — Used by the fail-closed gate to log critical injection failures as alignment violations, making them visible in drift reports.

4. **`alignment.py` `get_drift_report()`** (lines 492-518) — Automatically picks up injection failures via the `alignment_drift_log` table. No modification needed.

5. **Notifier** — The fail-closed gate sends critical notifications when agents are blocked.

**Component B:**

1. **`agent_dispatcher.py` `dispatch_pipeline()`** (lines 303-425) — Primary. Add coherence check after each step, between aggregation (Proposal 1) and passing output forward.

2. **`planner.py` `record_step_result()`** (lines 643-715) — Store coherence scores in plan execution context.

3. **`memories.db`** — New `coherence_log` table.

4. **Future: `planner.py` `replan()`** — When coherence drops below threshold, trigger automatic replanning from the failed step. (Not in this proposal, but designed to support it.)

### 6. Implementation Steps

| # | Step | Description | Est. Time |
|---|------|-------------|-----------|
| 1 | Add `InjectionResult` to `alignment.py` | Dataclass with `success`, `prefix`, `char_count`, `components_present`, `quality_score`, `meets_minimum` property. | 30 min |
| 2 | Implement `get_injection_with_verification()` | New method in `AlignmentCore`. Calls existing `compile_profile()`, calculates quality score from component presence, returns `InjectionResult`. | 1 hour |
| 3 | Modify `execute_agent()` fail-closed gate | Replace lines 444-455 in `agent_dispatcher.py`. Implement the gating logic: pipeline/high-priority agents are blocked without alignment, manual/low-priority get warning only. | 1.5 hours |
| 4 | Add violation logging for injection failures | When injection fails or is below quality, call `record_violation()` with `violation_type="injection_quality_below_threshold"`. | 30 min |
| 5 | Create `coherence.py` scaffold | File with `CoherenceMonitor`, `CoherenceCheck` dataclass, DB schema. | 1 hour |
| 6 | Implement keyword-based coherence checking | `check_step_coherence()`: keyword extraction from goal/description, overlap calculation with output, scoring. | 2 hours |
| 7 | Implement drift signal detection | `detect_drift_signals()`: regex patterns for confusion markers, off-topic indicators, suspiciously short outputs. | 1 hour |
| 8 | Implement trajectory coherence | `check_trajectory_coherence()`: cumulative keyword coverage across steps, stall detection. | 1 hour |
| 9 | Integrate coherence into `dispatch_pipeline()` | Add post-step coherence check. Implement halt/warn/proceed logic. | 1 hour |
| 10 | Add `coherence_log` DB table and logging | Schema creation, `log_coherence()` method. | 30 min |
| 11 | Integrate coherence into `record_step_result()` | Add optional `coherence_score` parameter, store in plan execution context. | 30 min |
| 12 | Write tests for alignment gate | Test: injection succeeds -> agent dispatched. Test: injection fails -> pipeline agent blocked. Test: injection fails -> manual agent warned but dispatched. Test: quality score calculation for various component combinations. | 2 hours |
| 13 | Write tests for coherence monitor | Test: coherent output scores > 0.5. Test: completely off-topic output scores < 0.1. Test: drift signals detected. Test: trajectory stall detected. Test: halt/warn/proceed thresholds. | 2 hours |
| 14 | Manual validation | Run test pipeline with intentionally bad alignment config -> verify agent blocked. Run test pipeline with good/bad output -> verify coherence catches bad steps. | 1 hour |

**Total estimated time: 2-3 days**

### 7. Test Plan

**Component A — Alignment Gate tests (`tests/test_alignment_gate.py`):**

1. **Injection quality calculation:**
   - All components present -> quality_score ~1.0, `meets_minimum` is True.
   - Only kernel present (>500 chars) -> quality_score = 0.4, `meets_minimum` is True.
   - Empty prefix -> quality_score = 0.0, `meets_minimum` is False.
   - Kernel present but < 500 chars, no corrections, 1 principle -> quality_score = 0.2, `meets_minimum` is False.

2. **Fail-closed behavior:**
   - Pipeline event + injection failure -> `AgentResult(success=False)` returned, agent NOT executed.
   - Pipeline event + quality below threshold -> same block behavior.
   - Manual low-priority event + injection failure -> warning logged, agent executed.
   - Alignment module not importable -> all pipeline agents blocked.

3. **Violation logging:**
   - Injection failure -> entry in `alignment_drift_log` with `violation_type="injection_quality_below_threshold"`.
   - Violation appears in `get_drift_report()`.

4. **Backward compatibility:**
   - `get_injection_for_autonomous()` still works (returns string, not InjectionResult).
   - Existing alignment tests pass unchanged.

5. **Edge cases:**
   - `alignment.py` DB file missing -> InjectionResult(success=False).
   - `kernel.md` file missing -> quality score reflects missing kernel, but other components can still satisfy minimum.
   - Concurrent injection attempts (threading) -> no deadlock, each gets independent result.

**Component B — Coherence Monitor tests (`tests/test_coherence.py`):**

6. **Coherent output detection:**
   - Step: "Extract walls from PDF". Output mentions walls, dimensions, rooms. -> score > 0.5, recommendation = "proceed".
   - Step: "Validate BIM model". Output mentions validation, pass/fail, issues found. -> score > 0.5.

7. **Incoherent output detection:**
   - Step: "Extract walls from PDF". Output is a recipe for chocolate cake. -> score < 0.1, recommendation = "halt".
   - Step: "Create Revit model". Output says "I don't know what Revit is." -> drift detected, recommendation = "halt".

8. **Drift signal detection:**
   - Output: "I'm not sure what you want me to do." -> drift signal detected.
   - Output: "Let me start over from the beginning." -> drift signal detected.
   - Output: "" (empty) -> drift signal detected.
   - Output < 50 chars for a step with estimated_minutes > 10 -> drift signal.

9. **Trajectory coherence:**
   - 3 steps, each adding new goal-relevant keywords -> trajectory score increasing.
   - 3 steps, step 3 adds no new goal keywords -> trajectory stall detected.
   - All 3 steps off-topic -> trajectory score near 0.

10. **Threshold tests:**
    - Score = 0.05 -> recommendation = "halt".
    - Score = 0.15 -> recommendation = "warn".
    - Score = 0.50 -> recommendation = "proceed".
    - Score = 0.95 -> recommendation = "proceed".

11. **Edge cases:**
    - Empty pipeline goal -> coherence check returns "proceed" (cannot evaluate without goal).
    - Very long output (50000 chars) -> check processes first 10000 chars, does not timeout.
    - Non-English output -> keyword overlap still works on matching words, lower score is acceptable.

### 8. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Fail-closed gate blocks legitimate agents due to transient alignment errors | High | Medium | Only fail-closed for pipeline/high-priority agents. Low-priority manual agents get warning only. Add a `--force-dispatch` override for debugging. Log all blocks for review. |
| Alignment system is down (DB missing, kernel missing) -> all pipeline agents blocked | High | Low | This is intentional and correct — better to halt than run unconstrained. Add monitoring: if >3 agents are blocked in 10 minutes, alert the user that the alignment system needs attention. |
| Coherence monitor produces false positives (flags good output as incoherent) | Medium | Medium | Start with conservative thresholds (only halt at very low scores < 0.1). Log all coherence checks. Review false positive rate weekly and tune thresholds. Only "warn" by default; "halt" requires explicit pipeline config opt-in. |
| Coherence keyword matching is too simple for nuanced tasks | Medium | High | Keyword overlap is the v1 implementation. Design the `CoherenceCheck` interface to support future upgrades (embedding similarity, LLM evaluation) without changing the integration API. |
| Adding checks to the pipeline path increases latency | Low | Low | Both checks are pure computation (no LLM calls, no network). Keyword extraction + comparison is O(n) on output length. Expect < 100ms per check. |
| Quality score thresholds are wrong for some agent types | Medium | Medium | Make thresholds configurable per agent in `AGENT_REGISTRY`: `"min_alignment_quality": 0.3`. Domain-specific agents (BIM) might need higher thresholds; research agents might tolerate lower. |

### 9. Success Criteria

1. **Zero unconstrained pipeline agents:** After implementation, 100% of pipeline agent dispatches either have alignment injection with `quality_score >= 0.3` or are blocked. Measured by: count of `injection_quality_below_threshold` violations + count of successful injections = count of pipeline dispatch attempts.

2. **Alignment injection coverage:** Tracked via a new metric: `% of dispatches with verified alignment injection > 100 chars`. Target: 100% for pipeline agents, >95% for all agents.

3. **Drift detection accuracy:** Track coherence check results against pipeline outcomes. A pipeline step that triggers a "warn" or "halt" should correlate with either (a) the pipeline eventually failing downstream, or (b) the output being genuinely off-topic upon human review. Target: < 10% false positive rate on "halt" recommendations over the first 50 pipeline runs.

4. **Coherence score distribution:** For successful pipelines, the average per-step coherence score should be > 0.5. Track via `coherence_log` table.

5. **No regression in manual agent dispatch:** Manual, low-priority single-agent dispatches are unaffected. The fail-closed gate only blocks pipeline and high-priority agents when alignment fails. Manual agents get a warning only.

6. **Pipeline failure clarity:** When a pipeline is halted due to alignment or coherence failure, the error message in `AgentResult` clearly states why, including the specific score and what threshold was violated. No silent failures.

---

## Cross-Proposal Dependencies

The two proposals are designed to work together but can be implemented independently:

- **Proposal 1 (Aggregator) is fully independent.** It modifies the pipeline's data path (what gets passed between steps) but does not depend on alignment or coherence checking.

- **Proposal 2 Component A (Fail-Closed Gate) is fully independent.** It modifies the pre-dispatch logic in `execute_agent()`, which runs before the pipeline loop.

- **Proposal 2 Component B (Coherence Monitor) is enhanced by Proposal 1** but does not require it. The coherence monitor checks raw output against the goal. If the Aggregator is also active, the coherence check should run on the raw output *before* aggregation (so it can see the full output for drift detection), while the aggregated output is what gets passed to the next step.

**Recommended implementation order:**
1. Proposal 2A (Fail-Closed Gate) — smallest change, highest safety impact, blocks the worst failure mode immediately
2. Proposal 1 (Aggregator) — addresses context growth, the most architecturally significant addition
3. Proposal 2B (Coherence Monitor) — adds runtime verification, benefits from aggregation being in place to see the full integration path

**Shared infrastructure:**
- Both proposals add tables to `memories.db` (`aggregation_log`, `coherence_log`). These should follow the same schema patterns used by `alignment_drift_log` (in `alignment.py`) and `plan_step_results` (in `planner.py`).
- Both proposals use the same graceful-import pattern (`try: import X; _available = True except ImportError: _available = False`) established in `agent_dispatcher.py` lines 25-30.
- Both proposals preserve the existing fallback behavior: if the new module is unavailable, the system operates exactly as it does today.
