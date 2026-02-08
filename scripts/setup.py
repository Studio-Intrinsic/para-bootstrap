#!/usr/bin/env python3
"""
setup.py — Interactive PARA bootstrap setup.
Self-contained Python 3 script (stdlib only). Four phases:
  A) Detection  — Find what's already installed
  B) Preferences — Interactive prompts with sensible defaults
  C) Install — Idempotent creation of directories, scripts, config, services
  D) Verify — Run verify.py

Flags:
  --dry-run   Show what would be installed without making changes
  --verify    Run verification checks only
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# ANSI colors
# ──────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
SCRIPTS_DIR = SKILL_DIR / "scripts"


def banner() -> None:
    print(f"""
{BOLD}╔══════════════════════════════════════════════╗
║        PARA Bootstrap for Claude Code        ║
║     Persistent memory in 5 minutes           ║
╚══════════════════════════════════════════════╝{RESET}
""")


def prompt_str(question: str, default: str) -> str:
    """Prompt for a string value with a default."""
    answer = input(f"  {question} [{default}]: ").strip()
    return answer if answer else default


def prompt_int(question: str, default: int) -> int:
    """Prompt for an integer value with a default."""
    answer = input(f"  {question} [{default}]: ").strip()
    if not answer:
        return default
    try:
        return int(answer)
    except ValueError:
        print(f"    {YELLOW}Invalid number, using default: {default}{RESET}")
        return default


def prompt_bool(question: str, default: bool) -> bool:
    """Prompt for a yes/no value with a default."""
    hint = "Y/n" if default else "y/N"
    answer = input(f"  {question} [{hint}]: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


# ──────────────────────────────────────────────
# Phase A: Detection
# ──────────────────────────────────────────────

def detect(para_root: Path) -> dict:
    """Detect what's already installed. Returns status dict."""
    status = {}

    # PARA dir
    status["para_exists"] = para_root.is_dir()
    facts_dir = para_root / "memory" / "facts"
    if facts_dir.is_dir():
        status["fact_count"] = len(list(facts_dir.glob("*.md")))
    else:
        status["fact_count"] = 0

    # Claude CLI
    claude_local = Path.home() / ".local" / "bin" / "claude"
    claude_which = shutil.which("claude")
    if claude_local.exists():
        status["claude_bin"] = str(claude_local)
    elif claude_which:
        status["claude_bin"] = claude_which
    else:
        status["claude_bin"] = None

    # bun / QMD
    status["bun_installed"] = shutil.which("bun") is not None
    status["qmd_installed"] = shutil.which("qmd") is not None
    if status["qmd_installed"]:
        try:
            result = subprocess.run(
                ["qmd", "collections"], capture_output=True, text=True, timeout=10
            )
            status["qmd_para_collection"] = "para" in result.stdout.lower()
        except Exception:
            status["qmd_para_collection"] = False
    else:
        status["qmd_para_collection"] = False

    # ~/.claude/CLAUDE.md
    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    status["global_claude_md_exists"] = global_claude_md.exists()
    if global_claude_md.exists():
        status["global_claude_md_has_para"] = (
            "GLOBAL PARA MEMORY AUTOMATION" in global_claude_md.read_text()
        )
    else:
        status["global_claude_md_has_para"] = False

    # Launchd
    plist_new = Path.home() / "Library" / "LaunchAgents" / "com.para-bootstrap.claude-pipeline.plist"
    plist_old = Path.home() / "Library" / "LaunchAgents" / "com.jonslemp.claude-reflection.plist"
    status["launchd_plist"] = plist_new.exists() or plist_old.exists()

    # Granola
    granola_cache = Path.home() / "Library" / "Application Support" / "Granola" / "cache-v3.json"
    granola_skill = Path.home() / ".claude" / "skills" / "granola-skill" / "SKILL.md"
    status["granola_cache"] = granola_cache.exists()
    status["granola_skill"] = granola_skill.exists()

    # Claudeception
    claudeception = Path.home() / ".claude" / "skills" / "claudeception"
    status["claudeception"] = claudeception.is_dir()

    # jq
    status["jq_installed"] = shutil.which("jq") is not None

    return status


