#!/bin/bash
# Install Ralph to your PATH
# Adds aliases to .bashrc

set -euo pipefail

RALPH_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Ralph..."
echo ""

# Add to .bashrc if not already there
BASHRC="$HOME/.bashrc"
MARKER="# Ralph - The Original Technique"

if grep -q "$MARKER" "$BASHRC" 2>/dev/null; then
    echo "Ralph already installed in .bashrc"
else
    cat >> "$BASHRC" << EOF

$MARKER
export RALPH_HOME="$RALPH_DIR"
alias ralph='$RALPH_DIR/ralph.sh'
alias ralph-init='$RALPH_DIR/ralph-init.sh'
alias ralph-hier='$RALPH_DIR/ralph-hierarchical.sh'
alias ralph-prd='$RALPH_DIR/ralph-prd.sh'
alias ralph-prd-init='$RALPH_DIR/ralph-prd-init.sh'
EOF
    echo "Added Ralph to .bashrc"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Commands available (after restarting shell or running 'source ~/.bashrc'):"
echo "  ralph         - Start Ralph loop (reads PROMPT.md)"
echo "  ralph-init    - Initialize Ralph in current project"
echo "  ralph-hier    - Run hierarchical multi-phase Ralph"
echo ""
echo "Quick start:"
echo "  cd /your/project"
echo "  ralph-init"
echo "  # Edit PROMPT.md with your task"
echo "  ralph"
echo ""
