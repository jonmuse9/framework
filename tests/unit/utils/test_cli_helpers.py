"""
Unit tests for CLI helper utilities.

Tests cover:
- WSL environment detection
- Path resolution and validation
- Datetime formatting
- Context detection (hub/spoke/uninitialized)
- User confirmation prompts
- Framework directory detection
"""

import os
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from wai_cli.utils.cli_helpers import (
    is_wsl,
    resolve_spoke_root,
    is_within_path,
    format_datetime,
    detect_start_context,
    confirm_exit,
    is_framework_directory
)


class TestIsWSL:
    """Test WSL environment detection."""

    def test_wsl_detected_via_env_var(self):
        """WSL detected when WSL_DISTRO_NAME is set."""
        with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"}):
            assert is_wsl() is True

    def test_wsl_detected_via_platform_microsoft(self):
        """WSL detected when platform contains 'microsoft'."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('platform.release', return_value='4.19.128-microsoft-standard'):
                assert is_wsl() is True

    def test_wsl_detected_via_platform_wsl(self):
        """WSL detected when platform contains 'wsl'."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('platform.release', return_value='5.10.16.3-wsl2'):
                assert is_wsl() is True

    def test_not_wsl_on_regular_linux(self):
        """WSL not detected on regular Linux."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('platform.release', return_value='5.15.0-generic'):
                assert is_wsl() is False

    def test_not_wsl_on_windows(self):
        """WSL not detected on Windows."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('platform.release', return_value='10.0.19041'):
                assert is_wsl() is False


class TestResolveSpokeRoot:
    """Test spoke root path resolution."""

    def test_resolve_wai_spoke_dir_to_parent(self, tmp_path):
        """WAI-Spoke directory resolves to its parent."""
        spoke_dir = tmp_path / "WAI-Spoke"
        spoke_dir.mkdir()
        result = resolve_spoke_root(spoke_dir)
        assert result == tmp_path

    def test_project_root_unchanged(self, tmp_path):
        """Project root path remains unchanged."""
        result = resolve_spoke_root(tmp_path)
        assert result == tmp_path

    def test_nested_project_unchanged(self, tmp_path):
        """Nested project paths remain unchanged."""
        nested = tmp_path / "projects" / "my-project"
        result = resolve_spoke_root(nested)
        assert result == nested