def print_status(status: dict) -> None:
    """Print a human-readable status report."""
    print(f"{BOLD}Current Status{RESET}")
    print(f"{'─' * 50}")

    def s(ok: bool, label: str, detail: str = "") -> None:
        icon = f"{GREEN}✓{RESET}" if ok else f"{DIM}✗{RESET}"
        extra = f"  {DIM}{detail}{RESET}" if detail else ""
        print(f"  {icon} {label}{extra}")

    s(status["para_exists"], "PARA directory",
      f"{status['fact_count']} facts" if status["para_exists"] else "")
    s(status["claude_bin"] is not None, "Claude CLI",
      status["claude_bin"] or "not found")
    s(status["jq_installed"], "jq")
    s(status["global_claude_md_exists"], "~/.claude/CLAUDE.md")
    s(status["global_claude_md_has_para"], "PARA section in CLAUDE.md")
    s(status["qmd_installed"], "QMD semantic search",
      "collection configured" if status["qmd_para_collection"] else "")
    s(status["launchd_plist"], "Launchd scheduler")
    s(status["granola_cache"], "Granola app cache")
    s(status["granola_skill"], "Granola skill")
    s(status["claudeception"], "Claudeception skill")
    print()


# ──────────────────────────────────────────────
# Phase B: Preferences
# ──────────────────────────────────────────────

def gather_preferences(status: dict) -> dict:
    """Interactive prompts for setup preferences."""
    print(f"{BOLD}Setup Preferences{RESET}")
    print(f"{'─' * 50}")
    print()

    prefs = {}
    prefs["para_root"] = prompt_str("PARA root directory", "~/para")
    prefs["bin_dir"] = prompt_str("Scripts directory", "~/bin")
    prefs["schedule_interval"] = prompt_int("Pipeline interval (seconds)", 3600)
    prefs["active_hour_start"] = prompt_int("Active hours start (0-23)", 8)
    prefs["active_hour_end"] = prompt_int("Active hours end (0-23)", 22)

    print()

    # Auto-detect toggles
    prefs["enable_qmd"] = prompt_bool(
        "Enable QMD semantic search?",
        status["bun_installed"] or status["qmd_installed"]
    )
    prefs["enable_launchd"] = prompt_bool(
        "Enable launchd scheduler?",
        sys.platform == "darwin"
    )
    prefs["enable_granola"] = prompt_bool(
        "Enable Granola meeting ingestion?",
        status["granola_cache"] and status["granola_skill"]
    )

    print()
    return prefs


# ──────────────────────────────────────────────
# Template rendering
# ──────────────────────────────────────────────

def render_template(template_path: Path, variables: dict) -> str:
    """Replace {{VAR}} placeholders and {{#COND}}...{{/COND}} blocks."""
    content = template_path.read_text()

    # Process conditional blocks: {{#ENABLE_GRANOLA}}...{{/ENABLE_GRANOLA}}
    import re
    for key, value in variables.items():
        if isinstance(value, bool):
            pattern = re.compile(
                r'\{\{#' + re.escape(key) + r'\}\}(.*?)\{\{/' + re.escape(key) + r'\}\}',
                re.DOTALL
            )
            if value:
                content = pattern.sub(r'\1', content)
            else:
                content = pattern.sub('', content)

    # Process simple variable substitution
    for key, value in variables.items():
        if not isinstance(value, bool):
            content = content.replace(f"{{{{{key}}}}}", str(value))

    return content


def build_variables(prefs: dict, status: dict) -> dict:
    """Build template variable dict from preferences."""
    para_root = os.path.expanduser(prefs["para_root"])
    bin_dir = os.path.expanduser(prefs["bin_dir"])
    home = str(Path.home())

    # Determine Claude binary path
    if status["claude_bin"]:
        claude_bin = status["claude_bin"]
    else:
        claude_bin = os.path.expanduser("~/.local/bin/claude")

    return {
        "PARA_ROOT": para_root,
        "BIN_DIR": bin_dir,
        "HOME": home,
        "CLAUDE_BIN": claude_bin,
        "SCHEDULE_INTERVAL": str(prefs["schedule_interval"]),
        "ACTIVE_HOUR_START": str(prefs["active_hour_start"]),
        "ACTIVE_HOUR_END": str(prefs["active_hour_end"]),
        "ENABLE_GRANOLA": prefs["enable_granola"],
    }


# ──────────────────────────────────────────────
# Phase C: Install
# ──────────────────────────────────────────────

