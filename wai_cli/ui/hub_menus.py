"""
Hub and project management menus for Wheelwright CLI.

This module contains interactive menu systems for managing hubs, spokes,
projects, and groups within the Wheelwright framework.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from ..hub import HubManager
from ..groups import GroupsManager
from ..init import check_spoke_initialized, init_spoke
from ..utils.input import (
    print_info, print_success, print_error, print_warning,
    safe_menu_choice, safe_input, safe_confirm
)
from ..utils.registry import load_registry


def show_spokes_menu(cli, framework_path: Path):
    """Show Spokes menu with registry listing and management."""
    while True:
        # Check for hub first
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        if not hub_path:
            print_info("\n" + "=" * 60)
            print_info("              Spokes Menu │ No Hub")
            print_info("=" * 60)
            print_info("")
            print_info("  ⚠️  No hub configured. Please set up a hub first.")
            print_info("")
            print_info("  A hub is required to manage spokes.")
            print_info("  Go to: Main Menu → Hub → Locate or Create")
            print_info("")
            input("  Press Enter to continue...")
            return

        # Load registry
        try:
            registry = load_registry(hub_path)
            projects = registry.get('projects', [])
        except Exception:
            # Registry doesn't exist yet or is corrupt
            projects = []
        spoke_count = len(projects)

        # Show menu with stats
        print_info("\n" + "=" * 60)
        print_info("              Spokes Menu")
        print_info(f"│ {spoke_count} Projects")
        print_info("=" * 60)
        print_info("")

        # Display project listing by default
        if projects:
            print_info("  Registered Projects (compact):")
            print_info("  Legend: 🟢 Active (updated <30 days)  🔴 Inactive (30+ days)")
            print_info("")
            for i, project in enumerate(projects, 1):
                # Extract project info
                name = project.get('name', 'Unknown')
                preferred_name = project.get('preferred_name', name)
                path = project.get('path', '')

                # Try to get additional details
                state_data = cli._get_spoke_details(Path(path))
                tech_stack = state_data.get('tech_stack', 'Unknown')
                signal_count = state_data.get('signal_count', 0)
                last_update = state_data.get('last_update', 'Unknown')
                status = state_data.get('status', 'Unknown')

                exists = state_data.get('exists', False)
                initialized = state_data.get('initialized', False)
                if not exists:
                    status_icon = "⚪"
                    status_label = "missing"
                elif not initialized:
                    status_icon = "🟡"
                    status_label = "not initialized"
                else:
                    status_icon = "🟢" if status == "active" else "🔴"
                    status_label = status
                display_name = preferred_name if preferred_name != name else name
                short_path = ""
                if path:
                    try:
                        path_obj = Path(path)
                        short_path = f"{path_obj.parent.name}/{path_obj.name}"
                    except Exception:
                        short_path = path

                line = (
                    f"  [{i}] {status_icon} {display_name} │ "
                    f"Tech: {tech_stack} │ Signals: {signal_count} │ Updated: {last_update} │ State: {status_label}"
                )
                if short_path:
                    line += f" │ Path: {short_path}"
                print_info(line)

            selection = safe_input("  Open project # (Enter to skip)", allow_empty=True)
            if selection:
                if selection.isdigit():
                    idx = int(selection)
                    if 1 <= idx <= len(projects):
                        spoke_path = Path(projects[idx - 1].get('path', ''))
                        if not spoke_path.exists():
                            print_warning("Project path not found on disk.")
                            continue
                        if not check_spoke_initialized(spoke_path):
                            print_warning("Project is not initialized with WAI-Spoke yet.")
                            if safe_confirm("  Initialize WAI-Spoke here?", default=False):
                                try:
                                    init_spoke(spoke_path, is_framework=False, verbose=True)
                                    show_spoke_actions_menu(cli, spoke_path)
                                except Exception as exc:
                                    print_error(f"Init failed: {exc}")
                            continue
                        show_spoke_actions_menu(cli, spoke_path)
                        continue
                    else:
                        print_warning("Project number out of range.")
                else:
                    print_warning("Please enter a numeric project number.")
        else:
            print_info("  No projects registered yet.")
            print_info("")

        # Menu options
        print_info("  1/a - ➕ Add Projects      Register new spokes")
        print_info("  2/m - ✏️  Modify Projects  Remove or organize")
        print_info("  3/g - 📁 Groups            Manage spoke groups")
        print_info("  4/r - 🔄 Refresh           Reload project list")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'a', '➕ Add Projects', 'add'),
            ('2', 'm', '✏️  Modify Projects', 'modify'),
            ('3', 'g', '📁 Groups', 'groups'),
            ('4', 'r', '🔄 Refresh', 'refresh'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select", options, default='b')

        if choice == "add":
            print_info("\nAdd Projects - Scan for projects in a directory\n")

            # Calculate default scan path (2 levels above hub)
            default_path = hub_path.parent.parent if hub_path else Path.cwd().parent
            print_info(f"  Default: {default_path}")
            print_info("")

            scan_path = safe_input(
                "  Folder to scan",
                default=str(default_path),
                allow_empty=True
            )

            if scan_path and scan_path.strip():
                args = type('Args', (), {'scan': [scan_path]})()
            else:
                args = type('Args', (), {'scan': None})()

            cli._projects_add(args)
            input("\n  Press Enter to continue...")
        elif choice == "modify":
            show_modify_projects_menu(cli, hub_path, projects)
        elif choice == "groups":
            show_groups_menu(cli)
        elif choice == "refresh":
            continue  # Reload
        elif choice == "quit":
            if cli._confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


def show_modify_projects_menu(cli, hub_path: Path, projects: list):
    """Show modify projects submenu."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("           Modify Projects Menu")
        print_info("=" * 60)
        print_info("")
        print_info("  1/r - 🗑️  Remove from Registry  Unregister a spoke")
        print_info("  2/n - ✏️  Rename Project        Set preferred display name")
        print_info("  3/g - 📁 Add to Group          Organize spoke")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'r', '🗑️  Remove', 'remove'),
            ('2', 'n', '✏️  Rename', 'rename'),
            ('3', 'g', '📁 Add to Group', 'add_to_group'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select", options, default='b')

        if choice == "remove":
            cli._projects_remove(hub_path, projects)
            input("\n  Press Enter to continue...")
            return  # Return to parent menu to refresh list
        elif choice == "rename":
            cli._projects_rename(hub_path, projects)
            input("\n  Press Enter to continue...")
            return  # Return to parent menu to refresh list
        elif choice == "add_to_group":
            cli._projects_add_to_group(hub_path, projects)
            input("\n  Press Enter to continue...")
            return  # Return to parent menu
        elif choice == "quit":
            if cli._confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


def show_groups_menu(cli):
    """Show Groups menu (child of Spokes)."""
    while True:
        print_info("\n" + "=" * 60)
        print_info("              Groups Menu")
        print_info("=" * 60)
        print_info("")
        print_info("  Organize your spokes into logical collections")
        print_info("")
        print_info("  1/l - 📋 List            View all groups")
        print_info("  2/c - ➕ Create          New group")
        print_info("  3/a - ➕ Add Spoke       Add spoke to group")
        print_info("  4/r - ➖ Remove Spoke    Remove spoke from group")
        print_info("  5/d - 🗑️  Delete         Delete group")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'l', '📋 List', 'list'),
            ('2', 'c', '➕ Create', 'create'),
            ('3', 'a', '➕ Add Spoke', 'add'),
            ('4', 'r', '➖ Remove Spoke', 'remove'),
            ('5', 'd', '🗑️  Delete', 'delete'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='1')

        if choice == "quit":
            if cli._confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return

        # Find hub first
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        if not hub_path:
            print_error("\n  No hub found. Create a hub first (Main Menu -> Hub -> Create).")
            continue

        groups_manager = GroupsManager(hub_path)

        if choice == "list":
            groups_manager.list_groups(verbose=True)
        elif choice == "create":
            name = safe_input("  Group name", allow_empty=False)
            if name:
                description = safe_input("  Description (optional)", allow_empty=True)
                groups_manager.create_group(name, description=description or None)
        elif choice == "add":
            group_name = safe_input("  Group name", allow_empty=False)
            spoke_id = safe_input("  Spoke name or path", allow_empty=False)
            if group_name and spoke_id:
                groups_manager.add_spoke_to_group(group_name, spoke_id)
        elif choice == "remove":
            group_name = safe_input("  Group name", allow_empty=False)
            spoke_id = safe_input("  Spoke name or path", allow_empty=False)
            if group_name and spoke_id:
                groups_manager.remove_spoke_from_group(group_name, spoke_id)
        elif choice == "delete":
            group_name = safe_input("  Group name", allow_empty=False)
            if group_name:
                confirm = safe_confirm(f"  Delete group '{group_name}'?", default=False)
                if confirm:
                    groups_manager.delete_group(group_name, force=True)


