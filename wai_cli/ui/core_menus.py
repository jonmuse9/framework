"""
Core interactive menus for Wheelwright CLI.

Provides main navigation menus for different contexts:
- Auto-detection menu (no command given)
- Uninitialized project intro
- Spoke analysis display
- Framework menu (workspace operations)
- Spoke menu (project operations)
- Init menu (initialization wizard)
- Wheelwright menu (session state management)
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..init import framework_first_init, init_spoke, init_spoke_interactive, check_spoke_initialized
from ..hub import HubManager
from ..utils.input import (
    print_info, print_success, print_error, print_warning,
    safe_menu_choice, safe_confirm
)

if TYPE_CHECKING:
    from ..core import WheelwrightCLI


def handle_no_command(cli: 'WheelwrightCLI', parser):
    """
    Handle no command - interactive menu based on context.

    Logic:
    1. If in hub folder → hub menu
    2. If in spoke folder → analysis then spoke menu
    3. Otherwise → initialization intro

    Args:
        cli: WheelwrightCLI instance
        parser: Argument parser for help display
    """
    cwd = Path.cwd()
    context, ctx_path = cli._detect_start_context(cwd)

    if context == "hub":
        cli._show_hub_actions_menu()
        return

    if context == "spoke":
        show_spoke_analysis(cli, ctx_path)
        if cli._is_framework_directory(ctx_path):
            show_framework_menu(cli, ctx_path)
        else:
            cli._show_spoke_actions_menu(ctx_path)
        return

    show_uninitialized_intro(cli, cwd)
    if safe_confirm("Initialize WAI-Spoke here?", default=False):
        try:
            init_spoke(cwd, is_framework=False, verbose=True)
            show_spoke_analysis(cli, cwd)
            cli._show_spoke_actions_menu(cwd)
        except Exception as exc:
            print_error(f"Init failed: {exc}")

    # Fallback to main menu instead of exit
    show_framework_menu(cli, cwd)
    return


def show_uninitialized_intro(cli: 'WheelwrightCLI', project_path: Path) -> None:
    """
    Show a short WAI intro for uninitialized projects.

    Args:
        cli: WheelwrightCLI instance
        project_path: Path to the project directory
    """
    cli._show_brand_banner()
    hub_manager = HubManager()
    hub_path = hub_manager.auto_discover_hub(project_path, verbose=False)

    print_info("")
    print_info("  This folder is not initialized with WAI yet.")
    print_info("  Wheelwright (WAI) keeps project context stable for AI work.\n")
    print_info("  Quick start:")
    print_info("   • Initialize this project: WAI init")
    print_info("   • Keep project state in WAI-Spoke/")
    print_info("   • Use hub learn/teach to share knowledge across projects")
    print_info("")
    if hub_path:
        print_info(f"  Detected hub: {hub_path}")
    else:
        print_info("  No hub detected yet. Create one with: WAI hub create")
    print_info("")
    print_info("  WAI for education: it captures goals, decisions, and next steps")
    print_info("  so you can resume work confidently across sessions.\n")


def show_spoke_analysis(cli: 'WheelwrightCLI', spoke_path: Path) -> None:
    """
    Show a focused analysis for an initialized spoke project.

    Args:
        cli: WheelwrightCLI instance
        spoke_path: Path to the spoke directory
    """
    spoke_root = cli._resolve_spoke_root(spoke_path)
    wai_spoke_dir = spoke_root / "WAI-Spoke"
    state_file = wai_spoke_dir / "WAI-State.json"

    project_name = spoke_root.name
    hub_path = None
    requires_review = False
    review_reason = None

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            project_name = state.get("wheel", {}).get("name", project_name)
            hub_path = state.get("wheelwright", {}).get("hub_path")
            session_state = state.get("_session_state", {})
            requires_review = bool(session_state.get("requires_review"))
            review_reason = session_state.get("review_reason")
        except Exception:
            pass

    # Branded intro banner
    cli._show_brand_banner()

    print_info("=" * 60)
    print_info("             Spoke Analysis")
    print_info("=" * 60)
    print_info(f"  Project: {project_name}")
    print_info(f"  Path:    {spoke_root}")

    if hub_path:
        hub_status = "OK" if Path(hub_path).exists() else "Missing"
        print_info(f"  Hub:     {hub_path} ({hub_status})")
    else:
        print_warning("  Hub:     Not configured")

    if requires_review:
        reason_text = f" ({review_reason})" if review_reason else ""
        print_warning(f"  Review:  Required{reason_text}")

    print_info("")
    print_info("  Suggested actions:")
    if requires_review:
        print_info("   • Review prior changes before continuing")
    if not hub_path or (hub_path and not Path(hub_path).exists()):
        print_info("   • Set a valid hub path or run: WAI hub create")
    else:
        print_info("   • Run 'WAI teach' if hub knowledge needs distribution")
    print_info("")


def show_framework_menu(cli: 'WheelwrightCLI', framework_path: Path):
    """
    Show interactive menu for framework directory.

    Args:
        cli: WheelwrightCLI instance
        framework_path: Path to the framework directory
    """
    # Banner already shown by show_spoke_analysis in interactive flow

    is_initialized = check_spoke_initialized(framework_path)

    if not is_initialized:
        while True:
            print_info("\n⚠️  Framework not initialized yet.\n")
            print_info("  1/i - ✨ Initialize      Set up framework (recommended)")
            print_info("  2/? - ❓ Help           Getting started")
            print_info("")
            print_info("  q   - 👋 Quit")
            print_info("")

            options = [
                ('1', 'i', '✨ Initialize', 'init'),
                ('2', '?', '❓ Help', 'help'),
                ('q', 'q', '👋 Quit', 'quit')
            ]

            choice = safe_menu_choice("Select option", options, default='1')

            if choice == "init":
                framework_first_init(framework_path, verbose=True)
                # After init, break to reload menu
                break
            elif choice == "help":
                cli._create_parser().print_help()
            elif choice == "quit" or choice is None:
                return
        # After init, show initialized menu
        is_initialized = True

    if is_initialized:
        while True:
            # Get last learn timestamp from hub
            hub_manager = HubManager()
            hub_path = hub_manager.auto_discover_hub(framework_path, verbose=False)
            last_learn_text = ""
            if hub_path:
                hub_profile = hub_path / 'hub-profile.json'
                if hub_profile.exists():
                    try:
                        from datetime import datetime
                        profile = json.loads(hub_profile.read_text())

                        # Get both learn and teach timestamps
                        last_learn = profile.get('last_learn_run')
                        last_teach = profile.get('last_teach_run')

                        # Find most recent activity
                        recent_activity = None
                        activity_type = None

                        for timestamp, label in [(last_learn, 'learn'), (last_teach, 'teach')]:
                            if timestamp and timestamp != 'never':
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    if recent_activity is None or dt > recent_activity:
                                        recent_activity = dt
                                        activity_type = label
                                except:
                                    pass

                        if recent_activity:
                            days_ago = (datetime.now() - recent_activity).days
                            if days_ago == 0:
                                last_learn_text = f" │ Last {activity_type}: Today"
                            elif days_ago == 1:
                                last_learn_text = f" │ Last {activity_type}: Yesterday"
                            else:
                                last_learn_text = f" │ Last {activity_type}: {days_ago}d ago"
                        else:
                            last_learn_text = " │ No hub activity yet"
                    except Exception:
                        pass

            # Render improved menu
            cli._render_menu_header("Wheelwright AI", status=last_learn_text.strip(" │") if last_learn_text else None)

            print_info("  WORKSPACE")
            print_info("  1/h - 🏢 Hub               Manage shared knowledge")
            print_info("  2/s - 🎡 Spokes            View registered projects")
            print_info("  3/l - 📦 Lugs              Track work & dependencies")
            print_info("")
            print_info("  INSIGHTS")
            print_info("  4/k - 🧠 Knowledge         Browse learnings")
            print_info("  5/t - 📊 Stats             View metrics")
            print_info("")
            print_info("  SYSTEM")
            print_info("  6/w - 🛞 About             Framework info & testing")
            print_info("  7/? - ❓ Help              Commands & guides")
            print_info("")
            print_info("  b   - ⬅️  Back to system")
            print_info("  q   - 👋 Quit")
            print_info("")

            options = [
                ('1', 'h', '🏢 Hub', 'hub'),
                ('2', 's', '🎡 Spokes', 'spokes'),
                ('3', 'l', '📦 Lugs', 'lugs'),
                ('4', 'k', '🧠 Knowledge', 'knowledge'),
                ('5', 't', '📊 Stats', 'statistics'),
                ('6', 'w', '🛞 About', 'about'),
                ('7', '?', '❓ Help', 'help'),
                ('b', 'b', '⬅️ Back', 'back'),
                ('q', 'q', '👋 Quit', 'quit')
            ]

            choice = safe_menu_choice("Select", options, default='1')

            if choice == "hub":
                cli._show_hub_actions_menu()
            elif choice == "spokes":
                cli._show_spokes_menu(framework_path)
            elif choice == "lugs":
                # Show lugs list
                from ..commands.lug import lug_command_list
                args = type('Args', (), {'spoke_path': str(framework_path), 'status': None, 'type': None, 'priority': None})()
                lug_command_list(args)
                input("\n  Press Enter to continue...")
            elif choice == "knowledge":
                cli._show_knowledge_base_menu()
            elif choice == "statistics":
                cli._show_statistics_menu()
            elif choice == "about":
                show_wheelwright_menu(cli, framework_path)
            elif choice == "help":
                cli._show_help_menu()
            elif choice == "back" or choice is None:
                return
            elif choice == "quit":
                if cli._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)


def show_spoke_menu(cli: 'WheelwrightCLI', spoke_path: Path):
    """
    Show interactive menu for spoke directory.

    Args:
        cli: WheelwrightCLI instance
        spoke_path: Path to the spoke directory
    """
    while True:
        print_info("\n" + "=" * 60)
        print_info(f"Spoke: {spoke_path.name}")
        print_info("=" * 60)
        print_info("")
        print_info("  Spoke-specific actions")
        print_info("")
        print_info("  1/s - ℹ️Status          View spoke status")
        print_info("  2/y - 🔄 Upgrade         Update spoke structure version")
        print_info("  3/c - 📝 Closeout        Session closeout")
        print_info("  4/o - 📄 Context         Export for LLM")
        print_info("  5/u - 🔧 Absorbe         Process seed folders & archive sprawl")
        print_info("  6/r - 🔎 Review          Project discovery snapshot")
        print_info("  7/w - 🛞 Wheelwright      Evolution, features, integrations, testing")
        print_info("  8/? - ❓ Help            Show all commands")
        print_info("")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 's', 'ℹ️Status', 'status'),
            ('2', 'y', '🔄 Upgrade', 'sync'),
            ('3', 'c', '📝 Closeout', 'closeout'),
            ('4', 'o', '📄 Context', 'context'),
            ('5', 'u', '🔧 Absorbe', 'update'),
            ('6', 'r', '🔎 Review', 'review'),
            ('7', 'w', '🛞 Wheelwright', 'wheelwright'),
            ('8', '?', '❓ Help', 'help'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='1')

        if choice == "status":
            cli._cmd_status(type('Args', (), {'path': '.'})())
        elif choice == "sync":
            cli._cmd_sync(type('Args', (), {'all': False})())
        elif choice == "closeout":
            cli._cmd_closeout(type('Args', (), {'path': str(spoke_path)})())
        elif choice == "context":
            cli._cmd_context(type('Args', (), {'path': '.'})())
        elif choice == "update":
            cli._cmd_update(type('Args', (), {'path': '.'})())
        elif choice == "review":
            cli._show_project_review(spoke_path)
        elif choice == "wheelwright":
            show_wheelwright_menu(cli, spoke_path)
        elif choice == "help":
            cli._create_parser().print_help()
        elif choice == "quit" or choice is None:
            return


def show_init_menu(cli: 'WheelwrightCLI', cwd: Path):
    """
    Show menu for uninitialized directory.

    Args:
        cli: WheelwrightCLI instance
        cwd: Current working directory
    """
    while True:
        print_info("\n" + "=" * 60)
        print_info("Wheelwright Framework")
        print_info("=" * 60)
        print_info("\nBuild projects with the help of AI that roll forward")
        print_info("faster and more efficiently with each iteration.\n")
        print_info(f"Current directory: {cwd}\n")
        print_info("⚠️  No spoke detected in this directory.\n")
        print_info("  1/i - ✨ Initialize      Create spoke here")
        print_info("  2/? - ❓ Help           Getting started")
        print_info("  q   - 👋 Exit")
        print_info("")

        options = [
            ('1', 'i', '✨ Initialize', 'init'),
            ('2', '?', '❓ Help', 'help'),
            ('q', 'q', '👋 Exit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='1')

        if choice == "init":
            init_spoke_interactive(verbose=True)
            # After init, could break and show spoke menu, but for now just continue
        elif choice == "help":
            cli._create_parser().print_help()
        elif choice == "quit" or choice is None:
            return


def show_wheelwright_menu(cli: 'WheelwrightCLI', spoke_path: Path):
    """
    Show Wheelwright overview menu.

    Args:
        cli: WheelwrightCLI instance
        spoke_path: Path to the spoke directory
    """
    while True:
        print_info("\n" + "=" * 60)
        print_info("             Wheelwright")
        print_info("=" * 60)
        print_info("")
        print_info("  1/e - 📈 Evolution       Gains over time")
        print_info("  2/f - 🧩 Main Features   What Wheelwright delivers")
        print_info("  3/i - 🔌 Integrations    Status + auto-regenerate")
        print_info("  4/t - 🧪 Testing Results Run tests and view results")
        print_info("  5/b - 📊 Benchmarks      View benchmark logs & performance")
        print_info("")
        print_info("  b   - ⬅️Back")
        print_info("  q   - 👋 Quit")
        print_info("")

        options = [
            ('1', 'e', '📈 Evolution', 'evolution'),
            ('2', 'f', '🧩 Main Features', 'features'),
            ('3', 'i', '🔌 Integrations', 'integrations'),
            ('4', 't', '🧪 Testing Results', 'testing'),
            ('5', 'b', '📊 Benchmarks', 'benchmarks'),
            ('b', 'b', '⬅️Back', 'back'),
            ('q', 'q', '👋 Quit', 'quit')
        ]

        choice = safe_menu_choice("Select option", options, default='b')

        if choice == "evolution":
            cli._show_evolution_menu(spoke_path)
        elif choice == "features":
            cli._show_features_menu()
        elif choice == "integrations":
            cli._show_integrations_menu(spoke_path)
        elif choice == "testing":
            cli._show_testing_menu(spoke_path)
        elif choice == "benchmarks":
            cli._show_benchmark_logs(spoke_path)
        elif choice == "quit":
            if cli._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)
        elif choice == "back" or choice is None:
            return
