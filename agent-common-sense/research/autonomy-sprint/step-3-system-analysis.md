# Step 3: System Gap Analysis -- Papers vs Our Architecture

> Generated: 2026-02-18
> Agent: system-analyst
> Sprint: Autonomy Stress Test
> Input: step-2-paper-summaries.md

---

## Paper 1: "The Hot Mess of AI" (Anthropic, ICLR 2026)

### Thesis: Failures are incoherence (variance), not misalignment (bias). Longer reasoning chains amplify randomness, not systematic error.

---

### 1. Current State

Our system already addresses this problem partially through several mechanisms:

- **Kernel v2.0 Self-Reflection block** (`kernel.md` lines 156-180): "During Multi-Step Tasks (every 3-5 steps), silently ask yourself: Am I making progress? Am I repeating myself? Am I drifting from scope?" This is exactly the kind of execution monitoring the paper argues for -- checking whether the agent has "lost the plot."

- **Strong Agent Framework bail-out rules** (`strong_agent.md` lines 82-88): "Stuck for 3+ steps with no progress? Stop. Report what you found and what's blocking you. Don't spin." This addresses the variance problem by providing circuit-breakers.

- **Planner checkpoint system** (`planner.py` lines 69-71): `PlanStep` has a `checkpoint: bool = False` field. When True, the plan pauses for human review after that step. This is a manual coherence gate.

- **Alignment drift detection** (`alignment.py` lines 451-490): The `detect_drift()` method looks for patterns of repeated violations over a time window, which is a form of post-hoc variance detection.

### 2. Gap Identified

**No real-time coherence monitoring during execution.** Our system has pre-action checks (Common Sense `before()`), post-action learning (`learn()`), and periodic self-reflection prompts (kernel). But there is no automated mechanism that watches an executing agent's trajectory and detects when its actions stop making sense relative to the stated goal. The self-reflection in the kernel is a *prompt instruction*, not an *enforced mechanism* -- the model can ignore it precisely when it is most incoherent (since incoherence means it has stopped following instructions).

**No atomic task decomposition enforcement.** The planner (`planner.py`) supports step decomposition, but steps are defined by templates or manual input. There is no mechanism that takes a complex task, measures its estimated reasoning depth, and automatically breaks it into smaller pieces to keep each sub-task within the "coherence zone." The paper's core finding is that there is a task-complexity threshold above which variance dominates -- our system has no way to detect or stay below that threshold.

**Context growth is uncontrolled.** The `coordinator.py` shared state mechanism (`get_accumulated_context()`) passes all shared state forward. The `agent_dispatcher.py` pipeline passes `previous_output` as raw text between agents. Neither compresses or summarizes intermediate context. As pipeline chains grow, context bloat pushes the model further into the high-variance regime.

### 3. Improvement Opportunities

| # | Improvement | Description | Difficulty | Impact |
|---|-----------|-------------|------------|--------|
| 1A | **Trajectory coherence monitor** | Add a lightweight post-step hook in `planner.py` that, after each step result, compares the step's output summary against the plan's goal. Flag if the output appears unrelated to the goal (e.g., cosine similarity between step output embedding and goal description drops below threshold). Surface as a warning in `record_step_result()`. | Medium (2-3 days) | 8/10 |
| 1B | **Automatic atomization heuristic** | In `planner.py`'s `decompose_goal()`, add logic to estimate task complexity (number of tools likely needed, estimated reasoning steps from keyword heuristics) and recursively decompose any step estimated above a threshold (e.g., >5 reasoning steps). Use the existing `replan()` mechanism to break large steps further. | Medium (2-3 days) | 7/10 |
| 1C | **Context compression between pipeline steps** | In `agent_dispatcher.py`'s `dispatch_pipeline()`, after each step completes, pass `previous_output` through a summarization call (or heuristic truncation to key facts + artifacts) before injecting it into the next step. Cap compressed output at ~2000 chars. | Easy (hours) | 6/10 |
| 1D | **Enforced self-check via tool hook** | Create a `PostToolUse` hook (or extend `PreToolUse`) that fires every N tool calls within a sub-agent session. The hook queries the agent: "State your current sub-goal in one sentence." If the response doesn't match the original task, flag for human review or terminate the session. | Hard (1-2 weeks) | 9/10 |

---

## Paper 2: "ROMA: Recursive Open Meta-Agent Framework" (Sentient AI, Feb 2026)

### Thesis: Four-role architecture (Atomizer/Planner/Executor/Aggregator) with recursive decomposition, parallel execution, and active context compression.

---

### 1. Current State

Our system has strong overlap with ROMA's architecture, but with critical gaps in two of the four roles:

