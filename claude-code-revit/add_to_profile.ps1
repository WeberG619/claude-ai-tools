# Add this to your PowerShell profile to auto-load Claude Code commands
# Run: notepad $PROFILE

# Load Claude Code + Revit integration
$claudeCodeScript = "D:\claude-code-revit\claude_code_integration.ps1"
if (Test-Path $claudeCodeScript) {
    . $claudeCodeScript
}
