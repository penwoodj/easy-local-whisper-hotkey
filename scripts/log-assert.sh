#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${1:-/tmp/whisper_hotkey.log}"
TIMEOUT="${2:-30}"
shift 2
PATTERNS=("$@")

if [ ${#PATTERNS[@]} -eq 0 ]; then
    echo "Usage: $0 <log_file> <timeout_seconds> <pattern1> [pattern2] ..."
    exit 1
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found: $LOG_FILE"
    exit 1
fi

FOUND_PATTERNS=()
START_TIME=$(date +%s)

echo "Waiting for patterns in $LOG_FILE (timeout: ${TIMEOUT}s):"
for pattern in "${PATTERNS[@]}"; do
    echo "  - $pattern"
done

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "Timeout after ${TIMEOUT}s"
        for pattern in "${PATTERNS[@]}"; do
            if ! printf '%s\n' "${FOUND_PATTERNS[@]}" | grep -qF "$pattern"; then
                echo "  NOT FOUND: $pattern"
            fi
        done
        exit 1
    fi

    for pattern in "${PATTERNS[@]}"; do
        if ! printf '%s\n' "${FOUND_PATTERNS[@]}" | grep -qF "$pattern"; then
            if grep -qE "$pattern" "$LOG_FILE"; then
                echo "  ✓ Found: $pattern"
                FOUND_PATTERNS+=("$pattern")
            fi
        fi
    done

    if [ ${#FOUND_PATTERNS[@]} -eq ${#PATTERNS[@]} ]; then
        echo "All patterns found in ${ELAPSED}s"
        exit 0
    fi

    sleep 0.5
done
