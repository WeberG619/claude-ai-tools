# Test Python connection to Revit MCP Bridge named pipe
# Run with Windows Python

import json
import subprocess
import sys

def test_connection():
    request = {"method": "ping"}
    request_json = json.dumps(request)

    # PowerShell script to send command via named pipe
    ps_script = """
$pipeName = "RevitMCPBridge2026"
$pipe = $null
try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)

    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    $reader = New-Object System.IO.StreamReader($pipe)

    $writer.WriteLine('REQUEST_PLACEHOLDER')
    $response = $reader.ReadLine()
    Write-Output $response
} catch {
    Write-Output ('{"success": false, "error": "' + $_.Exception.Message + '"}')
} finally {
    if ($pipe) { $pipe.Dispose() }
}
""".replace('REQUEST_PLACEHOLDER', request_json.replace("'", "''"))

    print("Running PowerShell command...")
    print("Request: " + request_json)

    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        print("Return code: " + str(result.returncode))
        print("Stdout: " + result.stdout)
        if result.stderr:
            print("Stderr: " + result.stderr)

        if result.stdout.strip():
            response = json.loads(result.stdout.strip())
            print("\nParsed response: " + json.dumps(response, indent=2))
            return response
        else:
            print("No output received")
            return None

    except Exception as e:
        print("Error: " + str(e))
        return None


if __name__ == "__main__":
    print("Testing Revit MCP Bridge connection from Python...")
    print("Python: " + sys.executable)
    print()

    result = test_connection()

    if result and result.get("success"):
        print("\n=== SUCCESS! Bridge is responding from Python ===")
    else:
        print("\n=== FAILED to connect ===")
