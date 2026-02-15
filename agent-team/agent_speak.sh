#!/bin/bash
# Agent Speak - Updates visual monitor AND plays voice
# Usage: ./agent_speak.sh <agent> "<message>"
# Agents: planner, researcher, builder, critic, narrator

AGENT=$1
MESSAGE=$2

# Map agent to role and voice
case $AGENT in
    planner)    ROLE="PLANNER"; VOICE="andrew" ;;
    researcher) ROLE="RESEARCHER"; VOICE="guy" ;;
    builder)    ROLE="BUILDER"; VOICE="christopher" ;;
    critic)     ROLE="CRITIC"; VOICE="eric" ;;
    narrator)   ROLE="NARRATOR"; VOICE="jenny" ;;
    *)          echo "Unknown agent: $AGENT"; exit 1 ;;
esac

# Set speaking status
echo "{\"agent\": \"$AGENT\", \"role\": \"$ROLE\", \"voice\": \"$VOICE\", \"status\": \"speaking\", \"timestamp\": \"$(date -Iseconds)\"}" > /tmp/agent_speech_status.json

# Speak
python3 /mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py "$MESSAGE" "$VOICE"

# Reset status (full reset with nulls)
echo '{"agent": null, "role": null, "voice": null, "status": "idle", "timestamp": "'$(date -Iseconds)'"}' > /tmp/agent_speech_status.json
