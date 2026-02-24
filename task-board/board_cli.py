#!/usr/bin/env python3
"""
Task Board CLI — Command-line interface for the unified task board.

Usage:
    board_cli.py dashboard          Show task board summary
    board_cli.py add "title" [-p N] Add a task (priority 1-10)
    board_cli.py done <id> [result] Mark task complete
    board_cli.py fail <id> [error]  Mark task failed
    board_cli.py next               Show next task to work on
    board_cli.py list [--status X]  List tasks
    board_cli.py get <id>           Show task details
    board_cli.py sync               Sync from all sources
    board_cli.py stats              Show statistics
    board_cli.py history <id>       Show task audit trail
    board_cli.py delete <id>        Delete a task
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from board import TaskBoard


def main():
    parser = argparse.ArgumentParser(description="Task Board CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # dashboard
    sub.add_parser("dashboard", help="Show task board summary")

    # add
    p_add = sub.add_parser("add", help="Add a task")
    p_add.add_argument("title", help="Task title")
    p_add.add_argument("-d", "--description", default="")
    p_add.add_argument("-p", "--priority", type=int, default=5)
    p_add.add_argument("--project", default="")
    p_add.add_argument("--agent", default="")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--parent", default=None)

    # done
    p_done = sub.add_parser("done", help="Mark task complete")
    p_done.add_argument("id", help="Task ID")
    p_done.add_argument("result", nargs="?", default="")

    # fail
    p_fail = sub.add_parser("fail", help="Mark task failed")
    p_fail.add_argument("id", help="Task ID")
    p_fail.add_argument("error", nargs="?", default="")

    # next
    sub.add_parser("next", help="Show next task to work on")

    # list
    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--project", default=None)
    p_list.add_argument("--limit", type=int, default=20)

    # get
    p_get = sub.add_parser("get", help="Show task details")
    p_get.add_argument("id", help="Task ID")

    # sync
    sub.add_parser("sync", help="Sync from all sources")

    # stats
    sub.add_parser("stats", help="Show statistics")

    # history
    p_hist = sub.add_parser("history", help="Show task audit trail")
    p_hist.add_argument("id", help="Task ID")

    # delete
    p_del = sub.add_parser("delete", help="Delete a task")
    p_del.add_argument("id", help="Task ID")

    args = parser.parse_args()
    board = TaskBoard()

    if args.command == "dashboard":
        print(board.dashboard())

    elif args.command == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        tid = board.add(
            title=args.title,
            description=args.description,
            priority=args.priority,
            project=args.project,
            agent=args.agent,
            tags=tags,
            parent_task_id=args.parent,
        )
        print(f"Created task [{tid}]: {args.title} (P{args.priority})")

    elif args.command == "done":
        if board.done(args.id, args.result):
            print(f"Task [{args.id}] marked done.")
        else:
            print(f"Task [{args.id}] not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "fail":
        if board.fail(args.id, args.error):
            print(f"Task [{args.id}] marked failed.")
        else:
            print(f"Task [{args.id}] not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "next":
        t = board.next_task()
        if t:
            print(f"[{t['id']}] P{t['priority']} — {t['title']}")
            if t['description']:
                print(f"  {t['description'][:200]}")
        else:
            print("No pending tasks.")

    elif args.command == "list":
        tasks = board.list_tasks(status=args.status, project=args.project, limit=args.limit)
        if not tasks:
            print("No tasks found.")
            return
        for t in tasks:
            status_icon = {"pending": " ", "active": ">", "blocked": "!", "done": "x", "failed": "!!"}.get(t['status'], "?")
            print(f"[{status_icon}] [{t['id']}] P{t['priority']} {t['status']:8s} {t['title']}")

    elif args.command == "get":
        t = board.get(args.id)
        if not t:
            print(f"Task [{args.id}] not found.", file=sys.stderr)
            sys.exit(1)
        print(f"ID:          {t['id']}")
        print(f"Title:       {t['title']}")
        print(f"Status:      {t['status']}")
        print(f"Priority:    {t['priority']}")
        print(f"Project:     {t['project']}")
        print(f"Agent:       {t['agent']}")
        print(f"Source:      {t['source']}")
        print(f"Created:     {t['created_at']}")
        print(f"Updated:     {t['updated_at']}")
        if t['description']:
            print(f"Description: {t['description'][:500]}")
        if t['result']:
            print(f"Result:      {t['result'][:500]}")
        if t['error']:
            print(f"Error:       {t['error'][:500]}")
        blocked = json.loads(t.get('blocked_by', '[]'))
        if blocked:
            print(f"Blocked by:  {', '.join(blocked)}")

    elif args.command == "sync":
        results = board.sync_all()
        total = sum(results.values())
        for source, count in results.items():
            if count:
                print(f"  {source}: +{count} tasks")
        print(f"Synced {total} new task(s).")

    elif args.command == "stats":
        s = board.stats()
        print(f"Total: {s['total']}")
        print(f"  Pending:  {s['pending']}")
        print(f"  Active:   {s['active']}")
        print(f"  Blocked:  {s['blocked']}")
        print(f"  Done:     {s['done']}")
        print(f"  Failed:   {s['failed']}")
        if s['projects']:
            print(f"  Projects: {', '.join(s['projects'])}")

    elif args.command == "history":
        events = board.get_history(args.id)
        if not events:
            print(f"No history for [{args.id}].")
            return
        for e in events:
            print(f"  {e['timestamp'][:19]}  {e['event']:10s}  {e['details'][:80]}")

    elif args.command == "delete":
        if board.delete(args.id):
            print(f"Task [{args.id}] deleted.")
        else:
            print(f"Task [{args.id}] not found.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
