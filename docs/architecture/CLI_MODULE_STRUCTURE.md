# CLI Module Structure

## Overview

The Wheelwright CLI (`wai_cli/`) has been refactored from a monolithic `core.py` into a modular architecture that separates concerns, improves maintainability, and enables parallel development.

**Refactoring Date:** January 21, 2026
**Related Commits:**
- `e10941a` - Extract utilities and helpers from core.py
- `43f5c9a` - Extract command handlers to commands/ modules
- `b1f2c5e` - Extract menu system to ui/ package
- `1450f3b` - Slim down core.py to orchestration only

---

## Architecture Principles

1. **Separation of Concerns:** Commands, UI, utilities, and orchestration are distinct layers
2. **Single Responsibility:** Each module handles one specific area of functionality
3. **Clear Dependencies:** Import hierarchy flows downward (core → commands → utils)
4. **Testability:** Isolated modules enable comprehensive unit testing
5. **Extensibility:** New commands and menus can be added without touching core orchestration

---

## Module Organization

```
wai_cli/
├── core.py                         # Main orchestration and routing
├── __init__.py                     # Package initialization
│
├── commands/                       # Command implementations
│   ├── __init__.py                 # Command exports
│   ├── baseline.py                 # Baseline testing commands
│   ├── closeout.py                 # Session closeout
│   ├── configure_ide.py            # IDE configuration
│   ├── context.py                  # Context generation
│   ├── group_commands.py           # Group management
│   ├── history.py                  # Changelog viewing
│   ├── hub_commands.py             # Hub operations
│   ├── init.py                     # Project initialization
│   ├── lug.py                      # Lug (task graph) management
│   ├── project_commands.py         # Project discovery/management
│   ├── shipit.py                   # Closeout + git commit
│   ├── stats.py                    # Statistics and analytics
│   ├── status.py                   # Status reports
│   ├── sync.py                     # Hub synchronization
│   ├── template.py                 # Template management
│   ├── time.py                     # Token usage estimation
│   ├── update.py                   # Framework updates
│   ├── version.py                  # Version information
│   └── workspace.py                # Workspace launcher
│
├── ui/                             # Interactive menu system
│   ├── __init__.py                 # Menu exports
│   ├── menu_manager.py             # Menu orchestration framework
│   ├── core_menus.py               # Main navigation menus
│   ├── hub_menus.py                # Hub and project menus
│   ├── analytics_menus.py          # Statistics and knowledge base
│   └── config_menus.py             # Configuration and help menus
│
├── utils/                          # Shared utilities
│   ├── __init__.py                 # Utility exports
│   ├── cli_helpers.py              # CLI utility functions
│   ├── input.py                    # User input/output helpers
│   ├── paths.py                    # Path manipulation
│   ├── registry.py                 # Wheel registry utilities
│   ├── jsonl.py                    # JSONL file operations
│   └── exceptions.py               # Custom exceptions
│
├── baseline_helpers.py             # Baseline testing utilities
├── bootstrap.py                    # Bootstrap context generation
├── changelog.py                    # Changelog management
├── closeout.py                     # Closeout processing
├── groups.py                       # Group management
├── health.py                       # Health checks
├── hub.py                          # Hub manager
├── hub_indexer.py                  # Hub indexing (Map & Compass)
├── init.py                         # Initialization logic
├── lugs.py                         # Lug system implementation
├── lug_handler.py                  # Lug handler utilities
├── metrics.py                      # Metrics and analytics
├── point.py                        # WAI-Point.json management
├── projects.py                     # Project discovery
├── quality_gates.py                # Quality gate enforcement
├── rebalancer.py                   # Context rebalancing
├── session.py                      # Session management
├── sessions.py                     # Multi-session tracking
├── spoke_update.py                 # Spoke version upgrades
├── templates.py                    # Template management
├── upgrader.py                     # Framework upgrade logic
│
└── integrations/                   # IDE/tool integrations
    ├── __init__.py
    ├── base.py                     # Base integration class
    ├── manager.py                  # Integration manager
    ├── commands.py                 # Integration commands
    ├── claude_code.py              # Claude Code integration
    ├── cursor.py                   # Cursor integration
    ├── vscode.py                   # VS Code integration
    ├── web_llm.py                  # Web LLM integration
    └── test_*.py                   # Integration tests
```

---

## Module Hierarchy

### Layer 1: Orchestration
**File:** `core.py`

