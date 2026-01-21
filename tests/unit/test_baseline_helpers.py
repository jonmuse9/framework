"""
Unit tests for baseline test management helpers.

Tests cover:
- Loading baseline runs from JSONL logs
- Printing baseline run summaries
- Logging test results
- Printing test logs
- IDE and model auto-detection
- Getting latest baseline summary
"""

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, call
import pytest

from wai_cli.baseline_helpers import (
    load_baseline_runs,
    print_baseline_runs,
    log_test_result,
    print_test_log,
    detect_ide_model,
    get_latest_baseline_summary
)


class TestLoadBaselineRuns:
    """Test loading baseline runs from log."""

    def test_load_empty_log(self, tmp_path):
        """Loading from non-existent log returns empty list."""
        result = load_baseline_runs(tmp_path)
        assert result == []

    def test_load_single_run(self, tmp_path):
        """Loading single run from log works correctly."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        run_data = {
            "timestamp": "2024-01-15T14:30:00Z",
            "ide": "Claude Code",
            "model": "Sonnet 4.5",
            "savings": {"percent_saved": 45.2}
        }
        log_file.write_text(json.dumps(run_data) + "\n")

        result = load_baseline_runs(tmp_path)
        assert len(result) == 1
        assert result[0]["ide"] == "Claude Code"
        assert result[0]["savings"]["percent_saved"] == 45.2

    def test_load_multiple_runs(self, tmp_path):
        """Loading multiple runs from log works correctly."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        runs = [
            {"timestamp": "2024-01-15T14:30:00Z", "ide": "Claude Code", "savings": {"percent_saved": 45.2}},
            {"timestamp": "2024-01-16T10:00:00Z", "ide": "Cursor", "savings": {"percent_saved": 52.1}},
            {"timestamp": "2024-01-17T08:15:00Z", "ide": "Claude Code", "savings": {"percent_saved": 48.7}}
        ]

        with open(log_file, 'w') as f:
            for run in runs:
                f.write(json.dumps(run) + "\n")

        result = load_baseline_runs(tmp_path)
        assert len(result) == 3
        assert result[0]["savings"]["percent_saved"] == 45.2
        assert result[2]["savings"]["percent_saved"] == 48.7

    def test_skip_empty_lines(self, tmp_path):
        """Empty lines in log are skipped."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        run1 = {"timestamp": "2024-01-15T14:30:00Z", "ide": "Claude Code"}
        run2 = {"timestamp": "2024-01-16T10:00:00Z", "ide": "Cursor"}

        with open(log_file, 'w') as f:
            f.write(json.dumps(run1) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps(run2) + "\n")

        result = load_baseline_runs(tmp_path)
        assert len(result) == 2

    def test_skip_malformed_json(self, tmp_path):
        """Malformed JSON lines are skipped."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        run = {"timestamp": "2024-01-15T14:30:00Z", "ide": "Claude Code"}

        with open(log_file, 'w') as f:
            f.write(json.dumps(run) + "\n")
            f.write("{ invalid json }\n")
            f.write(json.dumps(run) + "\n")

        result = load_baseline_runs(tmp_path)
        assert len(result) == 2


class TestPrintBaselineRuns:
    """Test printing baseline run summaries."""

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_empty_runs(self, mock_print):
        """Printing empty runs shows no data message."""
        print_baseline_runs([])
        mock_print.assert_called_with("\n  No baseline runs recorded.")

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_single_run(self, mock_print):
        """Printing single run displays correctly."""
        runs = [
            {"timestamp": "2024-01-15T14:30:00Z", "ide": "Claude Code",
             "model": "Sonnet 4.5", "savings": {"percent_saved": 45.2}}
        ]
        print_baseline_runs(runs)

        # Should print header and one run
        assert mock_print.call_count == 2
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert "\n  Recent runs:" in calls
        assert any("Claude Code" in call and "45.2%" in call for call in calls)

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_last_five_runs(self, mock_print):
        """Only last 5 runs are printed."""
        runs = [
            {"timestamp": f"2024-01-{i:02d}T14:30:00Z", "ide": "Claude Code",
             "model": "Sonnet", "savings": {"percent_saved": i * 10}}
            for i in range(1, 11)
        ]
        print_baseline_runs(runs)

        # Should print header + 5 runs
        assert mock_print.call_count == 6

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_handles_missing_fields(self, mock_print):
        """Handles runs with missing fields gracefully."""
        runs = [
            {"timestamp": "2024-01-15T14:30:00Z"}  # Missing ide, model, savings
        ]
        print_baseline_runs(runs)

        # Should still print without errors
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Unknown" in call for call in calls)