def show_spoke_actions_menu(cli, spoke_path: Path):
    """Show actions for Spoke object."""
    while True:
        # Get status info for header
        last_modified = "Unknown"
        wai_uptodate = True
        foundation_complete = False
        try:
            state_file = spoke_path / 'WAI-Spoke' / 'WAI-State.json'
            if state_file.exists():
                state = json.loads(state_file.read_text())
                foundation_complete = bool(state.get('_project_foundation', {}).get('completed'))
                session_state = state.get('_session_state', {})
                last_modified = session_state.get('last_modified_by', 'Unknown')
        except Exception:
            pass

        # Render with status header
        project_name = spoke_path.name
        status_line = f"Modified by: {last_modified}"
        if not wai_uptodate:
            status_line += " | ⚠️  Run Sync to update"

        cli._render_menu_header("WAI", breadcrumb=["WAI", project_name], status=status_line)

        print_info("  PROJECT")
        print_info("  1/s - ℹ️  Status          Project info & review")
        print_info("  2/a - ℹ️  About            View project details")
        print_info("")
        print_info("  MAINTENANCE")
        print_info("  3/y - 🔄 Sync             Update WAI files & process seed")
        print_info("  4/n - 🧭 Analysis        Check project readiness")
        print_info("")
        if not foundation_complete:
            print_info("  f   - 🧱 Foundation      Complete setup")
        if cli._is_framework_directory(spoke_path):
            print_info("  h   - 🏢 Hub             Access hub operations")
        print_info("  b   - ⬅️  Back           Return to main menu")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 's', 'ℹ️  Status', 'status'),
            ('2', 'a', 'ℹ️  About', 'about'),
            ('3', 'y', '🔄 Sync', 'sync'),
            ('4', 'n', '🧭 Analysis', 'analysis'),
        ]

        if not foundation_complete:
            options.append(('f', 'f', '🧱 Foundation', 'foundation'))

        # Add hub/back options
        if cli._is_framework_directory(spoke_path):
            options.append(('h', 'h', '🏢 Hub', 'hub'))

        options.extend([('b', 'b', '⬅️  Back', 'back'), ('q', 'q', '👋 Quit', 'quit')])

        choice = safe_menu_choice("Select", options, default='s')

        if choice == "foundation":
            cli._run_foundation_setup(spoke_path)
        elif choice == "status":
            # Combined status + review
            cli._show_spoke_status_and_review(spoke_path)
        elif choice == "about":
            # New about submenu
            show_project_about_menu(cli, spoke_path)
        elif choice == "sync":
            # Combined absorb + upgrade
            print_info("\n  Running Sync (Absorb + Upgrade)...")
            cli._cmd_update(type('Args', (), {'path': str(spoke_path)})())
            # Also run cleanup
            cleaned = cli._cleanup_deprecated_files(spoke_path)
            if cleaned:
                print_info(f"  Cleaned up deprecated files: {', '.join(cleaned)}")

            cli._cmd_sync(type('Args', (), {'all': False})())
            input("\n  Press Enter to continue...")
        elif choice == "analysis":
            cli._show_spoke_analysis(spoke_path)
        elif choice == "hub":
            show_hub_actions_menu(cli)
        elif choice == "back":
            # Return to parent (which will fall back to framework/main menu in _handle_no_command)
            return
        elif choice == "quit" or choice is None:
            if cli._confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)


