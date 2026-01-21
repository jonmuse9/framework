"""Configuration and help menus for Wheelwright CLI.

This module provides menu functions for:
- Evolution tracking and baseline metrics
- Feature status dashboard
- IDE and tool integrations
- Help and documentation browser
- Testing menu and test results
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ..utils.input import (
    print_info,
    print_success,
    print_error,
    print_warning,
    safe_menu_choice,
    safe_confirm
)


def show_evolution_menu(cli, spoke_path: Path):
    """Show evolution metrics and baseline history."""
    runs = _load_baseline_runs(spoke_path)
    total_runs = len(runs)
    avg_savings = 0.0
    if runs:
        avg_savings = sum(r.get("savings", {}).get("percent_saved", 0) for r in runs) / total_runs

    print_info("\n" + "=" * 60)
    print_info("               Evolution")
    print_info("=" * 60)
    print_info("")

    if not runs:
        print_info("  No baseline runs recorded yet.")
    else:
        latest = runs[-1]
        print_info(f"  Total runs: {total_runs}")
        print_info(f"  Average savings: {avg_savings:.1f}%")
        print_info(f"  Latest: {latest.get('timestamp', 'Unknown')}")
        print_info(f"    IDE: {latest.get('ide', 'Unknown')}")
        print_info(f"    Model: {latest.get('model', 'Unknown')}")
        print_info(f"    Saved: {latest.get('savings', {}).get('percent_saved', 0):.1f}%")

    print_info("")
    print_info("  1/r - ⚡ Run Baseline     Run automated comparison")
    print_info("  2/l - 📜 List Runs        Show recent runs")
    print_info("")
    print_info("  b   - ⬅️Back")
    print_info("  q   - 👋 Quit")
    print_info("")

    options = [
        ('1', 'r', '⚡ Run Baseline', 'run'),
        ('2', 'l', '📜 List Runs', 'list'),
        ('b', 'b', '⬅️Back', 'back'),
        ('q', 'q', '👋 Quit', 'quit')
    ]

    choice = safe_menu_choice("Select option", options, default='b')

    if choice == "run":
        cli._run_baseline_comparison(spoke_path)
    elif choice == "list":
        _print_baseline_runs(runs)
        input("\n  Press Enter to continue...")
    elif choice == "quit":
        if confirm_exit():
            print_info("\n  👋 Goodbye!")
            sys.exit(0)


def show_features_menu(cli):
    """Show core Wheelwright features."""
    print_info("\n" + "=" * 60)
    print_info("            Main Features")
    print_info("=" * 60)
    print_info("")
    print_info("  • Session continuity with WAI-Spoke state")
    print_info("  • Automatic session briefing via hooks")
    print_info("  • Smart closeout and conversation logging")
    print_info("  • Token efficiency protocols (ADAPTIVE)")
    print_info("  • Hub ↔ spoke learnings and signals")
    print_info("  • IDE integrations and auto-discovery")
    print_info("")
    input("  Press Enter to continue...")


def show_integrations_menu(cli, spoke_path: Path):
    """Show integrations status and auto-regenerate if needed."""
    from ..integrations.manager import IDEManager

    print_info("\n" + "=" * 60)
    print_info("             Integrations")
    print_info("=" * 60)
    print_info("")

    manager = IDEManager(spoke_path)
    supported = manager.list_supported()
    updated = 0

    for ide in manager.all_integrations:
        config_path = ide.config_file_path
        generated = ide.generate_config()
        current = config_path.read_text() if config_path.exists() else None

        if current != generated:
            ide.write_config(generated)
            updated += 1
            status = "Updated"
        else:
            status = "Up to date"

        print_info(f"  {ide.name}: {status}")
        print_info(f"    Config: {config_path}")

    if updated:
        print_success(f"\n  ✓ Auto-regenerated {updated} integration file(s)\n")
    else:
        print_success("\n  ✓ All integrations up to date\n")

    input("  Press Enter to continue...")


def show_testing_menu(cli, spoke_path: Path):
    """Show testing menu and run tests."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("            Testing Results")
        print_info("=" * 60)
        print_info("")
        print_info("  1/s - 🧪 Smoke Tests      Run framework smoke tests")
        print_info("  2/u - 🧩 Hook Unit Tests  Run session-start tests")
        print_info("  3/l - 📜 View Log         Show recent test results")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 's', '🧪 Smoke Tests', 'smoke'),
            ('2', 'u', '🧩 Hook Unit Tests', 'unit'),
            ('3', 'l', '📜 View Log', 'log'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='b')

        if choice == "smoke":
            result = subprocess.run(
                ['./tests/scripts/smoke-tests-phase1-2.sh'],
                cwd=spoke_path,
                capture_output=True,
                text=True
            )
            _log_test_result(
                spoke_path,
                test_name="tests/scripts/smoke-tests-phase1-2.sh",
                exit_code=result.returncode,
                output=result.stdout + result.stderr
            )
            print(result.stdout or result.stderr)
            input("\n  Press Enter to continue...")
        elif choice == "unit":
            result = subprocess.run(
                ['WAI-Spoke/hooks/test-session-start.sh'],
                cwd=spoke_path,
                capture_output=True,
                text=True
            )
            _log_test_result(
                spoke_path,
                test_name="WAI-Spoke/hooks/test-session-start.sh",
                exit_code=result.returncode,
                output=result.stdout + result.stderr
            )
            print(result.stdout or result.stderr)
            input("\n  Press Enter to continue...")
        elif choice == "log":
            _print_test_log(spoke_path)
            input("\n  Press Enter to continue...")
        elif choice == "quit":
            if confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


