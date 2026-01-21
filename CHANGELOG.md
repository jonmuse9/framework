# Changelog

All notable changes to the Wheelwright Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

#### CLI Modular Architecture Refactoring (2026-01-21)

**Summary:**
Major refactoring of the Wheelwright CLI from a monolithic `core.py` (3000+ lines) into a modular architecture with clear separation of concerns.

**Commits:**
- `e10941a` - Extract utilities and helpers from core.py
- `43f5c9a` - Extract command handlers to commands/ modules
- `b1f2c5e` - Extract menu system to ui/ package
- `1450f3b` - Slim down core.py to orchestration only

**Changes:**
- `core.py` reduced from 3000+ lines to ~500 lines (orchestration only)
- Created `wai_cli/commands/` package with 18 modular command handlers
- Created `wai_cli/ui/` package with organized menu system (core, hub, analytics, config)
- Created `wai_cli/utils/cli_helpers.py` for shared CLI utilities
- Created `wai_cli/baseline_helpers.py` for baseline test management
- Established clear import hierarchy: core → commands → utils
- Added comprehensive documentation: `docs/architecture/CLI_MODULE_STRUCTURE.md`
- Updated `docs/architecture/FRAMEWORK_OVERVIEW.md` with CLI architecture section

**Benefits:**
- **Maintainability:** Each module has single responsibility, easier to understand and modify
- **Testability:** Isolated modules enable comprehensive unit testing
- **Collaboration:** Multiple developers can work on different modules without conflicts
- **Extensibility:** New commands and menus can be added without touching core orchestration
- **Code Quality:** Clear separation reduces complexity and improves code organization

**Backwards Compatibility:**
- All CLI commands unchanged - no user-facing changes
- Menu flows unchanged
- Configuration files unchanged
- Internal refactoring only

**Architecture Principles:**
1. Separation of Concerns - Commands, UI, utilities, orchestration are distinct
2. Single Responsibility - Each module handles one specific area
3. Clear Dependencies - Import hierarchy flows downward
4. Testability - Isolated components enable thorough testing
5. Extensibility - Plugin-ready architecture for future enhancements

**Module Organization:**
```
wai_cli/
├── core.py                     # Main orchestration and routing (~500 lines)
├── commands/                   # Command implementations (18 modules)
├── ui/                         # Interactive menu system (5 modules)
├── utils/                      # Shared utilities (7 modules)
├── baseline_helpers.py         # Baseline test management
└── [other support modules]
```

For detailed architectural documentation, see:
- `docs/architecture/CLI_MODULE_STRUCTURE.md` - Complete CLI architecture guide
- `docs/architecture/FRAMEWORK_OVERVIEW.md` - High-level framework overview

---

## [1.0.0] - 2025-12-28

### Added
- Initial public release of Wheelwright Framework
- Rebranded from SCF (Session Continuity Framework) to Wheelwright
- WAI CLI tool with unified command interface
- Hub-Wheel architecture with separation of framework and user data
- Project foundation system with identity, boundaries, approach
- AI stewardship philosophy (detect drift, require acknowledgment)
- Wheel signals (JSONL) for hub-wheel communication
- WAI-Guide.md generation for AI instructions
- Spoke loader architecture with 3 built-in spokes
- SCF migration tool for legacy projects
- Non-coding project support (research, writing, design)
- Dogfooding - Wheelwright tracks its own development

### Changed
- Renamed WWAI to WAI (Wheelwright AI, pronounced "way")
- Capitalized .WAI/ directory for pronounced readability
- Reorganized file structure with WAI-* naming convention
- Created wheelwright-ai GitHub organization
- Established domain: wheelwright.ai

### Technical Decisions
- Framework-Hub separation (impact: 10)
- AI as responsible partner philosophy (impact: 9)
- Wheel metaphor terminology (Hub=memory, Spokes=capabilities, Wheel=project) (impact: 8)

---

## Pre-1.0 Development (SCF Era)

### [0.9.x] - 2025-12-22 to 2025-12-28
- Conversation logging with JSONL for session continuity
- Shipit command - closeout + git commit workflow
- CLAUDE.md v2.0 with priority levels and enforcement
- Automatic session start briefing protocol
- Token efficiency protocols with ADAPTIVE workflow
- Dual-layer testing (smoke tests + unit tests)
- Comprehensive integration test framework (130 tests)

### [0.8.x] - 2025-11-01 to 2025-12-22
- Initial SCF framework development
- Basic hub-spoke architecture
- Session state tracking
- Foundation system prototype

---

*For more information, visit [wheelwright.ai](https://wheelwright.ai)*
