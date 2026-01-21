"""
Template Command - Manage workflow templates.

This module handles template-related commands for creating, listing,
applying, and deleting project templates stored in the hub.
"""

from pathlib import Path

from ..templates import TemplateManager
from ..hub import HubManager
from ..init import check_spoke_initialized
from ..utils.input import safe_confirm, print_info, print_error, print_success
from ..utils.paths import normalize_path


def cmd_template(args):
    """
    Execute template command.

    Handles template management operations including:
    - create: Create template from existing spoke
    - list: List available templates in hub
    - apply: Apply template to new project
    - delete: Delete a template from hub

    Args:
        args: Argument namespace with:
            - template_command: Subcommand (create/list/apply/delete)
            - path: Path to spoke directory (for create/apply)
            - name: Template name
            - description: Template description (for create)
            - force: Skip confirmation (for delete)
    """
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
            _handle_create(args, template_manager)

        elif args.template_command == 'list':
            _handle_list(template_manager, hub_path)

        elif args.template_command == 'apply':
            _handle_apply(args, template_manager)

        elif args.template_command == 'delete':
            _handle_delete(args, template_manager)

    except ValueError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Template command failed: {e}")
        import traceback
        traceback.print_exc()


def _handle_create(args, template_manager):
    """
    Handle template create command.

    Args:
        args: Command arguments with path, name, description
        template_manager: TemplateManager instance
    """
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


def _handle_list(template_manager, hub_path):
    """
    Handle template list command.

    Args:
        template_manager: TemplateManager instance
        hub_path: Path to hub directory
    """
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


def _handle_apply(args, template_manager):
    """
    Handle template apply command.

    Args:
        args: Command arguments with path and name
        template_manager: TemplateManager instance
    """
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


def _handle_delete(args, template_manager):
    """
    Handle template delete command.

    Args:
        args: Command arguments with name and force flag
        template_manager: TemplateManager instance
    """
    if not args.force:
        if not safe_confirm(f"Delete template '{args.name}'?", default=False):
            print_info("Cancelled.")
            return

    if template_manager.delete_template(args.name):
        print_success(f"✓ Template '{args.name}' deleted")
    else:
        print_error(f"Template '{args.name}' not found")
