"""
Lug CLI commands for WAI framework.

Provides command-line interface for Lug operations:
- create: Create new Lugs with interactive prompts
- list: List/filter Lugs
- show: Show detailed Lug info
- update: Update Lug fields
- close: Close and archive Lugs
"""

import sys
from pathlib import Path
from typing import Optional

from ..lugs import LugManager
from ..utils.input import print_success, print_error, print_info, print_warning, safe_confirm

# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"

def _colorize(text: str, color_code: str) -> str:
    return f"{color_code}{text}{COLOR_RESET}"

def _get_priority_color(priority: str) -> str:
    priority = priority.lower()
    if priority == 'high': return COLOR_RED
    if priority == 'medium': return COLOR_YELLOW
    if priority == 'low': return COLOR_BLUE
    return COLOR_RESET

def _get_status_color(status: str) -> str:
    status = status.lower()
    if status in ['closed', 'done', 'completed']: return COLOR_GREEN
    if status in ['blocked', 'rejected']: return COLOR_RED
    if status in ['in_progress', 'working']: return COLOR_YELLOW
    return COLOR_RESET

def _get_type_color(lug_type: str) -> str:
    lt = lug_type.lower()
    if lt == 'bug': return COLOR_RED
    if lt == 'feat': return COLOR_GREEN
    if lt == 'epic': return COLOR_MAGENTA
    return COLOR_CYAN


def lug_command_group(args: list, spoke_dir: Path):
    """Handle all 'wai lug' commands."""
    if not args or args[0] in ['--help', '-h']:
        _print_lug_help()
        return
    
    subcommand = args[0]
    manager = LugManager(spoke_dir / 'WAI-Spoke')
    
    if subcommand in ['create', 'add']:
        _create_lug(manager, args[1:])
    elif subcommand == 'list':
        _list_lugs(manager, args[1:])
    elif subcommand == 'ready':
        _list_ready_lugs(manager, args[1:])
    elif subcommand == 'show':
        _show_lug(manager, args[1:])
    elif subcommand == 'update':
        _update_lug(manager, args[1:])
    elif subcommand == 'close':
        _close_lug(manager, args[1:])
    else:
        print_error(f"Unknown lug command: {subcommand}")
        _print_lug_help()
        sys.exit(1)


def _print_lug_help():
    """Print Lug command help."""
    print_info("""
WAI Lug Commands - AI-first task & dependency graph

Usage:
  wai lug add <title>                 Create new Lug (alias: create)
  wai lug list [opts]                 List Lugs (filter by --status, --type)
  wai lug ready                       List Lugs passing policy checks
  wai lug show <id-prefix>            Show detailed Lug info
  wai lug update <id-prefix> [opts]   Update fields (--status, --priority, etc.)
  wai lug close <id-prefix>           Close and archive Lug

Examples:
  wai lug add "Fix login bug"
  wai lug list --status=open --type=bug
  wai lug ready
  wai lug show a3f2
  wai lug update a3f2 --status=in_progress
  wai lug close a3f2
    """)


