#!/bin/bash
# claude-para-reflection.sh
# Hourly session reflector: reads Claude Code transcripts, extracts new facts,
# deduplicates against existing facts, writes atomic facts + daily log.
# Designed for unattended execution via launchd.
set -euo pipefail

PARA_DIR="{{PARA_ROOT}}"
STATE_FILE="$PARA_DIR/.last-reflection"
FACTS_DIR="$PARA_DIR/memory/facts"
DAILY_DIR="$PARA_DIR/memory/daily"
SESSIONS_DIR="$HOME/.claude/projects"
LOG_FILE="$PARA_DIR/logs/claude-reflection.log"
MAX_CONTEXT_BYTES=51200  # ~50KB truncation limit
CLAUDE_BIN="{{CLAUDE_BIN}}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# -- Active hours guard --
HOUR=$(date +%H)
if [[ $HOUR -lt {{ACTIVE_HOUR_START}} || $HOUR -ge {{ACTIVE_HOUR_END}} ]]; then
  log "Outside active hours — skipping"
  exit 0
fi

# -- Ensure directories exist --
mkdir -p "$FACTS_DIR" "$DAILY_DIR" "$(dirname "$LOG_FILE")"

# -- Determine cutoff time --
if [[ -f "$STATE_FILE" ]]; then
  CUTOFF=$(cat "$STATE_FILE")
  log "Resuming from last run: $CUTOFF"
else
  # First run: look back 24 hours
  CUTOFF=$(date -v-24H '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -d '24 hours ago' '+%Y-%m-%dT%H:%M:%S')
  log "First run — processing sessions from $CUTOFF"
fi

# -- Find session JSONL files modified since cutoff --
# Use find with -newer against a temp file stamped at CUTOFF
CUTOFF_REF=$(mktemp)
touch -t "$(echo "$CUTOFF" | sed 's/[-T:]//g' | cut -c1-12)" "$CUTOFF_REF" 2>/dev/null || touch -d "$CUTOFF" "$CUTOFF_REF" 2>/dev/null || touch "$CUTOFF_REF"

# Find main session files (UUIDs, not agent- prefixed subagent files)
SESSION_FILES=()
while IFS= read -r -d '' f; do
  SESSION_FILES+=("$f")
done < <(find "$SESSIONS_DIR" -name '*.jsonl' -newer "$CUTOFF_REF" ! -name 'agent-*' -print0 2>/dev/null)
rm -f "$CUTOFF_REF"

if [[ ${#SESSION_FILES[@]} -eq 0 ]]; then
  log "No new sessions since $CUTOFF — skipping"
  # Still update state file so we don't re-scan
  date '+%Y-%m-%dT%H:%M:%S' > "$STATE_FILE"
  exit 0
fi

log "Found ${#SESSION_FILES[@]} session file(s) to process"

# -- Phase 1: Extract meaningful text from sessions --
EXTRACTED=""

for sf in "${SESSION_FILES[@]}"; do
  # Derive project name from path
  PROJECT_PATH=$(dirname "$sf" | sed "s|$SESSIONS_DIR/||" | sed "s|^-Users-$(whoami)-||" | tr '-' '/')
  PROJECT_PATH=$(echo "$PROJECT_PATH" | sed 's|/subagents||')

  SESSION_TEXT=$(jq -r '
    # User messages: extract text content (skip tool_result, commands)
    if .type == "user" then
      if (.message.content | type) == "string" then
        if (.message.content | test("^<command-"; "")) then empty
        else "USER: " + .message.content
        end
      elif (.message.content | type) == "array" then
        .message.content[] |
        if .type == "text" then
          if (.text | test("^<command-"; "")) then empty
          else "USER: " + .text
          end
        else empty
        end
      else empty
      end
    # Assistant messages: extract only text blocks (skip tool_use)
    elif .type == "assistant" then
      if (.message.content | type) == "array" then
        .message.content[] |
        if .type == "text" and (.text | length) > 0 then
          "ASSISTANT: " + .text
        else empty
        end
      else empty
      end
    else empty
    end
  ' "$sf" 2>/dev/null || true)

  if [[ -n "$SESSION_TEXT" ]]; then
    EXTRACTED+="
=== Session from project: $PROJECT_PATH ===
$SESSION_TEXT
"
  fi
done

# -- Truncate to ~50KB --
if [[ ${#EXTRACTED} -gt $MAX_CONTEXT_BYTES ]]; then
  EXTRACTED="${EXTRACTED:0:$MAX_CONTEXT_BYTES}

[... truncated at ${MAX_CONTEXT_BYTES} bytes ...]"
  log "Extracted text truncated to ${MAX_CONTEXT_BYTES} bytes"
fi

if [[ -z "$EXTRACTED" || ${#EXTRACTED} -lt 50 ]]; then
  log "No meaningful content extracted — skipping"
  date '+%Y-%m-%dT%H:%M:%S' > "$STATE_FILE"
  exit 0
fi

log "Extracted ${#EXTRACTED} bytes of session content"

# -- Gather existing fact titles for dedup --
EXISTING_FACTS=""
if compgen -G "$FACTS_DIR/*.md" > /dev/null 2>&1; then
  EXISTING_FACTS=$(grep -h '^# Fact:' "$FACTS_DIR"/*.md 2>/dev/null | sed 's/^# Fact: //' || true)
fi

FACT_COUNT=$(echo "$EXISTING_FACTS" | grep -c . 2>/dev/null || echo "0")
log "Found $FACT_COUNT existing facts for dedup"

# -- Update state file BEFORE calling Claude (prevents re-processing on crash) --
date '+%Y-%m-%dT%H:%M:%S' > "$STATE_FILE"

# -- Phase 2: Pipe to Claude for reflection --
TODAY=$(date '+%Y-%m-%d')

PROMPT="You are a session reflector for a personal PARA knowledge system.

TASK: Read the session transcripts below, extract 1-8 meaningful atomic facts, and write them to {{PARA_ROOT}}/memory/facts/. Also append a summary to today's daily log.

EXISTING FACTS (do NOT duplicate these):
${EXISTING_FACTS:-<none yet>}

RULES:
1. Only extract genuinely useful, reusable knowledge — decisions, preferences, technical patterns, project context.
2. Skip ephemeral content: debugging steps, file listings, tool outputs, plan drafts.
3. Each fact file: {{PARA_ROOT}}/memory/facts/fact-<slug>.md using EXACTLY this template:

\`\`\`
# Fact: [Clear, unique title]

**Created**: $TODAY
**Last Accessed**:
**Superseded By**:
**Tags**: #tag1 #tag2

**Content**: [precise fact/decision/preference]

**Source**: From Claude Code session on $TODAY
\`\`\`

4. Append to {{PARA_ROOT}}/memory/daily/$TODAY.md (create if needed) with sections:
   ## Summary, ## Key Decisions, ## New Facts Extracted, ## Reflections
   If the file already has content, append under the existing sections or add new entries.
5. If nothing is worth remembering, output only: No new facts to extract.
6. Do NOT create facts that duplicate the existing facts listed above — check titles and content carefully.

SESSION TRANSCRIPTS:
$EXTRACTED"

echo "$PROMPT" | "$CLAUDE_BIN" -p \
  --model opus \
  --allowedTools "Write,Read,Edit,Glob,Grep" \
  --permission-mode bypassPermissions \
  --no-session-persistence \
  2>> "$LOG_FILE"

log "Reflection complete"