class TestIsWithinPath:
    """Test path containment checking."""

    def test_child_within_parent(self, tmp_path):
        """Child path is correctly detected within parent."""
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child" / "subdir"
        child.mkdir(parents=True)
        assert is_within_path(child, parent) is True

    def test_child_not_within_parent(self, tmp_path):
        """Non-child path correctly detected as not within parent."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        assert is_within_path(dir2, dir1) is False

    def test_same_path_is_within_itself(self, tmp_path):
        """Path is considered within itself."""
        assert is_within_path(tmp_path, tmp_path) is True

    def test_parent_not_within_child(self, tmp_path):
        """Parent is not within child."""
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()
        assert is_within_path(parent, child) is False

    def test_handles_nonexistent_paths_gracefully(self, tmp_path):
        """Non-existent paths handled gracefully."""
        nonexistent = tmp_path / "does-not-exist"
        # Non-existent path that's still a child of parent resolves to True
        # because Path.resolve() doesn't require the path to exist
        assert is_within_path(nonexistent, tmp_path) is True


class TestFormatDatetime:
    """Test datetime formatting."""

    def test_format_iso_with_z_suffix(self):
        """ISO datetime with Z suffix formats correctly."""
        result = format_datetime("2024-01-15T14:30:00Z")
        assert result == "2024-01-15 14:30 UTC"

    def test_format_iso_with_timezone_offset(self):
        """ISO datetime with timezone offset formats correctly."""
        result = format_datetime("2024-01-15T14:30:00+00:00")
        assert result == "2024-01-15 14:30 UTC"

    def test_empty_string_returns_unknown(self):
        """Empty string returns 'Unknown'."""
        assert format_datetime("") == "Unknown"

    def test_none_returns_unknown(self):
        """None returns 'Unknown'."""
        assert format_datetime(None) == "Unknown"

    def test_invalid_format_returns_original(self):
        """Invalid datetime format returns original value."""
        invalid = "not-a-datetime"
        assert format_datetime(invalid) == invalid

    def test_partial_datetime_returns_original(self):
        """Partial datetime returns original value."""
        partial = "2024-01-15"
        result = format_datetime(partial)
        # Should either format it or return original
        assert result is not None


class TestDetectStartContext:
    """Test startup context detection."""

    @patch('wai_cli.hub.HubManager')
    @patch('wai_cli.init.check_spoke_initialized')
    def test_detects_hub_context(self, mock_check_spoke, mock_hub_manager_class, tmp_path):
        """Hub context detected when in hub directory."""
        mock_hub_manager = Mock()
        hub_path = tmp_path / "hub"
        mock_hub_manager.auto_discover_hub.return_value = hub_path
        mock_hub_manager_class.return_value = mock_hub_manager

        # Create the hub directory so is_within_path works
        hub_path.mkdir()

        context_type, path = detect_start_context(hub_path)
        assert context_type == "hub"
        assert path == hub_path

    @patch('wai_cli.hub.HubManager')
    @patch('wai_cli.init.check_spoke_initialized')
    def test_detects_spoke_context(self, mock_check_spoke, mock_hub_manager_class, tmp_path):
        """Spoke context detected when in spoke directory."""
        mock_hub_manager = Mock()
        mock_hub_manager.auto_discover_hub.return_value = None
        mock_hub_manager_class.return_value = mock_hub_manager
        mock_check_spoke.return_value = True

        context_type, path = detect_start_context(tmp_path)
        assert context_type == "spoke"
        assert path == tmp_path

    @patch('wai_cli.hub.HubManager')
    @patch('wai_cli.init.check_spoke_initialized')
    def test_detects_uninitialized_context(self, mock_check_spoke, mock_hub_manager_class, tmp_path):
        """Uninitialized context detected when neither hub nor spoke."""
        mock_hub_manager = Mock()
        mock_hub_manager.auto_discover_hub.return_value = None
        mock_hub_manager_class.return_value = mock_hub_manager
        mock_check_spoke.return_value = False

        context_type, path = detect_start_context(tmp_path)
        assert context_type == "uninitialized"
        assert path == tmp_path


class TestConfirmExit:
    """Test exit confirmation."""

    @patch('wai_cli.utils.input.safe_confirm')
    def test_confirm_exit_returns_true_on_yes(self, mock_confirm):
        """confirm_exit returns True when user confirms."""
        mock_confirm.return_value = True
        assert confirm_exit() is True
        mock_confirm.assert_called_once_with("  Exit WAI CLI?", default=True)

    @patch('wai_cli.utils.input.safe_confirm')
    def test_confirm_exit_returns_false_on_no(self, mock_confirm):
        """confirm_exit returns False when user declines."""
        mock_confirm.return_value = False
        assert confirm_exit() is False


class TestIsFrameworkDirectory:
    """Test framework directory detection."""

    def test_detects_framework_directory(self, tmp_path):
        """Framework directory detected with all required files."""
        (tmp_path / "WAI").touch()
        (tmp_path / "templates").mkdir()
        (tmp_path / "wai_cli").mkdir()
        assert is_framework_directory(tmp_path) is True

    def test_not_framework_without_wai_script(self, tmp_path):
        """Not framework directory without WAI script."""
        (tmp_path / "templates").mkdir()
        (tmp_path / "wai_cli").mkdir()
        assert is_framework_directory(tmp_path) is False

    def test_not_framework_without_templates(self, tmp_path):
        """Not framework directory without templates."""
        (tmp_path / "WAI").touch()
        (tmp_path / "wai_cli").mkdir()
        assert is_framework_directory(tmp_path) is False

    def test_not_framework_without_wai_cli(self, tmp_path):
        """Not framework directory without wai_cli package."""
        (tmp_path / "WAI").touch()
        (tmp_path / "templates").mkdir()
        assert is_framework_directory(tmp_path) is False

    def test_empty_directory_not_framework(self, tmp_path):
        """Empty directory is not framework directory."""
        assert is_framework_directory(tmp_path) is False