def show_project_about_menu(cli, spoke_path: Path) -> None:
    """Show project about submenu with various details."""
    while True:
        cli._render_menu_header("About Project", breadcrumb=["WAI", spoke_path.name, "About"])

        print_info("  PROJECT INFO")
        print_info("  1 - 📊 Overview         Project summary & stats")
        print_info("  2 - 🗂️  Structure        Directory layout")
        print_info("  3 - 📝 Foundation       Setup details")
        print_info("")
        print_info("  b - ⬅️  Back")
        print_info("")

        options = [
            ('1', '1', '📊 Overview', 'overview'),
            ('2', '2', '🗂️  Structure', 'structure'),
            ('3', '3', '📝 Foundation', 'foundation'),
            ('b', 'b', '⬅️  Back', 'back')
        ]

        choice = safe_menu_choice("Select", options, default='b')

        if choice == "overview":
            cli._cmd_status(type('Args', (), {'path': str(spoke_path)})())
            input("\n  Press Enter to continue...")
        elif choice == "structure":
            show_project_review(cli, spoke_path)
            input("\n  Press Enter to continue...")
        elif choice == "foundation":
            cli._run_foundation_setup(spoke_path)
        elif choice == "back" or choice is None:
            return


def show_project_review(cli, spoke_path: Path) -> None:
    """Show a project discovery snapshot."""
    from ..spoke_update import SpokeUpdateProcessor

    updater = SpokeUpdateProcessor(spoke_path)
    review = updater.review_project()

    print_info("\n" + "=" * 60)
    print_info("             Project Review")
    print_info("=" * 60)
    print_info("")
    print_info(f"  Project: {review['name']}")
    print_info(f"  Path: {review['path']}")
    print_info(f"  WAI-Spoke: {'Yes' if review['has_wai_spoke'] else 'No'}")
    print_info("")

    if review["key_files"]:
        print_info("  Key files found:")
        for item in review["key_files"]:
            print_info(f"   - {item}")
    else:
        print_info("  No common entry files detected.")

    if review["readme_preview"]:
        print_info("\n  README preview:")
        print_info("  " + "-" * 56)
        for line in review["readme_preview"].splitlines():
            print_info(f"  {line}")
        print_info("  " + "-" * 56)

    input("\n  Press Enter to continue...")


