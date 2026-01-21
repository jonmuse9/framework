"""
Group Commands

Handles spoke group management within Wheelwright hubs.
"""

from pathlib import Path
from ..hub import HubManager
from ..groups import GroupsManager
from ..utils.input import print_info, print_error


def cmd_group(args):
    """
    Handle group commands.

    Manages spoke groups within a hub, including creation, listing,
    spoke assignment, and deletion. Groups allow logical organization
    of related spokes for coordinated operations.

    Args:
        args: Parsed command-line arguments containing:
            - group_command: Subcommand (create/list/add-spoke/remove-spoke/delete)
            - name: Group name (for create/delete)
            - description: Group description (for create)
            - group: Group name (for add-spoke/remove-spoke)
            - spoke: Spoke path or name (for add-spoke/remove-spoke)
            - verbose: Show detailed information (for list)
            - force: Skip confirmation (for delete)

    Subcommands:
        create: Create a new group
        list: List all groups
        add-spoke: Add a spoke to a group
        remove-spoke: Remove a spoke from a group
        delete: Delete a group

    Requires:
        A Wheelwright hub must be initialized and discoverable.
    """
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
