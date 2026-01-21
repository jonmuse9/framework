"""
WAI CLI Core

Main CLI entry point with command routing and error handling.
"""

import sys
import argparse
import json
import os
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import subprocess
from git import Repo, exc as git_exc

from .init import framework_first_init, init_spoke, init_spoke_interactive, check_spoke_initialized
from .hub import HubManager
from .projects import ProjectDiscovery
from .groups import GroupsManager
from .utils.input import print_info, print_success, print_error, print_warning, safe_menu_choice
from .utils.exceptions import WAIError
from .utils.paths import normalize_path


# Framework version
FRAMEWORK_VERSION = "2.0.1"
SPOKE_STRUCTURE_VERSION = "2.1"


class WheelwrightCLI:
    """Main CLI class for Wheelwright."""

    def __init__(self):
        """Initialize CLI."""
        self.framework_path = Path(__file__).parent.parent.resolve()

    def _is_wsl(self) -> bool:
        """Return True when running inside WSL."""
        if os.environ.get("WSL_DISTRO_NAME"):
            return True
        release = platform.release().lower()
        return "microsoft" in release or "wsl" in release

    def _resolve_spoke_root(self, spoke_path: Path) -> Path:
        """Normalize spoke root (project root, not WAI-Spoke)."""
        if spoke_path.name == "WAI-Spoke":
            return spoke_path.parent
        return spoke_path

    def _is_within_path(self, child: Path, parent: Path) -> bool:
        """Return True if child is within parent directory."""
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except Exception:
            return False

    def _format_datetime(self, value: str) -> str:
        """Return a human-readable UTC timestamp for ISO-like inputs."""
        if not value:
            return "Unknown"
        try:
            from datetime import datetime
            normalized = value.replace('Z', '+00:00')
            parsed = datetime.fromisoformat(normalized)
            return parsed.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            return value

    def _detect_start_context(self, cwd: Path) -> tuple:
        """Detect startup context (hub, spoke, uninitialized)."""
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(cwd, verbose=False)
        if hub_path and self._is_within_path(cwd, hub_path):
            return ("hub", hub_path)

        spoke_root = self._resolve_spoke_root(cwd)
        if check_spoke_initialized(spoke_root):
            return ("spoke", spoke_root)

        return ("uninitialized", cwd)

    def _validate_workspace_paths(self, spoke_path: Path) -> None:
        """Validate and persist workspace paths in WAI-State.json."""
        from .utils.input import safe_input, print_warning

        spoke_root = self._resolve_spoke_root(spoke_path)
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
        paths = workspace.setdefault("paths", {})
        win_paths = paths.setdefault("windows", {"root": None, "spoke": None, "hub": None})
        wsl_paths = paths.setdefault("wsl", {"root": None, "spoke": None, "hub": None})
        primary = paths.get("primary")

        is_wsl = self._is_wsl()
        is_windows = os.name == "nt"
        changed = False

        if not primary:
            primary = "wsl" if is_wsl else "windows"
            paths["primary"] = primary
            changed = True

        # Infer root/spoke for current environment.
        if is_windows:
            win_root = str(spoke_root.resolve())
            win_spoke = str((spoke_root / "WAI-Spoke").resolve())
            if not win_paths.get("root"):
                win_paths["root"] = win_root
                changed = True
            if not win_paths.get("spoke"):
                win_paths["spoke"] = win_spoke
                changed = True
        else:
            wsl_root = str(spoke_root.resolve())
            wsl_spoke = str((spoke_root / "WAI-Spoke").resolve())
            if not wsl_paths.get("root"):
                wsl_paths["root"] = wsl_root
                changed = True
            if not wsl_paths.get("spoke"):
                wsl_paths["spoke"] = wsl_spoke
                changed = True

        # Map wheelwright.hub_path into wsl/windows buckets when possible.
        wai_meta = state.setdefault("wheelwright", {})
        hub_path = wai_meta.get("hub_path")
        if hub_path:
            if hub_path.startswith("/") and not wsl_paths.get("hub"):
                wsl_paths["hub"] = hub_path
                changed = True
            if ":" in hub_path[:3] and not win_paths.get("hub"):
                win_paths["hub"] = hub_path
                changed = True

        # Prompt if primary hub path missing.
        if primary == "wsl" and not wsl_paths.get("hub"):
            prompt = "WSL hub path (e.g., /home/mario/projects/wheelwright-ai/hub)"
            value = safe_input(prompt, default=hub_path or "", allow_empty=True)
            if value:
                wsl_paths["hub"] = value
                wai_meta["hub_path"] = value
                changed = True
            else:
                print_warning("  Hub path missing for WSL; set in WAI-State.json to avoid prompts.")
        if primary == "windows" and not win_paths.get("hub"):
            prompt = "Windows hub path (e.g., C:\\\\path\\\\to\\\\hub)"
            value = safe_input(prompt, default=hub_path or "", allow_empty=True)
            if value:
                win_paths["hub"] = value
                wai_meta["hub_path"] = value
                changed = True
            else:
                print_warning("  Hub path missing for Windows; set in WAI-State.json to avoid prompts.")

        # Validate that the primary hub path exists and is accessible.
        if primary == "wsl" and is_wsl and wsl_paths.get("hub"):
            hub_candidate = Path(wsl_paths["hub"])
            if not hub_candidate.exists():
                print_warning(f"  WSL hub path not found: {hub_candidate}")
                prompt = "WSL hub path (must exist)"
                value = safe_input(prompt, default=str(hub_candidate), allow_empty=True)
                if value and Path(value).exists():
                    wsl_paths["hub"] = value
                    wai_meta["hub_path"] = value
                    changed = True
                else:
                    print_warning("  Keeping existing WSL hub path; update WAI-State.json when ready.")
        if primary == "windows" and is_windows and win_paths.get("hub"):
            hub_candidate = Path(win_paths["hub"])
            if not hub_candidate.exists():
                print_warning(f"  Windows hub path not found: {hub_candidate}")
                prompt = "Windows hub path (must exist)"
                value = safe_input(prompt, default=str(hub_candidate), allow_empty=True)
                if value and Path(value).exists():
                    win_paths["hub"] = value
                    wai_meta["hub_path"] = value
                    changed = True
                else:
                    print_warning("  Keeping existing Windows hub path; update WAI-State.json when ready.")

        # Keep wheelwright.hub_path aligned to primary.
        if primary == "wsl" and wsl_paths.get("hub") and wai_meta.get("hub_path") != wsl_paths["hub"]:
            wai_meta["hub_path"] = wsl_paths["hub"]
            changed = True
        if primary == "windows" and win_paths.get("hub") and wai_meta.get("hub_path") != win_paths["hub"]:
            wai_meta["hub_path"] = win_paths["hub"]
            changed = True

        if changed:
            state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _show_brand_banner(self) -> None:
        """Show the standard Wheelwright brand banner (Rotating)."""
        from .utils.input import print_info
        import random
        
        # Variant 1: Wide Block (The "Maximized" look)
        v1 = r"""
██╗    ██╗██╗  ██╗███████╗███████╗██╗     ██╗    ██╗██████╗ ██╗ ██████╗ ██╗  ██╗████████╗
██║    ██║██║  ██║██╔════╝██╔════╝██║     ██║    ██║██╔══██╗██║██╔════╝ ██║  ██║╚══██╔══╝
██║ █╗ ██║███████║█████╗  █████╗  ██║     ██║ █╗ ██║██████╔╝██║██║  ███╗███████║   ██║   
██║███╗██║██╔══██║██╔══╝  ██╔══╝  ██║     ██║███╗██║██╔══██╗██║██║   ██║██╔══██║   ██║   
╚███╔███╔╝██║  ██║███████╗███████╗███████╗╚███╔███╔╝██║  ██║██║╚██████╔╝██║  ██║   ██║   
 ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
             >> Build projects that roll forward"""

        # Variant 2: Sleek Slant (Speed / Kinetic feel)
        v2 = r"""
   _       __ __                  __                 _       __    __    __ 
  | |     / // /_   ___   ___    / /_      __ _____ (_)___ _/ /_  / /_  / / 
  | | /| / // __ \ / _ \ / _ \  / /| | /| / // ___// // __ `// __ \/ __/ / /  
  | |/ |/ // / / //  __//  __/ / / | |/ |/ // /   / // /_/ // / / / /_  /_/   
  |__/|__/ \_\/_/ \___/ \___/ /_/  |__/|__/ \_/  /_/ \__, / \_/ /_/_\  (_)    
                                                    /____/                    
           >> Build projects that roll forward"""

        # Variant 3: Compact Stack (Dense / Tech feel)
        v3 = r"""
 __        __ _               _                 _       _     _ 
 \ \      / /| |__   ___  ___| |_      __ _ __ (_) __ _| |__ | |_ 
  \ \ /\ / / | '_ \ / _ \/ _ \ \ \ /\ / / '__|| |/ _` | '_ \| __|
   \ V  V /  | | | |  __/  __/ |\ V  V /| |   | | (_| | | | | |_ 
    \_/\_/   |_| |_|\___|\___|_| \_/\_/ |_|   |_|\__, |_| |_|\__|
                                                 |___/           
       >> Build projects that roll forward"""

        variants = [(v1, 90), (v2, 80), (v3, 60)]
        logo, width = random.choice(variants)
        
        print_info("\n" + "=" * width)
        print_info(logo)
        print_info("=" * width)
        print_info("")

    # Menu rendering utilities
    def _render_menu_header(self, title: str, breadcrumb: Optional[List[str]] = None, status: Optional[str] = None):
        """
        Render consistent menu header with breadcrumb and optional status.
        
        Args:
            title: Menu title (used if no breadcrumb)
            breadcrumb: List of navigation path elements, e.g., ["Main Menu", "Hub"]
            status: Optional status line to show below title
        """
        from .utils.input import print_info
        
        # Build breadcrumb text
        if breadcrumb and len(breadcrumb) > 1:
            breadcrumb_text = " > ".join(breadcrumb)
        else:
            breadcrumb_text = title
        
        # Render header
        print_info("\n" + "=" * 60)
        print_info(f"           {breadcrumb_text}")
        if status:
            print_info(f"           {status}")
        print_info("=" * 60)
        print_info("")

    def _cleanup_deprecated_files(self, spoke_path: Path) -> List[str]:
        """
        Clean up deprecated files during teach operation.
        Archives files that have been replaced by the lug system.
        
        Args:
            spoke_path: Path to the spoke directory
            
        Returns:
            List of cleaned filenames
        """
        from .utils.input import print_info
        
        deprecated_files = [
            'WAI-Backlog.md',              # Replaced by lugs.jsonl
            'WAI-Implementation-Summary.md', # Replaced by lugs-closed.jsonl
        ]
        
        wai_spoke = spoke_path / 'WAI-Spoke'
        if not wai_spoke.exists():
            return []
        
        cleaned = []
        for filename in deprecated_files:
            file_path = wai_spoke / filename
            if file_path.exists():
                # Archive before deleting (allows recovery if needed)
                archive_path = wai_spoke / f'.archived-{filename}'
                try:
                    file_path.rename(archive_path)
                    cleaned.append(filename)
                except Exception:
                    pass  # Ignore errors, continue cleanup
        
        return cleaned

    def _confirm_exit(self) -> bool:
        """Confirm exit with user."""
        from .utils.input import safe_confirm
        return safe_confirm("  Exit WAI CLI?", default=True)

    def run(self):
        """Main entry point with command routing."""
        parser = self._create_parser()
        args = parser.parse_args()

        # Handle no command - context detection
        if not args.command:
            self._handle_no_command(parser)
            return

        # Route to command handlers
        try:
            self._route_command(args, parser)
        except KeyboardInterrupt:
            print_info("\n\nOperation cancelled by user.")
            sys.exit(130)
        except WAIError as e:
            print_error(str(e))
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            sys.exit(1)

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description='Wheelwright Framework - Build AI wheels that roll forward forever',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  WAI                         Auto-detect context and initialize
  WAI init                    Initialize spoke in current directory
  WAI status                  Show spoke status
  WAI group create <name>     Create a project group
  WAI group list              List all groups

