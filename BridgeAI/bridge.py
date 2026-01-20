#!/usr/bin/env python3
"""
BridgeAI Remote Interface
==========================
Control the Dell PC brain from anywhere.

Usage:
    python bridge.py "Turn on the Samsung TV"
    python bridge.py status
    python bridge.py memory "search query"
"""

import sys
import json
import urllib.request
import urllib.parse

BRAIN_URL = "http://192.168.1.31:5001"
HUB_URL = "http://192.168.1.31:5000"

def think(text: str) -> dict:
    """Send a thought to the brain"""
    data = json.dumps({"text": text}).encode('utf-8')
    req = urllib.request.Request(f"{BRAIN_URL}/think", data=data)
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def status() -> dict:
    """Get brain status"""
    try:
        with urllib.request.urlopen(f"{BRAIN_URL}/status", timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def memory(query: str = None) -> list:
    """Query brain memory"""
    url = f"{BRAIN_URL}/memory"
    if query:
        url += f"?q={urllib.parse.quote(query)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return [{"error": str(e)}]

def hub_status() -> dict:
    """Get hub status"""
    try:
        with urllib.request.urlopen(f"{HUB_URL}/api/health", timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def tv_control(device: str, command: str) -> dict:
    """Control TV directly"""
    url = f"{HUB_URL}/api/{device}/{command}"
    req = urllib.request.Request(url, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

# Quick functions
def samsung(cmd: str) -> dict:
    """Control Samsung TV"""
    return tv_control("samsung", cmd)

def lg(cmd: str) -> dict:
    """Control LG TV"""
    return tv_control("lg", cmd)

def ask(question: str) -> str:
    """Ask the brain a question and get just the response"""
    result = think(question)
    return result.get('response', result.get('error', 'No response'))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("BridgeAI Remote Interface")
        print()
        print("Usage:")
        print("  python bridge.py 'Turn on the TV'")
        print("  python bridge.py status")
        print("  python bridge.py memory [query]")
        print("  python bridge.py samsung power")
        print("  python bridge.py lg vol_up")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == 'status':
        print("Brain Status:")
        print(json.dumps(status(), indent=2))
        print()
        print("Hub Status:")
        print(json.dumps(hub_status(), indent=2))

    elif cmd == 'memory':
        query = sys.argv[2] if len(sys.argv) > 2 else None
        memories = memory(query)
        print(json.dumps(memories, indent=2))

    elif cmd == 'samsung':
        action = sys.argv[2] if len(sys.argv) > 2 else 'status'
        print(json.dumps(samsung(action), indent=2))

    elif cmd == 'lg':
        action = sys.argv[2] if len(sys.argv) > 2 else 'status'
        print(json.dumps(lg(action), indent=2))

    else:
        # Treat as a thought/command for the brain
        full_text = ' '.join(sys.argv[1:])
        result = think(full_text)
        print(f"Response: {result.get('response', 'No response')}")
        if result.get('results'):
            print(f"Actions: {len(result['results'])} executed")
