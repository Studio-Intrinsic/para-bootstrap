#!/bin/bash
# claude-para-pipeline.sh
# Orchestrates the full PARA memory pipeline:
#   1. Granola collector -> inbox/
#   2. Session reflector -> facts/ + daily/
#   3. Inbox processor -> facts/ + daily/
# Each step is fault-tolerant — one failure doesn't block the others.
set -euo pipefail

LOG_FILE="{{PARA_ROOT}}/logs/para-pipeline.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# -- Active hours guard --
HOUR=$(date +%H)
if [[ $HOUR -lt {{ACTIVE_HOUR_START}} || $HOUR -ge {{ACTIVE_HOUR_END}} ]]; then
  log "Outside active hours — skipping"
  exit 0
fi

log "=== Pipeline start ==="

{{#ENABLE_GRANOLA}}
# Step 1: Collect from Granola
log "Running Granola collector..."
python3 "{{BIN_DIR}}/granola-collector.py" 2>> "$LOG_FILE" || log "Granola collector failed (continuing)"
{{/ENABLE_GRANOLA}}

# Step 2: Session reflector
log "Running session reflector..."
"{{BIN_DIR}}/claude-para-reflection.sh" 2>> "$LOG_FILE" || log "Session reflector failed (continuing)"

# Step 3: Process inbox
log "Running inbox processor..."
"{{BIN_DIR}}/process-inbox.sh" 2>> "$LOG_FILE" || log "Inbox processor failed (continuing)"

log "=== Pipeline complete ==="
