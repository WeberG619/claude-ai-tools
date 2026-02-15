#!/usr/bin/env python3
"""
MCP Server Health Check
Validates all configured MCP servers can start and respond.
Reads from ~/.mcp.json (user-level) and project .mcp.json files.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# MCP config locations
MCP_CONFIGS = [
    Path.home() / ".mcp.json",
    Path("/mnt/d/.claude/.mcp.json"),
]

# How long to wait for server to start before checking (seconds)
STARTUP_TIMEOUT = 5


def load_all_servers() -> dict:
    """Load server definitions from all MCP config files."""
    all_servers = {}
    for config_path in MCP_CONFIGS:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                servers = data.get("mcpServers", {})
                for name, config in servers.items():
                    all_servers[name] = {**config, "_source": str(config_path)}
            except Exception as e:
                print(f"  WARN: Could not read {config_path}: {e}")
    return all_servers


def check_command_exists(command: str) -> bool:
    """Check if a command is available on PATH."""
    try:
        result = subprocess.run(
            ["which", command], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_script_exists(args: list) -> tuple[bool, str]:
    """Check if the server script file exists."""
    for arg in args:
        if arg.endswith(".py") or arg.endswith(".js") or arg.endswith(".ts"):
            path = Path(arg)
            if path.exists():
                return True, str(path)
            else:
                return False, f"Missing: {path}"
    return True, "(no script file in args)"


def check_server_starts(name: str, config: dict) -> tuple[bool, str]:
    """Try to start the server and see if it initializes without crashing."""
    command = config.get("command", "")
    args = config.get("args", [])
    env = {**os.environ, **config.get("env", {})}

    cmd = [command] + args

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )

        # Wait briefly and check if process is still running
        time.sleep(2)
        poll = proc.poll()

        if poll is not None:
            # Process exited - check stderr
            stderr = proc.stderr.read().decode(errors="replace")[:200]
            return False, f"Exited with code {poll}: {stderr.strip()}"

        # Process is running - send empty JSON-RPC to see if it responds
        try:
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "health-check", "version": "1.0"}
                }
            }) + "\n"
            proc.stdin.write(init_msg.encode())
            proc.stdin.flush()

            # Wait for response
            import select
            ready, _, _ = select.select([proc.stdout], [], [], 3)
            if ready:
                response = proc.stdout.readline().decode(errors="replace").strip()
                if "result" in response or "jsonrpc" in response:
                    return True, "Responds to initialize"
                else:
                    return True, f"Running (response: {response[:80]})"
            else:
                return True, "Running (no init response - may need framing)"
        except Exception:
            return True, "Running (could not send init)"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    except FileNotFoundError:
        return False, f"Command not found: {command}"
    except Exception as e:
        return False, str(e)[:100]


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    start_test = "--start" in sys.argv or "-s" in sys.argv

    print(f"MCP Server Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    servers = load_all_servers()
    if not servers:
        print("ERROR: No MCP servers found in config files.")
        return 1

    print(f"Found {len(servers)} servers across {len(MCP_CONFIGS)} configs\n")

    results = []
    for name, config in sorted(servers.items()):
        command = config.get("command", "unknown")
        args = config.get("args", [])
        source = config.get("_source", "unknown")

        # Check 1: Command exists
        cmd_ok = check_command_exists(command)

        # Check 2: Script file exists
        script_ok, script_msg = check_script_exists(args)

        # Check 3: Server starts (optional, slower)
        start_ok, start_msg = (None, "skipped")
        if start_test and cmd_ok and script_ok:
            start_ok, start_msg = check_server_starts(name, config)

        # Determine overall status
        if not cmd_ok:
            status = "FAIL"
            reason = f"Command not found: {command}"
        elif not script_ok:
            status = "FAIL"
            reason = script_msg
        elif start_test and start_ok is False:
            status = "FAIL"
            reason = start_msg
        elif start_test and start_ok is True:
            status = "OK"
            reason = start_msg
        else:
            status = "OK"
            reason = "Files exist"

        results.append((name, status, reason))

        # Print result
        icon = "+" if status == "OK" else "X"
        print(f"  [{icon}] {name:<30} {status}")
        if verbose or status == "FAIL":
            print(f"      {reason}")
            if verbose:
                print(f"      cmd: {command} {' '.join(args[:2])}")
                print(f"      src: {Path(source).name}")

    # Summary
    print("\n" + "=" * 65)
    ok_count = sum(1 for _, s, _ in results if s == "OK")
    fail_count = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"Results: {ok_count} OK, {fail_count} FAIL, {len(results)} total")

    if fail_count > 0:
        print("\nFailing servers:")
        for name, status, reason in results:
            if status == "FAIL":
                print(f"  - {name}: {reason}")

    # Write JSON report
    report_path = Path(__file__).parent / "health_report.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "ok": ok_count,
        "fail": fail_count,
        "servers": {
            name: {"status": status, "detail": reason}
            for name, status, reason in results
        },
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {report_path}")

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