class TestLogTestResult:
    """Test logging test results."""

    def test_log_passing_test(self, tmp_path):
        """Passing test is logged correctly."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()

        log_test_result(tmp_path, "test_example", 0, "Test passed")

        log_file = spoke_dir / "WAI-Testing-Log.jsonl"
        assert log_file.exists()

        with open(log_file, 'r') as f:
            entry = json.loads(f.read())

        assert entry["test"] == "test_example"
        assert entry["exit_code"] == 0
        assert entry["status"] == "pass"
        assert "timestamp" in entry

    def test_log_failing_test(self, tmp_path):
        """Failing test is logged correctly."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()

        log_test_result(tmp_path, "test_failure", 1, "Test failed")

        log_file = spoke_dir / "WAI-Testing-Log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.read())

        assert entry["test"] == "test_failure"
        assert entry["exit_code"] == 1
        assert entry["status"] == "fail"

    def test_log_multiple_tests(self, tmp_path):
        """Multiple test results are appended to log."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()

        log_test_result(tmp_path, "test1", 0, "")
        log_test_result(tmp_path, "test2", 1, "")
        log_test_result(tmp_path, "test3", 0, "")

        log_file = spoke_dir / "WAI-Testing-Log.jsonl"
        with open(log_file, 'r') as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 3
        assert entries[0]["test"] == "test1"
        assert entries[1]["test"] == "test2"
        assert entries[2]["test"] == "test3"


class TestPrintTestLog:
    """Test printing test log entries."""

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_no_log_file(self, mock_print, tmp_path):
        """Prints message when no log file exists."""
        print_test_log(tmp_path)
        mock_print.assert_called_with("\n  No test results logged yet.")

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_empty_log(self, mock_print, tmp_path):
        """Prints message when log is empty."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Testing-Log.jsonl"
        log_file.touch()

        print_test_log(tmp_path)
        mock_print.assert_called_with("\n  No test results logged yet.")

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_single_test_result(self, mock_print, tmp_path):
        """Prints single test result correctly."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Testing-Log.jsonl"

        entry = {
            "timestamp": "2024-01-15T14:30:00Z",
            "test": "test_example",
            "status": "pass"
        }
        log_file.write_text(json.dumps(entry) + "\n")

        print_test_log(tmp_path)

        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Recent test results" in call for call in calls)
        assert any("test_example" in call and "pass" in call for call in calls)

    @patch('wai_cli.baseline_helpers.print_info')
    def test_print_last_five_results(self, mock_print, tmp_path):
        """Only last 5 test results are printed."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Testing-Log.jsonl"

        with open(log_file, 'w') as f:
            for i in range(10):
                entry = {
                    "timestamp": f"2024-01-{i+1:02d}T14:30:00Z",
                    "test": f"test_{i}",
                    "status": "pass"
                }
                f.write(json.dumps(entry) + "\n")

        print_test_log(tmp_path)

        # Should print header + 5 results
        assert mock_print.call_count == 6


