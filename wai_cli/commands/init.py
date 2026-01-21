"""
Init Command

Initialize a new spoke in a project directory.
"""

from pathlib import Path

from ..init import init_spoke, init_spoke_interactive
from ..utils.input import print_success, print_error
from ..utils.paths import normalize_path


def cmd_init(args):
    """
    Handle init command.

    Initialize a spoke either at a specific path or interactively.

    Args:
        args: Argument namespace with optional 'path' attribute

    Examples:
        Initialize at specific path:
            args.path = "/path/to/project"

        Interactive initialization:
            args.path = None
    """
    if args.path:
        # Initialize specific path
        try:
            spoke_path = normalize_path(args.path)
            init_spoke(spoke_path, is_framework=False, verbose=True)
            print_success(f"\nSpoke initialized at {spoke_path}")
        except Exception as e:
            print_error(f"Initialization failed: {e}")
    else:
        # Interactive initialization
        init_spoke_interactive(verbose=True)
