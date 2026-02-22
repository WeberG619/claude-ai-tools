"""
Scheduled Task Feeder for Autonomous Agent
Runs daily/weekly tasks automatically
"""

import requests
import json
from datetime import datetime
import time

AGENT_API = "http://localhost:5050/api/agent/quick"

# Define recurring research tasks
DAILY_TASKS = [
    {
        "query": "Latest architecture and design news today - summarize top 5 stories",
        "template": "research"
    },
    {
        "query": "New construction permits filed in Miami-Dade County Florida this week",
        "template": "leads"
    }
]

WEEKLY_TASKS = [
    {
        "query": "Research trending residential architecture designs 2026 - modern, sustainable, hurricane-resistant",
        "template": "research"
    },
    {
        "query": "Find new commercial development projects announced in South Florida needing architects",
        "template": "leads"
    },
    {
        "query": "Summarize updates to Florida Building Code and local ordinances affecting residential construction",
        "template": "research"
    },
    {
        "query": "Research new building materials and technologies for hurricane-resistant construction",
        "template": "research"
    },
    {
        "query": "Analyze competitor architecture firms - new projects, awards, marketing strategies",
        "template": "analyze"
    }
]

MONTHLY_TASKS = [
    {
        "query": "Comprehensive market analysis: South Florida residential architecture market trends, pricing, demand",
        "template": "analyze"
    },
    {
        "query": "Research grant opportunities and incentives for sustainable building design in Florida",
        "template": "research"
    },
    {
        "query": "Generate 4 blog post ideas about architecture, home design, and Florida living",
        "template": "research"
    }
]


def add_task(task_data):
    """Add a task to the agent queue"""
    try:
        response = requests.post(AGENT_API, json=task_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"  Added: {task_data['query'][:50]}... -> {result.get('task_id')}")
            return result.get('task_id')
        else:
            print(f"  Error: {response.status_code}")
    except Exception as e:
        print(f"  Failed: {e}")
    return None


def run_daily():
    """Run daily tasks"""
    print(f"\n[{datetime.now()}] Running DAILY tasks...")
    for task in DAILY_TASKS:
        add_task(task)
        time.sleep(1)


def run_weekly():
    """Run weekly tasks (on Monday)"""
    if datetime.now().weekday() == 0:  # Monday
        print(f"\n[{datetime.now()}] Running WEEKLY tasks...")
        for task in WEEKLY_TASKS:
            add_task(task)
            time.sleep(1)


def run_monthly():
    """Run monthly tasks (on 1st of month)"""
    if datetime.now().day == 1:
        print(f"\n[{datetime.now()}] Running MONTHLY tasks...")
        for task in MONTHLY_TASKS:
            add_task(task)
            time.sleep(1)


def main():
    """Main scheduler loop"""
    print("=" * 50)
    print("  Autonomous Agent - Task Scheduler")
    print("=" * 50)
    print(f"Daily tasks: {len(DAILY_TASKS)}")
    print(f"Weekly tasks: {len(WEEKLY_TASKS)}")
    print(f"Monthly tasks: {len(MONTHLY_TASKS)}")
    print()

    last_daily = None

    while True:
        today = datetime.now().date()

        # Run daily tasks once per day
        if last_daily != today:
            run_daily()
            run_weekly()
            run_monthly()
            last_daily = today
            print(f"\nNext run: tomorrow. Sleeping...")

        # Sleep for 1 hour, then check again
        time.sleep(3600)


if __name__ == "__main__":
    main()
