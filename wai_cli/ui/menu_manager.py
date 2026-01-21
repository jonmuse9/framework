"""
Menu Manager - Base utilities for interactive menus.

Provides common menu functionality and helpers.
"""

from pathlib import Path
from typing import Optional, List


class MenuManager:
    """Base class for menu management utilities."""

    def __init__(self, cli_instance=None):
        """
        Initialize menu manager.

        Args:
            cli_instance: Reference to WheelwrightCLI instance (optional)
        """
        self.cli = cli_instance

    def render_header(self, title: str, breadcrumb: Optional[List[str]] = None,
                     status: Optional[str] = None, width: int = 60):
        """
        Render consistent menu header with breadcrumb and optional status.

        Args:
            title: Menu title (used if no breadcrumb)
            breadcrumb: List of navigation path elements
            status: Optional status line to show below title
            width: Width of separator line
        """
        from ..utils.input import print_info

        # Build breadcrumb text
        if breadcrumb and len(breadcrumb) > 1:
            breadcrumb_text = " > ".join(breadcrumb)
        else:
            breadcrumb_text = title

        # Render header
        print_info("\n" + "=" * width)
        print_info(f"           {breadcrumb_text}")
        if status:
            print_info(f"           {status}")
        print_info("=" * width)
        print_info("")

    def confirm_exit(self) -> bool:
        """Confirm exit with user."""
        from ..utils.input import safe_confirm
        return safe_confirm("  Exit WAI CLI?", default=True)