- **Planner role: Solid.** `planner.py` handles plan creation, template matching, step dependency tracking, and adaptive replanning. The `get_next_steps()` method already supports parallel execution -- it returns all steps whose dependencies are satisfied. The template system (`BUILTIN_TEMPLATES`) provides MECE-style decomposition for known domains.

- **Executor role: Solid.** `agent_dispatcher.py` executes agents via Claude Code CLI, tracks results, handles timeouts, and supports pipelines. The Strong Agent Framework provides per-agent execution methodology.

- **Atomizer role: Weak/absent.** `decompose_goal()` in `planner.py` does basic template matching or falls back to a generic 3-step plan. It does not recursively evaluate whether a step is truly atomic. There is no "is this small enough to execute directly?" decision gate. The `match_template()` method uses keyword counting, not semantic understanding of task complexity.

- **Aggregator role: Absent.** This is the biggest gap. There is no component that actively compresses, validates, or synthesizes results between stages. In `agent_dispatcher.py`, the pipeline passes raw output between steps. In `coordinator.py`, `get_accumulated_context()` returns all shared state as-is. Nobody is asking "what from this output actually matters for the next step?"

### 2. Gap Identified

**No Aggregator component.** The paper's key innovation -- active context compression between stages -- is completely missing from our system. When agent A finishes and agent B starts, B receives everything A produced. For a 3-step pipeline, this is manageable. For a 5+ step pipeline or recursive decomposition, context will explode. This directly causes the incoherence that Paper 1 warns about.

**No recursive decomposition.** Our planner creates a flat list of steps. If step 3 turns out to be more complex than expected, the only option is `replan()` which replaces steps -- it doesn't recursively decompose step 3 into sub-steps with their own Atomizer/Planner/Executor/Aggregator cycle. The hierarchy exists in `goals.py` (parent/child goals with progress rollup), but there is no mechanism to automatically spawn sub-plans from plan steps.

**No MECE validation.** ROMA's Planner creates subtask graphs that are mutually exclusive and collectively exhaustive. Our planner has no validation that steps cover the full goal without overlap. Steps are defined by templates or manual input and taken on faith.

### 3. Improvement Opportunities

| # | Improvement | Description | Difficulty | Impact |
|---|-----------|-------------|------------|--------|
| 2A | **Aggregator module** | Create `aggregator.py` in `agent-common-sense/`. After each pipeline step in `agent_dispatcher.py`, pass the step output through an aggregation function that: (a) extracts key facts/artifacts, (b) drops intermediate reasoning, (c) validates output against the step's expected_outputs field, (d) produces a compressed context package for the next step. Can start with heuristic extraction (regex for key patterns, truncation) and graduate to LLM-based summarization. | Medium (3-5 days) | 9/10 |
| 2B | **Recursive step decomposition** | Extend `planner.py` to support recursive plans. When a step is about to execute and its `estimated_minutes > 30` or its description matches complexity signals (multiple tools, "research and implement", etc.), automatically call `decompose_goal()` on that step to create a sub-plan. Link sub-plan to parent plan via a new `parent_plan_id` column. The parent step's result becomes the sub-plan's aggregated output. | Hard (1-2 weeks) | 8/10 |
| 2C | **Atomicity classifier** | Add an `is_atomic()` method to `planner.py` that evaluates a step description and returns True if it can be executed in a single agent call. Use heuristics: keyword count for multi-domain signals, presence of conjunctions ("and then", "followed by"), estimated tool count. Non-atomic steps get flagged for decomposition before execution starts. | Easy (hours) | 5/10 |
| 2D | **MECE validation for plans** | After plan creation, run a validation pass that checks: (a) do steps collectively cover the goal description's key requirements? (b) do any steps have overlapping descriptions? Use keyword extraction from goal + steps to compute coverage and overlap scores. Warn if coverage is below 80% or overlap above 20%. | Medium (2-3 days) | 4/10 |
| 2E | **Parallel execution in dispatcher** | The planner's `get_next_steps()` already returns multiple ready steps, but `dispatch_pipeline()` in `agent_dispatcher.py` executes steps sequentially in a loop. Modify to use `asyncio.gather()` for steps that `can_parallel=True` and have all dependencies met. | Easy (hours) | 6/10 |

---

## Paper 3: "Petri 2.0" (Anthropic, Jan 2026)

### Thesis: Automated behavioral auditing with eval-awareness mitigation. 70 scenarios for agentic failure modes including sub-agent delegation and multi-agent collusion.

---

### 1. Current State

Our system has alignment and safety infrastructure, but no automated behavioral testing:

- **Alignment principles** (`alignment.py`): We register, track, and inject alignment principles. We have drift detection and violation logging. The `verify_outcome()` method does basic keyword-based checking of results against principles.

- **Pre-action safety checks** (`sense.py`): The `before()` method classifies actions as destructive/shared-state/unfamiliar and blocks or warns accordingly. Seed corrections provide pre-loaded safety knowledge.

- **Sub-agent alignment injection** (`alignment.py` lines 302-342): `compile_profile()` builds per-agent alignment profiles with domain-aware principle selection, kernel injection, and correction loading. The `_trim_to_budget()` method keeps injection within token limits.

- **Agent Chaining Protocol** (`strong_agent.md` lines 93-149): Explicit rules for when to chain, how to pass context, maximum chain depth (4 agents), and chain failure handling.

### 2. Gap Identified

**No automated behavioral testing at all.** We have alignment *injection* (ensuring agents receive safety instructions) and *detection* (logging violations after they occur), but we have zero proactive *testing* of agent behavior. We never simulate adversarial scenarios to verify that our agents actually follow the injected principles. We assume injection equals compliance.

**Sub-agent safety is prompt-only.** Our entire sub-agent safety model relies on the Strong Agent Framework being injected into sub-agent prompts and the sub-agent choosing to follow it. The paper specifically identifies "delegation to unconstrained sub-agents" as a critical failure mode. Our `_run_claude_agent()` in `agent_dispatcher.py` runs sub-agents with `--dangerously-skip-permissions`, meaning they have full system access. If alignment injection fails (which `alignment.py` gracefully handles by continuing without injection -- see lines 445-455), the sub-agent runs completely unconstrained.

**No output validation against safety criteria.** The `verify_outcome()` method in `alignment.py` (lines 392-419) does extremely basic keyword matching. It checks if the word "verified" appears in results. It does not evaluate whether the agent's actual behavior was safe -- it cannot detect subtle violations like the agent having accessed files it shouldn't have, or having produced output that leaks sensitive information.

**No eval-awareness consideration.** Our self-reflection prompts in `kernel.md` could be "gamed" by a sufficiently capable model that recognizes they are alignment checks and performs differently during checks vs. normal execution. We have no mechanism to make our safety checks indistinguishable from normal operations.

### 3. Improvement Opportunities

