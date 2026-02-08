#!/bin/bash
# process-inbox.sh
# Reads files from inbox, calls Claude to extract atomic facts,
# writes to facts/ and daily log, moves processed files.
set -euo pipefail

PARA_DIR="{{PARA_ROOT}}"
INBOX_DIR="$PARA_DIR/memory/inbox"
PROCESSED_DIR="$INBOX_DIR/processed"
FACTS_DIR="$PARA_DIR/memory/facts"
DAILY_DIR="$PARA_DIR/memory/daily"
LOG_FILE="$PARA_DIR/logs/process-inbox.log"
MAX_CONTEXT_BYTES=51200  # ~50KB truncation limit
MAX_FILES_PER_BATCH=20
CLAUDE_BIN="{{CLAUDE_BIN}}"
LOCK_DIR="/tmp/process-inbox.lock.d"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# -- Active hours guard --
HOUR=$(date +%H)
if [[ $HOUR -lt {{ACTIVE_HOUR_START}} || $HOUR -ge {{ACTIVE_HOUR_END}} ]]; then
  log "Outside active hours — skipping"
  exit 0
fi

# -- Acquire lock (mkdir is atomic on macOS) --
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log "Another instance is running — skipping"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

# -- Ensure directories exist --
mkdir -p "$INBOX_DIR" "$PROCESSED_DIR" "$FACTS_DIR" "$DAILY_DIR" "$(dirname "$LOG_FILE")"

# -- Find inbox files (exclude processed/ subdirectory) --
INBOX_FILES=()
while IFS= read -r -d '' f; do
  INBOX_FILES+=("$f")
done < <(find "$INBOX_DIR" -maxdepth 1 -name '*.md' -print0 2>/dev/null | sort -z)

if [[ ${#INBOX_FILES[@]} -eq 0 ]]; then
  log "No inbox items — skipping"
  exit 0
fi

log "Found ${#INBOX_FILES[@]} inbox file(s) to process"

# -- Gather existing fact titles for dedup --
EXISTING_FACTS=""
if compgen -G "$FACTS_DIR/*.md" > /dev/null 2>&1; then
  EXISTING_FACTS=$(grep -h '^# Fact:' "$FACTS_DIR"/*.md 2>/dev/null | sed 's/^# Fact: //' || true)
fi

FACT_COUNT=$(echo "$EXISTING_FACTS" | grep -c . 2>/dev/null || echo "0")
log "Found $FACT_COUNT existing facts for dedup"

# -- Process in batches if needed --
process_batch() {
  local batch_files=("$@")
  local CONCATENATED=""

  for f in "${batch_files[@]}"; do
    CONCATENATED+="
--- FILE: $(basename "$f") ---
$(cat "$f")
"
  done

  # Truncate to ~50KB
  if [[ ${#CONCATENATED} -gt $MAX_CONTEXT_BYTES ]]; then
    CONCATENATED="${CONCATENATED:0:$MAX_CONTEXT_BYTES}

[... truncated at ${MAX_CONTEXT_BYTES} bytes ...]"
    log "Batch content truncated to ${MAX_CONTEXT_BYTES} bytes"
  fi

  TODAY=$(date '+%Y-%m-%d')

  PROMPT="You are a knowledge extraction assistant for a PARA personal knowledge system.

Below are meeting notes from Granola. Extract atomic facts following these rules:
- Decisions made (concrete outcomes that affect future work)
- People & relationships (context about who, their roles, preferences)
- Commitments & follow-ups (things promised, deadlines)
- Skip small talk, logistics, obvious context
- Only extract genuinely useful, reusable knowledge

EXISTING FACTS (do NOT duplicate these):
${EXISTING_FACTS:-<none yet>}

RULES:
1. Each fact file: {{PARA_ROOT}}/memory/facts/fact-<slug>.md using EXACTLY this template:

\`\`\`
# Fact: [Clear, unique title]

**Created**: $TODAY
**Last Accessed**:
**Superseded By**:
**Tags**: #tag1 #tag2 #project/slug-name

**Content**: [precise fact/decision/preference]

**Source**: From Granola meeting \"[meeting title]\" on [meeting date]
\`\`\`

2. PROJECT TAGGING: Always include a \`#project/slug-name\` tag identifying which client or initiative the fact belongs to (e.g. \`#project/metal-conversions\`, \`#project/heartland-vc\`). Use kebab-case. If a fact spans multiple projects, include multiple project tags.

3. Append to {{PARA_ROOT}}/memory/daily/$TODAY.md (create if needed) with sections:
   ## Summary, ## Key Decisions, ## New Facts Extracted, ## Reflections
   If the file already has content, append under the existing sections or add new entries.

4. NEW PROJECT CANDIDATES: In the daily log under ## Reflections, note any meetings that may represent a new project not yet tracked — e.g. \"New project candidate: Metal Conversions Freight Migration (freight quoting system rebuild for Metal Conversions)\". Only surface genuinely new initiatives, not one-off calls.

5. If nothing is worth remembering, output only: No new facts to extract.
6. Do NOT create facts that duplicate the existing facts listed above.

MEETING DATA:
$CONCATENATED"

  if ! echo "$PROMPT" | "$CLAUDE_BIN" -p \
    --model opus \
    --allowedTools "Write,Read,Edit,Glob,Grep" \
    --permission-mode bypassPermissions \
    --no-session-persistence \
    2>> "$LOG_FILE"; then
    log "ERROR: Claude call failed for batch"
    return 1
  fi

  # Move processed files only after Claude succeeds
  for f in "${batch_files[@]}"; do
    mv "$f" "$PROCESSED_DIR/"
    log "Processed: $(basename "$f")"
  done

  return 0
}

# -- Split into batches and process --
BATCH=()
for f in "${INBOX_FILES[@]}"; do
  BATCH+=("$f")
  if [[ ${#BATCH[@]} -ge $MAX_FILES_PER_BATCH ]]; then
    process_batch "${BATCH[@]}" || log "Batch processing failed — remaining files left in inbox"
    BATCH=()
  fi
done

# Process remaining files
if [[ ${#BATCH[@]} -gt 0 ]]; then
  process_batch "${BATCH[@]}" || log "Batch processing failed — files left in inbox"
fi

log "Inbox processing complete"
