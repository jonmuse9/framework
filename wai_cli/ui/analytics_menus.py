"""Analytics and knowledge base menus for Wheelwright CLI"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..hub import HubManager
from ..utils.input import (
    print_info,
    print_success,
    print_error,
    safe_menu_choice,
    safe_choice,
)


def show_baseline_menu(cli, spoke_path: Path):
    """Show baseline tracking menu for a spoke."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("           Baseline Tracking")
        print_info("=" * 60)

        state_file = spoke_path / 'WAI-Spoke' / 'WAI-State.json'
        baseline = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                baseline = state.get('analytics', {}).get('baseline_mode', {})
            except Exception:
                baseline = {}

        status = "ENABLED" if baseline.get('enabled') else "DISABLED"
        print_info(f"\n  Status: {status}")
        if baseline.get('enabled'):
            print_info(f"  Started: {baseline.get('started_at', 'Unknown')}")
            print_info(f"  Tokens tracked: {baseline.get('total_tokens_used', 0):,}")
            print_info(f"  Sessions tracked: {baseline.get('total_sessions', 0)}")
        elif baseline.get('total_tokens_used', 0) > 0:
            print_info(f"  Tokens tracked: {baseline.get('total_tokens_used', 0):,}")
            print_info(f"  Sessions tracked: {baseline.get('total_sessions', 0)}")

        print_info("\n  Baseline mode records sessions without WAI optimizations.")
        print_info("  Closeout still records metrics for baseline sessions.")
        print_info("")
        print_info("  1/e - ✅ Enable         Start baseline capture")
        print_info("  2/d - 🧊 Disable        Lock baseline data")
        print_info("  3/s - 🔍 Status         Show detailed status")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'e', '✅ Enable', 'enable'),
            ('2', 'd', '🧊 Disable', 'disable'),
            ('3', 's', '🔍 Status', 'status'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='b')

        if choice == "enable":
            cli._cmd_baseline(type('Args', (), {'baseline_command': 'enable', 'path': str(spoke_path)})())
            input("\n  Press Enter to continue...")
        elif choice == "disable":
            cli._cmd_baseline(type('Args', (), {'baseline_command': 'disable', 'path': str(spoke_path)})())
            input("\n  Press Enter to continue...")
        elif choice == "status":
            cli._cmd_baseline(type('Args', (), {'baseline_command': 'status', 'path': str(spoke_path)})())
            input("\n  Press Enter to continue...")
        elif choice == "quit":
            if cli._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


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
            if cli._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


def show_statistics_menu(cli):
    """Show statistics with insights and recommendations."""
    while True:
        print("\n" + "=" * 60)
        print("             Statistics & Insights")
        print("=" * 60)

        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        if not hub_path:
            print_info("\n  No hub found. Statistics require a hub.")
            print_info("\n  1. Create hub")
            print_info("  2. Back")
            print_info("")

            choice = safe_choice("Select option", choices=["1", "2"], default="2")
            if choice == "1":
                cli._hub_create(type('Args', (), {'path': None})())
            else:
                return
            continue

        # Load hub and spoke data
        from ..utils.registry import load_registry
        try:
            registry = load_registry(hub_path)
            spoke_count = len(registry.get('projects', []))
            group_count = len(registry.get('groups', {}))
        except:
            spoke_count = 0
            group_count = 0

        # Display statistics
        print_info("\n  Wheel Overview:")
        print_info(f"    Hub Location: {hub_path}")
        print_info(f"    Registered Spokes: {spoke_count}")
        print_info(f"    Groups: {group_count}")

        # Recommendations with impact values
        print_info("\n  Recommendations:")
        recommendations = []

        if spoke_count == 0:
            recommendations.append({
                'id': 1,
                'impact': 10,
                'action': 'Add your first spoke',
                'description': 'Register projects to start tracking development',
                'command': 'spokes_add'
            })

        if spoke_count > 5 and group_count == 0:
            recommendations.append({
                'id': 2,
                'impact': 3,
                'action': 'Create groups for organization',
                'description': 'With 5+ spokes, groups help manage CLI complexity',
                'command': 'groups_create'
            })

        # Only recommend teach if there are spokes and recent learning activity
        # Check if hub has recently learned (last learn < 30 days)
        if spoke_count > 0:
            has_recent_activity = False
            if hub_path:
                hub_profile = hub_path / 'hub-profile.json'
                if hub_profile.exists():
                    try:
                        profile_data = json.loads(hub_profile.read_text())

                        # Check for last_learn timestamp
                        last_learn = profile_data.get('last_learn_at')
                        if last_learn:
                            last_learn_date = datetime.fromisoformat(last_learn.replace('Z', '+00:00'))
                            days_since_learn = (datetime.now() - last_learn_date).days
                            has_recent_activity = days_since_learn < 30
                        else:
                            # If never learned, suggest learning first instead
                            has_recent_activity = False
                    except Exception:
                        pass

            if has_recent_activity:
                recommendations.append({
                    'id': 3,
                    'impact': 8,
                    'action': 'Run teach on all spokes',
                    'description': 'Update hub knowledge base from spoke learnings',
                    'command': 'teach_all'
                })

        if recommendations:
            for rec in sorted(recommendations, key=lambda x: x['impact'], reverse=True):
                print_info(f"\n    [{rec['id']}] Impact: {rec['impact']}/10 - {rec['action']}")
                print_info(f"        {rec['description']}")
        else:
            print_info("\n    No recommendations at this time.")

        print_info("")
        print_info("  1/e - ⚡ Enact           Execute a recommendation")
        print_info("  2/r - 🔄 Refresh         Update statistics")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'e', '⚡ Enact', 'enact'),
            ('2', 'r', '🔄 Refresh', 'refresh'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='b')

        if choice == "quit":
            if cli._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "enact" and recommendations:
            rec_id = safe_choice(
                "  Select recommendation",
                choices=[str(r['id']) for r in recommendations],
                default="1"
            )
            if rec_id:
                rec = next((r for r in recommendations if str(r['id']) == rec_id), None)
                if rec:
                    if rec['command'] == 'spokes_add':
                        cli._projects_add(type('Args', (), {'scan': None})())
                    elif rec['command'] == 'groups_create':
                        cli._show_groups_menu()
                    elif rec['command'] == 'teach_all':
                        print_info("\n  Teach all feature coming soon.")
        elif choice == "refresh":
            continue  # Refresh
        elif choice == "back" or choice is None:
            return


