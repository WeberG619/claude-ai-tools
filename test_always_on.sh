#!/bin/bash
# ============================================
# ALWAYS-ON SMOKE TEST
# ============================================
# Verifies all components of the always-on system.
# Run after start_always_on.sh to confirm everything works.
# ============================================

set -euo pipefail

TOOLS_DIR="/mnt/d/_CLAUDE-TOOLS"
PID_DIR="$TOOLS_DIR/gateway/pids"
PASS=0
FAIL=0
WARN=0

# Load environment
if [ -f "$TOOLS_DIR/.env" ]; then
    set -a
    source "$TOOLS_DIR/.env"
    set +a
fi

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

check_process() {
    local name=$1
    local pidfile="$PID_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            pass "$name running (PID $pid)"
            return 0
        fi
    fi
    fail "$name not running"
    return 1
}

echo "============================================"
echo "ALWAYS-ON SYSTEM SMOKE TEST"
echo "$(date)"
echo "============================================"
echo ""

# ── Test 1: Process Checks ──
echo "--- 1. Process Checks ---"
check_process "gateway-hub" || true
check_process "telegram-bot" || true
check_process "proactive" || true
check_process "email-watcher" || true
check_process "autonomous-agent" || true
check_process "opportunityengine" || true
echo ""

# ── Test 2: Telegram Connectivity ──
echo "--- 2. Telegram Connectivity ---"
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=Smoke test: Always-On system verification at $(date '+%H:%M:%S')" \
        2>/dev/null)
    if echo "$RESPONSE" | grep -q '"ok":true'; then
        pass "Telegram message sent"
    else
        fail "Telegram send failed: $RESPONSE"
    fi
else
    fail "Telegram credentials not set"
fi
echo ""

# ── Test 3: OpportunityEngine Database ──
echo "--- 3. OpportunityEngine Database ---"
OE_DB="$TOOLS_DIR/opportunityengine/pipeline.db"
if [ -f "$OE_DB" ]; then
    OPP_COUNT=$(sqlite3 "$OE_DB" "SELECT COUNT(*) FROM opportunities;" 2>/dev/null || echo "0")
    PROP_COUNT=$(sqlite3 "$OE_DB" "SELECT COUNT(*) FROM proposals;" 2>/dev/null || echo "0")
    pass "OE database exists (${OPP_COUNT} opportunities, ${PROP_COUNT} proposals)"
else
    warn "OE database not found (will be created on first scan)"
fi
echo ""

# ── Test 4: Autonomous Agent Queue ──
echo "--- 4. Autonomous Agent Queue ---"
QUEUE_DB="$TOOLS_DIR/autonomous-agent/queues/tasks.db"
if [ -f "$QUEUE_DB" ]; then
    PENDING=$(sqlite3 "$QUEUE_DB" "SELECT COUNT(*) FROM tasks WHERE status = 'pending';" 2>/dev/null || echo "0")
    pass "Agent queue exists (${PENDING} pending tasks)"
else
    warn "Agent queue not found (will be created on first task)"
fi
echo ""

# ── Test 5: Intelligence Report ──
echo "--- 5. Intelligence Report ---"
INTEL_OUTPUT=$(cd "$TOOLS_DIR/proactive" && python3 -c "
from intelligence_report import generate_intelligence_report
report = generate_intelligence_report()
print(f'Generated {len(report)} chars')
print(report[:200])
" 2>/dev/null || echo "FAILED")

if echo "$INTEL_OUTPUT" | grep -q "Generated"; then
    pass "Intelligence report generates successfully"
else
    fail "Intelligence report failed: $INTEL_OUTPUT"
fi
echo ""

# ── Test 6: Dynamic Agents File ──
echo "--- 6. Agent Factory ---"
DYNAMIC_FILE="$TOOLS_DIR/autonomous-agent/dynamic_agents.json"
if [ -f "$DYNAMIC_FILE" ]; then
    AGENT_COUNT=$(python3 -c "import json; print(len(json.load(open('$DYNAMIC_FILE'))))" 2>/dev/null || echo "0")
    pass "Dynamic agents file exists ($AGENT_COUNT agents)"
else
    pass "Dynamic agents file will be created when first agent is designed"
fi
echo ""

# ── Test 7: Environment Variables ──
echo "--- 7. Environment ---"
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] && pass "TELEGRAM_BOT_TOKEN set" || fail "TELEGRAM_BOT_TOKEN missing"
[ -n "${TELEGRAM_CHAT_ID:-}" ] && pass "TELEGRAM_CHAT_ID set" || fail "TELEGRAM_CHAT_ID missing"
[ -n "${ANTHROPIC_API_KEY:-}" ] && pass "ANTHROPIC_API_KEY set" || fail "ANTHROPIC_API_KEY missing"
echo ""

# ── Summary ──
echo "============================================"
echo "RESULTS: $PASS passed, $FAIL failed, $WARN warnings"
echo "============================================"

if [ $FAIL -gt 0 ]; then
    echo "Some tests failed. Fix issues and re-run."
    exit 1
else
    echo "All critical tests passed!"
    exit 0
fi
