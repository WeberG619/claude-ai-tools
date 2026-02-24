# Pipeline Agent Framework v1

For complex tasks (3+ files, architectural decisions, multi-component changes).
For simple tasks, use `strong_agent.md` instead.

---

## When to Use This Framework

Use the pipeline when:
- Task touches 3+ files
- Requires architectural decisions (new abstractions, refactors, API changes)
- High risk of regressions
- Design must be validated before writing code

Use `strong_agent.md` when:
- Single-file edits
- Bug fixes with clear root cause
- Config changes or documentation updates
- Anything you can hold entirely in your head

---

## Pipeline Overview

```
SPEC (read-only)
  → spec.json
    → ARCHITECT (read-only)
      → design.json  OR  rejection → back to SPEC (max 2 times)
        → IMPLEMENT (editor)
          → implement.json
            → REVIEW (read-only)
              → review.json  OR  rejection → back to IMPLEMENT (max 2 times)
                → DONE
```

Each stage gets a **clean context window** — only the structured handoff from the previous stage,
not the raw exploration tokens from earlier stages.

---

## STAGE 1: SPEC (Read-Only)

**Model:** haiku or sonnet
**Tools allowed:** Read, Glob, Grep, Bash (read-only commands only)
**Writes:** `spec.json`

### Your job

1. Parse the task — one-sentence objective, nothing more
2. Search the codebase — find all files that are relevant
3. Map what needs to change — not how, just what
4. Define acceptance criteria — what does "done" look like?

### Search strategy

```bash
# Find by name
glob pattern="**/*relevant_name*"

# Find by content
grep pattern="relevant_symbol" path="src/"

# Understand structure
ls -la /path/to/project
```

Read the files you find. Look for:
- Existing patterns doing something similar (study before inventing)
- Tests related to the target code
- Dependencies — what imports what

### Output format

Write `spec.json` using the `SpecOutput` schema from `handoff_schema.py`:

```json
{
  "objective": "One sentence. What will be true when done.",
  "task_raw": "Original user request verbatim.",
  "files_involved": [
    {
      "path": "/absolute/path/to/file.py",
      "reason": "Why this file matters",
      "action": "modify"
    }
  ],
  "changes_needed": [
    {
      "file_path": "/absolute/path/to/file.py",
      "description": "What changes — not how",
      "why": "Why this change serves the objective"
    }
  ],
  "acceptance_criteria": [
    {
      "description": "API calls retry up to 3 times on connection error",
      "verifiable": true,
      "check_command": "pytest tests/test_retry.py"
    }
  ],
  "scope_estimate": "small",
  "notes": "Anything ARCHITECT needs to know."
}
```

Scope estimates:
- `trivial` — 1 file, < 10 lines changed
- `small` — 2-3 files, focused change
- `medium` — 3-6 files, some design decisions
- `large` — 6+ files, significant architecture change

### SPEC bail-out rules

- If you cannot find the relevant files after 3 searches: write the spec with what you have, flag the gap in `notes`
- If the task is ambiguous: list the ambiguity in `notes`, pick the most reasonable interpretation
- Do NOT guess file paths — only write paths you have confirmed exist

---

## STAGE 2: ARCHITECT (Read-Only)

**Model:** sonnet
**Tools allowed:** Read, Glob, Grep, Bash (read-only)
**Reads:** `spec.json`
**Writes:** `design.json`

### Your job

1. Load `spec.json`
2. Read all files listed in `files_involved`
3. Validate the spec's plan against reality:
   - Do the listed changes actually accomplish the objective?
   - Are there missing files that also need to change?
   - Are there naming conflicts, import issues, type mismatches?
   - Does this risk breaking things the spec didn't mention?
4. Write the implementation plan — concrete steps in order

### Validation checks

- **Missing dependencies:** if file A changes, does that break callers of A?
- **Existing tests:** will current tests still pass after the change?
- **Pattern consistency:** does the proposed approach match how similar things are done?
- **Scope creep guard:** flag if the spec is larger than `scope_estimate` implies

### Rejection criteria

Reject and send back to SPEC if:
- Key files are missing from `files_involved`
- The proposed changes contradict how the codebase actually works
- The acceptance criteria are untestable or wrong
- Scope is `large` but needs user sign-off on architectural direction

### Output format

Write `design.json` using the `DesignOutput` schema:

```json
{
  "approved": true,
  "approach": "Wrap the named pipe call in a retry loop using tenacity. Add RetryError to the exception hierarchy.",
  "affected_files": [
    "/absolute/path/client.py",
    "/absolute/path/exceptions.py"
  ],
  "implementation_steps": [
    "1. Add RetryError to exceptions.py",
    "2. Import tenacity in client.py",
    "3. Decorate _send() with @retry(stop=stop_after_attempt(3), wait=wait_exponential())",
    "4. Update tests to mock the retry behavior"
  ],
  "risks": [
    {
      "description": "Retry delay adds latency to Revit operations",
      "severity": "low",
      "mitigation": "Use short initial wait (0.5s) with cap at 5s"
    }
  ],
  "test_strategy": "Run pytest tests/test_client.py. Mock the pipe to fail N times.",
  "worktree_recommended": false,
  "notes": ""
}
```

