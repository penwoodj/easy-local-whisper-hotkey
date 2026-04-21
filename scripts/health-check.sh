#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/tmp/whisper_hotkey.log"
LOCK_FILE="/tmp/whisper_hotkey.lock"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

HEALTHY=true

echo "=== Whisper Hotkey Health Check ==="

if pgrep -f "whisper_hotkey" >/dev/null; then
    echo -e "${GREEN}OK${NC}: Daemon process running"
else
    echo -e "${RED}FAIL${NC}: Daemon process not running"
    HEALTHY=false
fi

if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE")))
    if [ "$LOCK_AGE" -lt 60 ]; then
        echo -e "${GREEN}OK${NC}: Lock file exists and is recent (${LOCK_AGE}s old)"
    else
        echo -e "${RED}FAIL${NC}: Lock file exists but is stale (${LOCK_AGE}s old)"
        HEALTHY=false
    fi
else
    echo -e "${RED}FAIL${NC}: Lock file not found"
    HEALTHY=false
fi

if [ -f "$LOG_FILE" ]; then
    LOG_AGE=$(($(date +%s) - $(stat -c %Y "$LOG_FILE")))
    if [ "$LOG_AGE" -lt 60 ]; then
        echo -e "${GREEN}OK${NC}: Log file exists and is recent (${LOG_AGE}s old)"
    else
        echo -e "${RED}FAIL${NC}: Log file exists but is stale (${LOG_AGE}s old)"
        HEALTHY=false
    fi

    if grep -q "Daemon ready" "$LOG_FILE"; then
        echo -e "${GREEN}OK${NC}: Daemon ready message found in log"
    else
        echo -e "${RED}FAIL${NC}: Daemon ready message not found in log"
        HEALTHY=false
    fi
else
    echo -e "${RED}FAIL${NC}: Log file not found"
    HEALTHY=false
fi

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}=== HEALTHY ===${NC}"
    exit 0
else
    echo -e "${RED}=== UNHEALTHY ===${NC}"
    exit 1
fi
