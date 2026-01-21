"""
Closeout Command

Generate session closeout instructions.
"""

import json
from pathlib import Path


def generate_closeout() -> None:
    """Generate session closeout instructions."""
    project_path = Path('.').resolve()
    wai_dir = project_path / 'WAI-Spoke'

    if not wai_dir.exists():
        print(f"\n    No spoke in current directory")
        print(f"   Run 'WAI init' to initialize")
        return

    # Load state
    state_path = wai_dir / 'WAI-State.json'
    if not state_path.exists():
        print(f"    Spoke exists but WAI-State.json missing")
        return

    try:
        with open(state_path, encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        print(f"    Error loading state: {e}")
        return

    print(f"\n    Session Closeout")
    print(f"   " + "=" * 50)
    print(f"\n   Update your WAI-State files with the following:")
    print(f"\n   1. Update _session_state.last_modified_at to current time")
    print(f"   2. Increment session_count")
    print(f"   3. Add any decisions with impact >= 5 to decisions array")
    print(f"   4. Append high-impact learnings to WAI-Signals.jsonl")

    # Show current session state
    session = state.get('_session_state', {})
    print(f"\n   Current session state:")
    print(f"   - Last modified: {session.get('last_modified_at', 'Unknown')}")
    print(f"   - Session count: {session.get('session_count', 0)}")
    print(f"   - Last modified by: {session.get('last_modified_by', 'Unknown')}")

    print(f"\n   Note: Automated closeout feature coming in future release")
    print()


def cmd_closeout(args):
    """
    Handle closeout command.

    Args:
        args: Argument namespace (unused for now)
    """
    generate_closeout()