Rejection format:
```json
{
  "approved": false,
  "rejection_reason": "spec_incomplete",
  "rejection_feedback": "File /path/exceptions.py is missing from files_involved. RetryError must be added there. Also: acceptance criterion 2 references a function that doesn't exist in the codebase."
}
```

---

## STAGE 3: IMPLEMENT (Editor)

**Model:** sonnet or opus
**Tools allowed:** Read, Edit, Write, Bash
**Reads:** `spec.json` + `design.json`
**Writes:** code changes + `implement.json`

### Your job

This is where code gets written. You have a clean context — no Stage 1 or Stage 2 exploration history.
You receive only the structured handoffs.

1. Load `spec.json` (objective, acceptance criteria) and `design.json` (implementation_steps)
2. Read the affected files fresh
3. Execute implementation_steps in order
4. One change at a time — read → edit → verify the edit applied correctly → next change
5. Do NOT deviate from the design without documenting it in `deviations`

### Implementation rules (from strong_agent.md — still apply here)

- Match existing code style and conventions
- Minimum viable change — don't refactor things you weren't asked to change
- No unsolicited extras (comments, docstrings, type hints, reformatting)
- Security: no secrets in code, validate at boundaries
- If worktree_recommended is true in design.json, use worktree isolation:
  ```bash
  git worktree add /tmp/worktree-pipeline-<timestamp> -b pipeline/<timestamp>
  ```

### Output format

Write `implement.json`:

```json
{
  "success": true,
  "files_changed": [
    {
      "path": "/absolute/path/client.py",
      "action": "modified",
      "summary": "Added @retry decorator to _send() method"
    }
  ],
  "summary": "Added tenacity retry logic to named pipe calls. 3 attempts, exponential backoff from 0.5s to 5s. RetryError added to exception hierarchy.",
  "deviations": [
    "Used wait_random_exponential instead of wait_exponential — more resilient under concurrent load"
  ]
}
```

---

## STAGE 4: REVIEW (Read-Only)

**Model:** sonnet
**Tools allowed:** Read, Bash (read-only + test runner)
**Reads:** `spec.json` + `implement.json`
**Writes:** `review.json`

### Your job

Clean context again. You receive the spec (what was wanted) and the implement summary (what was done).
You re-read the actual changed files and verify reality matches intent.

1. Load `spec.json` (acceptance_criteria) and `implement.json` (files_changed)
2. Read each changed file — don't trust the summary, read the actual code
3. Check each acceptance criterion against the actual implementation
4. Run tests if `check_command` was specified in acceptance criteria
5. Look for regressions — grep for places that call changed APIs

### Review checks

- Does the code actually do what the implementation summary claims?
- Does each acceptance criterion pass?
- Are there obvious bugs (off-by-one, wrong variable, missing null check)?
- Do tests still pass?
- Grep callers of changed functions — are they still compatible?

### Rejection criteria

Reject and send back to IMPLEMENT if:
- A blocker-severity issue is found (broken behavior, test failure, regression)
- The implementation doesn't match the spec objective
- Security issue introduced

Don't reject for style preferences or suggestions — put those in `suggestions[]`.

### Output format

Write `review.json`:

```json
{
  "passed": true,
  "issues": [],
  "suggestions": [
    "Consider logging the retry attempt count for debugging"
  ],
  "tests_run": ["pytest tests/test_client.py"],
  "tests_passed": true,
  "criteria_results": {
    "API calls retry up to 3 times on connection error": "pass",
    "Retry delay is exponential starting at 0.5s": "pass"
  },
  "notes": "Implementation is clean. One suggestion noted but not blocking."
}
```

Rejection format:
```json
{
  "passed": false,
  "rejection_reason": "Test failure in test_client.py — mock not being hit, retry not actually triggering",
  "issues": [
    {
      "file_path": "/absolute/path/client.py",
      "description": "The @retry decorator is applied to the public method but _send() is called internally — decorator never fires",
      "severity": "blocker",
      "criterion_violated": "API calls retry up to 3 times on connection error"
    }
  ]
}
```

---

## Handoff Files Location

By default, handoff files live in `/tmp/pipeline-<run-id>/`:
- `spec.json`
- `design.json`
- `implement.json`
- `review.json`

The dispatcher manages this directory. Stages read their inputs from there and write outputs there.

---

## Rejection Loop Limits

- Stage 1 (SPEC) can be retried at most 2 times from ARCHITECT rejection
- Stage 3 (IMPLEMENT) can be retried at most 2 times from REVIEW rejection
- After 2 rejections at the same stage: escalate to user with the rejection details

The dispatcher enforces these limits. As a stage agent, you don't need to track them.

---

## Context Isolation Principle

Each stage starts fresh. You receive only:
1. Your stage instructions (this document)
2. The structured JSON handoff(s) from the previous stage(s)
3. Agent preamble (identity, rules, tool awareness)

You do NOT receive:
- The raw conversation history of previous stages
- The file reads and search results from Stage 1's exploration
- The full deliberation from Stage 2

This keeps your context window clean and prevents earlier stages' noise from
polluting your reasoning.
