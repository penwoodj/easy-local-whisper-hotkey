#!/usr/bin/env bash
set -euo pipefail

PID="${1:-}"
DURATION="${2:-60}"
INTERVAL="${3:-2}"
MEM_THRESHOLD_MB="${4:-50}"
CPU_THRESHOLD_PCT="${5:-80}"
CPU_SAMPLES="${6:-10}"

echo "=== Resource Guard ==="
echo "Duration: ${DURATION}s"
echo "Interval: ${INTERVAL}s"
echo "Memory threshold: +${MEM_THRESHOLD_MB}MB over baseline"
echo "CPU threshold: ${CPU_THRESHOLD_PCT}% sustained for ${CPU_SAMPLES} samples"

if [ -z "$PID" ]; then
    PID=$(pgrep -f "whisper_hotkey" | head -1 || true)
    if [ -z "$PID" ]; then
        echo "Error: No PID specified and whisper_hotkey not running"
        exit 1
    fi
    echo "Auto-detected PID: $PID"
fi

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Error: PID $PID not running"
    exit 1
fi

BASELINE_RSS=$(ps -o rss= -p "$PID" | awk '{print int($1/1024)}')
echo "Baseline RSS: ${BASELINE_RSS}MB"

CPU_HIGH_COUNT=0
ALERTED=false

END_TIME=$(($(date +%s) + DURATION))

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_RSS=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{print int($1/1024)}' || echo 0)
    RSS_DIFF=$((CURRENT_RSS - BASELINE_RSS))

    CPU_PCT=$(ps -o %cpu= -p "$PID" 2>/dev/null | awk '{print int($1)}' || echo 0)

    if [ "$RSS_DIFF" -gt "$MEM_THRESHOLD_MB" ]; then
        echo "ALERT: Memory growth detected: ${RSS_DIFF}MB over baseline (current: ${CURRENT_RSS}MB)"
        ALERTED=true
    fi

    if [ "$CPU_PCT" -gt "$CPU_THRESHOLD_PCT" ]; then
        CPU_HIGH_COUNT=$((CPU_HIGH_COUNT + 1))
        echo "CPU high: ${CPU_PCT}% (${CPU_HIGH_COUNT}/${CPU_SAMPLES})"
    else
        CPU_HIGH_COUNT=0
    fi

    if [ "$CPU_HIGH_COUNT" -ge "$CPU_SAMPLES" ]; then
        echo "ALERT: Sustained high CPU usage detected (${CPU_PCT}% for ${CPU_SAMPLES} samples)"
        ALERTED=true
        CPU_HIGH_COUNT=0
    fi

    sleep "$INTERVAL"
done

if [ "$ALERTED" = true ]; then
    echo "Resource guard finished with alerts"
    exit 1
else
    echo "Resource guard finished: no alerts"
    exit 0
fi
