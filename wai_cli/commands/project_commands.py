"""Project management commands for Wheelwright CLI."""

import json
from pathlib import Path

from ..hub import HubManager
from ..projects import ProjectDiscovery
from ..groups import GroupsManager
from ..utils.input import print_info, print_success, print_error, safe_input, safe_confirm
from ..utils.paths import normalize_path


def cmd_projects(args):
    """Handle projects commands."""
    if args.projects_command == 'add':
        projects_add(args)
    elif args.projects_command == 'list':
        projects_list(args)
    else:
        print_info("Projects commands: add, list")


def projects_add(args):
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


def projects_list(args):
    """List registered projects."""
    # Find hub
    hub_manager = HubManager()
    hub_path = hub_manager.auto_discover_hub(Path.cwd())

    if not hub_path:
        print_error("No hub found.")
        return

    # Load and display projects
    from ..utils.registry import list_projects

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


def projects_remove(hub_path: Path, projects: list):
    """Remove a project from the registry."""
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
                if safe_confirm(f"\n  Remove '{name}' from registry?", default=False):
                    # Load registry
                    from ..utils.registry import load_registry
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


def projects_rename(hub_path: Path, projects: list):
    """Rename a project by setting preferred display name."""
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
                    from ..utils.registry import load_registry
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


def projects_add_to_group(hub_path: Path, projects: list):
    """Add a project to a group."""
    from ..utils.registry import load_registry

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
