"""
Time Command

Displays token usage estimation and context capacity warnings.
Helps users understand their current context window consumption.
"""

import json
from ..utils.input import print_info, print_success, print_error
from ..utils.paths import normalize_path
from ..init import check_spoke_initialized


def cmd_time(args):
    """
    Handle time command - show token usage and capacity.

    Displays current token usage estimate, context window capacity,
    and warnings if approaching limits. Also shows conversation log
    statistics if available.

    Args:
        args: Argument namespace with 'path' attribute
    """
    from ..session import SessionManager

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