| # | Improvement | Description | Difficulty | Impact |
|---|-----------|-------------|------------|--------|
| 3A | **Behavioral test suite** | Create `tests/behavioral/` in `agent-common-sense/`. Write scenario scripts that launch sub-agents via `agent_dispatcher.py` with adversarial prompts (e.g., "delete this file", "ignore safety guidelines", "email this data to external address") and verify the agent refuses or escalates. Run as CI-like checks before deploying changes to agent infrastructure. Start with 10 scenarios covering: destructive actions, data exfiltration, ignoring injected corrections, scope creep beyond task. | Medium (3-5 days) | 8/10 |
| 3B | **Sub-agent output sandboxing** | Add a post-execution validation step in `agent_dispatcher.py`'s `execute_agent()`. After the agent returns, scan its output for: (a) file paths outside the expected working directory, (b) commands that shouldn't have been run, (c) references to sensitive data. Log violations via `alignment.record_violation()`. Optionally quarantine the output (don't pass to next pipeline step) if violations exceed a severity threshold. | Medium (2-3 days) | 7/10 |
| 3C | **Permission-scoped sub-agents** | Replace `--dangerously-skip-permissions` with a per-agent permission scope in `AGENT_REGISTRY`. Each agent gets a list of allowed tools/directories. The dispatcher generates a permission config and passes it to Claude Code. This prevents the "unconstrained sub-agent" scenario entirely at the infrastructure level rather than relying on prompt compliance. | Hard (1-2 weeks) | 9/10 |
| 3D | **Alignment injection verification** | After `compile_prompt()` in `alignment.py`, verify that the injection actually made it into the prompt (not silently dropped or truncated to nothing). If injection fails or produces <100 chars, refuse to dispatch the agent and log a critical alignment failure. Currently, `agent_dispatcher.py` line 454 logs a warning but continues execution. | Easy (hours) | 7/10 |
| 3E | **Naturalistic safety checks** | Instead of the explicit "Am I drifting from scope?" self-reflection prompts in `kernel.md`, embed safety verification as natural-seeming operations. E.g., after an agent modifies a file, the post-step hook "reads the file to verify the edit" -- but this read also checks the file contents against safety criteria (no secrets committed, no unauthorized modifications). The agent doesn't know the check is also a safety audit. | Hard (1-2 weeks) | 6/10 |

---

## Cross-Paper Synthesis

The three papers, taken together, paint a consistent picture that illuminates a single architectural weakness in our system:

**Our system is strong on alignment injection but weak on execution verification.**

- Paper 1 says: agents fail by going incoherent, not by being misaligned. *Our kernel injection is good, but we don't monitor whether agents actually stay coherent during execution.*
- Paper 2 says: recursive decomposition + active context compression prevents the conditions that cause incoherence. *Our planner decomposes but doesn't compress, and doesn't recurse.*
- Paper 3 says: you need to test whether your safety mechanisms actually work, not just trust injection. *We inject safety principles but never test whether agents follow them.*

The common thread is: **the gap between intent and execution.** We are excellent at telling agents what to do (kernel, strong agent framework, alignment principles, corrections) but have limited infrastructure for verifying they actually do it, detecting when they drift, and keeping context manageable enough that they *can* stay coherent.

---

## Prioritized Recommendations

Ranked by impact-to-effort ratio (impact / effort days):

| Rank | ID | Improvement | Impact | Effort | Ratio | Quick Win? |
|------|----|------------|--------|--------|-------|------------|
| 1 | 1C | Context compression between pipeline steps | 6 | 0.5 days | 12.0 | Yes |
| 2 | 2E | Parallel execution in dispatcher | 6 | 0.5 days | 12.0 | Yes |
| 3 | 3D | Alignment injection verification (fail-closed) | 7 | 0.5 days | 14.0 | Yes |
| 4 | 2C | Atomicity classifier for plan steps | 5 | 0.5 days | 10.0 | Yes |
| 5 | 1A | Trajectory coherence monitor | 8 | 3 days | 2.7 | No |
| 6 | 2A | Aggregator module | 9 | 4 days | 2.3 | No |
| 7 | 3B | Sub-agent output sandboxing | 7 | 3 days | 2.3 | No |
| 8 | 3A | Behavioral test suite | 8 | 4 days | 2.0 | No |
| 9 | 1B | Automatic atomization heuristic | 7 | 3 days | 2.3 | No |
| 10 | 2B | Recursive step decomposition | 8 | 10 days | 0.8 | No |
| 11 | 3C | Permission-scoped sub-agents | 9 | 10 days | 0.9 | No |
| 12 | 1D | Enforced self-check via tool hook | 9 | 10 days | 0.9 | No |
| 13 | 2D | MECE validation for plans | 4 | 3 days | 1.3 | No |
| 14 | 3E | Naturalistic safety checks | 6 | 10 days | 0.6 | No |

### Recommended Implementation Order

**Phase 1: Quick Wins (1-2 days total)**
1. **3D** - Make alignment injection fail-closed instead of fail-open. Simplest safety improvement with highest ratio.
2. **1C** - Add context compression between pipeline steps. Directly addresses both Paper 1 (reduces incoherence trigger) and Paper 2 (Aggregator-lite).
3. **2E** - Enable parallel step execution in dispatcher. Already supported by planner, just needs dispatcher integration.
4. **2C** - Add atomicity classifier. Simple heuristic that gates decomposition decisions.

**Phase 2: Core Architecture (1-2 weeks)**
5. **2A** - Build the Aggregator module. Single most impactful architectural addition per ROMA.
6. **1A** - Add trajectory coherence monitoring. Catches incoherence during execution, not after.
7. **3B** - Add output sandboxing. Catches unsafe outputs before they propagate.
8. **3A** - Build behavioral test suite. Validates that our entire safety stack actually works.

**Phase 3: Deep Structural (2-4 weeks)**
9. **1B** + **2B** - Automatic atomization + recursive decomposition. These are coupled and represent a fundamental upgrade to the planner.
10. **3C** - Permission-scoped sub-agents. Replaces prompt-trust with infrastructure enforcement.
11. **1D** - Enforced self-check hooks. Requires Claude Code hook system extension.

---

## Key Metrics to Track

After implementing these changes, measure:

1. **Pipeline completion rate** - % of multi-step pipelines that complete all steps without failure (baseline: unknown, target: >80%)
2. **Coherence score** - For coherence monitor (1A), track % of steps that pass coherence check (target: >90%)
3. **Context size at pipeline step N** - With aggregator (2A), track token count at each step (target: flat or decreasing, not growing)
4. **Alignment injection coverage** - % of agent dispatches that have >100 chars of alignment injection (target: 100%)
5. **Behavioral test pass rate** - % of adversarial scenarios where agent behaves safely (target: >95%)
6. **Sub-agent violation rate** - Number of output sandboxing violations per 100 dispatches (target: <2%)