**Purpose:** Main CLI entry point with command routing and error handling

**Responsibilities:**
- Argument parsing with argparse
- Command routing to appropriate handlers
- Error handling and exception management
- Environment detection (framework vs spoke vs hub)
- Interactive menu fallback when no command provided

**Key Functions:**
- `main()` - Entry point
- `detect_start_context()` - Determine execution context
- Command routing logic

**Dependencies:** Commands, UI, Utils

---

### Layer 2: Command Handlers
**Directory:** `commands/`

**Purpose:** Individual command implementations

**Structure:**
```python
# Each command module exports a cmd_* function
def cmd_<command_name>(args, extra_args=None):
    """
    Command handler for WAI <command_name>

    Args:
        args: Parsed command-line arguments
        extra_args: Additional arguments passed through

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Implementation
```

**Common Patterns:**
- Import utilities and managers from parent modules
- Use `print_info`, `print_success`, `print_error` for output
- Return 0 on success, 1 on failure
- Raise `WAIError` for expected failures

**Example:** `commands/status.py`
```python
from ..utils.input import print_info, print_success, print_error
from ..session import SessionManager

def cmd_status(args, extra_args=None):
    """Show wheel status and health check."""
    session = SessionManager()
    status = session.get_status()

    print_info(f"Last modified: {status['last_modified_at']}")
    print_success("Wheel is healthy")
    return 0
```

---

### Layer 3: Interactive UI
**Directory:** `ui/`

**Purpose:** Menu-driven interfaces for interactive usage

**Structure:**
- `menu_manager.py` - Base menu framework
- `core_menus.py` - Main navigation (spoke menu, framework menu, init menu)
- `hub_menus.py` - Hub operations (projects, groups, spokes)
- `analytics_menus.py` - Statistics and knowledge base
- `config_menus.py` - Configuration, features, help

**Menu Pattern:**
```python
def show_<menu_name>_menu(context):
    """
    Display interactive menu for <menu_name>

    Args:
        context: Dict containing necessary state (hub_path, spoke_path, etc.)

    Returns:
        Action code or None to exit menu
    """
    options = [
        "1) Option One",
        "2) Option Two",
        "q) Quit"
    ]

    choice = safe_menu_choice("Select action", options)

    if choice == "1":
        # Handle option 1
        pass
    elif choice == "2":
        # Handle option 2
        pass
    elif choice == "q":
        return "exit"
```

**Key Functions:**
- `safe_menu_choice(prompt, options)` - Get validated user input
- `print_info/success/warning/error` - Consistent output formatting

---

### Layer 4: Utilities
**Directory:** `utils/`

**Purpose:** Reusable helper functions

#### `cli_helpers.py` - CLI Utilities
```python
# Environment detection
is_wsl() -> bool
is_framework_directory(path) -> bool

# Path manipulation
resolve_spoke_root(spoke_path) -> Path
is_within_path(child, parent) -> bool
normalize_path(path) -> Path

# Datetime formatting
format_datetime(iso_string) -> str

# Context detection
detect_start_context() -> Tuple[str, Optional[Path]]

# User confirmation
confirm_exit() -> bool
```

#### `input.py` - User I/O Helpers
```python
# Output formatting
print_info(message)
print_success(message)
print_warning(message)
print_error(message)

# User input
safe_menu_choice(prompt, options) -> str
```

#### `paths.py` - Path Operations
```python
normalize_path(path) -> Path
find_spoke_root(start_path) -> Optional[Path]
```

#### `jsonl.py` - JSONL File Operations
```python
append_jsonl(file_path, data)
read_jsonl(file_path) -> List[Dict]
```

#### `exceptions.py` - Custom Exceptions
```python
class WAIError(Exception):
    """Base exception for WAI operations"""
    pass
```

---

### Layer 5: Baseline Helpers
**File:** `baseline_helpers.py`

**Purpose:** Baseline test management for token efficiency tracking

**Functions:**
```python
load_baseline_runs(spoke_path) -> List[Dict]
print_baseline_runs(runs)
log_test_result(spoke_path, test_data)
print_test_log(spoke_path)
detect_ide_model() -> Tuple[str, str]
get_latest_baseline_summary(spoke_path) -> str
```

