#!/usr/bin/env python3
"""
Decomposition Prompts — Templates for splitting work into parallel subtasks.
"""

# Decomposition strategies
STRATEGIES = {
    "by_file": {
        "name": "By File",
        "description": "Split work across files — each worker handles a subset of files",
        "prompt_template": """You are worker {worker_id} of {total_workers}.

Your assigned files: {assigned_items}

Task: {task_description}

Focus ONLY on your assigned files. Do not touch other files.
Report your findings/changes for your files only.
""",
    },

    "by_topic": {
        "name": "By Topic",
        "description": "Split work by topic/concern — each worker handles one aspect",
        "prompt_template": """You are worker {worker_id} of {total_workers}.

Your assigned topic: {assigned_items}

Overall task: {task_description}

Focus ONLY on your assigned topic. Be thorough within your scope.
Report findings relevant to your topic only.
""",
    },

    "by_element_category": {
        "name": "By Element Category",
        "description": "BIM-specific: split by Revit element categories",
        "prompt_template": """You are worker {worker_id} of {total_workers}.

Your assigned element categories: {assigned_items}

BIM Task: {task_description}

Focus ONLY on the element categories assigned to you.
Report element counts, issues, and recommendations for your categories.
""",
    },

    "by_chunk": {
        "name": "By Chunk",
        "description": "Split a large list into equal chunks for parallel processing",
        "prompt_template": """You are worker {worker_id} of {total_workers}.

Your assigned items (chunk {worker_id}): {assigned_items}

Task: {task_description}

Process ONLY your assigned items. Report results for each.
""",
    },
}


def get_strategy(name: str) -> dict:
    """Get a decomposition strategy by name."""
    return STRATEGIES.get(name, STRATEGIES["by_chunk"])


def list_strategies() -> list:
    """List all available strategies."""
    return [{"name": k, "description": v["description"]} for k, v in STRATEGIES.items()]


def build_worker_prompt(strategy_name: str, worker_id: int, total_workers: int,
                        assigned_items: str, task_description: str,
                        extra_context: str = "") -> str:
    """Build a prompt for a specific worker."""
    strategy = get_strategy(strategy_name)
    prompt = strategy["prompt_template"].format(
        worker_id=worker_id,
        total_workers=total_workers,
        assigned_items=assigned_items,
        task_description=task_description,
    )
    if extra_context:
        prompt += f"\n\nAdditional context:\n{extra_context}"
    return prompt


def decompose_items(items: list, num_workers: int) -> list:
    """Split a list of items into num_workers roughly equal chunks."""
    chunks = [[] for _ in range(num_workers)]
    for i, item in enumerate(items):
        chunks[i % num_workers].append(item)
    return [c for c in chunks if c]  # Remove empty chunks
