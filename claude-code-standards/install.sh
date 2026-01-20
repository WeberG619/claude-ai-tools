#!/bin/bash
# Claude Code Standards Installation Script

set -e  # Exit on error

echo "🚀 Installing Claude Code Standards System..."
echo ""

# Check if running from correct directory
if [ ! -f "README.md" ] || [ ! -d ".claude" ]; then
    echo "❌ Error: Please run this script from the claude-code-standards directory"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ~/.claude/hooks
mkdir -p ~/.claude/logs
mkdir -p ~/.claude/backup

# Backup existing settings if they exist
if [ -f ~/.claude/settings.json ]; then
    echo "📦 Backing up existing settings..."
    cp ~/.claude/settings.json ~/.claude/backup/settings.json.$(date +%Y%m%d%H%M%S)
fi

# Copy hook scripts
echo "📝 Installing hook scripts..."
cp .claude/hooks/*.py ~/.claude/hooks/
cp .claude/hooks/*.sh ~/.claude/hooks/

# Make scripts executable
echo "🔧 Setting permissions..."
chmod +x ~/.claude/hooks/*.py
chmod +x ~/.claude/hooks/*.sh

# Install or update settings.json
if [ -f ~/.claude/settings.json ]; then
    echo "⚠️  Existing settings.json found!"
    echo "   Current settings backed up to ~/.claude/backup/"
    read -p "   Replace with new settings? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .claude/settings.json ~/.claude/settings.json
        echo "✅ Settings updated"
    else
        echo "ℹ️  Keeping existing settings"
    fi
else
    cp .claude/settings.json ~/.claude/settings.json
    echo "✅ Settings installed"
fi

# Check for dependencies
echo ""
echo "🔍 Checking dependencies..."

# Check for Python 3
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found: $(python3 --version)"
else
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check for jq (used in bash hooks)
if command -v jq &> /dev/null; then
    echo "✅ jq found: $(jq --version)"
else
    echo "⚠️  jq not found. Install with:"
    echo "   Ubuntu/Debian: sudo apt-get install jq"
    echo "   macOS: brew install jq"
    echo "   The bash logging hook requires jq to parse JSON"
fi

# Test hook execution
echo ""
echo "🧪 Testing hooks..."

# Test bash validation
TEST_OUTPUT=$(echo '{"tool_name":"Bash","tool_input":{"command":"echo test"},"session_id":"test"}' | python3 ~/.claude/hooks/validate-bash.py 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ Bash validation hook works"
else
    echo "❌ Bash validation hook failed: $TEST_OUTPUT"
fi

# Test file validation
TEST_OUTPUT=$(echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.txt"},"session_id":"test"}' | python3 ~/.claude/hooks/validate-file-ops.py 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ File validation hook works"
else
    echo "❌ File validation hook failed: $TEST_OUTPUT"
fi

# Create reference card
echo ""
echo "📋 Creating quick reference..."
cat > ~/.claude/quick-reference.txt << 'EOF'
CLAUDE CODE STANDARDS QUICK REFERENCE

Blocked Commands:
- grep → use 'rg' instead
- find → use Glob tool instead
- cat/head/tail → use Read tool instead
- rm -rf / → extremely dangerous
- sudo rm → requires approval

Protected Paths:
- ~/.ssh/ - SSH configuration
- ~/.aws/ - AWS credentials
- /etc/ - System configuration
- /sys/ - System files

Logs Location:
- ~/.claude/logs/tool-usage.log - All tools
- ~/.claude/logs/bash-history.log - Bash commands
- ~/.claude/logs/file-changes.log - File operations

Disable Hooks:
export CLAUDE_HOOKS_DISABLED=1

View Logs:
tail -f ~/.claude/logs/tool-usage.log
EOF

echo ""
echo "✅ Installation complete!"
echo ""
echo "📚 Documentation is in: $(pwd)"
echo "🪝 Hooks installed in: ~/.claude/hooks/"
echo "📊 Logs will be in: ~/.claude/logs/"
echo "📋 Quick reference: ~/.claude/quick-reference.txt"
echo ""
echo "🎯 Next steps:"
echo "1. Review the documentation in each folder"
echo "2. Customize hooks in ~/.claude/hooks/ as needed"
echo "3. Monitor logs in ~/.claude/logs/"
echo ""
echo "Run 'cat ~/.claude/quick-reference.txt' for a quick reference guide"