def _create_lug(manager: LugManager, args: list):
    """Create a new Lug interactively or via flags."""
    import argparse
    parser = argparse.ArgumentParser(description="Create Lug", add_help=False)
    parser.add_argument('--title', help='Lug title')
    parser.add_argument('--type', dest='lug_type', help='Lug type')
    parser.add_argument('--priority', help='Priority')
    parser.add_argument('--impact', help='Impact')
    parser.add_argument('--value', type=int, help='Value/ROI')
    parser.add_argument('--description', help='Description/Justification')
    parser.add_argument('--origin', help='Origin')

    # Parse known args, leaving rest for title if needed
    parsed, unknown = parser.parse_known_args(args)
    
    # If title provided via flag, use it. Otherwise join positional args.
    title = parsed.title or ((' '.join(unknown)) if unknown else None)

    if not title:
        print_error("Usage: wai lug create <title> [options]")
        sys.exit(1)
    
    # If explicit flags provided, we skip interactive prompts for those fields
    # But if it's mixed provided/not provided, we might still prompt? 
    # For now, let's assume if flags are present we use them, if not we default.
    # Interactive mode is better if ONLY title is provided.
    
    interactive = not (parsed.lug_type or parsed.priority or parsed.impact or parsed.value)

    if interactive:
        print_info(f"\n📝 Creating Lug: {title}\n")
        
        # Prompt for type
        print_info("Type options: epic, issue, bug, work, ask (or custom)")
        lug_type = input("  Type [work]: ").strip() or 'work'
        
        # Prompt for priority
        print_info("Priority options: low, medium, high")
        priority = input("  Priority [medium]: ").strip() or 'medium'
        
        # Prompt for impact
        print_info("Impact options: small, medium, large")
        impact = input("  Impact [medium]: ").strip() or 'medium'
        
        # Prompt for value
        print_info("Value: 1-10 (ROI score)")
        value_input = input("  Value [5]: ").strip()
        value = int(value_input) if value_input else 5
        
        # Optional justification
        print_info("Justification (optional, press Enter to skip):")
        justification = input("  > ").strip() or None
        
        # Optional origin
        print_info("Origin (optional, e.g., 'user_request:chat', press Enter to skip):")
        origin = input("  > ").strip() or None

    else:
        # Non-interactive / Flags mode
        lug_type = parsed.lug_type or 'work'
        priority = parsed.priority or 'medium'
        impact = parsed.impact or 'medium'
        value = parsed.value or 5
        justification = parsed.description
        origin = parsed.origin

    # Create the Lug
    lug = manager.create_lug(
        title=title,
        lug_type=lug_type,
        priority=priority,
        impact=impact,
        value=value,
        justification=justification,
        origin=origin
    )
    
    print_success(f"\n✓ Created Lug: {lug.id}")
    print_info(f"  Title: {lug.title}")
    print_info(f"  Type: {lug.type}")
    print_info(f"  Priority: {lug.priority}")
    print_info(f"  Impact: {lug.impact}")
    print_info(f"  Value: {lug.value}")
    print_info(f"  Status: {lug.status}\n")
    
    # YOLO mode gating
    if priority == 'high' or impact == 'large' or value >= 7:
        print_warning("⚠️  High priority/impact/value detected!")
        print_info("YOLO mode: Consider reviewing before proceeding with implementation.\n")


def _list_lugs(manager: LugManager, args: list):
    """List Lugs with optional filters."""
    # Parse filters
    status_filter = None
    type_filter = None
    priority_filter = None
    
    for arg in args:
        if arg.startswith('--status='):
            status_filter = arg.split('=')[1]
        elif arg.startswith('--type='):
            type_filter = arg.split('=')[1]
        elif arg.startswith('--priority='):
            priority_filter = arg.split('=')[1]
    
    lugs = manager.list_lugs(status=status_filter, lug_type=type_filter, priority=priority_filter)
    
    if not lugs:
        print_info("No Lugs found.")
        return
    
    print_info(f"\n📋 Found {len(lugs)} Lug(s):\n")
    print_info(f"{'ID':<10} {'Type':<8} {'Pri':<8} {'Status':<12} {'Title'}")
    print_info("-" * 80)
    
    for lug in lugs:
        # Truncate title for clean table
        title = (lug.title[:45] + '...') if len(lug.title) > 48 else lug.title
        
        type_str = _colorize(f"{lug.type:<8}", _get_type_color(lug.type))
        pri_str = _colorize(f"{lug.priority[:3]:<8}", _get_priority_color(lug.priority))
        status_str = _colorize(f"{lug.status:<12}", _get_status_color(lug.status))
        
        print_info(f"{lug.id[:8]:<10} {type_str} {pri_str} {status_str} {title}")
    
    print_info("")


def _list_ready_lugs(manager: LugManager, args: list):
    """List Lugs that are ready to close."""
    lugs = manager.list_lugs_ready_to_close()
    
    if not lugs:
        print_info("\nNo Lugs currently pass all policy requirements for closing.\n")
        return
    
    print_info(f"\n✅ Found {len(lugs)} Lug(s) ready to close:\n")
    print_info(f"{'ID':<10} {'Type':<8} {'Pri':<8} {'Title'}")
    print_info("-" * 60)
    
    for lug in lugs:
        title = (lug.title[:45] + '...') if len(lug.title) > 48 else lug.title
        
        type_str = _colorize(f"{lug.type:<8}", _get_type_color(lug.type))
        pri_str = _colorize(f"{lug.priority[:3]:<8}", _get_priority_color(lug.priority))
        
        print_info(f"{lug.id[:8]:<10} {type_str} {pri_str} {title}")
    
    print_info("\nUse 'wai lug close <id>' to finalize.\n")


