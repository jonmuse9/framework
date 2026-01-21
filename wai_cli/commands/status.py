"""
Status Command

Display spoke status information.
"""

import json
from pathlib import Path
from typing import Optional

from ..hub import HubManager


def show_status(path: str = '.') -> None:
    """
    Show spoke status.

    Args:
        path: Path to spoke project (default: current directory)
    """
    project_path = Path(path).expanduser().resolve()
    wai_dir = project_path / 'WAI-Spoke'

    if not wai_dir.exists():
        print(f"\n    No spoke found at: {project_path}")
        print(f"   Run 'WAI init' to create one")
        return

    # Load state
    state_path = wai_dir / 'WAI-State.json'
    if not state_path.exists():
        print(f"    Spoke directory exists but WAI-State.json missing")
        return

    try:
        with open(state_path, encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        print(f"    Error loading WAI-State.json: {e}")
        return

    hub_manager = HubManager()
    discovered_hub = hub_manager.auto_discover_hub(project_path, verbose=False)
    wai_meta = state.get('wheelwright', {})
    stored_hub = wai_meta.get('hub_path')

    if discovered_hub and str(discovered_hub) != stored_hub:
        wai_meta['hub_path'] = str(discovered_hub)
        state['wheelwright'] = wai_meta
        try:
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
            stored_hub = wai_meta.get('hub_path')
        except Exception as e:
            print(f"    Warning: Failed to update hub path: {e}")

    # Display status
    wheel = state.get('wheel', {})
    foundation = state.get('_project_foundation', {})
    session = state.get('_session_state', {})
    workspace = wheel.get('workspace', {})
    paths = workspace.get('paths', {})
    primary = paths.get('primary')
    win_paths = paths.get('windows', {})
    wsl_paths = paths.get('wsl', {})

    print(f"\n    Wheelwright Status")
    print(f"   " + "=" * 50)

    print(f"\n    Spoke: {wheel.get('name', project_path.name)}")
    if wheel.get('type'):
        print(f"   Type: {wheel['type']}")
    if foundation.get('identity', {}).get('one_liner'):
        print(f"   Description: {foundation['identity']['one_liner']}")

    print(f"\n    Foundation:")
    if foundation.get('completed'):
        print(f"   ✓ Complete")
    else:
        print(f"   ⚠ Incomplete - needs setup")

    print(f"\n    Session State:")
    print(f"   Last modified by: {session.get('last_modified_by', 'Unknown')}")
    print(f"   Sessions: {session.get('session_count', 0)}")

    if stored_hub:
        print(f"\n    Hub: {stored_hub}")
    else:
        print(f"\n    Hub: Not connected")

    if primary or win_paths or wsl_paths:
        print(f"\n    Workspace Paths:")
        if primary:
            print(f"   Primary: {primary}")
        if win_paths:
            print(f"   Windows: {win_paths}")
        if wsl_paths:
            print(f"   WSL:     {wsl_paths}")

    # Check signals
    signals_path = wai_dir / 'WAI-Signals.jsonl'
    if signals_path.exists():
        try:
            signal_count = sum(1 for line in open(signals_path, encoding='utf-8') if line.strip())
            if signal_count > 0:
                print(f"\n    Signals: {signal_count} high-impact learnings recorded")
        except:
            pass

    # Check sync health
    if stored_hub:
        from ..sync_manager import SyncManager

        try:
            hub_path = Path(stored_hub)
            sync_manager = SyncManager(hub_path, project_path)
            health = sync_manager.calculate_sync_health()

            print(f"\n    Sync Health:")
            status_symbol = {
                'healthy': '✓',
                'stale': '⚠',
                'outdated': '✗',
                'never_synced': 'ℹ'
            }.get(health['status'], '?')

            print(f"   {status_symbol} Status: {health['status']}")

            if health['days_since_last_sync'] is not None:
                print(f"   Last sync: {health['days_since_last_sync']} days ago")

            if health['kb_version_drift']:
                print(f"   KB drift: {health['kb_version_drift']}")

            if health['pending_signals'] > 0:
                print(f"   Pending signals: {health['pending_signals']}")

            # Show recommendation if not healthy
            if health['status'] in ['stale', 'outdated']:
                print(f"   → Run 'WAI sync' to update")
            elif health['status'] == 'never_synced':
                print(f"   → Run 'WAI sync' to synchronize with hub")

        except Exception:
            # Silently skip if sync health check fails
            pass

    print()  # Final newline
