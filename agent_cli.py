"""
Simple CLI to interact with Dell Autonomous Agent from any machine
Put this on your main workstation for easy access
"""

import requests
import json
import sys
from datetime import datetime

AGENT_URL = "http://192.168.1.31:5050"


def add_task(query, template="research"):
    """Add a task to the queue"""
    try:
        resp = requests.post(
            f"{AGENT_URL}/api/agent/quick",
            json={"query": query, "template": template},
            timeout=10
        )
        data = resp.json()
        if data.get("success"):
            print(f"Task added: {data['task_id']}")
            print(f"Template: {data['template']}")
            return data['task_id']
        else:
            print(f"Error: {data}")
    except Exception as e:
        print(f"Failed to connect: {e}")
    return None


def get_status():
    """Get agent status"""
    try:
        resp = requests.get(f"{AGENT_URL}/api/agent/status", timeout=5)
        data = resp.json()
        print(f"\nAgent Status: {data['status']}")
        print(f"Queue:")
        for status, count in data['queue'].items():
            print(f"  {status}: {count}")
        print(f"Total tasks: {data['total_tasks']}")
    except Exception as e:
        print(f"Agent offline: {e}")


def list_tasks(status=None, limit=10):
    """List recent tasks"""
    try:
        url = f"{AGENT_URL}/api/agent/tasks?limit={limit}"
        if status:
            url += f"&status={status}"
        resp = requests.get(url, timeout=10)
        tasks = resp.json()['tasks']

        print(f"\n{'ID':<10} {'Status':<12} {'Title':<40} {'Created'}")
        print("-" * 80)
        for t in tasks:
            created = t['created_at'].split()[1][:5] if t['created_at'] else ''
            print(f"{t['id']:<10} {t['status']:<12} {t['title'][:40]:<40} {created}")
    except Exception as e:
        print(f"Failed: {e}")


def show_task(task_id):
    """Show task details and results"""
    try:
        resp = requests.get(f"{AGENT_URL}/api/agent/tasks/{task_id}", timeout=10)
        task = resp.json()

        print(f"\n{'='*60}")
        print(f"Task: {task['id']}")
        print(f"Title: {task['title']}")
        print(f"Status: {task['status']}")
        print(f"Created: {task['created_at']}")
        print(f"{'='*60}")

        if task.get('output_data'):
            print("\nRESULT:")
            print(json.dumps(task['output_data'], indent=2))
        elif task.get('error_message'):
            print(f"\nERROR: {task['error_message']}")
        else:
            print("\n(No output yet)")
    except Exception as e:
        print(f"Failed: {e}")


def main():
    if len(sys.argv) < 2:
        print("""
Dell Autonomous Agent CLI

Usage:
  python agent_cli.py status              - Check agent status
  python agent_cli.py add "your query"    - Add research task
  python agent_cli.py leads "query"       - Add lead generation task
  python agent_cli.py list                - List recent tasks
  python agent_cli.py list completed      - List completed tasks
  python agent_cli.py show <task_id>      - Show task result

Examples:
  python agent_cli.py add "Research hurricane-resistant roofing materials"
  python agent_cli.py leads "Architecture firms hiring in Miami"
  python agent_cli.py show abc123
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        get_status()

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: agent_cli.py add \"your query\"")
            return
        add_task(" ".join(sys.argv[2:]), "research")

    elif cmd == "leads":
        if len(sys.argv) < 3:
            print("Usage: agent_cli.py leads \"your query\"")
            return
        add_task(" ".join(sys.argv[2:]), "leads")

    elif cmd == "analyze":
        if len(sys.argv) < 3:
            print("Usage: agent_cli.py analyze \"your query\"")
            return
        add_task(" ".join(sys.argv[2:]), "analyze")

    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        list_tasks(status)

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: agent_cli.py show <task_id>")
            return
        show_task(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