def show_knowledge_base_menu(cli):
    """Show knowledge base menu - review learnings and insights."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("            Knowledge Base")
        print_info("=" * 60)
        print_info("")

        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        if not hub_path:
            print_info("  No hub found. Run 'learn' to create patterns from your projects.")
            print_info("")
            print_info("  b   - ⬅️Back")
            print_info("  q   - 👋 Quit")
            print_info("")

            options = [
                ('b', 'b', '⬅️Back', 'back'),
                ('q', 'q', '👋 Quit', 'quit')
            ]

            choice = safe_menu_choice("Select option", options, default='b')
            if choice == "quit":
                if cli._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            else:
                return

        # Load hub learnings summary
        signals_summary = get_hub_learnings_summary(hub_path)

        print_info("  Hub Knowledge Overview:")
        print_info(f"    Total signals: {signals_summary['total_signals']}")
        print_info(f"    High-impact learnings: {signals_summary['high_impact_count']}")
        print_info(f"    Last updated: {signals_summary['last_updated']}")
        print_info("")

        print_info("  Browse by Category:")
        print_info("")
        print_info("  1/p - 📚 Patterns          Code patterns & best practices")
        print_info("  2/d - 🚨 Decisions         Architectural & design decisions")
        print_info("  3/i - 💡 Insights          Project insights & observations")
        print_info("  4/w - ⚠️  Warnings         Common pitfalls & anti-patterns")
        print_info("  5/a - 📋 All Learnings     View all signals chronologically")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'p', '📚 Patterns', 'patterns'),
            ('2', 'd', '🚨 Decisions', 'decisions'),
            ('3', 'i', '💡 Insights', 'insights'),
            ('4', 'w', '⚠️Warnings', 'warnings'),
            ('5', 'a', '📋 All', 'all'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='b')

        if choice == "quit":
            if cli._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return
        elif choice in ['patterns', 'decisions', 'insights', 'warnings', 'all']:
            show_learnings_by_category(hub_path, choice)
            input("\n  Press Enter to continue...")


def show_learnings_by_category(hub_path: Path, category: str):
    """Show learnings filtered by category."""
    print_info(f"\n{('=' * 60)}")
    category_names = {
        'patterns': '📚 Code Patterns & Best Practices',
        'decisions': '🚨 Architectural & Design Decisions',
        'insights': '💡 Project Insights & Observations',
        'warnings': '⚠️  Common Pitfalls & Anti-Patterns',
        'all': '📋 All Learnings'
    }
    print_info(f"  {category_names.get(category, 'Learnings')}")
    print_info("=" * 60)
    print_info("")

    # Load signals from knowledge base
    kb_dir = hub_path / 'knowledge-base'
    learnings = []

    if kb_dir.exists():
        for signals_file in kb_dir.glob('*.jsonl'):
            try:
                lines = signals_file.read_text().strip().split('\n')
                for line in lines:
                    if line.strip():
                        try:
                            signal = json.loads(line)
                            for offer in signal.get('offers', []):
                                # Filter by category if not 'all'
                                if category == 'all' or offer.get('type') == category[:-1]:  # Remove 's' from plural
                                    learnings.append({
                                        'type': offer.get('type', 'unknown'),
                                        'topic': offer.get('topic', 'No topic'),
                                        'context': offer.get('context', 'No context'),
                                        'impact': offer.get('impact', 0),
                                        'timestamp': signal.get('timestamp', '')
                                    })
                        except:
                            pass
            except Exception:
                pass

    if not learnings:
        print_info("  No learnings found in this category yet.")
        print_info("")
        print_info("  As you work with your spokes and run 'teach' events,")
        print_info("  the hub will accumulate learnings here.")
    else:
        # Sort by impact (descending)
        learnings.sort(key=lambda x: x['impact'], reverse=True)

        for i, learning in enumerate(learnings[:20], 1):  # Show top 20
            type_icon = {
                'pattern': '📚',
                'decision': '🚨',
                'insight': '💡',
                'warning': '⚠️'
            }.get(learning['type'], '📝')

            print_info(f"  [{i}] {type_icon} {learning['topic']} (Impact: {learning['impact']}/10)")
            print_info(f"      {learning['context'][:80]}...")
            print_info("")

        if len(learnings) > 20:
            print_info(f"  ... and {len(learnings) - 20} more learnings")
            print_info("")


def get_spoke_details(spoke_path: Path) -> Dict[str, Any]:
    """Get detailed information about a spoke."""
    details = {
        'exists': False,
        'initialized': False,
        'tech_stack': 'Unknown',
        'last_teach': 'Never',
        'signal_count': 0,
        'last_update': 'Unknown',
        'status': 'inactive',
        'preferred_name': None
    }

    if not spoke_path.exists():
        return details
    details['exists'] = True

    # Check for WAI-Spoke directory
    wai_spoke = spoke_path / 'WAI-Spoke'
    if not wai_spoke.exists():
        return details
    details['initialized'] = True

    # Load WAI-State.json for details
    state_file = wai_spoke / 'WAI-State.json'
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())

            # Get preferred name from wheel section
            wheel = state.get('wheel', {})
            details['preferred_name'] = wheel.get('preferred_name')

            # Get tech stack from foundation
            foundation = state.get('_project_foundation', {})
            tech = foundation.get('tech_stack', {})
            if tech:
                tech_list = []
                if tech.get('languages'): tech_list.extend(tech['languages'][:2])
                if tech.get('frameworks'): tech_list.extend(tech['frameworks'][:1])
                details['tech_stack'] = ', '.join(tech_list) if tech_list else 'Unknown'

            # Get last teach date (placeholder - to be implemented)
            details['last_teach'] = 'Not synced'

            # Check modification time for status
            mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
            days_ago = (datetime.now() - mtime).days
            details['last_update'] = f"{days_ago}d ago" if days_ago > 0 else "Today"
            details['status'] = 'active' if days_ago < 30 else 'inactive'

        except Exception:
            pass

    # Count signals
    signals_file = wai_spoke / 'WAI-Signals.jsonl'
    if signals_file.exists():
        try:
            lines = signals_file.read_text().strip().split('\n')
            details['signal_count'] = len([l for l in lines if l.strip()])
        except Exception:
            pass

    return details


def get_hub_learnings_summary(hub_path: Path) -> Dict[str, Any]:
    """Get summary of hub learnings."""
    summary = {
        'total_signals': 0,
        'high_impact_count': 0,
        'last_updated': 'Never'
    }

    # Check hub knowledge base (aggregated signals)
    kb_dir = hub_path / 'knowledge-base'
    if kb_dir.exists():
        for signals_file in kb_dir.glob('*.jsonl'):
            try:
                lines = signals_file.read_text().strip().split('\n')
                for line in lines:
                    if line.strip():
                        summary['total_signals'] += 1
                        try:
                            signal = json.loads(line)
                            # Check for high impact offers
                            for offer in signal.get('offers', []):
                                if offer.get('impact', 0) >= 8:
                                    summary['high_impact_count'] += 1
                        except:
                            pass

                # Get last modified time
                mtime = datetime.fromtimestamp(signals_file.stat().st_mtime)
                days_ago = (datetime.now() - mtime).days
                if days_ago == 0:
                    summary['last_updated'] = "Today"
                elif days_ago == 1:
                    summary['last_updated'] = "Yesterday"
                else:
                    summary['last_updated'] = f"{days_ago}d ago"
            except Exception:
                pass

    return summary


# Helper functions for testing menu
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
