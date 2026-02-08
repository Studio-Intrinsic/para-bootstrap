#!/usr/bin/env python3
"""
granola-collector.py
Reads Granola meeting cache, writes structured markdown to inbox/
for downstream fact extraction by process-inbox.sh.

State file: {{PARA_ROOT}}/.last-granola-collection (ISO timestamp)
First run: processes all meetings from the past 30 days

Requires: granola-skill installed at ~/.claude/skills/granola-skill/
"""

import fcntl
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import granola_reader from the skill scripts
sys.path.insert(
    0, os.path.expanduser("~/.claude/skills/granola-skill/scripts")
)
from granola_reader import (
    load_cache,
    extract_meetings,
    get_meeting_date,
    get_meeting_id,
    get_meeting_title,
    get_notes,
    get_participants,
    get_summary,
    get_transcript,
    has_content,
)

PARA_DIR = Path(os.path.expanduser("{{PARA_ROOT}}"))
STATE_FILE = PARA_DIR / ".last-granola-collection"
INBOX_DIR = PARA_DIR / "memory" / "inbox"
LOG_FILE = PARA_DIR / "logs" / "granola-collector.log"
LOCK_FILE = Path("/tmp/granola-collector.lock")
TRANSCRIPT_CAP = 5000


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line)


def slugify(title: str) -> str:
    """Convert title to kebab-case filename slug."""
    slug = re.sub(r'[<>:"/\\|?*]', "", title)
    slug = re.sub(r"\s+", "-", slug.strip()).lower()
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80] if slug else "untitled"


def get_cutoff() -> datetime:
    """Read last collection timestamp or use first-run default."""
    if STATE_FILE.exists():
        raw = STATE_FILE.read_text().strip()
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            log(f"Invalid state file content: {raw!r}, using first-run cutoff")
    # First run: look back 30 days
    return datetime.now() - timedelta(days=30)


def get_updated_at(meeting: dict) -> datetime | None:
    """Get updated_at timestamp, falling back to created_at."""
    for field in ["updated_at", "created_at", "createdAt"]:
        val = meeting.get(field)
        if not val:
            continue
        try:
            if isinstance(val, (int, float)):
                if val > 1e12:
                    val = val / 1000
                return datetime.fromtimestamp(val)
            elif isinstance(val, str):
                clean = val.replace("Z", "+00:00")
                if "." in clean:
                    clean = clean.split("+")[0].split(".")[0]
                return datetime.fromisoformat(clean)
        except (ValueError, OSError):
            continue
    return None


def format_inbox_file(meeting: dict, state: dict) -> str:
    """Format a meeting as structured markdown for the inbox."""
    title = get_meeting_title(meeting)
    meeting_id = get_meeting_id(meeting)
    date = get_meeting_date(meeting)
    participants = get_participants(meeting)
    notes = get_notes(meeting, state)
    summary = get_summary(meeting)
    transcript = get_transcript(meeting, state)

    date_str = date.strftime("%Y-%m-%d %H:%M") if date else "Unknown"
    participants_str = ", ".join(participants) if participants else "Unknown"

    lines = [
        f"# Meeting: {title}",
        "",
        f"**Date**: {date_str}",
        f"**Participants**: {participants_str}",
        "**Source**: granola",
        f"**Meeting ID**: {meeting_id}",
        "",
        "## Notes",
        notes if notes.strip() else "No notes available",
        "",
        "## Summary",
        summary if summary.strip() else "No summary available",
        "",
        "## Transcript Highlights",
    ]

    if transcript and transcript.strip():
        if len(transcript) > TRANSCRIPT_CAP:
            transcript = transcript[:TRANSCRIPT_CAP] + "\n\n[... transcript truncated]"
        lines.append(transcript)
    else:
        lines.append("No transcript available")

    return "\n".join(lines) + "\n"


def inbox_filename(meeting: dict, state: dict) -> str:
    """Generate inbox filename: granola-YYYY-MM-DD-{slug}.md"""
    date = get_meeting_date(meeting)
    date_str = date.strftime("%Y-%m-%d") if date else "undated"
    title = get_meeting_title(meeting)
    slug = slugify(title)
    return f"granola-{date_str}-{slug}.md"


def main() -> int:
    # Acquire lock
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Another instance is running — skipping")
        return 0

    try:
        return _run()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _run() -> int:
    # Load Granola cache
    try:
        state = load_cache()
    except FileNotFoundError as e:
        log(f"Warning: {e}")
        return 0
    except Exception as e:
        log(f"Error loading Granola cache: {e}")
        return 1

    cutoff = get_cutoff()
    log(f"Processing meetings updated since {cutoff.isoformat()}")

    meetings = extract_meetings(state)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    seen_filenames: set[str] = set()

    for meeting in meetings:
        if not has_content(meeting, state):
            continue

        updated = get_updated_at(meeting)
        if not updated or updated < cutoff:
            continue

        fname = inbox_filename(meeting, state)
        if fname in seen_filenames:
            meeting_id = get_meeting_id(meeting)[:8]
            base, ext = fname.rsplit(".", 1)
            fname = f"{base}-{meeting_id}.{ext}"
        seen_filenames.add(fname)

        content = format_inbox_file(meeting, state)
        filepath = INBOX_DIR / fname
        filepath.write_text(content, encoding="utf-8")
        written += 1

    log(f"Wrote {written} inbox file(s)")

    # Update state file AFTER all writes succeed
    STATE_FILE.write_text(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