**Usage:**
```python
from .baseline_helpers import load_baseline_runs, log_test_result

runs = load_baseline_runs(Path.cwd())
log_test_result(
    Path.cwd(),
    {
        "timestamp": datetime.now().isoformat(),
        "ide": "claude-code",
        "model": "claude-opus-4-5",
        "tokens_used": 12500
    }
)
```

---

## Import Patterns

### Absolute Imports (Preferred)
```python
# From commands/
from ..utils.input import print_info, print_success
from ..hub import HubManager
from ..baseline_helpers import load_baseline_runs

# From ui/
from ..utils.cli_helpers import detect_start_context
from ..projects import ProjectDiscovery
```

### Package-Level Imports
```python
# In commands/__init__.py
from .status import cmd_status
from .sync import cmd_sync

# Usage in core.py
from .commands import cmd_status, cmd_sync
```

### Avoid Circular Imports
- Core imports commands/ui, not vice versa
- Commands import utils, not other commands
- Menus can import commands for direct invocation

---

## Adding New Commands

### 1. Create Command Module
**File:** `commands/my_command.py`

```python
"""WAI my-command - Brief description"""

from pathlib import Path
from ..utils.input import print_info, print_success, print_error
from ..utils.cli_helpers import detect_start_context

def cmd_my_command(args, extra_args=None):
    """
    Handler for 'WAI my-command'

    Args:
        args: Parsed arguments from argparse
        extra_args: Additional CLI arguments

    Returns:
        0 on success, 1 on failure
    """
    try:
        context_type, context_path = detect_start_context()

        # Command implementation
        print_info("Executing my-command...")

        # Do work
        result = do_something()

        print_success("Command completed successfully")
        return 0

    except Exception as e:
        print_error(f"Command failed: {e}")
        return 1
```

### 2. Export Command
**File:** `commands/__init__.py`

```python
from .my_command import cmd_my_command

__all__ = [
    # ... existing exports
    'cmd_my_command',
]
```

### 3. Register in Core
**File:** `core.py`

```python
# Import
from .commands.my_command import cmd_my_command

# Add argparse subcommand
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # ... existing subparsers

    # Add new command
    parser_my_command = subparsers.add_parser(
        'my-command',
        help='Brief description'
    )
    parser_my_command.add_argument(
        '--option',
        help='Optional argument'
    )

    # ... routing logic
    if command == 'my-command':
        return cmd_my_command(args)
```

### 4. Update Help Menu (Optional)
**File:** `ui/config_menus.py`

Add command to help menu display.

---

## Adding New Menus

### 1. Create Menu Function
**File:** `ui/my_menus.py`

```python
"""Menu system for my feature"""

from ..utils.input import print_info, safe_menu_choice
from ..commands.my_command import cmd_my_command

def show_my_menu(context):
    """
    Display my feature menu

    Args:
        context: Dict with hub_path, spoke_path, etc.

    Returns:
        Action code or None
    """
    while True:
        print("\n=== My Feature Menu ===")
        options = [
            "1) Option One",
            "2) Option Two",
            "3) Run My Command",
            "b) Back",
            "q) Quit"
        ]

        choice = safe_menu_choice("Select action", options)

        if choice == "1":
            handle_option_one(context)
        elif choice == "2":
            handle_option_two(context)
        elif choice == "3":
            # Invoke command directly
            cmd_my_command(None)
        elif choice == "b":
            return "back"
        elif choice == "q":
            return "exit"

def handle_option_one(context):
    """Handle menu option 1"""
    print_info("Handling option 1...")
    # Implementation
```

### 2. Export Menu
**File:** `ui/__init__.py`

```python
from .my_menus import show_my_menu

__all__ = [
    # ... existing exports
    'show_my_menu',
]
```

### 3. Integrate into Menu Hierarchy
**File:** `ui/core_menus.py` (or appropriate parent menu)

```python
from .my_menus import show_my_menu

def show_main_menu():
    # ... existing menu options
    elif choice == "X":
        show_my_menu(context)
```

---

## Testing Strategy

### Unit Tests
Test individual command handlers and utilities:

```python
# tests/unit/test_commands/test_my_command.py
import pytest
from wai_cli.commands.my_command import cmd_my_command

def test_cmd_my_command_success():
    """Test successful command execution"""
    result = cmd_my_command(None)
    assert result == 0

def test_cmd_my_command_error():
    """Test error handling"""
    # Set up error condition
    result = cmd_my_command(None)
    assert result == 1
```

### Integration Tests
Test menu flows and command integration:

```python
# tests/integration/test_menu_flow.py
def test_my_menu_flow():
    """Test complete menu navigation"""
    context = {"hub_path": test_hub_path}
    # Simulate user interaction
```

### Smoke Tests
Add to existing smoke test suite:

```bash
# tests/scripts/smoke-tests-framework.sh
echo "Testing WAI my-command..."
./WAI my-command
check_exit_code $? "my-command execution"
```

---

## CLI Menu Parity Rule

**From WAI-Guide.md:**
> When adding or extending WAI-CLI commands, update the interactive menus and help text to match.

**Process:**
1. Add command handler in `commands/`
2. Add argparse definition in `core.py`
3. Add menu option in appropriate `ui/` menu
4. Update help menu in `ui/config_menus.py`
5. Update documentation

**Example:**
- Command: `WAI my-command`
- CLI: Added to argparse with `--option`
- Menu: Added to "My Feature Menu" in `ui/my_menus.py`
- Help: Added to "Available Commands" in help menu

---

## Best Practices

### 1. Error Handling
```python
try:
    # Operation
    result = risky_operation()
except WAIError as e:
    print_error(f"WAI error: {e}")
    return 1
except Exception as e:
    print_error(f"Unexpected error: {e}")
    return 1
```

### 2. User Feedback
```python
# Always provide clear feedback
print_info("Starting operation...")
# ... do work
print_success("Operation completed successfully")

# Or on failure
print_warning("Operation partially completed")
print_error("Operation failed: reason")
```

### 3. Path Handling
```python
from pathlib import Path
from ..utils.paths import normalize_path

# Always use Path objects
spoke_path = normalize_path(args.path)

# Check existence before operations
if not spoke_path.exists():
    print_error(f"Path not found: {spoke_path}")
    return 1
```

### 4. Argument Validation
```python
def cmd_my_command(args, extra_args=None):
    """Handler with argument validation"""

    # Validate required args
    if not args.required_option:
        print_error("--required-option is mandatory")
        return 1

    # Validate argument values
    if args.count < 1:
        print_error("--count must be positive")
        return 1

    # Proceed with validated args
```

### 5. Context-Aware Commands
```python
from ..utils.cli_helpers import detect_start_context

def cmd_my_command(args, extra_args=None):
    """Context-aware command"""

    context_type, context_path = detect_start_context()

    if context_type == "spoke":
        # Spoke-specific behavior
        handle_spoke(context_path)
    elif context_type == "hub":
        # Hub-specific behavior
        handle_hub(context_path)
    elif context_type == "framework":
        # Framework-specific behavior
        handle_framework(context_path)
    else:
        print_error("No Wheelwright context detected")
        return 1
```

---

## Migration Notes

### What Changed
**Before (Monolithic core.py):**
- 3000+ lines in single file
- All commands, menus, and utilities together
- Difficult to navigate and maintain
- High risk of merge conflicts
- Hard to test individual components

**After (Modular Structure):**
- `core.py` reduced to ~500 lines (orchestration only)
- Commands separated into focused modules (~100-300 lines each)
- Menus organized by functional area
- Utilities extracted for reuse
- Clear import hierarchy
- Easy to test and extend

### Backwards Compatibility
- All CLI commands remain unchanged
- Menu flows unchanged
- Configuration files unchanged
- Internal refactoring only - no user-facing changes

### Performance Impact
- Minimal: Import overhead negligible
- Improved: Better code splitting enables lazy loading
- Faster development: Parallel work on different modules

---

## Future Enhancements

### Planned Improvements
1. **Plugin Architecture** - Dynamic command loading
2. **Command Aliases** - Short forms for common commands
3. **Batch Operations** - Multi-project commands
4. **API Layer** - Programmatic access to CLI functions
5. **Enhanced Testing** - Automated integration test suite

### Extension Points
- `commands/` - Add new command handlers
- `ui/` - Add new menu screens
- `integrations/` - Add IDE/tool integrations
- `utils/` - Add reusable utilities

---

## Related Documentation

- [Framework Overview](FRAMEWORK_OVERVIEW.md) - High-level architecture
- [WAI-Guide.md](../../WAI-Spoke/WAI-Guide.md) - AI instructions
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development guidelines
- [SMOKE-TESTS.md](../../SMOKE-TESTS.md) - Testing procedures

---

*Wheelwright Framework - Build AI wheels that roll forward forever*
*wheelwright.ai*
