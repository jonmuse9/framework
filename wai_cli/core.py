"""
WAI CLI Core

Main CLI entry point with command routing and error handling.
"""

import sys
import argparse
import json
import os
from pathlib import Path
import subprocess

from .init import check_spoke_initialized
from .utils.input import print_info, print_success, print_error, print_warning, safe_menu_choice
from .utils.exceptions import WAIError
from .utils.paths import normalize_path

# Import utilities
from .utils.cli_helpers import (
    is_wsl,
    resolve_spoke_root,
    is_within_path,
    format_datetime,
    detect_start_context,
    confirm_exit,
    is_framework_directory
)

# Import baseline helpers
from .baseline_helpers import (
    load_baseline_runs,
    print_baseline_runs,
    log_test_result,
    print_test_log,
    detect_ide_model,
    get_latest_baseline_summary
)

# Import command handlers
from .commands.init import cmd_init
from .commands.status import cmd_status
from .commands.hub_commands import cmd_hub
from .commands.project_commands import cmd_projects
from .commands.group_commands import cmd_group
from .commands.sync import cmd_sync
from .commands.update import cmd_update
from .commands.closeout import cmd_closeout
from .commands.stats import cmd_stats
from .commands.baseline import cmd_baseline
from .commands.time import cmd_time
from .commands.shipit import cmd_shipit
from .commands.template import cmd_template
from .commands.configure_ide import cmd_configure_ide
from .commands.context import cmd_context
from .commands.version import cmd_version

# Import UI menus
from .ui.core_menus import (
    show_uninitialized_intro,
    show_spoke_analysis,
    show_framework_menu,
    show_spoke_menu,
    show_init_menu,
    show_wheelwright_menu
)

from .ui.hub_menus import (
    show_hub_actions_menu,
    show_modify_projects_menu,
    show_spokes_menu,
    show_spoke_actions_menu,
    show_projects_actions_menu,
    show_groups_actions_menu,
    show_groups_menu,
    show_project_about_menu,
    show_project_review
)

from .ui.analytics_menus import (
    show_statistics_menu,
    show_knowledge_base_menu,
    get_hub_learnings_summary,
    show_learnings_by_category,
    get_spoke_details,
    show_baseline_menu
)

from .ui.config_menus import (
    show_evolution_menu,
    show_features_menu,
    show_integrations_menu,
    show_testing_menu,
    show_help_menu
)


# Framework version
FRAMEWORK_VERSION = "2.0.1"
SPOKE_STRUCTURE_VERSION = "2.1"


