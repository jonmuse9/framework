"""
Version Command

Display framework and spoke structure version information.
"""

from ..utils.input import print_info

# Framework version constants
FRAMEWORK_VERSION = "2.0.1"
SPOKE_STRUCTURE_VERSION = "2.1"


def cmd_version(args=None):
    """
    Show version information.

    Displays the Wheelwright framework version and spoke structure version.

    Args:
        args: Argument namespace (unused, for compatibility)
    """
    print_info(f"\nWheelwright Framework v{FRAMEWORK_VERSION}")
    print_info(f"Spoke structure version: {SPOKE_STRUCTURE_VERSION}\n")
