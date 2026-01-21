# Analytics Menus Extraction Summary

## File Created
- `wai_cli/ui/analytics_menus.py` (587 lines)

## Functions Extracted from core.py

### Menu Functions (Public API)
1. **show_baseline_menu(cli, spoke_path: Path)** - Line 19
   - Baseline tracking menu for a spoke
   - Displays baseline mode status and options to enable/disable

2. **show_testing_menu(cli, spoke_path: Path)** - Line 84
   - Testing menu with smoke tests and unit tests
   - Shows test execution interface

3. **show_statistics_menu(cli)** - Line 151
   - Statistics with insights and recommendations
   - Displays hub overview and actionable recommendations

4. **show_knowledge_base_menu(cli)** - Line 294
   - Knowledge base menu for reviewing learnings
   - Browse signals by category

5. **show_learnings_by_category(hub_path: Path, category: str)** - Line 372
   - Display learnings filtered by category
   - Supports patterns, decisions, insights, warnings, and all

### Helper Functions (Public API)
6. **get_spoke_details(spoke_path: Path) -> Dict[str, Any]** - Line 439
   - Get detailed information about a spoke
   - Returns tech stack, status, signal count, etc.

7. **get_hub_learnings_summary(hub_path: Path) -> Dict[str, Any]** - Line 505
   - Get summary of hub learnings
   - Returns total signals, high-impact count, last updated

### Internal Helper Functions (Private)
8. **_log_test_result(spoke_path: Path, test_name: str, exit_code: int, output: str)** - Line 547
   - Append test result to log

9. **_print_test_log(spoke_path: Path)** - Line 560
   - Print recent test log entries

## Dependencies
- `json` - JSON parsing
- `subprocess` - Running tests
- `datetime` - Timestamp handling
- `pathlib.Path` - Path operations
- `typing.Dict, Any` - Type hints
- `..hub.HubManager` - Hub discovery and management
- `..utils.input` - UI utilities (print_info, print_success, etc.)

## Integration Notes
- All functions take `cli` as first parameter to access CLI methods
- Functions removed leading underscores from original private methods
- Maintained compatibility with existing core.py dependencies
- Properly exported in __init__.py

## Original Locations in core.py
- `_show_baseline_menu` - Line 857
- `_show_testing_menu` - Line 1072
- `_get_spoke_details` - Line 1466
- `_show_statistics_menu` - Line 2023
- `_show_knowledge_base_menu` - Line 2172
- `_get_hub_learnings_summary` - Line 2252
- `_show_learnings_by_category` - Line 2295

## Next Steps
- Agent 4 will update core.py to import and use these functions
- Verify no breaking changes in existing menu flows