class TestDetectIDEModel:
    """Test IDE and model auto-detection."""

    def test_detect_codex_cli(self):
        """Codex CLI detected from environment."""
        with patch.dict(os.environ, {"CODEX_CLI": "true"}):
            ide, model = detect_ide_model()
            assert ide == "Codex CLI"

    def test_detect_codex_via_project_dir(self):
        """Codex detected via CODEX_PROJECT_DIR."""
        with patch.dict(os.environ, {"CODEX_PROJECT_DIR": "/path/to/project"}):
            ide, model = detect_ide_model()
            assert ide == "Codex CLI"

    def test_detect_claude_code(self):
        """Claude Code detected from environment."""
        with patch.dict(os.environ, {"CLAUDE_CLI": "true"}, clear=True):
            ide, model = detect_ide_model()
            assert ide == "Claude Code"

    def test_detect_unknown_ide(self):
        """Unknown IDE when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            ide, model = detect_ide_model()
            assert ide == "Unknown IDE"

    def test_detect_model_from_env(self):
        """Model detected from AI_MODEL env var."""
        with patch.dict(os.environ, {"AI_MODEL": "GPT-4"}):
            ide, model = detect_ide_model()
            assert model == "GPT-4"

    def test_unknown_model_when_not_set(self):
        """Unknown model when AI_MODEL not set."""
        with patch.dict(os.environ, {}, clear=True):
            ide, model = detect_ide_model()
            assert model == "Unknown Model"

    def test_prespecified_ide_not_overridden(self):
        """Pre-specified IDE is not overridden."""
        with patch.dict(os.environ, {"CODEX_CLI": "true"}):
            ide, model = detect_ide_model(ide="Custom IDE")
            assert ide == "Custom IDE"

    def test_prespecified_model_not_overridden(self):
        """Pre-specified model is not overridden."""
        with patch.dict(os.environ, {"AI_MODEL": "GPT-4"}):
            ide, model = detect_ide_model(model="Custom Model")
            assert model == "Custom Model"


class TestGetLatestBaselineSummary:
    """Test getting latest baseline summary."""

    def test_no_log_file_returns_empty(self, tmp_path):
        """Returns empty string when no log file."""
        result = get_latest_baseline_summary(tmp_path)
        assert result == ""

    def test_empty_log_returns_empty(self, tmp_path):
        """Returns empty string when log is empty."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"
        log_file.touch()

        result = get_latest_baseline_summary(tmp_path)
        assert result == ""

    def test_get_latest_with_savings(self, tmp_path):
        """Returns summary with savings percentage."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        entry = {
            "timestamp": "2024-01-15T14:30:00Z",
            "ide": "Claude Code",
            "model": "Sonnet 4.5",
            "savings": {"percent_saved": 45.2}
        }
        log_file.write_text(json.dumps(entry) + "\n")

        result = get_latest_baseline_summary(tmp_path)
        assert "2024-01-15T14:30:00Z" in result
        assert "Claude Code" in result
        assert "Sonnet 4.5" in result
        assert "45.2%" in result

    def test_get_latest_without_savings(self, tmp_path):
        """Returns summary without savings when not available."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        entry = {
            "timestamp": "2024-01-15T14:30:00Z",
            "ide": "Claude Code",
            "model": "Sonnet 4.5"
        }
        log_file.write_text(json.dumps(entry) + "\n")

        result = get_latest_baseline_summary(tmp_path)
        assert "2024-01-15T14:30:00Z" in result
        assert "Claude Code" in result
        assert "%" not in result

    def test_get_latest_from_multiple_entries(self, tmp_path):
        """Returns only the latest entry."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"

        entries = [
            {"timestamp": "2024-01-15T14:30:00Z", "ide": "Cursor", "model": "GPT-4", "savings": {"percent_saved": 30.0}},
            {"timestamp": "2024-01-16T10:00:00Z", "ide": "Claude Code", "model": "Sonnet", "savings": {"percent_saved": 45.2}}
        ]

        with open(log_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = get_latest_baseline_summary(tmp_path)
        assert "2024-01-16T10:00:00Z" in result
        assert "Claude Code" in result
        assert "45.2%" in result
        assert "Cursor" not in result

    def test_malformed_json_returns_empty(self, tmp_path):
        """Returns empty string when JSON is malformed."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        log_file = spoke_dir / "WAI-Baseline-Log.jsonl"
        log_file.write_text("{ invalid json }\n")

        result = get_latest_baseline_summary(tmp_path)
        assert result == ""
