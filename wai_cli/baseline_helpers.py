"""
Baseline Test Management Helpers

This module provides helper functions for managing baseline test runs in the
Wheelwright framework. Baseline tests measure token savings and AI performance
across different IDE and model combinations.

Functions:
    load_baseline_runs: Load baseline test runs from log
    print_baseline_runs: Display baseline run summaries
    log_test_result: Log test execution results
    print_test_log: Display recent test logs
    detect_ide_model: Auto-detect IDE and model for baseline tracking
    get_latest_baseline_summary: Get one-line summary of most recent baseline
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .utils.input import print_info
from .utils.paths import normalize_path


def load_baseline_runs(spoke_path: Path) -> list:
    """
    Load baseline runs from log.

    Args:
        spoke_path: Path to the spoke directory

    Returns:
        List of baseline run entries (dicts)
    """
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
                runs.append(json.loads(line))
            except Exception:
                continue
    return runs


def print_baseline_runs(runs: list):
    """
    Print baseline runs summary.

    Args:
        runs: List of baseline run entries
    """
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


def log_test_result(spoke_path: Path, test_name: str, exit_code: int, output: str):
    """
    Append test result to log.

    Args:
        spoke_path: Path to the spoke directory
        test_name: Name of the test that was run
        exit_code: Exit code from test execution
        output: Test output (currently unused but kept for future expansion)
    """
    log_path = spoke_path / 'WAI-Spoke' / 'WAI-Testing-Log.jsonl'
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test": test_name,
        "exit_code": exit_code,
        "status": "pass" if exit_code == 0 else "fail"
    }
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + "\n")


def print_test_log(spoke_path: Path):
    """
    Print recent test log entries.

    Args:
        spoke_path: Path to the spoke directory
    """
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


def detect_ide_model(ide: str = None, model: str = None) -> tuple:
    """
    Best-effort detection of IDE and model.

    Checks environment variables to auto-detect the IDE and model being used.
    Useful for baseline tracking when not explicitly provided.

    Args:
        ide: Pre-specified IDE (optional)
        model: Pre-specified model (optional)

    Returns:
        Tuple of (ide, model) strings
    """
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


def get_latest_baseline_summary(spoke_path: Path) -> str:
    """
    Return a one-line summary of the latest baseline run, if available.

    Args:
        spoke_path: Path to the spoke directory

    Returns:
        One-line summary string, or empty string if no baseline runs exist
    """
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