def show_hub_actions_menu(cli):
    """Show actions for Hub object with stats and enhanced features."""
    while True:
        # Get hub info for stats
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        hub_stats = ""
        if hub_path:
            try:
                # Load hub profile for stats
                profile_path = hub_path / 'hub-profile.json'
                if profile_path.exists():
                    profile = json.loads(profile_path.read_text())
                    # Fix: Read version from hub_config.version
                    hub_config = profile.get('hub_config', {})
                    version = hub_config.get('version', profile.get('hub_version', '1.0'))

                    # Get both learn and teach timestamps
                    last_learn_raw = profile.get('last_learn_run')
                    last_teach_raw = profile.get('last_teach_run')

                    # Find most recent activity
                    recent_activity = None
                    activity_label = "No activity"

                    for timestamp, label in [(last_learn_raw, 'Learn'), (last_teach_raw, 'Teach')]:
                        if timestamp and timestamp != 'never':
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                if recent_activity is None or dt > recent_activity[0]:
                                    recent_activity = (dt, label)
                            except:
                                pass

                    if recent_activity:
                        dt, label = recent_activity
                        days_ago = (datetime.now() - dt).days
                        if days_ago == 0:
                            activity_label = f"{label} today"
                        elif days_ago == 1:
                            activity_label = f"{label} yesterday"
                        elif days_ago < 30:
                            activity_label = f"{label} {days_ago}d ago"
                        else:
                            activity_label = f"{label} on {dt.strftime('%Y-%m-%d')}"

                    hub_stats = f" │ Version: {version} │ {activity_label}"
            except:
                hub_stats = f" │ {hub_path.name}"
        else:
            hub_stats = " │ No hub configured"

        print_info("\n" + "=" * 60)
        print_info("               Hub Menu")
        print_info(hub_stats if hub_stats else "")
        print_info("=" * 60)
        print_info("")
        print_info("  Central knowledge repository for all spokes")
        print_info("")

        if hub_path:
            print_info("  1/i - 🔍 Info            Show hub location & details")
            print_info("  2/l - 📚 Learn           Hub learns from spoke projects")
            print_info("  3/t - 🎓 Teach           Hub distributes knowledge to spokes")
            print_info("")
            print_info("  v   - ℹ️ Version         Show version info")
            print_info("")
            print_info("  b   - ⬅️Back")
            print_info("  q   - 👋 Quit")
            print_info("")

            options = [
                ('1', 'i', '🔍 Info', 'info'),
                ('2', 'l', '📚 Learn', 'learn'),
                ('3', 't', '🎓 Teach', 'teach'),
                ('v', 'v', 'ℹ️ Version', 'version'),
                ('b', 'b', '⬅️Back', 'back'),
                ('q', 'q', '👋 Quit', 'quit')
            ]
        else:
            print_info("  1/l - 🔍 Locate          Find hub (scan for candidates)")
            print_info("  2/c - ✨ Create          Initialize new hub")
            print_info("")
            print_info("  v   - ℹ️ Version         Show version info")
            print_info("")
            print_info("  b   - ⬅️Back")
            print_info("  q   - 👋 Quit")
            print_info("")

            options = [
                ('1', 'l', '🔍 Locate', 'locate'),
                ('2', 'c', '✨ Create', 'create'),
                ('v', 'v', 'ℹ️ Version', 'version'),
                ('b', 'b', '⬅️Back', 'back'),
                ('q', 'q', '👋 Quit', 'quit')
            ]

        choice = safe_menu_choice("Select", options, default='1')

        if choice == "info":
            cli._hub_locate_with_candidates()
            input("\n  Press Enter to continue...")
        elif choice == "locate":
            cli._hub_locate_with_candidates()
            input("\n  Press Enter to continue...")
        elif choice == "learn":
            # "Learn" means hub learns FROM spokes
            cli._hub_trigger_teach(hub_path)  # This function makes hub learn from spokes
            input("\n  Press Enter to continue...")
        elif choice == "teach":
            # "Teach" means hub teaches TO spokes
            cli._hub_trigger_learn(hub_path)  # This function makes hub teach to spokes
            input("\n  Press Enter to continue...")
        elif choice == "create":
            cli._hub_create(type('Args', (), {'path': None})())
            input("\n  Press Enter to continue...")
        elif choice == "version":
            # Show version without pausing
            from ..core import FRAMEWORK_VERSION, SPOKE_STRUCTURE_VERSION
            print_info(f"\n  Wheelwright Framework v{FRAMEWORK_VERSION}")
            print_info(f"  Spoke Structure v{SPOKE_STRUCTURE_VERSION}")
        elif choice == "quit":
            if cli._confirm_exit():
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return


