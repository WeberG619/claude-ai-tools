#!/usr/bin/env python3
"""Launch OBS Studio from WSL with correct working directory."""
import subprocess
import sys
import time

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


def launch_obs():
    """Launch OBS via PowerShell with proper working directory."""
    ps_cmd = (
        "Start-Process "
        "'C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe' "
        "-WorkingDirectory 'C:\\Program Files\\obs-studio\\bin\\64bit'"
    )
    _run_ps(ps_cmd, timeout=10)

    # Wait for OBS to load and WebSocket to be ready
    for i in range(20):
        time.sleep(1)
        try:
            import obsws_python as obs
            # Get WSL2 host IP
            host = "localhost"
            try:
                with open("/etc/resolv.conf") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            host = line.split()[1]
                            break
            except Exception:
                pass

            cl = obs.ReqClient(host=host, port=4455, password="2GwO1bvUqSIy3V2X", timeout=3)
            scene = cl.get_current_program_scene()
            print(f"OBS ready! Scene: {scene.current_program_scene_name}")
            cl.disconnect()
            return True
        except Exception:
            pass

    print("OBS launched but WebSocket not responding after 20s")
    return False


if __name__ == "__main__":
    launch_obs()
