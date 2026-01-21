"""
History Command - Visualize session bead chain.
"""

import sys
from pathlib import Path
from ..lugs import LugManager
from ..utils.input import print_info, print_success, print_error, print_warning

def history_command_group(args: list, spoke_dir: Path):
    """Handle 'wai history' command."""
    # Initialize implementation with correct path (WAI-Spoke)
    # spoke_dir passed in is project root, we need WAI-Spoke for data
    wai_spoke_dir = spoke_dir / 'WAI-Spoke'
    manager = LugManager(wai_spoke_dir)
    
    _show_history(manager)

def _show_history(manager: LugManager):
    """Render the bead chain visualization."""
    beads = manager.get_bead_chain()
    validation = manager.validate_bead_chain()
    
    if not beads:
        print_info("\n📿 No session history (beads) found yet.\n")
        return

    print_info(f"\n📜 Session History ({len(beads)} beads)\n")
    
    # ASCII Visualization
    # ● [8f7a2b] 2026-01-01 12:00:00 (Session summary truncated...)
    # │
    # ● ...
    
    for i, bead in enumerate(beads):
        bead_id = bead.get('bead_id', '????????')[:8]
        timestamp = bead.get('timestamp', 'Unknown')
        # Format timestamp for readability if ISO
        try:
            ts_short = timestamp.replace('T', ' ')[:16]
        except:
            ts_short = timestamp
            
        summary = bead.get('summary', 'No summary')
        if len(summary) > 60:
            summary = summary[:57] + "..."
            
        # Coloring for the node (dot)
        # First node (genesis for this file) or valid link
        is_genesis = bead.get('parent_id') is None
        
        # Check if this specific bead had errors in validation (naive check)
        # Validation returns list of error strings, not mapped to IDs directly in this simpler impl
        # So we just check global validity
        
        marker = "●"
        connector = "│"
        
        print_info(f" {marker} [{bead_id}] {ts_short}  {summary}")
        
        # Draw connector unless it's the last one
        if i < len(beads) - 1:
             print_info(f" {connector}")
             
    print_info("")
    
    # Validation Status Footer
    if validation['valid']:
        print_success("✓ Chain integrity verified: Valid")
    else:
        print_warning(f"⚠️  Chain integrity issues: {len(validation['errors'])} errors")
        for err in validation['errors']:
            print_error(f"  - {err}")
    print_info("")


def cmd_changelog(args):
    """
    Handle history/changelog command.

    Args:
        args: Argument namespace (unused for now)
    """
    spoke_dir = Path.cwd()
    # Extract remaining args from the namespace
    history_args = getattr(args, 'history_args', [])
    history_command_group(history_args, spoke_dir)