def show_projects_actions_menu(cli):
    """Show actions for Projects object."""
    from ..utils.input import safe_choice

    while True:
        print_info("\n--- Projects Actions ---\n")
        print_info("1. List all projects")
        print_info("2. Add new projects")
        print_info("3. List by group")
        print_info("4. Back\n")

        choice = safe_choice(
            "Select action",
            choices=["1", "2", "3", "4"],
            default="1"
        )

        if choice == "1":
            cli._projects_list(type('Args', (), {'group': None})())
        elif choice == "2":
            cli._projects_add(type('Args', (), {'scan': None})())
        elif choice == "3":
            group_name = safe_input("Group name", allow_empty=False)
            if group_name:
                cli._projects_list(type('Args', (), {'group': group_name})())
        elif choice == "4" or choice is None:
            return


def show_groups_actions_menu(cli):
    """Show actions for Groups object."""
    from ..utils.input import safe_choice

    while True:
        print_info("\n--- Groups Actions ---\n")
        print_info("1. List all groups")
        print_info("2. Create new group")
        print_info("3. Add spoke to group")
        print_info("4. Remove spoke from group")
        print_info("5. Delete group")
        print_info("6. Back\n")

        choice = safe_choice(
            "Select action",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )

        if choice == "6" or choice is None:
            return

        # Find hub first
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

        if not hub_path:
            print_error("No hub found. Create a hub first (select Hub -> Create new hub).")
            continue

        groups_manager = GroupsManager(hub_path)

        if choice == "1":
            groups_manager.list_groups(verbose=True)

        elif choice == "2":
            name = safe_input("Group name", allow_empty=False)
            if name:
                description = safe_input("Description (optional)", allow_empty=True)
                groups_manager.create_group(name, description=description or None)

        elif choice == "3":
            group_name = safe_input("Group name", allow_empty=False)
            spoke_id = safe_input("Spoke name or path", allow_empty=False)
            if group_name and spoke_id:
                groups_manager.add_spoke_to_group(group_name, spoke_id)

        elif choice == "4":
            group_name = safe_input("Group name", allow_empty=False)
            spoke_id = safe_input("Spoke name or path", allow_empty=False)
            if group_name and spoke_id:
                groups_manager.remove_spoke_from_group(group_name, spoke_id)

        elif choice == "5":
            group_name = safe_input("Group name", allow_empty=False)
            if group_name:
                confirm = safe_confirm(f"Delete group '{group_name}'?", default=False)
                if confirm:
                    groups_manager.delete_group(group_name, force=True)
