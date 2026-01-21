# Wheelwright Framework Architecture

## Overview

Wheelwright is a context persistence framework for AI-assisted development. It maintains project memory across sessions, enabling AI assistants to work as informed partners rather than stateless tools.

## Core Concepts

### The Wheel Metaphor

```
                    ┌─────────────┐
                    │    Wheel    │
                    │  (Project)  │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴────┐      ┌─────┴─────┐     ┌────┴────┐
    │  Spoke  │      │    Hub    │     │  Spoke  │
    │(Capability)    │ (Memory)  │     │(Capability)
    └─────────┘      └───────────┘     └─────────┘
```

- **Wheel**: A project with Wheelwright context
- **Hub**: Central memory and consolidated knowledge
- **Spokes**: Specialized capabilities that extend the wheel
- **Rolling**: Each session moves forward, preserving context

## File Structure

### Wheel Files (`WAI-Spoke/`)

```
WAI-Spoke/
├── WAI-State.json       # Machine-readable state
├── WAI-State.md         # Human-readable context
├── WAI-Guide.md         # AI instructions
├── WAI-Signals.jsonl   # High-impact learnings
└── WAI-KB-Sync.json          # Hub sync status
```

### Hub Files

```
wheelwright-hub/
├── WAI-Spoke/                # Hub's own state
├── .WAI-registry/       # Wheel tracking
│   ├── wheels/           # Individual wheel data
│   └── wheel-projects.json
├── hub-profile.json      # User preferences
└── learnings/            # Cross-project patterns
```

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   AI Session │────▶│    Wheel     │────▶│     Hub      │
│              │     │  (WAI-Spoke/)    │     │  (learnings) │
└──────────────┘     └──────────────┘     └──────────────┘
       ▲                    │                    │
       │                    ▼                    ▼
       │              ┌──────────────┐    ┌──────────────┐
       └──────────────│   Signals    │    │ Other Wheels │
                      │  (.jsonl)    │    │              │
                      └──────────────┘    └──────────────┘
```

## Core Components

### 1. State Management

**WAI-State.json** stores:
- Project foundation (identity, boundaries, approach)
- Session state (last modified, session count)
- Decisions and their rationale
- Active spokes
- AI rules and behaviors

**WAI-State.md** provides:
- Human-readable strategic context
- Evolution log
- Current focus and next actions

### 2. Foundation System

The project foundation ensures AI partners understand:
- What the project is
- What's in scope and out of scope
- How to collaborate effectively

Foundation must be completed before any work begins.

### 3. Signal System

High-impact learnings (impact >= 8) are:
1. Recorded in `WAI-Signals.jsonl`
2. Synced to the hub
3. Distributed to other wheels

This creates a learning flywheel across projects.

### 4. Stewardship Model

AI partners follow stewardship philosophy:
- Detect scope drift before enabling
- Require acknowledgment for changes
- Complete foundation before work
- Verify rather than assume

## Extension Points

### Spokes

Spokes add capabilities:
- Meta-consultation (multi-AI queries)
- Document analysis
- Code review
- Custom spokes (future)

### Integrations

Planned integrations:
- VS Code extension
- Browser extension
- Cloud sync
- API access

## Security Considerations

- No secrets in state files
- Local-first by default
- User controls all data
- Optional cloud sync

## Performance

- Lightweight JSON state
- Append-only signals
- Lazy hub sync
- Minimal dependencies

## CLI Architecture

The Wheelwright CLI (`wai_cli/`) uses a modular architecture for maintainability and extensibility:

```
wai_cli/
├── core.py                  # Orchestration and routing
├── commands/                # Command implementations
│   ├── init.py
│   ├── status.py
│   ├── sync.py
│   └── ... (15+ commands)
├── ui/                      # Interactive menu system
│   ├── core_menus.py
│   ├── hub_menus.py
│   ├── analytics_menus.py
│   └── config_menus.py
├── utils/                   # Shared utilities
│   ├── cli_helpers.py
│   ├── input.py
│   └── paths.py
└── baseline_helpers.py      # Baseline test management
```

**Key Design Principles:**
- **Separation of Concerns:** Commands, UI, utilities, and orchestration are distinct
- **Single Responsibility:** Each module handles one specific area
- **Clear Dependencies:** Import hierarchy flows downward
- **Testability:** Isolated modules enable comprehensive testing
- **Extensibility:** New commands/menus can be added without touching core

For detailed CLI architecture documentation, see [CLI_MODULE_STRUCTURE.md](CLI_MODULE_STRUCTURE.md).

---

*Wheelwright Framework - wheelwright.ai*