"We aren't reinventing the wheel - we're evolving it faster than one person ever could."
            '''
        )

        subparsers = parser.add_subparsers(dest='command', help='Commands')

        # Init command
        init_parser = subparsers.add_parser('init', help='Initialize spoke')
        init_parser.add_argument('path', nargs='?', default=None, help='Project path (default: interactive)')

        # Status command
        status_parser = subparsers.add_parser('status', help='Show spoke status')
        status_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        # Update command
        update_parser = subparsers.add_parser(
            'absorbe',
            aliases=['update'],
            help='Process seed folders and archive sprawl'
        )
        update_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        # Hub commands
        hub_parser = subparsers.add_parser('hub', help='Hub management')
        hub_subparsers = hub_parser.add_subparsers(dest='hub_command')

        hub_create = hub_subparsers.add_parser('create', help='Create a new hub')
        hub_create.add_argument('path', nargs='?', default=None, help='Hub location')

        hub_locate = hub_subparsers.add_parser('locate', help='Find hub location')

        # Projects commands
        projects_parser = subparsers.add_parser('projects', help='Project management')
        projects_subparsers = projects_parser.add_subparsers(dest='projects_command')

        projects_add = projects_subparsers.add_parser('add', help='Add projects to hub')
        projects_add.add_argument('--scan', nargs='+', help='Paths to scan for projects')

        projects_list = projects_subparsers.add_parser('list', help='List registered projects')
        projects_list.add_argument('--group', help='Filter by group')

        # Group commands
        group_parser = subparsers.add_parser('group', help='Group management')
        group_subparsers = group_parser.add_subparsers(dest='group_command')

        # group create
        group_create = group_subparsers.add_parser('create', help='Create a new group')
        group_create.add_argument('name', help='Group name')
        group_create.add_argument('--description', '-d', help='Group description')

        # group list
        group_list = group_subparsers.add_parser('list', help='List all groups')
        group_list.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')

        # group add-spoke
        group_add_spoke = group_subparsers.add_parser('add-spoke', help='Add spoke to group')
        group_add_spoke.add_argument('group', help='Group name')
        group_add_spoke.add_argument('spoke', help='Spoke name or path')

        # group remove-spoke
        group_remove_spoke = group_subparsers.add_parser('remove-spoke', help='Remove spoke from group')
        group_remove_spoke.add_argument('group', help='Group name')
        group_remove_spoke.add_argument('spoke', help='Spoke name or path')

        # group delete
        group_delete = group_subparsers.add_parser('delete', help='Delete a group')
        group_delete.add_argument('name', help='Group name')
        group_delete.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

        lug_parser = subparsers.add_parser('lug', help='Lug task/dependency graph management')
        lug_parser.add_argument('lug_args', nargs=argparse.REMAINDER, help='Lug sub-command and arguments')

        # Sync command (structure upgrade)
        sync_parser = subparsers.add_parser('sync', help='Upgrade spoke structure')
        sync_parser.add_argument('--all', action='store_true', help='Upgrade all spokes')

        # Closeout command
        closeout_parser = subparsers.add_parser('closeout', help='Generate session closeout')
        closeout_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')
        closeout_parser.add_argument('--non-interactive', action='store_true', help='Skip confirmations')
        closeout_parser.add_argument('--skip-quality-gates', action='store_true', help='Skip quality gates (tests, etc.)')

        # Stats command
        stats_parser = subparsers.add_parser('stats', help='Show session analytics and metrics')
        stats_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        # Baseline command
        baseline_parser = subparsers.add_parser('baseline', help='Manage baseline mode tracking')
        baseline_subparsers = baseline_parser.add_subparsers(dest='baseline_command')

        baseline_enable = baseline_subparsers.add_parser('enable', help='Enable baseline mode')
        baseline_enable.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        baseline_disable = baseline_subparsers.add_parser('disable', help='Disable baseline mode and lock data')
        baseline_disable.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        baseline_status = baseline_subparsers.add_parser('status', help='Show baseline mode status')
        baseline_status.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        baseline_run = baseline_subparsers.add_parser('run', help='Run automated baseline comparison')
        baseline_run.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')
        baseline_run.add_argument('--ide', help='IDE name (e.g., "Codex CLI")')
        baseline_run.add_argument('--model', help='AI model name (e.g., "GPT-5")')
        baseline_run.add_argument('--notes', help='Optional notes for the run')

        # Time command
        time_parser = subparsers.add_parser('time', help='Show current session token usage and capacity')
        time_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        # Teach command (Share learnings with Hub)
        teach_parser = subparsers.add_parser('teach', help='Share project learnings with the Hub')
        teach_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')

        # Shipit command (closeout + git commit)
        shipit_parser = subparsers.add_parser('shipit', help='Closeout session and create git commit')
        shipit_parser.add_argument('path', nargs='?', default='.', help='Project path (default: current directory)')
        shipit_parser.add_argument('--non-interactive', action='store_true', help='Skip confirmations')
        shipit_parser.add_argument('--no-push', action='store_true', help='Skip pushing to remote')
        shipit_parser.add_argument('--skip-quality-gates', action='store_true', help='Skip quality gates (tests, etc.)')

        # Template commands
        template_parser = subparsers.add_parser('template', help='Manage project templates')
        template_subparsers = template_parser.add_subparsers(dest='template_command')

        template_create = template_subparsers.add_parser('create', help='Create template from spoke')
        template_create.add_argument('name', help='Template name')
        template_create.add_argument('--path', default='.', help='Spoke path (default: current directory)')
        template_create.add_argument('--description', '-d', help='Template description')

        template_list = template_subparsers.add_parser('list', help='List available templates')

        template_apply = template_subparsers.add_parser('apply', help='Apply template to new project')
        template_apply.add_argument('name', help='Template name')
        template_apply.add_argument('path', help='Target project path')

        template_delete = template_subparsers.add_parser('delete', help='Delete a template')
        template_delete.add_argument('name', help='Template name')
        template_delete.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

        # Context command (placeholder)
        context_parser = subparsers.add_parser('context', help='Output context for LLM paste')
        context_parser.add_argument('path', nargs='?', default='.', help='Project path')

        subparsers.add_parser('changelog', help='Generate CHANGELOG.md from closed Lugs')
    
        # Configure IDE command
        config_ide_parser = subparsers.add_parser('configure-ide', help='Configure IDE integration')
        config_ide_subparsers = config_ide_parser.add_subparsers(dest='config_ide_command')

        config_ide_detect = config_ide_subparsers.add_parser('detect', help='Detect IDEs in use')
        config_ide_detect.add_argument('path', nargs='?', default='.', help='Project path')

        config_ide_list = config_ide_subparsers.add_parser('list', help='List supported IDE integrations')
        config_ide_list.add_argument('path', nargs='?', default='.', help='Project path')

        config_ide_setup = config_ide_subparsers.add_parser('setup', help='Setup IDE configuration')
        config_ide_setup.add_argument('ide', nargs='?', help='IDE name (default: all detected)')
        config_ide_setup.add_argument('path', nargs='?', default='.', help='Project path')
        config_ide_setup.add_argument('--force', action='store_true', help='Overwrite existing config')

        config_ide_capabilities = config_ide_subparsers.add_parser('capabilities', help='Show IDE capabilities')
        config_ide_capabilities.add_argument('ide', nargs='?', help='IDE name (default: all detected)')
        config_ide_capabilities.add_argument('path', nargs='?', default='.', help='Project path')

        config_ide_optimize = config_ide_subparsers.add_parser('optimize', help='Get optimization suggestions')
        config_ide_optimize.add_argument('path', nargs='?', default='.', help='Project path')

        # Version command
        version_parser = subparsers.add_parser('version', help='Show version info')

        return parser

    def _handle_no_command(self, parser):
        """
        Handle no command - interactive menu based on context.

        Logic:
        1. If in hub folder → hub menu
        2. If in spoke folder → analysis then spoke menu
        3. Otherwise → initialization intro
        """
        from .utils.input import safe_confirm

        cwd = Path.cwd()
        context, ctx_path = self._detect_start_context(cwd)

        if context == "hub":
            self._show_hub_actions_menu()
            return

        if context == "spoke":
            self._show_spoke_analysis(ctx_path)
            if self._is_framework_directory(ctx_path):
                self._show_framework_menu(ctx_path)
            else:
                self._show_spoke_actions_menu(ctx_path)
            return

        self._show_uninitialized_intro(cwd)
        if safe_confirm("Initialize WAI-Spoke here?", default=False):
            try:
                init_spoke(cwd, is_framework=False, verbose=True)
                self._show_spoke_analysis(cwd)
                self._show_spoke_actions_menu(cwd)
            except Exception as exc:
                print_error(f"Init failed: {exc}")
        
        # Fallback to main menu instead of exit
        self._show_framework_menu(cwd)
        return

    def _show_uninitialized_intro(self, project_path: Path) -> None:
        """Show a short WAI intro for uninitialized projects."""
        self._show_brand_banner()
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

    def _show_spoke_analysis(self, spoke_path: Path) -> None:
        """Show a focused analysis for an initialized spoke project."""
        spoke_root = self._resolve_spoke_root(spoke_path)
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
        self._show_brand_banner()
        
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

    def _show_framework_menu(self, framework_path: Path):
        """Show interactive menu for framework directory."""
        # Banner already shown by _show_spoke_analysis in interactive flow

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
                    self._create_parser().print_help()
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
                            import json
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
                self._render_menu_header("Wheelwright AI", status=last_learn_text.strip(" │") if last_learn_text else None)
                
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
                    self._show_hub_actions_menu()
                elif choice == "spokes":
                    self._show_spokes_menu(framework_path)
                elif choice == "lugs":
                    # Show lugs list
                    from .commands.lug import lug_command_list
                    args = type('Args', (), {'spoke_path': str(framework_path), 'status': None, 'type': None, 'priority': None})()
                    lug_command_list(args)
                    input("\n  Press Enter to continue...")
                elif choice == "knowledge":
                    self._show_knowledge_base_menu()
                elif choice == "statistics":
                    self._show_statistics_menu()
                elif choice == "about":
                    self._show_wheelwright_menu(framework_path)
                elif choice == "help":
                    self._show_help_menu()
                elif choice == "back" or choice is None:
                    return
                elif choice == "quit":
                    if self._confirm_exit():
                        import sys
                        print_info("\n  👋 Goodbye!")
                        sys.exit(0)

    def _show_spoke_menu(self, spoke_path: Path):
        """Show interactive menu for spoke directory."""
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
                self._cmd_status(type('Args', (), {'path': '.'})())
            elif choice == "sync":
                self._cmd_sync(type('Args', (), {'all': False})())
            elif choice == "closeout":
                self._cmd_closeout(type('Args', (), {'path': str(spoke_path)})())
            elif choice == "context":
                self._cmd_context(type('Args', (), {'path': '.'})())
            elif choice == "update":
                self._cmd_update(type('Args', (), {'path': '.'})())
            elif choice == "review":
                self._show_project_review(spoke_path)
            elif choice == "wheelwright":
                self._show_wheelwright_menu(spoke_path)
            elif choice == "help":
                self._create_parser().print_help()
            elif choice == "quit" or choice is None:
                return

    def _show_init_menu(self, cwd: Path):
        """Show menu for uninitialized directory."""
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
                self._create_parser().print_help()
            elif choice == "quit" or choice is None:
                return

    def _show_baseline_menu(self, spoke_path: Path):
        """Show baseline tracking menu for a spoke."""
        import json

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
                self._cmd_baseline(type('Args', (), {'baseline_command': 'enable', 'path': str(spoke_path)})())
                input("\n  Press Enter to continue...")
            elif choice == "disable":
                self._cmd_baseline(type('Args', (), {'baseline_command': 'disable', 'path': str(spoke_path)})())
                input("\n  Press Enter to continue...")
            elif choice == "status":
                self._cmd_baseline(type('Args', (), {'baseline_command': 'status', 'path': str(spoke_path)})())
                input("\n  Press Enter to continue...")
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _show_wheelwright_menu(self, spoke_path: Path):
        """Show Wheelwright overview menu."""
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
                self._show_evolution_menu(spoke_path)
            elif choice == "features":
                self._show_features_menu()
            elif choice == "integrations":
                self._show_integrations_menu(spoke_path)
            elif choice == "testing":
                self._show_testing_menu(spoke_path)
            elif choice == "benchmarks":
                self._show_benchmark_logs(spoke_path)
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _show_evolution_menu(self, spoke_path: Path):
        """Show evolution metrics and baseline history."""
        runs = self._load_baseline_runs(spoke_path)
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
            self._run_baseline_comparison(spoke_path)
        elif choice == "list":
            self._print_baseline_runs(runs)
            input("\n  Press Enter to continue...")
        elif choice == "quit":
            if self._confirm_exit():
                import sys
                print_info("\n  👋 Goodbye!")
                sys.exit(0)

    def _show_features_menu(self):
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

    def _show_integrations_menu(self, spoke_path: Path):
        """Show integrations status and auto-regenerate if needed."""
        from .integrations.manager import IDEManager

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

    def _show_testing_menu(self, spoke_path: Path):
        """Show testing menu and run tests."""
        import subprocess
        from datetime import datetime

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
                self._log_test_result(
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
                self._log_test_result(
                    spoke_path,
                    test_name="WAI-Spoke/hooks/test-session-start.sh",
                    exit_code=result.returncode,
                    output=result.stdout + result.stderr
                )
                print(result.stdout or result.stderr)
                input("\n  Press Enter to continue...")
            elif choice == "log":
                self._print_test_log(spoke_path)
                input("\n  Press Enter to continue...")
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _load_baseline_runs(self, spoke_path: Path) -> list:
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
                    import json
                    runs.append(json.loads(line))
                except Exception:
                    continue
        return runs

    def _print_baseline_runs(self, runs: list):
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

    def _log_test_result(self, spoke_path: Path, test_name: str, exit_code: int, output: str):
        """Append test result to log."""
        from datetime import datetime
        import json

        log_path = spoke_path / 'WAI-Spoke' / 'WAI-Testing-Log.jsonl'
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "test": test_name,
            "exit_code": exit_code,
            "status": "pass" if exit_code == 0 else "fail"
        }
        with open(log_path, 'a') as f:
            f.write(json.dumps(entry) + "\n")

    def _print_test_log(self, spoke_path: Path):
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
                    import json
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

    def _show_benchmark_logs(self, spoke_path: Path):
        """Show benchmark execution logs."""
        benchmark_log = spoke_path / 'WAI-Spoke' / 'benchmark-log.txt'
        
        if not benchmark_log.exists():
            print_info("\n  No benchmark logs found.")
            print_info("  Run benchmarks first: Wheelwright Menu → Testing → Run Benchmarks\n")
            input("  Press Enter to continue...")
            return
        
        # Show last 100 lines of log
        try:
            with open(benchmark_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print_info("\n" + "=" * 60)
            print_info("         Benchmark Logs (Last 100 Lines)")
            print_info("=" * 60 + "\n")
            
            for line in lines[-100:]:
                print_info(f"  {line.rstrip()}")
            
            print_info("\n" + "=" * 60)
            print_info(f"  Full log: {benchmark_log}")
            print_info("=" * 60)
            input("\n  Press Enter to continue...")
        except Exception as e:
            print_error(f"  Failed to read benchmark log: {e}")
            input("\n  Press Enter to continue...")

    def _show_spokes_menu(self, framework_path: Path):
        """Show Spokes menu with registry listing and management."""
        import json
        from datetime import datetime

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
            from .utils.registry import load_registry
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
                    state_data = self._get_spoke_details(Path(path))
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

                from .utils.input import safe_confirm, safe_input, print_warning
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
                                        self._show_spoke_actions_menu(spoke_path)
                                    except Exception as exc:
                                        print_error(f"Init failed: {exc}")
                                continue
                            self._show_spoke_actions_menu(spoke_path)
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
                from .utils.input import safe_input
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

                self._projects_add(args)
                input("\n  Press Enter to continue...")
            elif choice == "modify":
                self._show_modify_projects_menu(hub_path, projects)
            elif choice == "groups":
                self._show_groups_menu()
            elif choice == "refresh":
                continue  # Reload
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _show_modify_projects_menu(self, hub_path: Path, projects: list):
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
                self._projects_remove(hub_path, projects)
                input("\n  Press Enter to continue...")
                return  # Return to parent menu to refresh list
            elif choice == "rename":
                self._projects_rename(hub_path, projects)
                input("\n  Press Enter to continue...")
                return  # Return to parent menu to refresh list
            elif choice == "add_to_group":
                self._projects_add_to_group(hub_path, projects)
                input("\n  Press Enter to continue...")
                return  # Return to parent menu
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _get_spoke_details(self, spoke_path: Path):
        """Get detailed information about a spoke."""
        import json
        from datetime import datetime

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

    def _show_groups_menu(self):
        """Show Groups menu (child of Spokes)."""
        from .utils.input import safe_input

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
                if self._confirm_exit():
                    import sys
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
                    from .utils.input import safe_confirm
                    confirm = safe_confirm(f"  Delete group '{group_name}'?", default=False)
                    if confirm:
                        groups_manager.delete_group(group_name, force=True)

    def _show_spoke_actions_menu(self, spoke_path: Path):
        """Show actions for Spoke object."""
        while True:
            # Get status info for header
            last_modified = "Unknown"
            wai_uptodate = True
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
            
            self._render_menu_header("WAI", breadcrumb=["WAI", project_name], status=status_line)
            
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
            if self._is_framework_directory(spoke_path):
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
            if self._is_framework_directory(spoke_path):
                options.append(('h', 'h', '🏢 Hub', 'hub'))
            
            options.extend([('b', 'b', '⬅️  Back', 'back'), ('q', 'q', '👋 Quit', 'quit')])

            choice = safe_menu_choice("Select", options, default='s')

            if choice == "foundation":
                self._run_foundation_setup(spoke_path)
            elif choice == "status":
                # Combined status + review
                self._show_spoke_status_and_review(spoke_path)
            elif choice == "about":
                # New about submenu
                self._show_project_about_menu(spoke_path)
            elif choice == "sync":
                # Combined absorb + upgrade
                print_info("\n  Running Sync (Absorb + Upgrade)...")
                self._cmd_update(type('Args', (), {'path': str(spoke_path)})())
                # Also run cleanup
                cleaned = self._cleanup_deprecated_files(spoke_path)
                if cleaned:
                    print_info(f"  Cleaned up deprecated files: {', '.join(cleaned)}")
                    
                self._cmd_sync(type('Args', (), {'all': False})())
                input("\n  Press Enter to continue...")
            elif choice == "analysis":
                self._show_spoke_analysis(spoke_path)
            elif choice == "hub":
                self._show_hub_actions_menu()
            elif choice == "back":
                # Return to parent (which will fall back to framework/main menu in _handle_no_command)
                return
            elif choice == "quit" or choice is None:
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)

    def _show_spoke_status_and_review(self, spoke_path: Path) -> None:
        """Combined status and review display."""
        # Call existing status command
        self._cmd_status(type('Args', (), {'path': str(spoke_path)})())
        input("\n  Press Enter to continue...")

    def _show_project_about_menu(self, spoke_path: Path) -> None:
        """Show project about submenu with various details."""
        while True:
            self._render_menu_header("About Project", breadcrumb=["WAI", spoke_path.name, "About"])
            
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
                self._cmd_status(type('Args', (), {'path': str(spoke_path)})())
                input("\n  Press Enter to continue...")
            elif choice == "structure":
                self._show_project_review(spoke_path)
                input("\n  Press Enter to continue...")
            elif choice == "foundation":
                self._run_foundation_setup(spoke_path)
            elif choice == "back" or choice is None:
                return

    def _run_foundation_setup(self, spoke_path: Path) -> None:
        """Prompt for foundation info and update WAI-State.json."""
        from .utils.input import safe_input, safe_confirm, print_info, print_success, print_warning, print_error
        from datetime import datetime

        state_file = spoke_path / 'WAI-Spoke' / 'WAI-State.json'
        if not state_file.exists():
            print_error("WAI-State.json not found for this spoke.")
            return

        try:
            state = json.loads(state_file.read_text())
        except Exception as exc:
            print_error(f"Failed to read WAI-State.json: {exc}")
            return

        foundation = state.get('_project_foundation', {})
        identity = foundation.get('identity', {})
        boundaries = foundation.get('boundaries', {})
        approach = foundation.get('approach', {})

        def parse_list(value: str):
            items = []
            for chunk in (value or "").split(','):
                item = chunk.strip()
                if item:
                    items.append(item)
            return items

        print_info("\n🧱 Foundation Setup\n")
        
        # Show current state first
        print_info("  Current Configuration:")
        print_info(f"    Name: {identity.get('name', spoke_path.name)}")
        print_info(f"    One-liner: {identity.get('one_liner', 'Not set')}")
        print_info(f"    Type: {identity.get('type', 'software')}")
        print_info("")
        
        if not safe_confirm("  Update foundation settings?", default=False):
            return

        # Helper for field updates
        def update_field(label: str, current_val: str, examples: list = None) -> str:
            print_info(f"\n  {label}")
            print_info(f"  Current: {current_val or 'Empty'}")
            
            if safe_confirm(f"  Change {label}?", default=False):
                if examples:
                    print_info("\n  Examples:")
                    for ex in examples:
                        print_info(f"   • {ex}")
                    print_info("")
                
                val = safe_input(f"  New {label}", default=current_val, allow_empty=True)
                return val
            return current_val

        # Update Identity
        name = update_field("Project name", identity.get('name', spoke_path.name), ["CondoShield CRM", "WAI Framework"])
        one_liner = update_field("One-liner", identity.get('one_liner', ''), ["CRM for sales ops", "AI-first dev framework"])
        success = update_field("Success looks like", identity.get('success_looks_like', ''), ["Clear pipeline", "Fast iteration"])
        proj_type = update_field("Project type", identity.get('type', 'software'), ["software", "research", "design"])

        # Update Boundaries
        in_scope_list = boundaries.get('in_scope', [])
        in_scope_str = ", ".join(in_scope_list)
        in_scope_new = update_field("In scope", in_scope_str, ["lead management", "core api", "frontend"])
        
        out_scope_list = boundaries.get('out_of_scope', [])
        out_scope_str = ", ".join(out_scope_list)
        out_scope_new = update_field("Out of scope", out_scope_str, ["marketing site", "billing", "legacy code"])

        constraints_list = boundaries.get('constraints', [])
        constraints_str = ", ".join(constraints_list)
        constraints_new = update_field("Constraints", constraints_str, ["no external dbs", "mobile first", "offline support"])

        # Update Approach
        ai_style = update_field("AI collaboration style", approach.get('ai_collaboration_style', 'yolo'), ["yolo (fast)", "check-in (cautious)"])
        review = update_field("Review process", approach.get('review_process', 'Closeout logs'), ["Closeout logs", "PR review", "Pair programming"])

        print_info("")
        if not safe_confirm("  Save changes?", default=True):
            print_info("Cancelled.")
            return

        in_scope = in_scope_new
        out_scope = out_scope_new
        constraints = constraints_new

        updated = dict(foundation)
        updated['completed'] = True
        updated['completed_at'] = datetime.utcnow().isoformat() + "Z"
        updated['completed_with'] = "WAI"
        updated['identity'] = {
            'type': proj_type or 'software',
            'name': name or spoke_path.name,
            'one_liner': one_liner or '',
            'success_looks_like': success or ''
        }
        updated['boundaries'] = {
            'in_scope': parse_list(in_scope),
            'out_of_scope': parse_list(out_scope),
            'constraints': parse_list(constraints),
            'deferred': boundaries.get('deferred', [])
        }
        updated['approach'] = {
            'stack_or_tools': approach.get('stack_or_tools', []),
            'workflow': approach.get('workflow', ''),
            'ai_collaboration_style': ai_style or 'yolo',
            'review_process': review or 'Closeout logs'
        }

        state['_project_foundation'] = updated

        try:
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            print_success("Foundation saved.")
        except Exception as exc:
            print_error(f"Failed to write WAI-State.json: {exc}")

    def _show_project_review(self, spoke_path: Path) -> None:
        """Show a project discovery snapshot."""
        from .spoke_update import SpokeUpdateProcessor

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

    def _show_hub_actions_menu(self):
        """Show actions for Hub object with stats and enhanced features."""
        import json

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
                        from datetime import datetime
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
                self._hub_locate_with_candidates()
                input("\n  Press Enter to continue...")
            elif choice == "locate":
                self._hub_locate_with_candidates()
                input("\n  Press Enter to continue...")
            elif choice == "learn":
                # "Learn" means hub learns FROM spokes
                self._hub_trigger_teach(hub_path)  # This function makes hub learn from spokes
                input("\n  Press Enter to continue...")
            elif choice == "teach":
                # "Teach" means hub teaches TO spokes
                self._hub_trigger_learn(hub_path)  # This function makes hub teach to spokes
                input("\n  Press Enter to continue...")
            elif choice == "create":
                self._hub_create(type('Args', (), {'path': None})())
                input("\n  Press Enter to continue...")
            elif choice == "version":
                # Show version without pausing
                print_info(f"\n  Wheelwright Framework v{FRAMEWORK_VERSION}")
                print_info(f"  Spoke Structure v{SPOKE_STRUCTURE_VERSION}")
            elif choice == "quit":
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return

    def _show_statistics_menu(self):
        """Show statistics with insights and recommendations."""
        from .utils.input import safe_choice
        import json

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
                    self._hub_create(type('Args', (), {'path': None})())
                else:
                    return
                continue

            # Load hub and spoke data
            from .utils.registry import load_registry
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
                # TODO: Check hub-profile.json for last_learn_timestamp
                # For now, recommend if spokes exist and have been active
                has_recent_activity = False
                if hub_path:
                    hub_profile = hub_path / 'hub-profile.json'
                    if hub_profile.exists():
                        try:
                            import json
                            from datetime import datetime, timedelta
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
                if self._confirm_exit():
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
                            self._projects_add(type('Args', (), {'scan': None})())
                        elif rec['command'] == 'groups_create':
                            self._show_groups_menu()
                        elif rec['command'] == 'teach_all':
                            print_info("\n  Teach all feature coming soon.")
            elif choice == "refresh":
                continue  # Refresh
            elif choice == "back" or choice is None:
                return

    def _show_knowledge_base_menu(self):
        """Show knowledge base menu - review learnings and insights."""
        import json
        from datetime import datetime

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
                    if self._confirm_exit():
                        import sys
                        print_info("\n  👋 Goodbye!")
                        sys.exit(0)
                else:
                    return

            # Load hub learnings summary
            signals_summary = self._get_hub_learnings_summary(hub_path)

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
                if self._confirm_exit():
                    import sys
                    print_info("\n  👋 Goodbye!")
                    sys.exit(0)
            elif choice == "back" or choice is None:
                return
            elif choice in ['patterns', 'decisions', 'insights', 'warnings', 'all']:
                self._show_learnings_by_category(hub_path, choice)
                input("\n  Press Enter to continue...")

    def _get_hub_learnings_summary(self, hub_path: Path):
        """Get summary of hub learnings."""
        import json
        from datetime import datetime

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

    def _show_learnings_by_category(self, hub_path: Path, category: str):
        """Show learnings filtered by category."""
        import json

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

    def _show_help_menu(self):
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
                if self._confirm_exit():
                    import sys
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

    def _show_projects_actions_menu(self):
        """Show actions for Projects object."""
        from .utils.input import safe_choice

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
                self._projects_list(type('Args', (), {'group': None})())
            elif choice == "2":
                self._projects_add(type('Args', (), {'scan': None})())
            elif choice == "3":
                from .utils.input import safe_input
                group_name = safe_input("Group name", allow_empty=False)
                if group_name:
                    self._projects_list(type('Args', (), {'group': group_name})())
            elif choice == "4" or choice is None:
                return

    def _show_groups_actions_menu(self):
        """Show actions for Groups object."""
        from .utils.input import safe_choice, safe_input

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
                    from .utils.input import safe_confirm
                    confirm = safe_confirm(f"Delete group '{group_name}'?", default=False)
                    if confirm:
                        groups_manager.delete_group(group_name, force=True)

    def _is_framework_directory(self, path: Path) -> bool:
        """
        Check if path is the framework directory.

        Checks:
        - Has WAI script
        - Has templates/ directory
        - Has wai_cli/ package

        Args:
            path: Path to check

        Returns:
            True if framework directory
        """
        return (
            (path / 'WAI').exists() and
            (path / 'templates').exists() and
            (path / 'wai_cli').exists()
        )

    def _route_command(self, args, parser):
        """Route command to appropriate handler."""
        path_commands = {
            "status",
            "update",
            "sync",
            "closeout",
            "stats",
            "baseline",
            "time",
            "teach",
            "shipit",
            "template",
            "context"
        }
        if args.command in path_commands:
            path_arg = getattr(args, "path", ".") or "."
            try:
                spoke_path = normalize_path(path_arg)
                self._validate_workspace_paths(spoke_path)
            except Exception:
                pass

        if args.command == 'init':
            self._cmd_init(args)
        elif args.command == 'status':
            self._cmd_status(args)
        elif args.command == 'hub':
            self._cmd_hub(args)
        elif args.command == 'projects':
            self._cmd_projects(args)
        elif args.command == 'group':
            self._cmd_group(args)
        elif args.command == 'sync':
            self._cmd_sync(args)
        elif args.command == 'update':
            self._cmd_update(args)
        elif args.command == 'closeout':
            self._cmd_closeout(args)
        elif args.command == 'stats':
            self._cmd_stats(args)
        elif args.command == 'baseline':
            self._cmd_baseline(args)
        elif args.command == 'time':
            self._cmd_time(args)
        elif args.command == 'teach':
            self._cmd_teach(args)
        elif args.command == 'shipit':
            self._cmd_shipit(args)
        elif args.command == 'template':
            self._cmd_template(args)
        elif args.command == 'lug':
            self._cmd_lug(args)
        elif args.command == 'changelog':
            self._cmd_changelog(args)
        elif args.command == 'configure-ide':
            self._cmd_configure_ide(args)
        elif args.command == 'context':
            self._cmd_context(args)
        elif args.command == 'version':
            self._cmd_version()
        else:
            parser.print_help()

    # Command handlers

    def _cmd_init(self, args):
        """Handle init command."""
        if args.path:
            # Initialize specific path
            try:
                spoke_path = normalize_path(args.path)
                from .init import init_spoke
                init_spoke(spoke_path, is_framework=False, verbose=True)
                print_success(f"\nSpoke initialized at {spoke_path}")
            except Exception as e:
                print_error(f"Initialization failed: {e}")
        else:
            # Interactive initialization
            init_spoke_interactive(verbose=True)

    def _cmd_status(self, args):
        """Handle status command."""
        from .commands.status import show_status
        show_status(args.path)

    def _cmd_hub(self, args):
        """Handle hub commands."""
        if args.hub_command == 'create':
            self._hub_create(args)
        elif args.hub_command == 'locate':
            self._hub_locate()
        else:
            print_info("Hub commands: create, locate")

    def _hub_create(self, args):
        """Create new hub."""
        hub_manager = HubManager()

        if args.path:
            try:
                hub_path = normalize_path(args.path)
                hub_manager.prompt_create_hub(default_path=hub_path)
            except Exception as e:
                print_error(f"Hub creation failed: {e}")
        else:
            # Interactive with default ../hub
            try:
                cwd = Path.cwd()
                default_path = (cwd.parent / 'hub').resolve()
                hub_manager.prompt_create_hub(default_path=default_path, framework_path=cwd)
            except Exception as e:
                print_error(f"Hub creation failed: {e}")

    def _hub_locate(self):
        """Locate hub."""
        hub_manager = HubManager()
        cwd = Path.cwd()

        hub_path = hub_manager.auto_discover_hub(cwd, verbose=True)

        if hub_path:
            print_success(f"\nHub found at: {hub_path}")
        else:
            print_info("\nNo hub found.")
            print_info("Run 'WAI hub create' to create a new hub.")

    def _hub_locate_with_candidates(self):
        """Locate hub and show all candidates with selection options."""
        from .utils.input import safe_input, safe_confirm

        hub_manager = HubManager()
        cwd = Path.cwd()

        print_info("\n🔍 Scanning for hub candidates...\n")

        # Get all candidates (modify auto_discover to return all)
        candidates = self._get_all_hub_candidates(cwd)

        if not candidates:
            print_info("  No hub candidates found.")
            print_info("  Run 'Create' to initialize a new hub.")
            return

        # Show all candidates
        print_info(f"  Found {len(candidates)} hub candidate(s):\n")
        for i, candidate in enumerate(candidates, 1):
            print_info(f"  [{i}] {candidate.path} (score: {candidate.score})")
            for reason in candidate.reasons[:3]:  # Show top 3 reasons
                print_info(f"      {reason}")
            print_info("")

        if len(candidates) == 1:
            print_success(f"  Using hub: {candidates[0].path}")
            return

        # Multiple candidates - prompt for selection
        print_info("  Multiple hub candidates found. What would you like to do?\n")
        print_info("  1. Use highest-scored hub (recommended)")
        print_info("  2. Select specific hub")
        print_info("  3. Cancel\n")

        choice = safe_input("  Choice", default="1")

        if choice == "1":
            selected = candidates[0]
            print_success(f"\n  Selected: {selected.path}")
        elif choice == "2":
            idx = safe_input(f"  Select hub (1-{len(candidates)})", default="1")
            try:
                selected = candidates[int(idx) - 1]
                print_success(f"\n  Selected: {selected.path}")
            except (ValueError, IndexError):
                print_info("\n  Invalid selection.")
                return
        else:
            return

        # Ask about other candidates
        if len(candidates) > 1:
            print_info(f"\n  Other candidates found:")
            for candidate in candidates[1:]:
                print_info(f"    - {candidate.path}")

            action = safe_input("\n  Action for other hubs? (ignore/subsume/skip)", default="skip")

            if action == "ignore":
                print_info("\n  Ignoring other hubs...")
                self._hub_ignore_candidates([c.path for c in candidates[1:]], selected.path)
            elif action == "subsume":
                print_info("\n  Subsuming other hubs into primary...")
                for candidate in candidates[1:]:
                    self._hub_subsume(source_hub=candidate.path, target_hub=selected.path)

    def _get_all_hub_candidates(self, current_path: Path):
        """Get all hub candidates with scoring."""
        hub_manager = HubManager()

        # Use internal methods to get all candidates
        candidates = []

        # Environment variable
        import os
        env_hub = os.environ.get('WHEELWRIGHT_HUB_PATH')
        if env_hub:
            try:
                from .utils.paths import normalize_path
                env_path = normalize_path(env_hub)
                if env_path.exists():
                    from .hub import HubCandidate
                    candidate = HubCandidate(env_path)
                    candidate.add_score(15, "From $WHEELWRIGHT_HUB_PATH")
                    candidates.append(candidate)
            except Exception:
                pass

        # Parent folder scan
        parent_candidates = hub_manager._scan_parent_folder(current_path)
        candidates.extend(parent_candidates)

        # Score all candidates
        for candidate in candidates:
            hub_manager._score_candidate(candidate)

        # Sort by score
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Return ALL candidates (not filtered by score)
        # This allows user to see and choose even low-scored options
        return candidates

    def _hub_trigger_teach(self, hub_path: Path):
        """Trigger teach event - hub learns from spokes (called by 'Learn' menu option)."""
        from .utils.registry import load_registry
        from .utils.input import safe_confirm

        print_info("\n📚 Learn Event - Hub Learns from Spoke Projects\n")

        # Load and show registered spokes
        try:
            registry = load_registry(hub_path)
            spokes = registry.get('projects', [])  # Registry uses 'projects' not 'spokes'

            if not spokes:
                print_info("  No spokes registered in hub.")
                print_info("  Add spokes first: Main Menu → Spokes → Add Projects")
                return

            print_info("  📊 Preview of what will happen:")
            print_info("")
            print_info(f"  Hub: {hub_path.name}")
            print_info(f"  Spokes to scan: {len(spokes)}")
            print_info("")
            for spoke in spokes[:5]:  # Show first 5
                spoke_name = spoke.get('preferred_name', spoke.get('path', 'Unknown'))
                print_info(f"    • {spoke_name}")
            if len(spokes) > 5:
                print_info(f"    ... and {len(spokes) - 5} more")
            print_info("")
            print_info("  Actions:")
            print_info("    1. Scan each spoke's WAI-Signals.jsonl")
            print_info("    2. Extract high-impact learnings (impact ≥8)")
            print_info("    3. Update hub knowledge base")
            print_info("    4. Record learn timestamp")
            print_info("")

            if not safe_confirm("  Proceed with learning from spokes?", default=False):
                print_info("  Cancelled.")
                return

            # Actually perform the learning
            print_info("\n  📚 Hub learning from spokes...")
            print_info("")

            import json
            from datetime import datetime


            # Create knowledge base directory if it doesn't exist
            kb_dir = hub_path / 'knowledge-base'
            kb_dir.mkdir(exist_ok=True)

            total_new_signals = 0
            spoke_results = []

            for spoke in spokes:
                spoke_path = Path(spoke.get('path', ''))
                spoke_name = spoke.get('preferred_name', spoke_path.name)

                # Look for WAI-Signals.jsonl in the spoke
                signals_file = spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
                if not signals_file.exists():
                    spoke_results.append((spoke_name, 0, "No signals file"))
                    continue

                try:
                    # Read spoke signals
                    new_signals = []
                    
                    # 1. Standard signals
                    if signals_file.exists():
                        with open(signals_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        signal = json.loads(line)
                                        if signal.get('impact', 0) >= 8:
                                            new_signals.append(signal)
                                    except: pass
                    
                    # 2. Promote significant Lugs
                    closed_lugs_file = spoke_path / 'WAI-Spoke' / 'lugs-closed.jsonl'
                    if closed_lugs_file.exists():
                        with open(closed_lugs_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        # Use a simplified parser or LugManager if available, 
                                        # but direct JSON for speed during hub sync
                                        lug_data = json.loads(line)
                                        # Map minified keys if necessary, but here we assume impact/priority
                                        # are stored in lugs.jsonl logic
                                        impact = lug_data.get('i', 0) if 'i' in lug_data else lug_data.get('impact_score', 0)
                                        priority = lug_data.get('p', '') if 'p' in lug_data else lug_data.get('priority', '')
                                        
                                        if (impact >= 8 or priority == 'high'):
                                            new_signals.append({
                                                'type': 'lug_promotion',
                                                'id': lug_data.get('id', 'unknown'),
                                                'title': lug_data.get('title', 'Untitled Lug'),
                                                'summary': lug_data.get('summary', ''),
                                                'impact': impact,
                                                'timestamp': lug_data.get('closed_at', datetime.now().isoformat()),
                                                'origin_spoke': spoke_name
                                            })
                                    except: pass

                    if new_signals:
                        # Append to hub knowledge
                        target_file = kb_dir / f"{spoke_name}-signals.jsonl"
                        
                        existing_ids = set()
                        if target_file.exists():
                            with open(target_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    try:
                                        s = json.loads(line)
                                        if 'id' in s: existing_ids.add(s['id'])
                                    except: pass
                        
                        added = 0
                        with open(target_file, 'a', encoding='utf-8') as f:
                            for signal in new_signals:
                                if signal.get('id') not in existing_ids:
                                    f.write(json.dumps(signal) + "\n")
                                    added += 1
                        
                        spoke_results.append((spoke_name, added, "Updated"))
                        total_new_signals += added
                    else:
                        spoke_results.append((spoke_name, 0, "No high-impact signals"))

                except Exception as e:
                    spoke_results.append((spoke_name, 0, f"Error: {e}"))

            # Generate Hub Index (Map)
            from .hub_indexer import HubIndexer
            try:
                print_info("  🗺️  Regenerating Hub Index...")
                indexer = HubIndexer(hub_path)
                index_path = indexer.generate_index()
                print_success(f"     Index updated: {index_path.name}")
            except Exception as e:
                print_error(f"     Failed to generate index: {e}")

            # Display results
            print_info("  Results by spoke:")
            print_info("")
            for spoke_name, count, status in spoke_results:
                if count > 0:
                    print_success(f"    ✓ {spoke_name}: {count} new signal(s) - {status}")
                else:
                    print_info(f"      {spoke_name}: {count} new signals - {status}")

            print_info("")
            if total_new_signals > 0:
                print_success(f"  ✓ Learn complete! Added {total_new_signals} new signal(s) to hub knowledge base")

                # Update hub profile with last learn timestamp
                profile_path = hub_path / 'hub-profile.json'
                if profile_path.exists():
                    try:
                        profile = json.loads(profile_path.read_text())
                        profile['last_learn_run'] = datetime.now().isoformat()
                        profile_path.write_text(json.dumps(profile, indent=2))
                    except:
                        pass
            else:
                print_info(f"  ✓ Learn complete! No new signals found (all spokes already absorbed)")

            print_info("")
            print_info("  📝 Next: To apply these learnings in an active AI session:")
            print_info("     1. If AI is already working on a spoke project:")
            print_info("        - Say 'Closeout' to end current session")
            print_info("        - Start new session to load updated WAI-Guide.md")
            print_info("     2. Hub knowledge is now available in hub/knowledge-base/")
            print_info("     3. Run 'Teach' to distribute to specific spokes")

        except Exception as e:
            print_error(f"  Error loading registry: {e}")

    def _hub_trigger_learn(self, hub_path: Path):
        """Trigger learn event - spokes learn from hub (called by 'Teach' menu option)."""
        from .utils.registry import load_registry
        from .utils.input import safe_confirm
        from .init import init_spoke

        print_info("\n🎓 Teach Event - Hub Distributes Knowledge to Spokes\n")

        # Auto-Learn first: Ensure we have latest signals
        print_info("  🔄 Auto-Learn: Gathering latest signals from spokes first...")
        self._hub_trigger_teach(hub_path)

        # Load and show registered spokes
        try:
            registry = load_registry(hub_path)
            spokes = registry.get('projects', [])  # Registry uses 'projects' not 'spokes'

            if not spokes:
                print_info("  No spokes registered in hub.")
                print_info("  Add spokes first: Main Menu → Spokes → Add Projects")
                return

            def ensure_spoke_workspace(spoke_path: Path):
                spoke_dir = spoke_path / 'WAI-Spoke'
                created_spoke = False
                workspace_created = []

                if not spoke_dir.exists():
                    try:
                        init_spoke(spoke_path, is_framework=False, verbose=False)
                        created_spoke = True
                    except Exception as exc:
                        return False, created_spoke, workspace_created, f"Init failed: {exc}"

                templates_dir = Path(__file__).parent.parent / 'templates' / 'WAI'
                if not templates_dir.exists():
                    return False, created_spoke, workspace_created, "Templates directory not found"

                workspace_files = ['WAI-Workspace.cmd', 'wai-shell.sh', 'wai-cli-launch.sh']

                def parse_version(value: str) -> tuple:
                    if not value:
                        return (0, 0, 0)
                    try:
                        parts = [int(p) for p in value.strip().split(".")]
                        while len(parts) < 3:
                            parts.append(0)
                        return tuple(parts[:3])
                    except Exception:
                        return (0, 0, 0)

                def extract_version(path: Path) -> tuple:
                    try:
                        text = path.read_text(encoding='utf-8', errors='ignore')
                    except Exception:
                        return (0, 0, 0)
                    for line in text.splitlines()[:10]:
                        if "WAI_WORKSPACE_VERSION" in line:
                            raw = line.split("=", 1)[-1].strip().strip('"').strip("'")
                            return parse_version(raw)
                    return (0, 0, 0)

                for filename in workspace_files:
                    src = templates_dir / filename
                    dst = spoke_dir / filename
                    if not src.exists():
                        continue

                    needs_update = False
                    if not dst.exists():
                        needs_update = True
                    else:
                        src_version = extract_version(src)
                        dst_version = extract_version(dst)
                        if src_version > dst_version:
                            needs_update = True

                    if needs_update:
                        try:
                            dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
                            workspace_created.append(filename)
                        except Exception as exc:
                            return False, created_spoke, workspace_created, f"Failed to write {filename}: {exc}"

                return True, created_spoke, workspace_created, None

            # Check if hub has knowledge to share
            kb_dir = hub_path / 'knowledge-base'
            has_knowledge = kb_dir.exists() and any(kb_dir.glob('*.jsonl'))

            print_info("  📊 Preview of what will happen:")
            print_info("")
            print_info(f"  Hub: {hub_path.name}")
            print_info(f"  Spokes to update: {len(spokes)}")
            print_info("")
            for spoke in spokes[:5]:  # Show first 5
                spoke_name = spoke.get('preferred_name', spoke.get('path', 'Unknown'))
                print_info(f"    • {spoke_name}")
            if len(spokes) > 5:
                print_info(f"    ... and {len(spokes) - 5} more")
            print_info("")
            print_info("  Actions:")
            print_info("    1. Ensure each spoke has WAI-Spoke and workspace files")
            if has_knowledge:
                print_info("    2. Read hub knowledge base patterns")
                print_info("    3. Update each spoke's WAI-Guide.md")
                print_info("    4. Add relevant best practices and learnings")
                print_info("    5. Record teach timestamp")
            print_info("")

            if not has_knowledge:
                print_info("  ⚠️  Hub knowledge base is empty.")
                print_info("  Proceeding will bootstrap WAI-Spoke + workspace files only.")

            if not safe_confirm("  Proceed with distributing knowledge to spokes?", default=False):
                print_info("  Cancelled.")
                return

            # Actually perform the teaching
            print_info("\n  🎓 Hub teaching to spokes...")
            print_info("")

            import json
            from datetime import datetime

            total_updated = 0
            total_bootstrapped = 0
            spoke_updates = []

            # Read all hub knowledge base files
            kb_patterns = []
            for kb_file in kb_dir.glob('*.jsonl'):
                try:
                    with open(kb_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    signal = json.loads(line)
                                    # Extract high-impact patterns
                                    for offer in signal.get('offers', []):
                                        if offer.get('impact', 0) >= 8:
                                            kb_patterns.append({
                                                'type': offer.get('type', 'pattern'),
                                                'topic': offer.get('topic', 'Unknown'),
                                                'context': offer.get('context', ''),
                                                'impact': offer.get('impact', 8),
                                                'source': kb_file.stem
                                            })
                                except json.JSONDecodeError:
                                    pass
                except Exception:
                    pass

            if has_knowledge and not kb_patterns:
                print_error("  No patterns found in knowledge base to distribute.")
                return

            if has_knowledge:
                print_info(f"  Found {len(kb_patterns)} high-impact pattern(s) from hub knowledge base")
                print_info(f"  (Patterns = learnings, best practices, and insights to share)")
                print_info("")

            # Update each spoke
            for spoke in spokes:
                spoke_path = Path(spoke.get('path', ''))
                spoke_name = spoke.get('preferred_name', spoke_path.name)
                wai_spoke_dir = spoke_path / 'WAI-Spoke'

                bootstrap_status = ""
                ok, created_spoke, workspace_created, bootstrap_error = ensure_spoke_workspace(spoke_path)
                if not ok:
                    spoke_updates.append((spoke_name, 0, f"Bootstrap failed: {bootstrap_error}", bootstrap_status))
                    continue

                if created_spoke or workspace_created:
                    total_bootstrapped += 1
                    parts = []
                    if created_spoke:
                        parts.append("initialized")
                    if workspace_created:
                        parts.append("workspace files")
                    bootstrap_status = f"bootstrapped ({', '.join(parts)})"

                if not has_knowledge:
                    spoke_updates.append((spoke_name, 0, "Bootstrap only (no hub knowledge)", bootstrap_status))
                    continue

                try:
                    # Create a hub-learnings file that closeout will reconcile
                    learnings_file = wai_spoke_dir / 'WAI-Hub-Learnings.md'

                    # Generate learnings content
                    content = f"# Hub Learnings - {datetime.now().strftime('%Y-%m-%d')}\n\n"
                    content += "These patterns were distributed from the hub knowledge base.\n"
                    content += "Run closeout to integrate these into your WAI-Guide.md\n\n"

                    # Group by type
                    patterns_by_type = {}
                    for pattern in kb_patterns:
                        ptype = pattern['type']
                        if ptype not in patterns_by_type:
                            patterns_by_type[ptype] = []
                        patterns_by_type[ptype].append(pattern)

                    # Write patterns
                    for ptype, patterns in patterns_by_type.items():
                        content += f"## {ptype.title()}\n\n"
                        for pattern in patterns:
                            content += f"### {pattern['topic']}\n"
                            if pattern['context']:
                                content += f"{pattern['context']}\n"
                            content += f"\n*Impact: {pattern['impact']} | Source: {pattern['source']}*\n\n"

                    # Write the file
                    learnings_file.write_text(content)
                    spoke_updates.append((spoke_name, len(kb_patterns), "✓ Updated", bootstrap_status))
                    total_updated += 1

                except Exception as e:
                    spoke_updates.append((spoke_name, 0, f"Error: {str(e)[:30]}", bootstrap_status))

            # Display results
            print_info("  Results by spoke:")
            print_info("")
            for spoke_name, count, status, bootstrap_status in spoke_updates:
                if bootstrap_status:
                    status = f"{status} | {bootstrap_status}"
                # Don't add another checkmark if status already has one
                if count > 0 or "Updated" in status:
                    print_success(f"    {spoke_name}: {count} pattern(s) - {status}")
                else:
                    print_info(f"      {spoke_name}: {count} patterns - {status}")

            print_info("")
            if total_updated > 0:
                print_success(f"  ✓ Teach complete! Updated {total_updated} spoke(s) with hub knowledge")
                if total_bootstrapped > 0:
                    print_info(f"  ✓ Bootstrapped {total_bootstrapped} spoke(s) with workspace files")

                # Update hub profile with last teach timestamp
                profile_path = hub_path / 'hub-profile.json'
                if profile_path.exists():
                    try:
                        profile = json.loads(profile_path.read_text())
                        profile['last_teach_run'] = datetime.now().isoformat()
                        profile_path.write_text(json.dumps(profile, indent=2))
                    except:
                        pass

                print_info("")
                print_info("  📝 IMPORTANT - Next Steps:")
                print_info("     1. If AI is currently working on one of the updated spokes:")
                print_info("        a. Say 'Closeout' to end the current session")
                print_info("        b. Closeout will reconcile WAI-Hub-Learnings.md into WAI-Guide.md")
                print_info("        c. Start a new session to load the updated guidance")
                print_info("")
                print_info("     2. New files created in each spoke:")
                print_info("        • WAI-Spoke/WAI-Hub-Learnings.md (temporary - for closeout)")
                print_info("")
                print_info("     3. After closeout, patterns will be in:")
                print_info("        • WAI-Spoke/WAI-Guide.md (permanent)")
                print_info("")
                print_info("  💡 This enables seamless learning on the fly!")
            else:
                if total_bootstrapped > 0:
                    print_success(f"  ✓ Bootstrapped {total_bootstrapped} spoke(s) with workspace files")
                else:
                    print_info(f"  No spokes were updated.")

        except Exception as e:
            print_error(f"  Error loading registry: {e}")

    def _hub_ignore_candidates(self, ignore_paths: list, primary_hub: Path):
        """Add hub paths to ignore list in primary hub profile."""
        import json

        try:
            profile_path = primary_hub / 'hub-profile.json'
            if not profile_path.exists():
                print_error("  Hub profile not found.")
                return

            profile = json.loads(profile_path.read_text())

            # Add ignore list to profile
            if 'hub_config' not in profile:
                profile['hub_config'] = {}

            if 'ignored_hubs' not in profile['hub_config']:
                profile['hub_config']['ignored_hubs'] = []

            # Add new ignore paths
            for path in ignore_paths:
                path_str = str(path)
                if path_str not in profile['hub_config']['ignored_hubs']:
                    profile['hub_config']['ignored_hubs'].append(path_str)
                    print_success(f"  Added to ignore list: {path}")

            # Save updated profile
            profile_path.write_text(json.dumps(profile, indent=2))
            print_success("\n  Ignore list updated!")

        except Exception as e:
            print_error(f"  Failed to update ignore list: {e}")

    def _hub_subsume(self, source_hub: Path, target_hub: Path):
        """Merge source hub into target hub."""
        import json
        import shutil
        from .utils.input import safe_confirm

        print_info(f"\n🔄 Subsuming {source_hub.name} → {target_hub.name}\n")

        # Load both registries
        try:
            source_registry_path = source_hub / 'registry' / 'wheel-projects.json'
            target_registry_path = target_hub / 'registry' / 'wheel-projects.json'

            if not source_registry_path.exists():
                print_error(f"  Source registry not found: {source_registry_path}")
                return

            source_registry = json.loads(source_registry_path.read_text())
            target_registry = json.loads(target_registry_path.read_text()) if target_registry_path.exists() else {"version": "2.0", "projects": [], "groups": {}}

            # Merge projects
            source_projects = source_registry.get('projects', [])
            target_projects = target_registry.get('projects', [])
            target_paths = {p['path'] for p in target_projects}

            added_count = 0
            duplicate_count = 0

            for project in source_projects:
                if project['path'] not in target_paths:
                    target_projects.append(project)
                    added_count += 1
                    print_success(f"  ✓ Added: {project.get('name', 'Unknown')}")
                else:
                    duplicate_count += 1
                    print_info(f"  ⊙ Skipped duplicate: {project.get('name', 'Unknown')}")

            # Merge groups
            source_groups = source_registry.get('groups', {})
            target_groups = target_registry.get('groups', {})

            for group_name, group_data in source_groups.items():
                if group_name not in target_groups:
                    target_groups[group_name] = group_data
                    print_success(f"  ✓ Added group: {group_name}")
                else:
                    # Merge spokes in existing group
                    existing_spokes = set(target_groups[group_name].get('spokes', []))
                    new_spokes = group_data.get('spokes', [])
                    for spoke in new_spokes:
                        if spoke not in existing_spokes:
                            target_groups[group_name].setdefault('spokes', []).append(spoke)

            # Update target registry
            target_registry['projects'] = target_projects
            target_registry['groups'] = target_groups

            # Save merged registry
            target_registry_path.parent.mkdir(parents=True, exist_ok=True)
            target_registry_path.write_text(json.dumps(target_registry, indent=2))

            print_info(f"\n  Summary:")
            print_info(f"    Projects added: {added_count}")
            print_info(f"    Duplicates skipped: {duplicate_count}")
            print_info(f"    Groups merged: {len(source_groups)}")

            # Ask about deleting source hub
            if safe_confirm(f"\n  Delete source hub ({source_hub})?", default=False):
                try:
                    shutil.rmtree(source_hub)
                    print_success(f"  ✓ Deleted: {source_hub}")
                except Exception as e:
                    print_error(f"  Failed to delete source hub: {e}")
            else:
                print_info(f"  Source hub preserved: {source_hub}")

            print_success("\n  ✓ Subsume complete!")

        except Exception as e:
            print_error(f"  Subsume failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_projects(self, args):
        """Handle projects commands."""
        if args.projects_command == 'add':
            self._projects_add(args)
        elif args.projects_command == 'list':
            self._projects_list(args)
        else:
            print_info("Projects commands: add, list")

    def _projects_add(self, args):
        """Add projects to hub."""
        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd())

        if not hub_path:
            print_error("No hub found. Run 'WAI hub create' first.")
            return

        # Scan paths
        scan_paths = [normalize_path(p) for p in args.scan] if args.scan else None

        # Discover and add
        discovery = ProjectDiscovery()
        count = discovery.discover_and_add_projects(
            hub_path=hub_path,
            scan_paths=scan_paths,
            auto_add=False
        )

    def _projects_list(self, args):
        """List registered projects."""
        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd())

        if not hub_path:
            print_error("No hub found.")
            return

        # Load and display projects
        from .utils.registry import list_projects

        try:
            projects = list_projects(hub_path, group_filter=args.group)

            if not projects:
                print_info("No projects registered.")
                return

            print_info(f"\nRegistered projects ({len(projects)}):\n")

            for project in projects:
                name = project.get('name', 'Unknown')
                path = project.get('path', '')
                description = project.get('description', '')

                print_info(f"  {name}")
                if description:
                    print_info(f"    Description: {description}")
                print_info(f"    Path: {path}\n")

        except Exception as e:
            print_error(f"Failed to list projects: {e}")

    def _projects_remove(self, hub_path: Path, projects: list):
        """Remove a project from the registry."""
        import json
        from .utils.input import safe_input

        if not projects:
            print_info("\n  No projects to remove.")
            return

        # Display projects with numbers
        print_info("\n  Select project to remove:\n")
        for i, project in enumerate(projects, 1):
            name = project.get('name', 'Unknown')
            path = project.get('path', '')
            print_info(f"  [{i}] {name}")
            print_info(f"      {path}")
            print_info("")

        # Prompt for selection
        choice = safe_input(
            "  Project number (or 'c' to cancel)",
            default="c",
            allow_empty=True
        )

        if choice and choice.lower() != 'c':
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    project = projects[idx]
                    name = project.get('name', 'Unknown')

                    # Confirm removal
                    from .utils.input import safe_confirm
                    if safe_confirm(f"\n  Remove '{name}' from registry?", default=False):
                        # Load registry
                        from .utils.registry import load_registry
                        registry_path = hub_path / 'registry' / 'wheel-projects.json'
                        registry = load_registry(hub_path)

                        # Remove project
                        registry['projects'] = [p for p in registry['projects'] if p.get('path') != project.get('path')]

                        # Save
                        registry_path.write_text(json.dumps(registry, indent=2))
                        print_success(f"\n  ✓ Removed '{name}' from registry")
                    else:
                        print_info("\n  Removal cancelled")
                else:
                    print_error("\n  Invalid project number")
            except ValueError:
                print_error("\n  Invalid input")
        else:
            print_info("\n  Removal cancelled")

    def _projects_rename(self, hub_path: Path, projects: list):
        """Rename a project by setting preferred display name."""
        import json
        from .utils.input import safe_input

        if not projects:
            print_info("\n  No projects to rename.")
            return

        # Display projects with numbers
        print_info("\n  Select project to rename:\n")
        for i, project in enumerate(projects, 1):
            name = project.get('name', 'Unknown')
            preferred_name = project.get('preferred_name')
            path = project.get('path', '')

            # Show current preferred name if exists
            if preferred_name and preferred_name != name:
                print_info(f"  [{i}] {preferred_name} (folder: {name})")
            else:
                print_info(f"  [{i}] {name}")
            print_info(f"      {path}")
            print_info("")

        # Prompt for selection
        choice = safe_input(
            "  Project number (or 'c' to cancel)",
            default="c",
            allow_empty=True
        )

        if choice and choice.lower() != 'c':
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    project = projects[idx]
                    current_name = project.get('name', 'Unknown')
                    preferred_name = project.get('preferred_name', current_name)
                    project_path = Path(project.get('path', ''))

                    print_info(f"\n  Renaming: {preferred_name}")
                    print_info(f"  Current display name: {preferred_name}")

                    # Prompt for new name
                    new_name = safe_input(
                        "\n  New display name",
                        default=preferred_name,
                        allow_empty=False
                    )

                    if new_name and new_name != preferred_name:
                        # Update spoke's WAI-State.json if it exists
                        spoke_state_file = project_path / 'WAI-Spoke' / 'WAI-State.json'
                        if spoke_state_file.exists():
                            try:
                                state = json.loads(spoke_state_file.read_text())
                                if 'wheel' not in state:
                                    state['wheel'] = {}
                                state['wheel']['preferred_name'] = new_name
                                spoke_state_file.write_text(json.dumps(state, indent=2))
                                print_success(f"  ✓ Updated spoke WAI-State.json")
                            except Exception as e:
                                print_error(f"  Failed to update spoke state: {e}")

                        # Update registry
                        from .utils.registry import load_registry
                        registry_path = hub_path / 'registry' / 'wheel-projects.json'
                        registry = load_registry(hub_path)

                        # Find and update project in registry
                        for reg_project in registry.get('projects', []):
                            if reg_project.get('path') == project.get('path'):
                                reg_project['preferred_name'] = new_name
                                break

                        # Save registry
                        registry_path.write_text(json.dumps(registry, indent=2))
                        print_success(f"\n  ✓ Renamed '{preferred_name}' to '{new_name}'")
                        print_info(f"  Display name updated in registry and spoke")
                    else:
                        print_info("\n  No changes made")
                else:
                    print_error("\n  Invalid project number")
            except ValueError:
                print_error("\n  Invalid input")
        else:
            print_info("\n  Rename cancelled")

    def _projects_add_to_group(self, hub_path: Path, projects: list):
        """Add a project to a group."""
        import json
        from .utils.input import safe_input
        from .utils.registry import load_registry

        if not projects:
            print_info("\n  No projects to add to group.")
            return

        # Load registry to get groups
        registry = load_registry(hub_path)
        groups = registry.get('groups', {})

        if not groups:
            print_info("\n  No groups exist. Create a group first.")
            return

        # Display projects
        print_info("\n  Select project:\n")
        for i, project in enumerate(projects, 1):
            name = project.get('name', 'Unknown')
            preferred_name = project.get('preferred_name', name)
            display_name = preferred_name if preferred_name != name else name
            print_info(f"  [{i}] {display_name}")

        project_choice = safe_input(
            "\n  Project number (or 'c' to cancel)",
            default="c",
            allow_empty=True
        )

        if not project_choice or project_choice.lower() == 'c':
            print_info("\n  Cancelled")
            return

        try:
            proj_idx = int(project_choice) - 1
            if not (0 <= proj_idx < len(projects)):
                print_error("\n  Invalid project number")
                return

            selected_project = projects[proj_idx]
            project_path = selected_project.get('path')

            # Display groups
            print_info("\n  Select group:\n")
            group_list = list(groups.keys())
            for i, group_name in enumerate(group_list, 1):
                print_info(f"  [{i}] {group_name}")

            group_choice = safe_input(
                "\n  Group number (or 'c' to cancel)",
                default="c",
                allow_empty=True
            )

            if not group_choice or group_choice.lower() == 'c':
                print_info("\n  Cancelled")
                return

            group_idx = int(group_choice) - 1
            if not (0 <= group_idx < len(group_list)):
                print_error("\n  Invalid group number")
                return

            group_name = group_list[group_idx]

            # Add project to group
            if 'spokes' not in groups[group_name]:
                groups[group_name]['spokes'] = []

            if project_path not in groups[group_name]['spokes']:
                groups[group_name]['spokes'].append(project_path)
                registry['groups'] = groups

                # Save
                registry_path = hub_path / 'registry' / 'wheel-projects.json'
                registry_path.write_text(json.dumps(registry, indent=2))

                print_success(f"\n  ✓ Added '{selected_project.get('name')}' to group '{group_name}'")
            else:
                print_info(f"\n  Project already in group '{group_name}'")

        except ValueError:
            print_error("\n  Invalid input")

    def _cmd_group(self, args):
        """Handle group commands."""
        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(Path.cwd())

        if not hub_path:
            print_error("No hub found. Run 'WAI hub create' first.")
            return

        groups_manager = GroupsManager(hub_path)

        if args.group_command == 'create':
            groups_manager.create_group(args.name, description=args.description)

        elif args.group_command == 'list':
            groups_manager.list_groups(verbose=args.verbose)

        elif args.group_command == 'add-spoke':
            groups_manager.add_spoke_to_group(args.group, args.spoke)

        elif args.group_command == 'remove-spoke':
            groups_manager.remove_spoke_from_group(args.group, args.spoke)

        elif args.group_command == 'delete':
            groups_manager.delete_group(args.name, force=args.force)

        else:
            print_info("Group commands: create, list, add-spoke, remove-spoke, delete")

    def _cmd_sync(self, args):
        """Handle sync command."""
        from .commands.sync import sync_spoke
        sync_spoke(all_spokes=args.all)

    def _cmd_update(self, args):
        """Handle update command."""
        from .spoke_update import SpokeUpdateProcessor
        from .utils.input import safe_confirm

        try:
            spoke_path = normalize_path(args.path)

            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            updater = SpokeUpdateProcessor(spoke_path)
            plan = updater.plan_update()

            ingest_files = plan.get("ingest_files", [])
            reference_files = plan.get("reference_files", [])
            unknown_items = plan.get("unknown_items", [])

            print_info("\nAbsorbe Preview:")
            print_info(f"  Seed ingest files: {len(ingest_files)}")
            print_info(f"  Seed reference files: {len(reference_files)}")
            print_info(f"  Unknown items to archive: {len(unknown_items)}")

            if not (ingest_files or reference_files or unknown_items):
                print_info("  Nothing to update.")
                return

            if not safe_confirm("Proceed with update?", default=True):
                print_info("Absorbe cancelled.")
                return

            results = updater.run_update()
            print_success("\nAbsorbe complete.")
            print_info(f"  Ingested: {len(results['ingested'])}")
            print_info(f"  Archived reference: {len(results['archived_reference'])}")
            print_info(f"  Archived unknown: {len(results['archived_unknown'])}")
            if results.get("ingest_notes"):
                print_info("\n  Ingest details:")
                for note in results["ingest_notes"]:
                    targets = ", ".join(note.get("applied_to", []))
                    preview = note.get("preview", "")
                    print_info(f"   - {note.get('file')} → {targets}")
                    if preview:
                        print_info(f"     preview: {preview}")
            for warning in results.get("warnings", []):
                print_warning(f"  ⚠️  {warning}")

        except Exception as e:
            print_error(f"Absorbe failed: {e}")

    def _cmd_closeout(self, args):
        """Handle closeout command."""
        from .closeout import CloseoutProcessor

        try:
            raw_path = getattr(args, 'path', '.')
            spoke_path = normalize_path(raw_path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            # Run closeout processor
            processor = CloseoutProcessor(spoke_path)
            interactive = not getattr(args, 'non_interactive', False)
            results = processor.process_closeout(interactive=interactive)
            processor.print_summary(results)

        except Exception as e:
            print_error(f"Closeout failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_stats(self, args):
        """Handle stats command."""
        from .metrics import MetricsTracker

        try:
            spoke_path = normalize_path(args.path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            wai_spoke_dir = spoke_path / 'WAI-Spoke'
            metrics = MetricsTracker(wai_spoke_dir)
            stats = metrics.get_session_stats()

            # Display stats
            print_info("\n" + "=" * 60)
            print_success("  Session Analytics & Metrics")
            print_info("=" * 60 + "\n")

            # Sessions
            print_info("  📊 Sessions:")
            print_info(f"      Total: {stats['sessions']['total']}")
            print_info(f"      Avg turns: {stats['sessions']['avg_turns']}")
            print_info(f"      Avg duration: {stats['sessions']['avg_duration']}")

            # Tokens
            print_info("\n  🎯 Token Efficiency:")
            print_info(f"      Total tokens used: {stats['tokens']['total_used']:,}")
            print_info(f"      Avg per session: {stats['tokens']['avg_per_session']:,}")
            print_info(f"      Context limit: {stats['tokens']['context_limit']:,}")

            # Token savings if available
            if 'token_savings' in stats:
                savings = stats['token_savings']
                print_info("\n  💰 Token Savings vs Baseline:")
                print_info(f"      Baseline tokens: {savings['baseline_tokens']:,}")
                print_info(f"      Optimized tokens: {savings['optimized_tokens']:,}")
                print_info(f"      Tokens saved: {savings['tokens_saved']:,}")
                print_success(f"      Savings: {savings['percent_saved']}%")
                if savings['meets_claim']:
                    print_success("      ✓ Meets 50-80% savings claim!")

            # Time tracking
            print_info("\n  ⏱️  Time Tracking:")
            print_info(f"      Total time: {stats['time']['total']}")
            print_info(f"      Time together: {stats['time']['together']} ({stats['time']['together_percent']:.1f}%)")
            print_info(f"      Time AI alone: {stats['time']['ai_alone']}")

            # AI wins
            print_info("\n  🏆 AI Wins:")
            print_info(f"      Total: {stats['ai_wins']['total']}")
            if stats['ai_wins']['recent']:
                print_info("      Recent wins:")
                for win in stats['ai_wins']['recent'][-3:]:
                    print_success(f"        • {win.get('type', 'unknown')}: {win.get('description', 'N/A')}")

            print_info("\n" + "=" * 60 + "\n")

        except Exception as e:
            print_error(f"Stats failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_baseline(self, args):
        """Handle baseline command."""
        from .metrics import MetricsTracker

        try:
            spoke_path = normalize_path(args.path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            wai_spoke_dir = spoke_path / 'WAI-Spoke'
            metrics = MetricsTracker(wai_spoke_dir)

            if not hasattr(args, 'baseline_command') or args.baseline_command is None:
                # Show status
                args.baseline_command = 'status'

            if args.baseline_command == 'enable':
                result = metrics.enable_baseline_mode()
                print_success(f"\n✓ {result['message']}")
                print_info("  Notes:")
                print_info("  - Baseline sessions should avoid WAI optimizations (planning gates, compact, etc.)")
                print_info("  - Run 'Closeout' at the end of each baseline session to record metrics\n")

            elif args.baseline_command == 'disable':
                result = metrics.disable_baseline_mode()
                if result['disabled']:
                    print_success(f"\n✓ {result['message']}")
                    print_info(f"  Baseline data: {result['baseline_tokens']:,} tokens over {result['baseline_sessions']} sessions\n")
                else:
                    print_warning(f"\n⚠️  {result['message']}\n")

            elif args.baseline_command == 'status':
                state_file = wai_spoke_dir / 'WAI-State.json'
                with open(state_file, 'r') as f:
                    import json
                    state = json.load(f)

                baseline = state.get('analytics', {}).get('baseline_mode', {})

                print_info("\n" + "=" * 60)
                print_info("  Baseline Mode Status")
                print_info("=" * 60 + "\n")

                if baseline.get('enabled'):
                    print_success("  Status: ENABLED")
                    print_info(f"  Started: {self._format_datetime(baseline.get('started_at'))}")
                    print_info(f"  Tokens tracked: {baseline.get('total_tokens_used', 0):,}")
                    print_info(f"  Sessions tracked: {baseline.get('total_sessions', 0)}")
                    print_info(f"\n  {baseline.get('description', '')}")
                    print_info("  Reminder: Closeout records baseline sessions; optimized totals pause while baseline is enabled.\n")
                else:
                    print_info("  Status: DISABLED")
                    if baseline.get('total_tokens_used', 0) > 0:
                        print_info(f"\n  Baseline data (locked):")
                        print_info(f"    Tokens: {baseline.get('total_tokens_used', 0):,}")
                        print_info(f"    Sessions: {baseline.get('total_sessions', 0)}")
                        print_info(f"    Period: {self._format_datetime(baseline.get('started_at'))} to {self._format_datetime(baseline.get('ended_at'))}\n")
                    else:
                        print_info("\n  No baseline data collected yet.\n")
                        print_info("  To enable: WAI baseline enable\n")

                print_info("=" * 60 + "\n")
            elif args.baseline_command == 'run':
                ide = getattr(args, 'ide', None)
                model = getattr(args, 'model', None)
                notes = getattr(args, 'notes', None)
                self._run_baseline_comparison(spoke_path, ide=ide, model=model, notes=notes)

        except Exception as e:
            print_error(f"Baseline command failed: {e}")
            import traceback
            traceback.print_exc()

    def _run_baseline_comparison(self, spoke_path: Path, ide: str = None, model: str = None, notes: str = None):
        """Run a synthetic baseline vs optimized comparison and log results."""
        from .metrics import MetricsTracker
        from .session import SessionManager
        import json
        import uuid
        from datetime import datetime

        if not check_spoke_initialized(spoke_path):
            print_error(f"No spoke found at {spoke_path}")
            return

        wai_spoke_dir = spoke_path / 'WAI-Spoke'
        metrics = MetricsTracker(wai_spoke_dir)

        state_file = wai_spoke_dir / 'WAI-State.json'
        state = json.loads(state_file.read_text())
        baseline_state = state.get('analytics', {}).get('baseline_mode', {})
        if baseline_state.get('enabled'):
            print_warning("Baseline mode is already enabled. Disable it before running an automated comparison.")
            return

        resolved_ide, resolved_model = self._detect_ide_model(ide, model)
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat() + "Z"

        pre_stats = metrics.get_session_stats()
        pre_optimized_tokens = state.get('analytics', {}).get('token_efficiency', {}).get('total_tokens_used', 0)
        pre_baseline_tokens = baseline_state.get('total_tokens_used', 0)

        print_info("\n📏 Running automated baseline comparison...\n")

        # Baseline capture
        metrics.enable_baseline_mode()
        baseline_session = self._simulate_session(
            SessionManager(spoke_path),
            ai_model=resolved_model,
            label="baseline"
        )
        metrics.record_session_end(baseline_session)
        metrics.disable_baseline_mode()

        # Optimized capture
        optimized_session = self._simulate_session(
            SessionManager(spoke_path),
            ai_model=resolved_model,
            label="optimized"
        )
        metrics.record_session_end(optimized_session)

        baseline_tokens = baseline_session['tokens_estimate']
        optimized_tokens = optimized_session['tokens_estimate']
        tokens_saved = baseline_tokens - optimized_tokens
        percent_saved = (tokens_saved / baseline_tokens * 100) if baseline_tokens > 0 else 0

        post_stats = metrics.get_session_stats()
        post_state = json.loads(state_file.read_text())
        post_optimized_tokens = post_state.get('analytics', {}).get('token_efficiency', {}).get('total_tokens_used', 0)
        post_baseline_tokens = post_state.get('analytics', {}).get('baseline_mode', {}).get('total_tokens_used', 0)

        log_entry = {
            "timestamp": started_at,
            "run_id": run_id,
            "run_type": "synthetic",
            "ide": resolved_ide,
            "model": resolved_model,
            "baseline": {
                "tokens": baseline_tokens,
                "turns": baseline_session["turns"]
            },
            "optimized": {
                "tokens": optimized_tokens,
                "turns": optimized_session["turns"]
            },
            "savings": {
                "tokens_saved": tokens_saved,
                "percent_saved": round(percent_saved, 1)
            },
            "pre_stats": {
                "optimized_tokens_total": pre_optimized_tokens,
                "baseline_tokens_total": pre_baseline_tokens,
                "sessions_total": pre_stats.get("sessions", {}).get("total", 0)
            },
            "post_stats": {
                "optimized_tokens_total": post_optimized_tokens,
                "baseline_tokens_total": post_baseline_tokens,
                "sessions_total": post_stats.get("sessions", {}).get("total", 0)
            },
            "notes": notes
        }

        log_path = wai_spoke_dir / 'WAI-Baseline-Log.jsonl'
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

        print_success("✓ Baseline comparison complete\n")
        print_info("Results:")
        print_info(f"  IDE: {resolved_ide}")
        print_info(f"  Model: {resolved_model}")
        print_info(f"  Baseline tokens: {baseline_tokens:,}")
        print_info(f"  Optimized tokens: {optimized_tokens:,}")
        print_info(f"  Tokens saved: {tokens_saved:,} ({percent_saved:.1f}%)\n")
        print_info(f"Logged to: {log_path}\n")

    def _simulate_session(self, session: "SessionManager", ai_model: str, label: str) -> Dict[str, Any]:
        """Simulate a short session and return session metrics."""
        session.start_session(ai_name=ai_model)

        if label == "baseline":
            user_text = (
                "Baseline benchmark: please provide a verbose walkthrough of the current "
                "Wheelwright context, recent changes, and suggested next actions with full detail."
            )
            assistant_text = (
                "Baseline response: This is a verbose baseline response used to simulate a longer, "
                "less optimized interaction. It includes extra detail, redundancy, and longer phrasing "
                "to represent a less efficient workflow without compacting context or applying strict "
                "planning gates."
            )
        else:
            user_text = "Optimized benchmark: summarize the current context and next actions succinctly."
            assistant_text = "Optimized response: concise summary with key actions only."

        session.log_turn("user", user_text, {"benchmark_label": label})
        session.log_turn("assistant", assistant_text, {"benchmark_label": label, "ai_model": ai_model})

        session_data = {
            "session_id": session.session_id,
            "turns": session.turn_count,
            "tokens_estimate": session.tokens_estimate,
            "duration_seconds": 1,
            "time_together_seconds": 1,
            "time_ai_alone_seconds": 0
        }

        session.clear_log()
        return session_data

    def _detect_ide_model(self, ide: str = None, model: str = None) -> tuple:
        """Best-effort detection of IDE and model."""
        import os

        detected_ide = ide
        detected_model = model

        if not detected_ide:
            if os.environ.get("CODEX_CLI") is not None or os.environ.get("CODEX_PROJECT_DIR") is not None:
                detected_ide = "Codex CLI"
            elif os.environ.get("CLAUDE_CLI") is not None:
                detected_ide = "Claude Code"
            else:
                detected_ide = "Unknown IDE"

        if not detected_model:
            detected_model = os.environ.get("AI_MODEL", "Unknown Model")

        return detected_ide, detected_model

    def _get_latest_baseline_summary(self, spoke_path: Path) -> str:
        """Return a one-line summary of the latest baseline run, if available."""
        log_path = spoke_path / 'WAI-Spoke' / 'WAI-Baseline-Log.jsonl'
        if not log_path.exists():
            return ""

        last_line = ""
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    last_line = line

        if not last_line:
            return ""

        try:
            import json
            entry = json.loads(last_line)
            savings = entry.get("savings", {})
            percent = savings.get("percent_saved")
            ide = entry.get("ide", "Unknown IDE")
            model = entry.get("model", "Unknown Model")
            timestamp = entry.get("timestamp", "Unknown time")
            if percent is None:
                return f"Baseline run: {timestamp} | IDE: {ide} | Model: {model}"
            return f"Baseline run: {timestamp} | IDE: {ide} | Model: {model} | Saved: {percent}%"
        except Exception:
            return ""

    def _cmd_time(self, args):
        """Handle time command - show token usage and capacity."""
        from .session import SessionManager

        try:
            spoke_path = normalize_path(args.path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            session = SessionManager(spoke_path)
            capacity = session.get_capacity_estimate()

            print_info("\n" + "=" * 60)
            print_success("  Token Usage Estimate")
            print_info("=" * 60 + "\n")

            # Display capacity
            capacity_pct = capacity['capacity_percent']
            tokens_used = capacity['tokens_used']
            context_limit = capacity['context_limit']
            warning_level = capacity['warning_level']

            print_info(f"  Estimated usage: ~{capacity_pct * 100:.1f}% of context window")
            print_info(f"  Tokens used: ~{tokens_used:,} / {context_limit:,}")
            print_info(f"  Capacity: {context_limit:,} tokens\n")

            # Warning thresholds
            if warning_level == 'critical':
                print_error("  ⚠️  CRITICAL: Approaching capacity limit!")
                print_info("     Context window is nearly full.")
                print_info("     Recommend running 'Closeout' immediately to consolidate state.\n")
            elif warning_level == 'high':
                print_error("  ⚠️  WARNING: High capacity usage!")
                print_info("     Consider running 'Closeout' soon to consolidate state.\n")
            elif warning_level == 'medium':
                print_info("  ℹ️  Moderate usage - you have plenty of capacity remaining.\n")
            else:
                print_success("  ✓ Low usage - plenty of capacity available.\n")

            # Show conversation log stats if exists
            log_file = spoke_path / 'WAI-Spoke' / 'WAI-Session-Log.jsonl'
            if log_file.exists():
                # Count turns
                turns = 0
                import json
                with open(log_file, 'r') as f:
                    for line in f:
                        turns += 1

                print_info(f"  Session turns logged: {turns}")

                if turns > 0:
                    avg_tokens = tokens_used / turns if turns > 0 else 0
                    print_info(f"  Average per turn: ~{avg_tokens:.0f} tokens\n")

            print_info("=" * 60 + "\n")

        except Exception as e:
            print_error(f"Time command failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_shipit(self, args):
        """Handle shipit command - closeout + git commit."""
        from .closeout import CloseoutProcessor
        from .bootstrap import refresh_bootstrap
        from .utils.input import safe_confirm
        import subprocess

        try:
            spoke_path = normalize_path(args.path)

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            # Check if this is a git repository
            try:
                repo = Repo(spoke_path, search_parent_directories=True)
            except git_exc.InvalidGitRepositoryError:
                print_error("Not a git repository.")
                print_info("Initialize git first: git init")
                return

            # Step 1: Run full closeout
            print_info("\n🚀 Shipit: Closeout + Git Commit\n")
            print_info("=" * 60)

            processor = CloseoutProcessor(spoke_path)
            results = processor.process_closeout(
                interactive=not args.non_interactive,
                skip_quality_gates=args.skip_quality_gates
            )

            # Check if closeout was aborted
            if results.get('errors') and any('aborted' in e.lower() for e in results['errors']):
                print_error("\nShipit aborted due to closeout errors.")
                return

            # Step 1.5: Refresh bootstrap (framework repo only)
            framework_root = Path(__file__).resolve().parent.parent
            if spoke_path.resolve() == framework_root.resolve():
                print_info("\n  Refreshing bootstrap folder...")
                refresh_bootstrap(framework_root, verbose=True)

            # Step 2: Git workflow using GitPython
            print_info("\n" + "=" * 60)
            print_info("  Git Commit Workflow")
            print_info("=" * 60 + "\n")

            if not repo.is_dirty(untracked_files=True):
                print_info("  Working tree clean - nothing to commit.\n")
                return

            # Show what changed
            print_info("  Changed files:")
            for item in repo.index.diff(None) + repo.index.diff("HEAD"):
                print_info(f"    M {item.a_path}")
            for f in repo.untracked_files:
                print_info(f"    ?? {f}")
            print_info("")

            # Stage WAI state files and Lugs
            wai_files = [
                'WAI-Spoke/WAI-State.json',
                'WAI-Spoke/WAI-State.md',
                'WAI-Spoke/WAI-Guide.md',
                'WAI-Spoke/WAI-Signals.jsonl',
                'WAI-Spoke/lugs.jsonl',
                'WAI-Spoke/lugs-closed.jsonl',
                'WAI-Spoke/lug-sessions.jsonl',
                'WAI-Spoke/WAI-Point.json'
            ]

            files_to_commit = []
            for wai_file in wai_files:
                if (spoke_path / wai_file).exists():
                    # Check if file is modified or untracked
                    is_modified = any(item.a_path == wai_file for item in repo.index.diff(None))
                    is_untracked = wai_file in repo.untracked_files
                    if is_modified or is_untracked:
                        files_to_commit.append(wai_file)

            if files_to_commit:
                print_info("  Auto-staging WAI files:")
                for f in files_to_commit:
                    print_info(f"    + {f}")
                    repo.index.add([f])
                print_info("")

            # Ask about other files
            unstaged_files = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
            unstaged_files = [f for f in unstaged_files if not f.startswith('WAI-Spoke/')]
            
            if unstaged_files and not args.non_interactive:
                print_info("  Other modified files:")
                for f in unstaged_files:
                    print_info(f"    {f}")
                print_info("")
                
                print_info("  The following files are modified or untracked but were not automatically staged by the Framework.")
                print_info("  You can choose to include them in this commit.")

                if safe_confirm("  Stage these files too?", default=True):
                    for f in unstaged_files:
                        repo.index.add([f])
                        print_info(f"    + {f}")
                    print_info("")

            # Get Lugs for this session to close
            session_state = processor.session.get_state()
            session_id = session_state.get('session_id')
            closed_lugs_info = []
            
            if session_id:
                from .lugs import LugManager
                lug_manager = LugManager(spoke_path)
                session_lugs = lug_manager.get_session_lugs(session_id)
                
                if session_lugs:
                    print_info(f"  Found {len(session_lugs)} Lugs associated with this session.")
                    for lug in session_lugs:
                        if lug.status == 'open':
                            if args.non_interactive or safe_confirm(f"  Close Lug {lug.id} ({lug.title})?", default=True):
                                lug_manager.close_lug(lug.id, summary=results.get('session_summary', {}).get('summary', 'Closed via shipit'))
                                closed_lugs_info.append(f"{lug.id} ({lug.title})")
                    
                    # Ensure lug files are staged after closing
                    repo.index.add(['WAI-Spoke/lugs.jsonl', 'WAI-Spoke/lugs-closed.jsonl'])
            
            # Update Changelog
            try:
                from .changelog import ChangelogGenerator
                generator = ChangelogGenerator(Path(spoke_path))
                generator.update_changelog_file()
                if (Path(spoke_path) / "CHANGELOG.md").exists():
                    repo.index.add(["CHANGELOG.md"])
                print_info("    [shipit] CHANGELOG.md updated.")
            except Exception as e:
                print_warning(f"    [shipit] Failed to update changelog: {e}")

            # Generate commit message
            session_summary = results.get('session_summary', {})
            summary_text = session_summary.get('summary', 'Session closeout')
            key_topics = session_summary.get('key_topics', [])
            turns = session_summary.get('turns', 0)
            baseline_summary = self._get_latest_baseline_summary(spoke_path)

            lugs_msg = ""
            if closed_lugs_info:
                lugs_msg = "\nClosed Lugs:\n" + "\n".join([f"- {info}" for info in closed_lugs_info])

            commit_msg = f"""Session closeout: {summary_text[:60]}

{summary_text}

Session turns: {turns}
{f'Key topics: {", ".join(key_topics)}' if key_topics else ''}
{lugs_msg}
{baseline_summary}

🤖 Generated with [Wheelwright AI](https://github.com/mario/wheelwright-ai)
Co-Authored-By: Wheelwright AI <noreply@wheelwright.ai>"""

            # Create commit
            commit = repo.index.commit(commit_msg)
            print_success(f"\n  ✓ Commit {commit.hexsha[:7]} created successfully!\n")

            # Show commit details
            print_info(repo.git.log("-1", "--stat"))

            # Push to remote by default (unless --no-push)
            if not args.no_push:
                print_info("  Pushing to remote...")
                try:
                    origin = repo.remote(name='origin')
                    origin.push()
                    print_success("  ✓ Pushed to remote successfully!\n")
                except Exception as e:
                    print_error(f"  Push failed: {e}")
            else:
                print_info("  To push to remote, run: git push\n")

            print_info("=" * 60)
            print_success("  Shipit Complete!")
            print_info("=" * 60 + "\n")

        except Exception as e:
            print_error(f"Shipit command failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_template(self, args):
        """Handle template command."""
        from .templates import TemplateManager
        from .hub import HubManager
        from .utils.input import safe_confirm

        try:
            # Get hub path
            hub_manager = HubManager()
            hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

            if not hub_path and args.template_command != 'list':
                print_error("No hub found. Templates require a hub.")
                print_info("Run 'WAI hub create' to create a hub first.")
                return

            template_manager = TemplateManager(hub_path)

            if not hasattr(args, 'template_command') or args.template_command is None:
                # Show available commands
                print_info("\nTemplate Commands:")
                print_info("  create  - Create template from spoke")
                print_info("  list    - List available templates")
                print_info("  apply   - Apply template to new project")
                print_info("  delete  - Delete a template\n")
                return

            if args.template_command == 'create':
                spoke_path = normalize_path(args.path)

                # Check if spoke exists
                if not check_spoke_initialized(spoke_path):
                    print_error(f"No spoke found at {spoke_path}")
                    print_info("Run 'WAI init' to initialize a spoke first.")
                    return

                print_info(f"\n📝 Creating template '{args.name}'...\n")

                result = template_manager.create_template(
                    spoke_path=spoke_path,
                    template_name=args.name,
                    description=args.description or ""
                )

                if result['success']:
                    print_success(f"✓ Template '{args.name}' created successfully!\n")
                    print_info(f"  Template path: {result['template_path']}")
                    print_info(f"  Files included: {result['files_included']}")
                    print_info(f"  Project type: {result['analysis']['project_type']}\n")
                else:
                    print_error("Template creation failed")

            elif args.template_command == 'list':
                templates = template_manager.list_templates()

                if not templates:
                    print_info("\nNo templates found.")
                    if not hub_path:
                        print_info("Create a hub first: WAI hub create\n")
                    else:
                        print_info("Create your first template: WAI template create <name>\n")
                    return

                print_info("\n" + "=" * 60)
                print_success("  Available Templates")
                print_info("=" * 60 + "\n")

                for template in templates:
                    print_success(f"  {template['name']}")
                    if template.get('description'):
                        print_info(f"    {template['description']}")
                    print_info(f"    Project type: {template['structure']['project_type']}")
                    print_info(f"    Created: {template['created_at'][:10]}")
                    print_info("")

                print_info("=" * 60 + "\n")

            elif args.template_command == 'apply':
                target_path = normalize_path(args.path)

                print_info(f"\n📦 Applying template '{args.name}' to {target_path}...\n")

                # TODO: Ask template questions if defined
                # For now, just apply with no customizations

                result = template_manager.apply_template(
                    template_name=args.name,
                    target_path=target_path,
                    answers=None
                )

                if result['success']:
                    print_success(f"✓ Template applied successfully!\n")
                    print_info(f"  Spoke created at: {result['spoke_path']}")
                    print_info(f"  Template used: {result['template_used']}\n")
                    print_info("  Next steps:")
                    print_info("    1. Review and customize WAI-Guide.md")
                    print_info("    2. Complete project foundation")
                    print_info("    3. Start your first session\n")
                else:
                    print_error("Template application failed")

            elif args.template_command == 'delete':
                if not args.force:
                    if not safe_confirm(f"Delete template '{args.name}'?", default=False):
                        print_info("Cancelled.")
                        return

                if template_manager.delete_template(args.name):
                    print_success(f"✓ Template '{args.name}' deleted")
                else:
                    print_error(f"Template '{args.name}' not found")

        except ValueError as e:
            print_error(str(e))
        except Exception as e:
            print_error(f"Template command failed: {e}")
            import traceback
            traceback.print_exc()

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
        from .utils.input import print_success, print_info, print_markdown
        
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

    def _cmd_configure_ide(self, args):
        """Handle configure-ide command."""
        from .integrations.manager import IDEManager

        try:
            spoke_path = normalize_path(args.path if hasattr(args, 'path') else '.')

            # Check if spoke exists
            if not check_spoke_initialized(spoke_path):
                print_error(f"No spoke found at {spoke_path}")
                print_info("Run 'WAI init' to initialize a spoke first.")
                return

            manager = IDEManager(spoke_path)

            if not hasattr(args, 'config_ide_command') or args.config_ide_command is None:
                # Show available commands
                print_info("\nIDE Configuration Commands:")
                print_info("  detect        - Detect IDEs in use")
                print_info("  list          - List supported IDE integrations")
                print_info("  setup         - Setup IDE configuration")
                print_info("  capabilities  - Show IDE capabilities")
                print_info("  optimize      - Get optimization suggestions\n")
                return

            if args.config_ide_command == 'detect':
                ides = manager.detect_ides()

                print_info("\n" + "=" * 60)
                print_success("  Detected IDEs")
                print_info("=" * 60 + "\n")

                if not ides:
                    print_info("  No IDEs detected.")
                    print_info("\n  Supported IDEs:")
                    print_info("    - Codex CLI")
                    print_info("    - Claude Code")
                    print_info("    - VS Code")
                    print_info("    - Cursor")
                    print_info("    - Web LLMs (Claude.ai, ChatGPT, etc.)\n")
                else:
                    for ide_info in ides:
                        status = "✓ Configured" if ide_info['configured'] else "⚠️ Not configured"
                        print_success(f"  {ide_info['name']}: {status}")
                        print_info(f"    Config: {ide_info['config_path']}")

                print_info("\n" + "=" * 60 + "\n")

            elif args.config_ide_command == 'list':
                supported = manager.list_supported()

                print_info("\n" + "=" * 60)
                print_success("  Supported IDE Integrations")
                print_info("=" * 60 + "\n")

                for ide_info in supported:
                    print_success(f"  {ide_info['name']}")
                    print_info(f"    Config: {ide_info['config_path']}")
                    print_info("    Capabilities:")
                    for cap, value in ide_info['capabilities'].items():
                        print_info(f"      - {cap}: {value}")
                    print_info("")

                print_info("=" * 60 + "\n")

            elif args.config_ide_command == 'setup':
                ide_name = args.ide if hasattr(args, 'ide') and args.ide else None
                force = args.force if hasattr(args, 'force') else False

                if ide_name:
                    # Setup specific IDE
                    result = manager.configure_ide(ide_name, force=force)

                    if result.get('success'):
                        print_success(f"\n✓ Configured {ide_name}")
                        print_info(f"  Config file: {result['config_path']}\n")
                    else:
                        print_error(f"\n✗ Failed to configure {ide_name}")
                        print_info(f"  {result.get('error', 'Unknown error')}\n")
                        if 'available' in result:
                            print_info("  Available IDEs:")
                            for available in result['available']:
                                print_info(f"    - {available}")
                            print_info("")
                else:
                    # Setup all detected
                    results = manager.configure_all_detected(force=force)

                    print_info("\n" + "=" * 60)
                    print_success("  IDE Configuration Results")
                    print_info("=" * 60 + "\n")

                    for ide, result in results['results'].items():
                        if result.get('configured'):
                            print_success(f"  ✓ {ide}: Configured")
                            print_info(f"    {result['config_path']}")
                        else:
                            print_warning(f"  ⚠️ {ide}: {result.get('reason', 'Not configured')}")

                    print_info(f"\n  Total configured: {results['configured_count']}/{len(results['results'])}\n")

            elif args.config_ide_command == 'capabilities':
                ide_name = args.ide if hasattr(args, 'ide') and args.ide else None

                capabilities = manager.list_supported()

                print_info("\n" + "=" * 60)
                print_success("  IDE Capabilities")
                print_info("=" * 60 + "\n")

                if ide_name:
                    matched = next((i for i in capabilities if i['name'].lower() == ide_name.lower()), None)
                    if not matched:
                        print_error(f"  Unknown IDE: {ide_name}\n")
                    else:
                        print_info(f"  IDE: {matched['name']}\n")
                        for cap, value in matched['capabilities'].items():
                            print_info(f"    {cap}: {value}")
                        print_info("")
                else:
                    for ide_info in capabilities:
                        print_success(f"  {ide_info['name']}:")
                        for cap, value in ide_info['capabilities'].items():
                            print_info(f"    {cap}: {value}")
                        print_info("")

            elif args.config_ide_command == 'optimize':
                report = manager.get_optimization_report()

                print_info("\n" + "=" * 60)
                print_success("  IDE Optimization Suggestions")
                print_info("=" * 60 + "\n")

                if not report['detected_ides']:
                    print_info("  No IDEs detected.\n")
                else:
                    for ide in report['detected_ides']:
                        suggestions = report['suggestions_by_ide'][ide]
                        print_success(f"  {ide}:")
                        if suggestions:
                            for suggestion in suggestions:
                                print_info(f"    • {suggestion}")
                        else:
                            print_info("    No specific suggestions")
                        print_info("")

        except Exception as e:
            print_error(f"IDE configuration failed: {e}")
            import traceback
            traceback.print_exc()

    def _cmd_context(self, args):
        """Handle context command."""
        from .commands.context import output_context
        output_context(args.path)

    def _cmd_version(self):
        """Show version information."""
        print_info(f"\nWheelwright Framework v{FRAMEWORK_VERSION}")
        print_info(f"Spoke structure version: {SPOKE_STRUCTURE_VERSION}\n")

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


def main():
    """CLI entry point with error handling."""
    try:
        cli = WheelwrightCLI()
        cli.run()
    except KeyboardInterrupt:
        print_info("\n\nOperation cancelled by user.")
        sys.exit(130)
    except WAIError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()
