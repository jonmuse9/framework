"""
IDE Configuration Command

Handles IDE integration setup and configuration for Wheelwright spokes.
"""

from pathlib import Path
from ..init import check_spoke_initialized
from ..utils.input import print_info, print_success, print_error, print_warning
from ..utils.paths import normalize_path


def cmd_configure_ide(args):
    """
    Handle configure-ide command.

    Manages IDE integration configuration including detection, setup,
    and optimization suggestions for supported IDEs.

    Args:
        args: Parsed command-line arguments containing:
            - path: Path to spoke (default: current directory)
            - config_ide_command: Subcommand (detect/list/setup/capabilities/optimize)
            - ide: Specific IDE name (for setup/capabilities)
            - force: Force overwrite existing configuration

    Supported IDEs:
        - Codex CLI
        - Claude Code
        - VS Code
        - Cursor
        - Web LLMs (Claude.ai, ChatGPT, etc.)

    Subcommands:
        detect: Detect IDEs in use
        list: List supported IDE integrations
        setup: Setup IDE configuration (all detected or specific IDE)
        capabilities: Show IDE capabilities
        optimize: Get optimization suggestions
    """
    from ..integrations.manager import IDEManager

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
