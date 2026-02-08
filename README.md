# PARA Bootstrap for Claude Code

Give Claude Code persistent memory in 5 minutes.

Packages a complete [PARA](https://fortelabs.com/blog/para/) personal knowledge management system with automated session reflection, meeting ingestion, and semantic search — as a single idempotent bootstrap.

## What You Get

| Component | What It Does |
|-----------|-------------|
| **Session reflector** | Extracts atomic facts from your Claude Code transcripts every hour |
| **Inbox processor** | Extracts facts from meeting notes dropped into `~/para/memory/inbox/` |
| **Granola collector** | Pulls meetings from [Granola](https://granola.ai) into the inbox (optional) |
| **QMD semantic search** | `qmd query "pricing decisions"` searches your entire knowledge base (optional) |
| **CLAUDE.md config** | Teaches Claude Code to respond to "remember this", "recall [topic]", etc. |
| **launchd scheduler** | Runs the pipeline hourly during active hours (macOS) |

After setup, Claude Code automatically builds a searchable knowledge base from your work sessions and meetings — no manual effort required.

## Install

```bash
git clone https://github.com/Studio-Intrinsic/para-bootstrap.git ~/.claude/skills/para-bootstrap
python3 ~/.claude/skills/para-bootstrap/scripts/setup.py
```

The setup script is interactive with sensible defaults. It detects what's already installed and skips existing components.

### Flags

```bash
# Preview what would be installed
python3 ~/.claude/skills/para-bootstrap/scripts/setup.py --dry-run

# Check existing installation health
python3 ~/.claude/skills/para-bootstrap/scripts/setup.py --verify
```

## Prerequisites

- **Required**: [Claude CLI](https://docs.anthropic.com/en/docs/claude-code), Python 3.8+, `jq`
- **Optional**: [bun](https://bun.sh) + [qmd](https://github.com/jonslemp/qmd) (semantic search), [Granola](https://granola.ai) app

## How It Works

```
Claude Code sessions        Granola meetings
        │                          │
        ▼                          ▼
claude-para-reflection.sh   granola-collector.py
        │                          │
        ▼                          ▼
  ~/para/memory/facts/      ~/para/memory/inbox/
        │                          │
        └──────────┬───────────────┘
                   ▼
           process-inbox.sh
                   │
                   ▼
    ~/para/memory/facts/*.md  (atomic facts)
    ~/para/memory/daily/*.md  (daily logs)
```

The pipeline runs hourly via launchd. Each script is fault-tolerant — one failure doesn't block the others.

### Key design patterns

- **Crash-safe**: State file written before Claude call, not after
- **Idempotent**: Deduplicates against existing fact titles
- **macOS-native**: `mkdir`-based atomic locking (not `flock`)
- **Context-aware**: 50KB truncation limit per Claude call
- **Active hours**: Scripts skip execution outside configurable hours (default 8am-10pm)

## File Structure

```
~/para/
├── Projects/          # Active goals with deadlines
├── Areas/             # Ongoing responsibilities
├── Resources/         # Reference material
├── Archives/          # Completed/inactive items
├── memory/
│   ├── facts/         # Atomic fact files (fact-*.md)
│   ├── daily/         # Daily reflection logs (YYYY-MM-DD.md)
│   └── inbox/         # Staging area for meeting notes
│       └── processed/ # Already-extracted meetings
├── logs/              # Pipeline execution logs
└── CLAUDE.md          # Claude Code instructions for this workspace
```

## Usage

Once installed, Claude Code responds to these triggers in any project:

- **"remember this"** / **"extract facts"** — Extract atomic facts from the conversation
- **"recall [topic]"** / **"search PARA for [thing]"** — Search your knowledge base
- **"daily reflection"** — Write today's summary and extract facts

Search from terminal:

```bash
qmd query "what did we decide about pricing"
```

## Updating

```bash
cd ~/.claude/skills/para-bootstrap && git pull
```

Then re-run setup to pick up any new templates:

```bash
python3 ~/.claude/skills/para-bootstrap/scripts/setup.py
```

Existing files are compared before overwriting — you'll be prompted if anything differs.

## Platform Support

- **macOS** — Full support (launchd scheduling)
- **Linux** — Planned (cron/systemd)

## License

MIT
