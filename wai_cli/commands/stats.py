"""
Stats Command

Displays project statistics and analytics including session metrics,
token efficiency, time tracking, and AI wins.
"""

from ..utils.input import print_info, print_success, print_error, print_warning
from ..utils.paths import normalize_path
from ..init import check_spoke_initialized


def cmd_stats(args):
    """
    Handle stats command.

    Displays comprehensive analytics for the Wheelwright spoke including:
    - Session statistics (total sessions, average turns, duration)
    - Token efficiency metrics
    - Token savings vs baseline (if available)
    - Time tracking (total time, time together, time AI alone)
    - AI wins (recent accomplishments)

    Args:
        args: Argument namespace with 'path' attribute
    """
    from ..metrics import MetricsTracker

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