def show_help_menu(cli):
    """Show help menu with structured options."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("               Help Menu")
        print_info("=" * 60)
        print_info("")
        print_info("  1/c - 🖥️CLI Usage        Navigate interactive menus")
        print_info("  2/p - 📦 Project Use      Initialize & manage spokes")
        print_info("  3/m - 💻 Command Line     Quick reference guide")
        print_info("  4/s - ⏱️Session Commands  Time/Compact/Closeout/Shipit")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'c', '🖥️CLI Usage', 'cli'),
            ('2', 'p', '📦 Project Use', 'project'),
            ('3', 'm', '💻 Command Line', 'commands'),
            ('4', 's', '⏱️Session Commands', 'session'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='1')

        if choice == "quit":
            if confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "cli":
            print_info("\n" + "=" * 60)
            print_info("           Using WAI CLI")
            print_info("=" * 60)
            print_info("\n  The WAI CLI provides interactive menus to:")
            print_info("")
            print_info("  • Manage your hub (central repository)")
            print_info("  • Register and organize spokes (projects)")
            print_info("  • View statistics and recommendations")
            print_info("  • Access project context and status")
            print_info("")
            print_info("  Navigation:")
            print_info("  - Use numbers OR letter shortcuts (e.g., 1/h for Hub)")
            print_info("  - Press Enter to use default (shown in brackets)")
            print_info("  - Press 'b' for Back, 'q' for Quit")
            print_info("  - Ctrl+C to cancel current operation")
            print_info("")
            input("  Press Enter to continue...")

        elif choice == "project":
            print_info("\n" + "=" * 60)
            print_info("        Using WAI Within a Project")
            print_info("=" * 60)
            print_info("\n  Each project can have its own spoke:")
            print_info("")
            print_info("  1. Initialize spoke in project:")
            print_info("     $ cd /path/to/project")
            print_info("     $ WAI init")
            print_info("")
            print_info("  2. Key files created (WAI-Spoke/):")
            print_info("     • WAI-Guide.md - AI instructions")
            print_info("     • WAI-State.json - Project state")
            print_info("     • WAI-State.md - Strategic context")
            print_info("     • WAI-Signals.jsonl - Learning signals")
            print_info("")
            print_info("  3. Seed folders for brownfield projects:")
            print_info("     • WAI-Spoke/seed/ingest - ingest into WAI files")
            print_info("     • WAI-Spoke/seed/reference - archive into WAI-Spoke/reference")
            print_info("     Run 'WAI absorbe' (or update) to process these folders.")
            print_info("")
            print_info("  4. During development:")
            print_info("     - AI assistants read WAI-Guide.md")
            print_info("     - Track decisions in WAI-State.json")
            print_info("     - Sync learnings to hub periodically")
            print_info("")
            input("  Press Enter to continue...")

        elif choice == "commands":
            print_info("\n" + "=" * 60)
            print_info("        Using WAI via Command Line")
            print_info("=" * 60)
            print_info("\n  Quick commands (bypass menus):")
            print_info("")
            print_info("  Status & Info:")
            print_info("    WAI status              Show spoke status")
            print_info("    WAI version             Show version")
            print_info("")
            print_info("  Baseline:")
            print_info("    WAI baseline enable     Start baseline capture")
            print_info("    WAI baseline disable    Lock baseline data")
            print_info("    WAI baseline status     Show baseline status")
            print_info("")
            print_info("  Update & Review:")
            print_info("    WAI absorbe             Process seed folders (incl. Lug deltas)")
            print_info("    WAI update              Alias for absorbe")
            print_info("    WAI context             Export project context for LLM paste")
            print_info("")
            print_info("  Lug System (AI-first tasks):")
            print_info("    WAI lug add <title>     Create a new Lug")
            print_info("    WAI lug list            List active Lugs")
            print_info("    WAI lug ready           Show Lugs meeting policy requirements")
            print_info("    WAI lug show <id>       Show Lug details")
            print_info("    WAI lug close <id>      Resolve and archive a Lug")
            print_info("")
            print_info("  Hub:")
            print_info("    WAI hub locate          Find hub")
            print_info("    WAI hub create [path]   Create hub")
            print_info("")
            print_info("  Groups:")
            print_info("    WAI group create <name> [--description TEXT]")
            print_info("    WAI group list [--verbose]")
            print_info("    WAI group add-spoke <group> <spoke>")
            print_info("    WAI group remove-spoke <group> <spoke>")
            print_info("    WAI group delete <name>")
            print_info("")
            print_info("  Integrations:")
            print_info("    WAI configure-ide list         List supported IDEs")
            print_info("    WAI configure-ide detect       Detect IDEs in use")
            print_info("    WAI configure-ide setup <ide>  Generate integration files")
            print_info("")
            print_info("  See 'WAI --help' for complete list")
            print_info("")
            input("  Press Enter to continue...")

        elif choice == "session":
            print_info("\n" + "=" * 60)
            print_info("           Session Commands")
            print_info("=" * 60)
            print_info("\n  Commands for managing AI sessions:")
            print_info("")
            print_info("  'Time'")
            print_info("    Check token usage and context capacity")
            print_info("    Shows: ~X% of context window used")
            print_info("    Warns: At 60%, 80%, 90% capacity")
            print_info("    When: Anytime during session to monitor usage")
            print_info("")
            print_info("  'Compact'")
            print_info("    Compress context by summarizing resolved discussions")
            print_info("    Reduces: Conversation history to key outcomes")
            print_info("    Keeps: Decisions, modified files, open questions")
            print_info("    When: At 80% capacity or before major work")
            print_info("")
            print_info("  'Closeout'")
            print_info("    End session and save state")
            print_info("    Actions:")
            print_info("      - Compresses context automatically")
            print_info("      - Scans WAI-Spoke/ for unknown files")
            print_info("      - Rebalances JSON/MD content")
            print_info("      - Extracts high-impact learnings (impact ≥8)")
            print_info("      - Updates session summary")
            print_info("      - Clears conversation log")
            print_info("    When: End of work session")
            print_info("")
            print_info("  'Shipit'")
            print_info("    Closeout + git commit + WAI Point update")
            print_info("    Same as: Closeout, then git add & commit")
            print_info("    Creates: Commit with session summary and closed Lug IDs")
            print_info("    When: End of session with changes to commit")
            print_info("")
            print_info("  'Lugs'")
            print_info("    Access the task & dependency graph")
            print_info("    Actions: Add, List, Show, Ready, Close")
            print_info("    When: Anytime to plan work or track progress")
            print_info("")
            print_info("  Note: Session commands are triggered by saying")
            print_info("        the command word to your AI assistant.")
            print_info("        Example: \"Time\" or \"Run closeout\"")
            print_info("")
            input("  Press Enter to continue...")

        elif choice == "back" or choice is None:
            return


# Helper functions


def confirm_exit() -> bool:
    """Confirm exit with user."""
    return safe_confirm("  Exit WAI CLI?", default=True)


def _load_baseline_runs(spoke_path: Path) -> List[Dict[str, Any]]:
    """Load baseline runs from log."""
    log_path = spoke_path / 'WAI-Spoke' / 'WAI-Baseline-Log.jsonl'
    if not log_path.exists():
        return []

    runs = []
    with open(log_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except Exception:
                continue
    return runs


def _print_baseline_runs(runs: List[Dict[str, Any]]):
    """Print baseline runs summary."""
    if not runs:
        print_info("\n  No baseline runs recorded.")
        return

    print_info("\n  Recent runs:")
    for run in runs[-5:]:
        ts = run.get("timestamp", "Unknown")
        ide = run.get("ide", "Unknown")
        model = run.get("model", "Unknown")
        saved = run.get("savings", {}).get("percent_saved", 0)
        print_info(f"  - {ts} | {ide} | {model} | Saved: {saved:.1f}%")


def _log_test_result(spoke_path: Path, test_name: str, exit_code: int, output: str):
    """Append test result to log."""
    log_path = spoke_path / 'WAI-Spoke' / 'WAI-Testing-Log.jsonl'
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test": test_name,
        "exit_code": exit_code,
        "status": "pass" if exit_code == 0 else "fail"
    }
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + "\n")


def _print_test_log(spoke_path: Path):
    """Print recent test log entries."""
    log_path = spoke_path / 'WAI-Spoke' / 'WAI-Testing-Log.jsonl'
    if not log_path.exists():
        print_info("\n  No test results logged yet.")
        return

    entries = []
    with open(log_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    if not entries:
        print_info("\n  No test results logged yet.")
        return

    print_info("\n  Recent test results:")
    for entry in entries[-5:]:
        ts = entry.get("timestamp", "Unknown")
        test = entry.get("test", "Unknown")
        status = entry.get("status", "unknown")
        print_info(f"  - {ts} | {test} | {status}")