def install(prefs: dict, variables: dict, dry_run: bool = False) -> None:
    """Idempotent installation of all PARA components."""
    para_root = Path(os.path.expanduser(prefs["para_root"]))
    bin_dir = Path(os.path.expanduser(prefs["bin_dir"]))
    home = Path.home()

    print(f"\n{BOLD}Installing PARA System{RESET}")
    print(f"{'─' * 50}")

    # -- Step 1: Create PARA directories --
    dirs = [
        para_root / "Projects",
        para_root / "Areas",
        para_root / "Resources",
        para_root / "Archives",
        para_root / "memory" / "facts",
        para_root / "memory" / "daily",
        para_root / "memory" / "inbox",
        para_root / "memory" / "inbox" / "processed",
        para_root / "logs",
    ]
    for d in dirs:
        if d.exists():
            print(f"  {DIM}EXISTS{RESET}  {d}")
        else:
            print(f"  {GREEN}CREATE{RESET}  {d}")
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

    # -- Step 2: Write ~/para/CLAUDE.md --
    write_template_file(
        TEMPLATES_DIR / "para-claude-md.md",
        para_root / "CLAUDE.md",
        variables, dry_run
    )

    # -- Step 3: Append PARA section to ~/.claude/CLAUDE.md --
    global_claude_md = home / ".claude" / "CLAUDE.md"
    marker = "GLOBAL PARA MEMORY AUTOMATION"

    if global_claude_md.exists():
        existing = global_claude_md.read_text()
        if marker in existing:
            print(f"  {DIM}EXISTS{RESET}  PARA section in ~/.claude/CLAUDE.md")
        else:
            section = render_template(
                TEMPLATES_DIR / "global-claude-md-section.md", variables
            )
            print(f"  {GREEN}APPEND{RESET}  PARA section to ~/.claude/CLAUDE.md")
            if not dry_run:
                with open(global_claude_md, "a") as f:
                    f.write(section)
    else:
        print(f"  {YELLOW}WARN{RESET}    ~/.claude/CLAUDE.md not found — creating with PARA section")
        if not dry_run:
            global_claude_md.parent.mkdir(parents=True, exist_ok=True)
            section = render_template(
                TEMPLATES_DIR / "global-claude-md-section.md", variables
            )
            global_claude_md.write_text(section)

    # -- Step 4: Write scripts to bin_dir --
    bin_dir.mkdir(parents=True, exist_ok=True)

    shell_scripts = [
        "claude-para-pipeline.sh",
        "claude-para-reflection.sh",
        "process-inbox.sh",
    ]
    for script_name in shell_scripts:
        write_template_file(
            TEMPLATES_DIR / script_name,
            bin_dir / script_name,
            variables, dry_run, executable=True
        )

    # Granola collector (optional)
    if prefs["enable_granola"]:
        write_template_file(
            TEMPLATES_DIR / "granola-collector.py",
            bin_dir / "granola-collector.py",
            variables, dry_run
        )
    else:
        print(f"  {CYAN}SKIP{RESET}    granola-collector.py (Granola disabled)")

    # -- Step 5: QMD setup --
    if prefs["enable_qmd"]:
        setup_qmd(para_root, dry_run)
    else:
        print(f"  {CYAN}SKIP{RESET}    QMD semantic search (disabled)")

    # -- Step 6: Launchd plist --
    if prefs["enable_launchd"] and sys.platform == "darwin":
        setup_launchd(variables, dry_run)
    else:
        reason = "disabled" if not prefs["enable_launchd"] else "not macOS"
        print(f"  {CYAN}SKIP{RESET}    Launchd scheduler ({reason})")

    print()


def write_template_file(
    template_path: Path, dest_path: Path, variables: dict,
    dry_run: bool, executable: bool = False
) -> None:
    """Render and write a template file, with idempotent comparison."""
    rendered = render_template(template_path, variables)

    if dest_path.exists():
        existing = dest_path.read_text()
        if existing == rendered:
            print(f"  {DIM}EXISTS{RESET}  {dest_path} (identical)")
            return
        else:
            # Content differs — ask before overwriting
            print(f"  {YELLOW}DIFFER{RESET}  {dest_path}")
            if dry_run:
                print(f"         {DIM}Would overwrite (--dry-run){RESET}")
                return
            if not prompt_bool(f"    Overwrite {dest_path}?", True):
                print(f"         {DIM}Skipped{RESET}")
                return

    print(f"  {GREEN}WRITE{RESET}   {dest_path}")
    if not dry_run:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(rendered)
        if executable:
            dest_path.chmod(0o755)


