"""
UI package for Wheelwright CLI.

Contains interactive menu systems and display components.
"""

# Core menus
from .core_menus import (
    handle_no_command,
    show_uninitialized_intro,
    show_spoke_analysis,
    show_framework_menu,
    show_spoke_menu,
    show_init_menu,
    show_wheelwright_menu,
)

# Configuration and help menus
from .config_menus import (
    show_evolution_menu,
    show_features_menu,
    show_integrations_menu,
    show_testing_menu,
    show_help_menu,
    confirm_exit,
)

# Hub and project menus
from .hub_menus import (
    show_spokes_menu,
    show_modify_projects_menu,
    show_groups_menu,
    show_spoke_actions_menu,
    show_project_about_menu,
    show_project_review,
    show_hub_actions_menu,
    show_projects_actions_menu,
    show_groups_actions_menu,
)

# Analytics and knowledge base menus
from .analytics_menus import (
    show_statistics_menu,
    show_baseline_menu,
    show_knowledge_base_menu,
    show_learnings_by_category,
    get_spoke_details,
    get_hub_learnings_summary,
)

# Menu manager
from .menu_manager import MenuManager

__all__ = [
    # Core menus
    'handle_no_command',
    'show_uninitialized_intro',
    'show_spoke_analysis',
    'show_framework_menu',
    'show_spoke_menu',
    'show_init_menu',
    'show_wheelwright_menu',
    # Config and help menus
    'show_evolution_menu',
    'show_features_menu',
    'show_integrations_menu',
    'show_testing_menu',
    'show_help_menu',
    'confirm_exit',
    # Hub and project menus
    'show_spokes_menu',
    'show_modify_projects_menu',
    'show_groups_menu',
    'show_spoke_actions_menu',
    'show_project_about_menu',
    'show_project_review',
    'show_hub_actions_menu',
    'show_projects_actions_menu',
    'show_groups_actions_menu',
    # Analytics and knowledge base menus
    'show_statistics_menu',
    'show_baseline_menu',
    'show_knowledge_base_menu',
    'show_learnings_by_category',
    'get_spoke_details',
    'get_hub_learnings_summary',
    # Menu manager
    'MenuManager',
]
