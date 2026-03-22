#!/bin/bash
# Run the job finder if it hasn't run yet today.
# Called by cron at 7am AND by launchd on wake/login.

PROJECT_DIR="/Users/foxy/Desktop/Development/Jamal"
LOCK_FILE="${PROJECT_DIR}/data/.last_run_date"
TODAY=$(date +%Y-%m-%d)

# Check if already ran today
if [ -f "$LOCK_FILE" ] && [ "$(cat "$LOCK_FILE")" = "$TODAY" ]; then
    echo "$(date): Already ran today, skipping." >> "${PROJECT_DIR}/data/cron.log"
    exit 0
fi

# Mark as running today (do this first to prevent double runs)
echo "$TODAY" > "$LOCK_FILE"

echo "$(date): Starting daily job finder run." >> "${PROJECT_DIR}/data/cron.log"
cd "$PROJECT_DIR"
caffeinate -i "${PROJECT_DIR}/.venv/bin/python3" "${PROJECT_DIR}/main.py" >> "${PROJECT_DIR}/data/cron.log" 2>&1
echo "$(date): Run complete." >> "${PROJECT_DIR}/data/cron.log"
