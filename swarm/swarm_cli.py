#!/usr/bin/env python3
"""
Swarm CLI — Plan, dispatch, monitor, and collect parallel agent work.

Usage:
    swarm_cli.py plan "task" --items a,b,c --workers 5 --strategy by_chunk
    swarm_cli.py dispatch <plan_file>
    swarm_cli.py status <swarm_id>
    swarm_cli.py collect <swarm_id> [--merge deduplicate]
    swarm_cli.py strategies
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from swarm_engine import SwarmEngine
from decomposition_prompts import list_strategies
from merge_strategies import list_merge_strategies


def main():
    parser = argparse.ArgumentParser(description="Swarm CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # plan
    p_plan = sub.add_parser("plan", help="Create a decomposition plan")
    p_plan.add_argument("task", help="Task description")
    p_plan.add_argument("--items", required=True, help="Comma-separated items to split")
    p_plan.add_argument("--workers", type=int, default=5)
    p_plan.add_argument("--strategy", default="by_chunk", choices=["by_file", "by_topic", "by_element_category", "by_chunk"])
    p_plan.add_argument("--merge", default="deduplicate", choices=["concatenate", "deduplicate", "merge_json", "vote"])
    p_plan.add_argument("--save", help="Save plan to JSON file")

    # dispatch
    p_dispatch = sub.add_parser("dispatch", help="Dispatch a plan")
    p_dispatch.add_argument("plan_file", help="Path to plan JSON file")
    p_dispatch.add_argument("--project", default="")
    p_dispatch.add_argument("--priority", type=int, default=5)

    # status
    p_status = sub.add_parser("status", help="Check swarm status")
    p_status.add_argument("swarm_id", help="Swarm ID")

    # collect
    p_collect = sub.add_parser("collect", help="Collect and merge results")
    p_collect.add_argument("swarm_id", help="Swarm ID")
    p_collect.add_argument("--merge", default="deduplicate")

    # strategies
    sub.add_parser("strategies", help="List available strategies")

    args = parser.parse_args()
    engine = SwarmEngine()

    if args.command == "plan":
        items = [i.strip() for i in args.items.split(",") if i.strip()]
        plan = engine.plan(
            task_description=args.task,
            items=items,
            num_workers=args.workers,
            strategy=args.strategy,
            merge=args.merge,
        )
        print(engine.format_plan(plan))

        if args.save:
            Path(args.save).write_text(json.dumps(plan, indent=2))
            print(f"\nPlan saved to: {args.save}")
        else:
            # Save to temp
            plan_file = Path(f"/tmp/swarm_plan_{plan['swarm_id']}.json")
            plan_file.write_text(json.dumps(plan, indent=2))
            print(f"\nPlan saved to: {plan_file}")
            print(f"To dispatch: swarm_cli.py dispatch {plan_file}")

    elif args.command == "dispatch":
        plan_path = Path(args.plan_file)
        if not plan_path.exists():
            print(f"Plan file not found: {args.plan_file}", file=sys.stderr)
            sys.exit(1)
        plan = json.loads(plan_path.read_text())
        result = engine.dispatch(plan, project=args.project, priority=args.priority)
        print(f"Dispatched swarm {result['swarm_id']}")
        print(f"  Parent task: {result['parent_task_id']}")
        print(f"  Workers dispatched: {len(result['dispatched'])}")
        for d in result['dispatched']:
            tid = d.get('agent_task_id', d.get('board_task_id', '?'))
            print(f"    Worker {d['worker_id']}: task #{tid}")

    elif args.command == "status":
        print(engine.format_status(args.swarm_id))

    elif args.command == "collect":
        result = engine.collect(args.swarm_id, merge_strategy=args.merge)
        if result is None:
            print("Swarm not done yet. Check status first.")
            print(engine.format_status(args.swarm_id))
        else:
            print(result)

    elif args.command == "strategies":
        print("Decomposition Strategies:")
        for s in list_strategies():
            print(f"  {s['name']:25s} {s['description']}")
        print("\nMerge Strategies:")
        for s in list_merge_strategies():
            print(f"  {s['name']:25s} {s['description']}")


if __name__ == "__main__":
    main()
