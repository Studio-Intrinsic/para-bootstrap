# PARA Bootstrap Skill

## Description

Bootstraps a complete PARA personal knowledge management system with automated session reflection, inbox processing, and optional Granola meeting ingestion. Gives Claude Code persistent memory in 5 minutes.

## Triggers

Activate this skill when the user says any of:
- "para bootstrap"
- "set up PARA"
- "setup memory"
- "give Claude memory"
- "bootstrap knowledge system"
- "install PARA"

## Instructions

Run the interactive setup script:

```bash
python3 ~/.claude/skills/para-bootstrap/scripts/setup.py
```

The setup script has four phases:

1. **Detection** — Scans for existing PARA components and prints a status report
2. **Preferences** — Interactive prompts with sensible defaults (PARA root, schedule, toggles)
3. **Install** — Idempotent creation of directories, scripts, config, and services
4. **Verify** — Runs `verify.py` to confirm everything is working

### Flags

- `--dry-run` — Show what would be installed without making changes
- `--verify` — Run verification checks only (skip install)

### What Gets Installed

| Component | Description |
|-----------|-------------|
| PARA directories | `~/para/{Projects,Areas,Resources,Archives,memory/{facts,daily,inbox}}` |
| `~/para/CLAUDE.md` | Repository-level instructions for Claude Code in PARA workspace |
| `~/.claude/CLAUDE.md` section | Global PARA memory automation triggers appended |
| `~/bin/claude-para-pipeline.sh` | Pipeline orchestrator (runs all steps) |
| `~/bin/claude-para-reflection.sh` | Session reflector (extracts facts from Claude Code transcripts) |
| `~/bin/process-inbox.sh` | Inbox processor (extracts facts from meeting notes) |
| `~/bin/granola-collector.py` | Granola meeting collector (optional, requires granola-skill) |
| launchd plist | Hourly scheduler for the pipeline (macOS only) |
| QMD semantic search | Collection and index for semantic search over facts (optional) |

### Dependencies

- **Required**: Claude CLI (`claude` or `~/.local/bin/claude`), Python 3.8+, `jq`
- **Optional**: `bun` + `qmd` (semantic search), Granola app + granola-skill, claudeception

### Manual Verification

After setup, verify with:

```bash
python3 ~/.claude/skills/para-bootstrap/scripts/verify.py
```

### Platform Support

- macOS (launchd for scheduling)
- Linux support planned (cron/systemd)