def setup_qmd(para_root: Path, dry_run: bool) -> None:
    """Install and configure QMD semantic search."""
    qmd_bin = shutil.which("qmd")

    if not qmd_bin:
        bun_bin = shutil.which("bun")
        if not bun_bin:
            print(f"  {YELLOW}WARN{RESET}    bun not found — skipping QMD install")
            print(f"         Install bun first: curl -fsSL https://bun.sh/install | bash")
            return

        print(f"  {GREEN}INSTALL{RESET} QMD via bun")
        if not dry_run:
            result = subprocess.run(
                ["bun", "install", "-g", "qmd"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                print(f"  {RED}FAIL{RESET}    QMD install failed: {result.stderr.strip()}")
                return
            qmd_bin = shutil.which("qmd")
            if not qmd_bin:
                print(f"  {RED}FAIL{RESET}    QMD installed but not found in PATH")
                return
    else:
        print(f"  {DIM}EXISTS{RESET}  QMD ({qmd_bin})")

    # Check if collection exists
    if dry_run:
        print(f"  {DIM}DRY-RUN{RESET} Would configure QMD para collection")
        return

    try:
        result = subprocess.run(
            ["qmd", "collections"], capture_output=True, text=True, timeout=10
        )
        if "para" in result.stdout.lower():
            print(f"  {DIM}EXISTS{RESET}  QMD 'para' collection")
        else:
            print(f"  {GREEN}CREATE{RESET}  QMD 'para' collection")
            subprocess.run(
                ["qmd", "add", str(para_root / "memory"), "--name", "para"],
                capture_output=True, text=True, timeout=30
            )

        # Set default context
        print(f"  {GREEN}CONFIG{RESET}  QMD default context -> para")
        subprocess.run(
            ["qmd", "context", "para"],
            capture_output=True, text=True, timeout=10
        )

        # Index
        print(f"  {GREEN}INDEX{RESET}   Indexing PARA collection...")
        subprocess.run(
            ["qmd", "index"],
            capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        print(f"  {YELLOW}WARN{RESET}    QMD operation timed out")
    except FileNotFoundError:
        print(f"  {YELLOW}WARN{RESET}    QMD binary not found after install")


def setup_launchd(variables: dict, dry_run: bool) -> None:
    """Install and load launchd plist."""
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_path = plist_dir / "com.para-bootstrap.claude-pipeline.plist"

    rendered = render_template(TEMPLATES_DIR / "launchd-plist.xml", variables)

    if plist_path.exists():
        existing = plist_path.read_text()
        if existing == rendered:
            print(f"  {DIM}EXISTS{RESET}  {plist_path} (identical)")
            return
        else:
            print(f"  {YELLOW}DIFFER{RESET}  {plist_path}")
            if dry_run:
                print(f"         {DIM}Would overwrite (--dry-run){RESET}")
                return
            if not prompt_bool(f"    Overwrite {plist_path}?", True):
                print(f"         {DIM}Skipped{RESET}")
                return
            # Unload before overwriting
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True, timeout=10
            )

    print(f"  {GREEN}WRITE{RESET}   {plist_path}")
    if not dry_run:
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(rendered)

        # Validate
        result = subprocess.run(
            ["plutil", "-lint", str(plist_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"  {RED}FAIL{RESET}    plist validation: {result.stderr.strip()}")
            return

        # Load
        print(f"  {GREEN}LOAD{RESET}    launchctl load {plist_path}")
        result = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"  {YELLOW}WARN{RESET}    launchctl load: {result.stderr.strip()}")


# ──────────────────────────────────────────────
# Phase D: Verify
# ──────────────────────────────────────────────

def verify(para_root: str, bin_dir: str) -> int:
    """Run verify.py with appropriate env vars."""
    verify_script = SCRIPTS_DIR / "verify.py"
    env = os.environ.copy()
    env["PARA_ROOT"] = os.path.expanduser(para_root)
    env["PARA_BIN_DIR"] = os.path.expanduser(bin_dir)

    result = subprocess.run(
        [sys.executable, str(verify_script)],
        env=env
    )
    return result.returncode


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    verify_only = "--verify" in args

    banner()

    if verify_only:
        return verify("~/para", "~/bin")

    # Phase A: Detection
    default_para = os.path.expanduser("~/para")
    status = detect(Path(default_para))
    print_status(status)

    # Check prerequisites
    if not status["claude_bin"]:
        print(f"{RED}Claude CLI not found.{RESET}")
        print(f"Install it first: https://docs.anthropic.com/en/docs/claude-code")
        if not prompt_bool("Continue anyway?", False):
            return 1

    if not status["jq_installed"]:
        print(f"{YELLOW}jq not found (needed for session reflection).{RESET}")
        print(f"Install: brew install jq")
        if not prompt_bool("Continue anyway?", True):
            return 1

    # Phase B: Preferences
    prefs = gather_preferences(status)

    # Re-detect with actual para_root
    actual_para = Path(os.path.expanduser(prefs["para_root"]))
    if str(actual_para) != default_para:
        status = detect(actual_para)

    # Build template variables
    variables = build_variables(prefs, status)

    if dry_run:
        print(f"\n{YELLOW}{BOLD}DRY RUN — no changes will be made{RESET}\n")

    # Phase C: Install
    install(prefs, variables, dry_run=dry_run)

    # Phase D: Verify
    if not dry_run:
        print(f"\n{BOLD}Running verification...{RESET}")
        verify(prefs["para_root"], prefs["bin_dir"])

    print(f"""
{BOLD}Next steps:{RESET}
  1. Open a Claude Code session in ~/para and try: "remember this is a test"
  2. Check pipeline logs: cat {os.path.expanduser(prefs['para_root'])}/logs/para-pipeline.log
  3. Search your memory: qmd query "test"
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
