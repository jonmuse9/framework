"""CLI helper utilities for Wheelwright Framework.

This module contains utility functions used throughout the CLI for:
- Environment detection (WSL)
- Path manipulation and validation
- Datetime formatting
- Context detection (hub/spoke/framework)
- User confirmation prompts
"""

import os
import platform
from pathlib import Path
from typing import Tuple


def is_wsl() -> bool:
    """Return True when running inside WSL.

    Checks for WSL environment by looking at:
    - WSL_DISTRO_NAME environment variable
    - platform.release() containing 'microsoft' or 'wsl'

    Returns:
        True if running in WSL, False otherwise
    """
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def resolve_spoke_root(spoke_path: Path) -> Path:
    """Normalize spoke root (project root, not WAI-Spoke).

    If the provided path is the WAI-Spoke directory itself,
    return its parent (the project root). Otherwise return
    the path as-is.

    Args:
        spoke_path: Path to normalize

    Returns:
        Project root path
    """
    if spoke_path.name == "WAI-Spoke":
        return spoke_path.parent
    return spoke_path


def is_within_path(child: Path, parent: Path) -> bool:
    """Return True if child is within parent directory.

    Uses path resolution and relative_to() to determine
    if child is a subdirectory of parent.

    Args:
        child: Potential child path
        parent: Potential parent path

    Returns:
        True if child is within parent, False otherwise
    """
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def format_datetime(value: str) -> str:
    """Return a human-readable UTC timestamp for ISO-like inputs.

    Converts ISO 8601 datetime strings to a more readable format.
    Handles both 'Z' suffix and timezone offsets.

    Args:
        value: ISO 8601 datetime string

    Returns:
        Formatted datetime string (YYYY-MM-DD HH:MM UTC) or original value if parsing fails
    """
    if not value:
        return "Unknown"
    try:
        from datetime import datetime
        normalized = value.replace('Z', '+00:00')
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value


def detect_start_context(cwd: Path) -> Tuple[str, Path]:
    """Detect startup context (hub, spoke, uninitialized).

    Determines the current working directory's context by checking:
    1. If within a hub directory
    2. If within an initialized spoke
    3. Otherwise uninitialized

    Args:
        cwd: Current working directory

    Returns:
        Tuple of (context_type, path) where context_type is one of:
        - "hub": Within a hub directory
        - "spoke": Within an initialized spoke
        - "uninitialized": Neither hub nor spoke
    """
    from ..hub import HubManager
    from ..init import check_spoke_initialized

    hub_manager = HubManager()
    hub_path = hub_manager.auto_discover_hub(cwd, verbose=False)
    if hub_path and is_within_path(cwd, hub_path):
        return ("hub", hub_path)

    spoke_root = resolve_spoke_root(cwd)
    if check_spoke_initialized(spoke_root):
        return ("spoke", spoke_root)

    return ("uninitialized", cwd)


def confirm_exit() -> bool:
    """Confirm exit with user.

    Prompts the user to confirm they want to exit the CLI.

    Returns:
        True if user confirms exit, False otherwise
    """
    from .input import safe_confirm
    return safe_confirm("  Exit WAI CLI?", default=True)


def is_framework_directory(path: Path) -> bool:
    """Check if path is the framework directory.

    Checks for presence of framework-specific files:
    - WAI script
    - templates/ directory
    - wai_cli/ package

    Args:
        path: Path to check

    Returns:
        True if framework directory, False otherwise
    """
    return (
        (path / 'WAI').exists() and
        (path / 'templates').exists() and
        (path / 'wai_cli').exists()
    )
