#!/usr/bin/env python3
"""
verify.py — Post-setup validation for PARA bootstrap.
Checks each component and prints a PASS/WARN/FAIL/SKIP table.
Exit 0 if no FAILs, exit 1 otherwise.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# -- Defaults (can be overridden by env vars for testing) --
PARA_ROOT = Path(os.environ.get("PARA_ROOT", os.path.expanduser("~/para")))
BIN_DIR = Path(os.environ.get("PARA_BIN_DIR", os.path.expanduser("~/bin")))
HOME = Path.home()

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results: list[tuple[str, str, str]] = []  # (status, component, detail)


def check(status: str, component: str, detail: str = "") -> None:
    results.append((status, component, detail))


def file_exists(path: Path, component: str) -> bool:
    if path.exists():
        check("PASS", component, str(path))
        return True
    else:
        check("FAIL", component, f"Missing: {path}")
        return False


def file_executable(path: Path, component: str) -> bool:
    if not path.exists():
        check("FAIL", component, f"Missing: {path}")
        return False
    if os.access(path, os.X_OK):
        check("PASS", component, str(path))
        return True
    else:
        check("WARN", component, f"Not executable: {path}")
        return False


def main() -> int:
    print(f"\n{BOLD}PARA Bootstrap Verification{RESET}")
    print(f"{'=' * 50}\n")

    # -- 1. PARA directories --
    for subdir in ["Projects", "Areas", "Resources", "Archives",
                   "memory/facts", "memory/daily", "memory/inbox",
                   "memory/inbox/processed", "logs"]:
        d = PARA_ROOT / subdir
        if d.is_dir():
            check("PASS", f"Directory: {subdir}")
        else:
            check("FAIL", f"Directory: {subdir}", f"Missing: {d}")

    # -- 2. CLAUDE.md files --
    file_exists(PARA_ROOT / "CLAUDE.md", "~/para/CLAUDE.md")

    global_claude_md = HOME / ".claude" / "CLAUDE.md"
    if global_claude_md.exists():
        content = global_claude_md.read_text()
        if "GLOBAL PARA MEMORY AUTOMATION" in content:
            check("PASS", "~/.claude/CLAUDE.md PARA section")
        else:
            check("WARN", "~/.claude/CLAUDE.md PARA section",
                  "File exists but missing PARA section")
    else:
        check("FAIL", "~/.claude/CLAUDE.md", "File missing")

    # -- 3. Scripts --
    scripts = [
        ("claude-para-pipeline.sh", True),
        ("claude-para-reflection.sh", True),
        ("process-inbox.sh", True),
    ]
    for script, required in scripts:
        path = BIN_DIR / script
        if required:
            file_executable(path, f"Script: {script}")
        elif path.exists():
            file_executable(path, f"Script: {script}")
        else:
            check("SKIP", f"Script: {script}", "Optional, not installed")

    # Granola collector (optional)
    granola_path = BIN_DIR / "granola-collector.py"
    if granola_path.exists():
        file_exists(granola_path, "Script: granola-collector.py")
    else:
        check("SKIP", "Script: granola-collector.py", "Optional, not installed")

    # -- 4. Claude CLI --
    claude_bin = HOME / ".local" / "bin" / "claude"
    if claude_bin.exists():
        check("PASS", "Claude CLI", str(claude_bin))
    elif shutil.which("claude"):
        check("PASS", "Claude CLI", shutil.which("claude"))
    else:
        check("FAIL", "Claude CLI", "Not found at ~/.local/bin/claude or in PATH")

    # -- 5. jq --
    if shutil.which("jq"):
        check("PASS", "jq", shutil.which("jq"))
    else:
        check("FAIL", "jq", "Not found in PATH (required for session reflection)")

    # -- 6. QMD (optional) --
    qmd_bin = shutil.which("qmd")
    if qmd_bin:
        # Check if PARA collection exists
        try:
            result = subprocess.run(
                ["qmd", "collections"],
                capture_output=True, text=True, timeout=10
            )
            if "para" in result.stdout.lower():
                check("PASS", "QMD collection", "para collection found")
            else:
                check("WARN", "QMD collection",
                      "qmd installed but 'para' collection not found")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            check("WARN", "QMD", "qmd found but couldn't query collections")
    else:
        check("SKIP", "QMD semantic search", "Not installed (optional)")

    # -- 7. Launchd plist (macOS only) --
    if sys.platform == "darwin":
        plist_path = HOME / "Library" / "LaunchAgents" / "com.para-bootstrap.claude-pipeline.plist"
        # Also check Jon's existing plist name
        plist_alt = HOME / "Library" / "LaunchAgents" / "com.jonslemp.claude-reflection.plist"
        if plist_path.exists():
            # Check if loaded
            try:
                result = subprocess.run(
                    ["launchctl", "list", "com.para-bootstrap.claude-pipeline"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    check("PASS", "Launchd plist", "Loaded and active")
                else:
                    check("WARN", "Launchd plist", "File exists but not loaded")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                check("WARN", "Launchd plist", "File exists, couldn't check load status")
        elif plist_alt.exists():
            check("PASS", "Launchd plist", f"Found at {plist_alt} (existing setup)")
        else:
            check("SKIP", "Launchd plist", "Not installed")
    else:
        check("SKIP", "Launchd plist", "Not macOS")

    # -- 8. Granola skill (optional) --
    granola_skill = HOME / ".claude" / "skills" / "granola-skill" / "SKILL.md"
    if granola_skill.exists():
        check("PASS", "Granola skill", str(granola_skill))
    else:
        check("SKIP", "Granola skill", "Not installed (optional)")

    # -- 9. Claudeception (optional) --
    claudeception = HOME / ".claude" / "skills" / "claudeception"
    if claudeception.is_dir():
        check("PASS", "Claudeception skill", str(claudeception))
    else:
        check("SKIP", "Claudeception skill", "Not installed (optional)")

    # -- 10. Fact count --
    facts_dir = PARA_ROOT / "memory" / "facts"
    if facts_dir.is_dir():
        facts = list(facts_dir.glob("*.md"))
        if len(facts) > 0:
            check("PASS", f"Facts: {len(facts)} atomic facts found")
        else:
            check("WARN", "Facts", "No facts yet (will populate after first pipeline run)")
    else:
        check("WARN", "Facts directory", "Not yet created")

    # -- Print results --
    print(f"{'Status':<6}  {'Component':<40}  {'Detail'}")
    print(f"{'─' * 6}  {'─' * 40}  {'─' * 40}")

    fails = 0
    for status, component, detail in results:
        if status == "PASS":
            color = GREEN
        elif status == "WARN":
            color = YELLOW
        elif status == "FAIL":
            color = RED
            fails += 1
        else:  # SKIP
            color = CYAN

        print(f"{color}{status:<6}{RESET}  {component:<40}  {detail}")

    print()
    if fails == 0:
        print(f"{GREEN}{BOLD}All checks passed!{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}{fails} check(s) FAILED.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