def _show_lug(manager: LugManager, args: list):
    """Show detailed Lug information."""
    if not args:
        print_error("Usage: wai lug show <id-prefix>")
        sys.exit(1)
    
    lug_id_prefix = args[0]
    
    try:
        lug = manager.get_lug(lug_id_prefix)
        if not lug:
            print_error(f"No Lug found with ID prefix: {lug_id_prefix}")
            sys.exit(1)
        
        print_info(f"\n📌 Lug: {lug.id}\n")
        print_info(f"  Title: {lug.title}")
        print_info(f"  Type: {lug.type}")
        print_info(f"  Status: {lug.status}")
        print_info(f"  Priority: {lug.priority}")
        print_info(f"  Impact: {lug.impact}")
        print_info(f"  Value: {lug.value}")
        print_info(f"  Created: {lug.created_at}")
        print_info(f"  Updated: {lug.updated_at}")
        
        if lug.closed_at:
            print_info(f"  Closed: {lug.closed_at}")
        
        if lug.deps:
            print_info(f"  Dependencies: {', '.join(lug.deps)}")
        
        if lug.blocked_by:
            print_info(f"  Blocked by: {', '.join(lug.blocked_by)}")
        
        if lug.policy_tags:
            print_info(f"  Policy tags: {', '.join(lug.policy_tags)}")
        
        if lug.justification:
            print_info(f"  Justification: {lug.justification}")
        
        if lug.origin:
            print_info(f"  Origin: {lug.origin}")
        
        if lug.from_file:
            print_info(f"  From file: {lug.from_file}")
        
        if lug.summary:
            print_info(f"  Summary: {lug.summary}")
        
        if lug.resolved_by:
            print_info(f"  Resolved by: {lug.resolved_by}")
        
        if lug.extras:
            print_info(f"  Extras: {lug.extras}")
        
        print_info("")
        
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)


def _update_lug(manager: LugManager, args: list):
    """Update an existing Lug."""
    if not args:
        print_error("Usage: wai lug update <id-prefix> [--status=STATUS] [--priority=PRIORITY] ...")
        sys.exit(1)
    
    lug_id_prefix = args[0]
    
    # Parse updates
    status = None
    priority = None
    impact = None
    value = None
    
    for arg in args[1:]:
        if arg.startswith('--status='):
            status = arg.split('=')[1]
        elif arg.startswith('--priority='):
            priority = arg.split('=')[1]
        elif arg.startswith('--impact='):
            impact = arg.split('=')[1]
        elif arg.startswith('--value='):
            value = int(arg.split('=')[1])
    
    if not any([status, priority, impact, value]):
        print_error("No updates specified. Use --status, --priority, --impact, or --value.")
        sys.exit(1)
    
    try:
        lug = manager.update_lug(
            lug_id_prefix=lug_id_prefix,
            status=status,
            priority=priority,
            impact=impact,
            value=value
        )
        
        print_success(f"✓ Updated Lug: {lug.id}")
        print_info(f"  Status: {lug.status}")
        print_info(f"  Priority: {lug.priority}")
        print_info(f"  Impact: {lug.impact}")
        print_info(f"  Value: {lug.value}\n")
        
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)


def _close_lug(manager: LugManager, args: list):
    """Close and archive a Lug."""
    if not args:
        print_error("Usage: wai lug close <id-prefix>")
        sys.exit(1)
    
    lug_id_prefix = args[0]
    
    try:
        lug = manager.get_lug(lug_id_prefix)
        if not lug:
            print_error(f"No Lug found with ID prefix: {lug_id_prefix}")
            sys.exit(1)
        
        print_info(f"\n🔒 Closing Lug: {lug.id}")
        print_info(f"  Title: {lug.title}\n")
        
        # Optional summary
        print_info("Summary (optional, press Enter to skip):")
        summary = input("  > ").strip() or None
        
        # Check policies
        violations = manager.validate_policies(lug)
        if violations:
            print_warning("⚠️  Policy violations detected:")
            for violation in violations:
                print_warning(f"    - {violation}")
            
            if not safe_confirm("\nClose anyway?", default=False):
                print_info("Cancelled.")
                return
        
        # Close the Lug
        closed_lug = manager.close_lug(
            lug_id_prefix=lug_id_prefix,
            summary=summary,
            skip_policy_check=bool(violations)  # Skip check if user confirmed
        )
        
        print_success(f"\n✓ Closed Lug: {closed_lug.id}")
        print_info(f"  Archived to: lugs-closed.jsonl\n")
        
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)