class WheelwrightCLI:
    """Main CLI class for Wheelwright."""

    def __init__(self):
        """Initialize CLI."""
        self.framework_path = Path(__file__).parent.parent.resolve()

    def _validate_workspace_paths(self, spoke_path: Path) -> None:
        """Validate and persist workspace paths in WAI-State.json."""
        from .utils.input import safe_input, print_warning

        spoke_root = resolve_spoke_root(spoke_path)
        wai_spoke_dir = spoke_root / "WAI-Spoke"
        state_file = wai_spoke_dir / "WAI-State.json"
        if not state_file.exists():
            return

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return

        wheel = state.setdefault("wheel", {})
        workspace = wheel.setdefault("workspace", {})

        # Determine expected workspace root
        expected_root = None
        if is_wsl():
            # Check if we have a .vscode folder with settings
            vscode_dir = spoke_root / ".vscode"
            settings_file = vscode_dir / "settings.json"
            if settings_file.exists():
                try:
                    vscode_settings = json.loads(settings_file.read_text(encoding="utf-8"))
                    remote_path = vscode_settings.get("remote.WSL.folderPath")
                    if remote_path:
                        expected_root = remote_path
                except Exception:
                    pass

            # If not found in vscode, try to convert from WSL path
            if not expected_root:
                wsl_path = str(spoke_root.resolve())
                result = subprocess.run(
                    ["wslpath", "-w", wsl_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    expected_root = result.stdout.strip()
        else:
            expected_root = str(spoke_root.resolve())

        if expected_root:
            expected_root = normalize_path(expected_root)

        # Check if we need to update
        current_root = workspace.get("root", "").strip()
        if current_root != expected_root:
            if current_root:
                print_warning(f"Workspace root mismatch detected:")
                print_warning(f"  Current: {current_root}")
                print_warning(f"  Expected: {expected_root}")
                update = safe_input("Update workspace.root in WAI-State.json? (y/n): ").strip().lower()
                if update == "y":
                    workspace["root"] = expected_root
                    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
                    print_success("Workspace root updated.")
            else:
                # First time setup
                workspace["root"] = expected_root
                state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="WAI",
            description="Wheelwright Framework CLI",
            add_help=False
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # init command
        init_parser = subparsers.add_parser("init", help="Initialize Wheelwright spoke")
        init_parser.add_argument("--path", help="Path to initialize (default: current directory)")
        init_parser.add_argument("--guided", action="store_true", help="Run guided initialization")

        # status command
        subparsers.add_parser("status", help="Show current project status")

        # hub command
        hub_parser = subparsers.add_parser("hub", help="Manage Wheelwright hub")
        hub_parser.add_argument("action", nargs="?", choices=["create", "locate", "teach", "learn", "subsume", "ignore"], help="Hub action")
        hub_parser.add_argument("--guided", action="store_true", help="Run guided hub creation")
        hub_parser.add_argument("--path", help="Hub path")
        hub_parser.add_argument("--source", help="Source hub path (for subsume)")
        hub_parser.add_argument("--target", help="Target hub path (for subsume)")
        hub_parser.add_argument("--ignore", nargs="+", help="Paths to ignore (for ignore)")

        # projects command
        projects_parser = subparsers.add_parser("projects", help="Manage hub projects")
        projects_parser.add_argument("action", nargs="?", choices=["list", "add", "remove", "rename", "add-to-group"], help="Projects action")
        projects_parser.add_argument("--hub", help="Hub path")
        projects_parser.add_argument("--path", help="Project path to add")
        projects_parser.add_argument("--name", help="Project name")
        projects_parser.add_argument("--group", help="Group name for add-to-group action")

        # group command
        group_parser = subparsers.add_parser("group", help="Manage project groups")
        group_parser.add_argument("action", nargs="?", choices=["create", "list", "add", "remove", "delete"], help="Group action")
        group_parser.add_argument("--name", help="Group name")
        group_parser.add_argument("--description", help="Group description")
        group_parser.add_argument("--project", help="Project name")

        # sync command
        sync_parser = subparsers.add_parser("sync", help="Sync with hub")
        sync_parser.add_argument("--hub", help="Hub path")
        sync_parser.add_argument("--all", action="store_true", help="Sync all projects")
        sync_parser.add_argument("--upload", action="store_true", help="Upload to hub")
        sync_parser.add_argument("--download", action="store_true", help="Download from hub")

        # update command
        update_parser = subparsers.add_parser("update", help="Update Wheelwright files")
        update_parser.add_argument("--force", action="store_true", help="Force update even if files exist")

        # closeout command
        closeout_parser = subparsers.add_parser("closeout", help="Close current session")
        closeout_parser.add_argument("--skip-git", action="store_true", help="Skip git operations")

        # stats command
        stats_parser = subparsers.add_parser("stats", help="Show project statistics")
        stats_parser.add_argument("--path", help="Project path")

        # baseline command
        baseline_parser = subparsers.add_parser("baseline", help="Run baseline comparison")
        baseline_parser.add_argument("action", nargs="?", choices=["run", "list", "log"], help="Baseline action")
        baseline_parser.add_argument("--ide", help="IDE name")
        baseline_parser.add_argument("--model", help="Model name")
        baseline_parser.add_argument("--notes", help="Test notes")

        # time command
        time_parser = subparsers.add_parser("time", help="Estimate token usage")
        time_parser.add_argument("--path", help="Project path")

        # shipit command
        shipit_parser = subparsers.add_parser("shipit", help="Closeout and commit")
        shipit_parser.add_argument("-m", "--message", help="Commit message")
        shipit_parser.add_argument("--skip-closeout", action="store_true", help="Skip closeout process")

        # template command
        template_parser = subparsers.add_parser("template", help="Manage project templates")
        template_parser.add_argument("action", nargs="?", choices=["list", "create", "apply"], help="Template action")
        template_parser.add_argument("--name", help="Template name")
        template_parser.add_argument("--path", help="Template or project path")

        # lug command (deprecated)
        subparsers.add_parser("lug", help="[Deprecated] Use 'group' instead")

        # changelog command
        changelog_parser = subparsers.add_parser("changelog", help="Generate changelog")
        changelog_parser.add_argument("--path", help="Project path")

        # configure-ide command
        configure_ide_parser = subparsers.add_parser("configure-ide", help="Configure IDE integration")
        configure_ide_parser.add_argument("--force", action="store_true", help="Force overwrite existing files")

        # context command
        context_parser = subparsers.add_parser("context", help="Show context information")
        context_parser.add_argument("--path", help="Project path")

        # version command
        subparsers.add_parser("version", help="Show version information")

        # teach command (hidden/debug)
        teach_parser = subparsers.add_parser("teach", help="Teach hub from spoke signals")
        teach_parser.add_argument("--hub", help="Hub path")
        teach_parser.add_argument("--spoke", help="Spoke path")

        return parser

    def _handle_no_command(self, parser):
        """Handle case where no command is provided."""
        cwd = Path.cwd()
        context_type, context_path = detect_start_context(self, cwd)

        if context_type == "uninitialized":
            show_uninitialized_intro(self, context_path)
            show_init_menu(self, context_path)
        elif context_type == "hub":
            show_framework_menu(self, context_path)
        elif context_type == "spoke":
            self._validate_workspace_paths(context_path)
            show_spoke_menu(self, context_path)
        else:
            parser.print_help()
            sys.exit(1)

    def _route_command(self, args, parser):
        """Route command to appropriate handler."""
        if args.command == "init":
            cmd_init(args)
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "hub":
            cmd_hub(self, args)  # Needs CLI reference
        elif args.command == "projects":
            cmd_projects(args)
        elif args.command == "group":
            cmd_group(args)
        elif args.command == "sync":
            cmd_sync(args)
        elif args.command == "update":
            cmd_update(args)
        elif args.command == "closeout":
            cmd_closeout(args)
        elif args.command == "stats":
            cmd_stats(args)
        elif args.command == "baseline":
            cmd_baseline(args)
        elif args.command == "time":
            cmd_time(args)
        elif args.command == "shipit":
            cmd_shipit(args)
        elif args.command == "template":
            cmd_template(args)
        elif args.command == "lug":
            self._cmd_lug(args)  # Not yet extracted
        elif args.command == "changelog":
            self._cmd_changelog(args)  # Not yet extracted
        elif args.command == "configure-ide":
            cmd_configure_ide(args)
        elif args.command == "context":
            cmd_context(args)
        elif args.command == "version":
            cmd_version(args)
        elif args.command == "teach":
            self._cmd_teach(args)  # Not yet extracted
        else:
            self._handle_no_command(parser)

    def _cmd_lug(self, args):
        """Handle lug command."""
        from .commands.lug import lug_command_group

        spoke_path = normalize_path(getattr(args, 'path', '.') or '.')

        # Pass lug_args to command group
        lug_args = getattr(args, 'lug_args', [])
        lug_command_group(lug_args, spoke_path)

    def _cmd_changelog(self, args):
        """Handle changelog command."""
        from .changelog import ChangelogGenerator
        from .utils.input import print_success, print_info, print_markdown, safe_confirm

        print_info("Generating changelog from closed Lugs...")
        generator = ChangelogGenerator(Path(os.getcwd()))
        content = generator.generate_changelog_content()

        if content:
            print_success("\nGenerated Content Preview:\n")
            print_markdown(content)
            if safe_confirm("Apply these changes to CHANGELOG.md?", default=True):
                generator.update_changelog_file()
                print_success("CHANGELOG.md updated.")
        else:
            print_info("No closed Lugs found to generate changelog from.")

    def _cmd_teach(self, args):
        """Handle teach command - Share learnings with Hub and get Map."""
        from .hub import HubManager
        from .hub_indexer import HubIndexer
        import shutil

        try:
            spoke_path = normalize_path(args.path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            # Find Hub
            hub_manager = HubManager()
            state_file = spoke_path / 'WAI-Spoke' / 'WAI-State.json'
            hub_path = None

            try:
                import json
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    path_str = state.get('wheelwright', {}).get('hub_path')
                    if path_str:
                        hub_path = Path(path_str)
            except:
                pass

            if not hub_path or not hub_path.exists():
                hub_path = hub_manager.auto_discover_hub(spoke_path, verbose=False)

            if not hub_path:
                print_error("No hub configured or found.")
                print_info("Run 'WAI hub create' (or configure hub path in WAI-State.json)")
                return

            print_info(f"\n🎓 Teaching Hub ({hub_path.name})...\n")

            # 1. Pull signals from this spoke to Hub
            kb_dir = hub_path / 'knowledge-base'
            kb_dir.mkdir(exist_ok=True)

            spoke_name = spoke_path.name
            signals_file = spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

            added_signals = 0
            if signals_file.exists():
                try:
                    # Filter high impact
                    new_signals = []
                    import json
                    with open(signals_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    s = json.loads(line)
                                    if s.get('impact', 0) >= 8:
                                        new_signals.append(s)
                                except: pass

                    if new_signals:
                         target_file = kb_dir / f"{spoke_name}-signals.jsonl"
                         existing_ids = set()
                         if target_file.exists():
                             with open(target_file, 'r', encoding='utf-8') as f:
                                 for line in f:
                                     try:
                                         s = json.loads(line)
                                         if 'id' in s: existing_ids.add(s['id'])
                                     except: pass

                         with open(target_file, 'a', encoding='utf-8') as f:
                             for signal in new_signals:
                                 if signal.get('id') not in existing_ids:
                                     f.write(json.dumps(signal) + "\n")
                                     added_signals += 1
                except Exception as e:
                    print_warning(f"  Failed to process signals: {e}")

            if added_signals > 0:
                print_success(f"  ✓ Shared {added_signals} high-impact signals with Hub")
            else:
                print_info("  No new high-impact signals to share")

            # 2. Generate Index
            print_info("  🗺️  Regenerating Hub Index...")
            indexer = HubIndexer(hub_path)
            index_path = indexer.generate_index()

            # 3. Distribute Map to Spoke
            print_info("  📦 Retrieving updated Map...")
            ref_dir = spoke_path / 'WAI-Spoke' / 'reference'
            ref_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy2(index_path, ref_dir / "WAI-Hub-Index.md")
            print_success(f"  ✓ Updated Map saved to: WAI-Spoke/reference/WAI-Hub-Index.md")

            print_info("\n✨ Teach complete.\n")

        except Exception as e:
            print_error(f"Teach command failed: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Main entry point for the CLI."""
        try:
            parser = self._create_parser()
            args = parser.parse_args()

            if not args.command:
                self._handle_no_command(parser)
            else:
                self._route_command(args, parser)

        except KeyboardInterrupt:
            print_info("\nOperation cancelled by user.")
            sys.exit(0)
        except WAIError as e:
            print_error(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """CLI entry point."""
    cli = WheelwrightCLI()
    cli.run()


if __name__ == "__main__":
    main()
