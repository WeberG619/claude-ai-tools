#!/usr/bin/env python3
"""Test script to cycle through all dashboard view types."""

import json
import time
from pathlib import Path

STATUS_FILE = Path(r"D:\_CLAUDE-TOOLS\agent-team\agent_status.json")

def write_status(activity_type: str, **kwargs):
    """Write a status update to the file."""
    status = {
        "agent": "narrator",
        "speaking": False,
        "text": f"Testing {activity_type}",
        "timestamp": time.time(),
        "activity": {
            "type": activity_type,
            **kwargs
        }
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))
    print(f"[{time.strftime('%H:%M:%S')}] Wrote: {activity_type}")

def main():
    print("Dashboard View Test - cycling through all activity types")
    print("Watch the dashboard for changes...")
    print("-" * 50)

    # Test 1: Terminal view
    print("\n1. Testing TERMINAL view...")
    write_status(
        "terminal_run",
        command="python --version",
        output="Python 3.11.5\nInstalled packages:\n- numpy 1.24.0\n- pandas 2.0.0"
    )
    time.sleep(5)

    # Test 2: Code view
    print("\n2. Testing CODE view...")
    write_status(
        "code_write",
        file_path="/mnt/d/project/example.py",
        content='''#!/usr/bin/env python3
"""Example code for testing the dashboard code view."""

def hello_world():
    """Print hello world."""
    print("Hello from the Agent Team!")

if __name__ == "__main__":
    hello_world()
''',
        language="python"
    )
    time.sleep(5)

    # Test 3: Browser view
    print("\n3. Testing BROWSER view...")
    write_status(
        "browser_navigate",
        url="https://docs.python.org/3/",
        title="Python Documentation"
    )
    time.sleep(5)

    # Test 4: Back to terminal
    print("\n4. Testing TERMINAL view again...")
    write_status(
        "terminal_run",
        command="git status",
        output="On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean"
    )
    time.sleep(5)

    # Test 5: Code view with different language
    print("\n5. Testing CODE view (JavaScript)...")
    write_status(
        "code_write",
        file_path="/mnt/d/project/app.js",
        content='''// React component example
import React from 'react';

function App() {
    const [count, setCount] = useState(0);

    return (
        <div className="app">
            <h1>Counter: {count}</h1>
            <button onClick={() => setCount(c => c + 1)}>
                Increment
            </button>
        </div>
    );
}

export default App;
''',
        language="javascript"
    )
    time.sleep(5)

    print("\n" + "=" * 50)
    print("Test complete! Did you see all views change?")
    print("- Terminal (green command/output)")
    print("- Code (syntax highlighted Python)")
    print("- Browser (Python docs)")
    print("- Terminal (git status)")
    print("- Code (JavaScript/React)")

if __name__ == "__main__":
    main()
