"""
Baseline Command

Manages baseline mode for token savings measurement and runs automated
baseline vs optimized comparisons.

Baseline mode allows tracking of unoptimized AI sessions to establish
a performance baseline for comparison with Wheelwright-optimized sessions.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..utils.input import print_info, print_success, print_error, print_warning
from ..utils.paths import normalize_path
from ..init import check_spoke_initialized
from ..baseline_helpers import detect_ide_model


def _format_datetime(value: str) -> str:
    """
    Return a human-readable UTC timestamp for ISO-like inputs.

    Args:
        value: ISO-formatted timestamp string

    Returns:
        Formatted datetime string or original value if parsing fails
    """
    if not value:
        return "Unknown"
    try:
        normalized = value.replace('Z', '+00:00')
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value


def cmd_baseline(args):
    """
    Handle baseline command - manages baseline mode and runs comparisons.

    Subcommands:
        enable  - Enable baseline tracking mode
        disable - Disable baseline mode and lock data
        status  - Show current baseline mode status
        run     - Run automated baseline vs optimized comparison

    Args:
        args: Argument namespace with 'path' and 'baseline_command' attributes
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

        if not hasattr(args, 'baseline_command') or args.baseline_command is None:
            # Show status by default
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
                state = json.load(f)

            baseline = state.get('analytics', {}).get('baseline_mode', {})

            print_info("\n" + "=" * 60)
            print_info("  Baseline Mode Status")
            print_info("=" * 60 + "\n")

            if baseline.get('enabled'):
                print_success("  Status: ENABLED")
                print_info(f"  Started: {_format_datetime(baseline.get('started_at'))}")
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
                    print_info(f"    Period: {_format_datetime(baseline.get('started_at'))} to {_format_datetime(baseline.get('ended_at'))}\n")
                else:
                    print_info("\n  No baseline data collected yet.\n")
                    print_info("  To enable: WAI baseline enable\n")

            print_info("=" * 60 + "\n")

        elif args.baseline_command == 'run':
            ide = getattr(args, 'ide', None)
            model = getattr(args, 'model', None)
            notes = getattr(args, 'notes', None)
            _run_baseline_comparison(spoke_path, ide=ide, model=model, notes=notes)

    except Exception as e:
        print_error(f"Baseline command failed: {e}")
        import traceback
        traceback.print_exc()


def _run_baseline_comparison(spoke_path: Path, ide: str = None, model: str = None, notes: str = None):
    """
    Run a synthetic baseline vs optimized comparison and log results.

    Creates two simulated sessions (baseline and optimized), measures their
    token usage, and logs the comparison results to WAI-Baseline-Log.jsonl.

    Args:
        spoke_path: Path to the spoke directory
        ide: IDE identifier (auto-detected if not provided)
        model: AI model identifier (auto-detected if not provided)
        notes: Optional notes to include in the log entry
    """
    from ..metrics import MetricsTracker
    from ..session import SessionManager

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

    resolved_ide, resolved_model = detect_ide_model(ide, model)
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat() + "Z"

    pre_stats = metrics.get_session_stats()
    pre_optimized_tokens = state.get('analytics', {}).get('token_efficiency', {}).get('total_tokens_used', 0)
    pre_baseline_tokens = baseline_state.get('total_tokens_used', 0)

    print_info("\n📏 Running automated baseline comparison...\n")

    # Baseline capture
    metrics.enable_baseline_mode()
    baseline_session = _simulate_session(
        SessionManager(spoke_path),
        ai_model=resolved_model,
        label="baseline"
    )
    metrics.record_session_end(baseline_session)
    metrics.disable_baseline_mode()

    # Optimized capture
    optimized_session = _simulate_session(
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


def _simulate_session(session: "SessionManager", ai_model: str, label: str) -> Dict[str, Any]:
    """
    Simulate a short session and return session metrics.

    Creates a simulated conversation turn with different verbosity levels
    for baseline vs optimized sessions.

    Args:
        session: SessionManager instance
        ai_model: AI model identifier
        label: Session label ("baseline" or "optimized")

    Returns:
        Dictionary containing session metrics (session_id, turns, tokens_estimate, etc.)
    """
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
