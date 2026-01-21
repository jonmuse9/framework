# WAI-CLI Command Reference

**Wheelwright Framework v2.0.1**

Build AI wheels that roll forward forever - Universal context persistence for any knowledge work.

## Overview

WAI-CLI is the unified command-line interface for the Wheelwright Framework. It provides tools for initializing projects (spokes), managing a central knowledge hub, tracking sessions, and maintaining continuous AI context across conversations.

### Getting Started

```bash
# Initialize Wheelwright in your project
wai init

# Show status of current spoke
wai status

# Interactive menu (run without arguments)
wai
```

### Command Syntax

All commands follow the pattern:
```bash
wai <command> [subcommand] [arguments] [flags]
```

Use `--help` on any command for detailed information:
```bash
wai --help
wai hub --help
wai baseline enable --help
```

---

## Quick Reference

| Command | Purpose | Common Usage |
|---------|---------|--------------|
| `wai init` | Initialize Wheelwright in project | `wai init` (interactive) |
| `wai status` | Show spoke status and health | `wai status` |
| `wai absorbe` | Process seed folders, archive sprawl | `wai absorbe` |
| `wai context` | Output context files for LLM | `wai context` |
| `wai closeout` | Generate session closeout | `wai closeout` |
| `wai shipit` | Closeout + git commit | `wai shipit` |
| `wai time` | Show token usage estimate | `wai time` |
| `wai stats` | Show session analytics | `wai stats` |
| `wai sync` | Upgrade spoke structure | `wai sync` |
| `wai hub create` | Create new hub | `wai hub create` |
| `wai hub locate` | Find hub location | `wai hub locate` |
| `wai projects add` | Register projects with hub | `wai projects add` |
| `wai projects list` | List registered projects | `wai projects list` |
| `wai group create` | Create project group | `wai group create clients` |
| `wai group list` | List all groups | `wai group list -v` |
| `wai baseline enable` | Enable baseline tracking | `wai baseline enable` |
| `wai baseline run` | Run baseline comparison | `wai baseline run` |
| `wai template create` | Create reusable template | `wai template create my-template` |
| `wai template apply` | Apply template to project | `wai template apply my-template ./new-project` |
| `wai configure-ide detect` | Detect IDEs in use | `wai configure-ide detect` |
| `wai configure-ide setup` | Setup IDE integration | `wai configure-ide setup` |
| `wai version` | Show version information | `wai version` |

---

## Core Commands

### `init`

Initialize Wheelwright in a project directory, creating the WAI-Spoke structure for session continuity.

**Purpose:** Sets up a project as a "spoke" with all necessary files for AI session persistence (WAI-Guide.md, WAI-State.json, WAI-State.md, etc.).

**Syntax:**
```bash
wai init [path]
```

**Arguments:**
- `path` (optional): Project directory path. If omitted, runs in interactive mode.

**Flags:**
- None

**Examples:**
```bash
# Interactive initialization (prompts for project details)
wai init

# Initialize specific directory
wai init /home/user/my-project

# Initialize current directory explicitly
wai init .
```

**What It Creates:**
- `WAI-Spoke/` - Container for all Wheelwright files
- `WAI-Spoke/WAI-Guide.md` - AI instructions for session continuity
- `WAI-Spoke/WAI-State.json` - Technical project state and analytics
- `WAI-Spoke/WAI-State.md` - Strategic vision and learnings
- `WAI-Spoke/WAI-Session-Log.jsonl` - Conversation logging
- `WAI-Spoke/WAI-Signals.jsonl` - High-impact learnings (append-only)
- `WAI-Spoke/.gitignore` - Ignores session logs
- Project root `CLAUDE.md` - IDE integration instructions

**Related Commands:** status, hub create

---

### `status`

Show comprehensive status and health information for the current spoke.

**Purpose:** Display spoke initialization status, foundation completeness, recent session activity, hub connection, and project metadata.

**Syntax:**
```bash
wai status [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Show status of current directory
wai status

# Show status of specific project
wai status /home/user/my-project
```

**Output Includes:**
- Spoke initialization status
- Foundation completeness (setup phase)
- Last session information (who, when, focus)
- Hub connection status and path
- Project metadata (name, type, scope)
- Workspace paths (Windows/WSL if applicable)

**Related Commands:** init, hub locate, stats

---

### `absorbe` / `update`

Process seed folders and archive sprawl into proper Wheelwright structure.

**Purpose:** Migrate legacy sprawl (unstructured context files) into the organized WAI-Spoke/ structure. "Absorbe" is the primary command name, with "update" as an alias.

**Syntax:**
```bash
wai absorbe [path]
wai update [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Process current directory
wai absorbe

# Process specific project
wai update /home/user/legacy-project
```

**What It Does:**
- Scans for `__seed/` directories (legacy context format)
- Archives sprawl files into WAI-Spoke/
- Upgrades spoke structure to latest version
- Preserves all historical context

**Notes:**
- Safe to run multiple times (idempotent)
- Does not delete original files

**Related Commands:** sync, init

---

### `context`

Output context files (WAI-Guide.md, WAI-State.json, WAI-State.md) formatted for LLM paste.

**Purpose:** Generate concatenated context suitable for pasting into an AI conversation, providing full project context.

**Syntax:**
```bash
wai context [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Output context for current project
wai context

# Output context for specific project
wai context /home/user/my-project
```

**Output Format:**
```
=== WAI-Guide.md ===
[Contents of WAI-Guide.md]

=== WAI-State.json ===
[Contents of WAI-State.json]

=== WAI-State.md ===
[Contents of WAI-State.md]
```

**Use Case:**
- Starting new AI session with full project context
- Debugging session continuity issues
- Manual context transfer between AI tools

**Related Commands:** status, closeout

---

### `version`

Display Wheelwright Framework version information.

**Purpose:** Show installed framework version and spoke structure version.

**Syntax:**
```bash
wai version
```

**Arguments:**
- None

**Flags:**
- None

**Examples:**
```bash
wai version
```

**Output:**
```
Wheelwright Framework v2.0.1
Spoke structure version: 2.1
```

**Related Commands:** status

---

## Hub Management

The hub is a central repository that aggregates learnings from all your spokes (projects), enabling cross-project knowledge sharing.

### `hub create`

Create a new Wheelwright hub.

**Purpose:** Initialize a hub directory with profile and registry structure for managing multiple spoke projects.

**Syntax:**
```bash
wai hub create [path]
```

**Arguments:**
- `path` (optional): Hub location. If omitted, prompts interactively with default `../hub`.

**Flags:**
- None

**Examples:**
```bash
# Interactive creation (suggests ../hub)
wai hub create

# Create at specific location
wai hub create ~/wheelwright-hub

# Create in parent directory
wai hub create ../hub
```

**What It Creates:**
- `hub-profile.json` - Hub metadata and configuration
- `registry/` - Project tracking directory
- `registry/wheel-projects.json` - Registered projects list
- `learnings/` - Aggregated knowledge (created on first sync)

**Hub Structure:**
```
hub/
├── hub-profile.json
├── registry/
│   └── wheel-projects.json
└── learnings/ (created later)
```

**Notes:**
- Typically created once per user or organization
- Multiple spokes can share one hub
- Can be version-controlled or kept private

**Related Commands:** hub locate, projects add

---

### `hub locate`

Find and display the hub location using intelligent discovery.

**Purpose:** Auto-discover hub using environment variables, parent folder scanning, and common paths. Shows scored candidates.

**Syntax:**
```bash
wai hub locate
```

**Arguments:**
- None

**Flags:**
- None

**Examples:**
```bash
wai hub locate
```

**Discovery Priority:**
1. `$WHEELWRIGHT_HUB_PATH` environment variable (+15 points)
2. Parent folder scan (`../hub`, `../*hub*`, etc.)
3. Common paths (`~/wheelwright-hub`)
4. Registry contains current project (+12 points)

**Scoring Factors:**
- Has `hub-profile.json`: +10 points
- Has `registry/wheel-projects.json`: +5 points
- Has `WAI-Spoke/`: -5 points (likely a spoke, not hub)
- Modified last 30 days: +2 points
- Name exactly "hub": +1 point

**Output:**
```
Hub candidates (scored):
  1. /home/user/projects/hub (score: 27)
     +15: From $WHEELWRIGHT_HUB_PATH
     +10: Has hub-profile.json
     +2: Modified in last 30 days

Found valid hub at /home/user/projects/hub
```

**Related Commands:** hub create, projects add

---

### `hub status`

> **⚠️ NOT YET IMPLEMENTED**
> This command is documented in roadmap but not currently available in the CLI.

**Planned Purpose:** Show hub health, metrics, and synchronization status.

**Expected Syntax:**
```bash
wai hub status
```

**Planned Output:**
- Number of registered spokes
- Last sync timestamp per spoke
- Learning aggregation statistics
- Hub version and structure status

**Status:** Tracked in framework development roadmap

**Workaround:** Use `wai projects list` to see registered spokes and `wai hub locate` to verify hub location.

---

## Project Management

Manage spoke projects registered with the hub.

### `projects add`

Register one or more projects with the hub, with optional auto-discovery.

**Purpose:** Add spoke projects to the hub registry for centralized tracking and knowledge aggregation.

**Syntax:**
```bash
wai projects add [--scan PATH...]
```

**Arguments:**
- None (prompts for project selection)

**Flags:**
- `--scan PATH...` - Paths to scan for Wheelwright projects

**Examples:**
```bash
# Interactive selection (discovers projects automatically)
wai projects add

# Scan specific directories
wai projects add --scan ~/projects ~/work

# Scan multiple paths
wai projects add --scan /home/user/project1 /home/user/project2

# Scan parent directory
wai projects add --scan ..
```

**Interactive Mode:**
1. Scans specified paths (or parent directory if none given)
2. Discovers projects with `WAI-Spoke/` directories
3. Shows list of discovered projects
4. Prompts to select which to add
5. Adds selected projects to hub registry

**Registry Updates:**
- Adds project path, name, and metadata to `registry/wheel-projects.json`
- Avoids duplicates (checks existing entries)
- Updates hub-spoke linkage in spoke's `WAI-State.json`

**Related Commands:** projects list, hub create

---

### `projects list`

List all projects registered with the hub.

**Purpose:** Display registered spoke projects with optional filtering by group.

**Syntax:**
```bash
wai projects list [--group GROUP_NAME]
```

**Arguments:**
- None

**Flags:**
- `--group GROUP_NAME` - Filter projects by group

**Examples:**
```bash
# List all registered projects
wai projects list

# List projects in "clients" group
wai projects list --group clients

# List projects in "internal" group
wai projects list --group internal
```

**Output:**
```
Registered Projects (5):

  my-app
    Path: /home/user/projects/my-app
    Groups: clients, web-apps
    Last sync: 2026-01-20 15:30 UTC

  data-pipeline
    Path: /home/user/projects/data-pipeline
    Groups: internal
    Last sync: 2026-01-19 10:15 UTC
```

**Related Commands:** projects add, group list

---

### `projects scan`

> **⚠️ NOT YET IMPLEMENTED**
> This command does not exist as a standalone command. Use `wai projects add --scan` instead.

**Expected Syntax:**
```bash
wai projects scan [paths...]
```

**Actual Implementation:**
Use the `--scan` flag with `projects add`:
```bash
wai projects add --scan ~/projects ~/work
```

**Status:** Not planned for separate implementation; functionality exists in `projects add`.

---

## Group Management

Organize projects into logical groups for better organization and batch operations.

### `group create`

Create a new project group.

**Purpose:** Define a named group for organizing related spoke projects (e.g., "clients", "internal", "research").

**Syntax:**
```bash
wai group create <name> [--description TEXT]
```

**Arguments:**
- `name` (required): Group name (alphanumeric, dashes, underscores)

**Flags:**
- `--description TEXT` or `-d TEXT` - Group description

**Examples:**
```bash
# Create simple group
wai group create clients

# Create group with description
wai group create clients --description "Client project work"

# Short flag version
wai group create internal -d "Internal tools and utilities"
```

**Registry Updates:**
- Adds group to `registry/wheel-projects.json` groups section
- Initializes empty spokes list
- Prevents duplicate group names

**Related Commands:** group list, group add-spoke

---

### `group list`

List all defined groups with member projects.

**Purpose:** Display all project groups with spoke counts and optional details.

**Syntax:**
```bash
wai group list [--verbose]
```

**Arguments:**
- None

**Flags:**
- `--verbose` or `-v` - Show detailed information (member projects, descriptions)

**Examples:**
```bash
# Simple list
wai group list

# Detailed list with members
wai group list --verbose
wai group list -v
```

**Output (simple):**
```
Groups (3):

  clients (5 project(s)) - Client project work
  internal (3 project(s)) - Internal tools
  research (1 project(s))
```

**Output (verbose):**
```
Groups (3):

  clients (5 project(s))
    Description: Client project work
    Projects:
      - my-client-app (/home/user/projects/my-client-app)
      - another-client (/home/user/projects/another-client)
      ...

  internal (3 project(s))
    Description: Internal tools
    Projects:
      - admin-dashboard (/home/user/projects/admin-dashboard)
      ...
```

**Related Commands:** group create, projects list

---

### `group add-spoke`

Add a spoke project to a group.

**Purpose:** Associate an existing registered project with a group.

**Syntax:**
```bash
wai group add-spoke <group_name> <spoke_identifier>
```

**Arguments:**
- `group_name` (required): Name of the group
- `spoke_identifier` (required): Project name or path

**Flags:**
- None

**Examples:**
```bash
# Add by project name
wai group add-spoke clients my-app

# Add by project path
wai group add-spoke clients /home/user/projects/my-app

# Add to multiple groups (run twice)
wai group add-spoke clients my-app
wai group add-spoke web-apps my-app
```

**Notes:**
- Project must be registered with hub first (use `projects add`)
- A project can belong to multiple groups
- Spoke identifier can be either project name or full path

**Related Commands:** group create, group remove-spoke, projects add

---

### `group remove-spoke`

Remove a spoke project from a group.

**Purpose:** Disassociate a project from a group (does not delete project from registry).

**Syntax:**
```bash
wai group remove-spoke <group_name> <spoke_identifier>
```

**Arguments:**
- `group_name` (required): Name of the group
- `spoke_identifier` (required): Project name or path

**Flags:**
- None

**Examples:**
```bash
# Remove by project name
wai group remove-spoke clients my-app

# Remove by project path
wai group remove-spoke clients /home/user/projects/my-app
```

**Notes:**
- Only removes from group, does not delete project from registry
- Project remains accessible via `projects list`

**Related Commands:** group add-spoke, group delete

---

### `group delete`

Delete a group.

**Purpose:** Remove a group definition from the registry.

**Syntax:**
```bash
wai group delete <name> [--force]
```

**Arguments:**
- `name` (required): Group name to delete

**Flags:**
- `--force` or `-f` - Skip confirmation prompt

**Examples:**
```bash
# Delete with confirmation prompt
wai group delete old-clients

# Force delete without prompt
wai group delete old-clients --force
wai group delete old-clients -f
```

**Confirmation:**
If group contains projects and `--force` is not used, prompts:
```
Group 'old-clients' contains 5 project(s).
Delete anyway? (projects will remain in registry) [y/N]:
```

**Notes:**
- Deletes group only, not member projects
- Projects remain in registry and can be re-grouped
- Cannot be undone (group membership lost)

**Related Commands:** group create, group list

---

## Session Management

Track and manage AI session continuity.

### `closeout`

Generate session closeout instructions for AI to update WAI-State files.

**Purpose:** Prompt AI to summarize session work and update WAI-State.json and WAI-State.md with decisions, progress, and next actions.

**Syntax:**
```bash
wai closeout [path] [--non-interactive]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- `--non-interactive` - Skip confirmation prompts

**Examples:**
```bash
# Interactive closeout (current directory)
wai closeout

# Closeout specific project
wai closeout /home/user/my-project

# Non-interactive mode
wai closeout --non-interactive
```

**What It Does:**
1. Outputs instructions for AI to:
   - Update `_session_state` in WAI-State.json
   - Add session log entry to WAI-State.md
   - Append high-impact decisions to WAI-Signals.jsonl
   - Update analytics and session count
2. AI follows instructions to generate updated files
3. User reviews and saves changes

**AI Updates:**
- `WAI-State.json`:
  - `_session_state.last_modified_at` (timestamp)
  - `_session_state.last_modified_by` (AI identifier)
  - `_session_state.session_count` (increment)
  - `_session_state.requires_review` (if significant changes)
  - `decisions` array (high-impact decisions)
- `WAI-State.md`:
  - Session log entry (date, focus, outcomes)
  - Recent Progress section
  - Next Actions checklist
  - Evolution log (if direction changed)
- `WAI-Signals.jsonl`:
  - Append high-impact learnings (impact >= 8)

**Related Commands:** shipit, stats, time

---

### `shipit`

Session closeout + git commit in one command.

**Purpose:** Generate closeout instructions AND create a git commit with session changes. Streamlines end-of-session workflow.

**Syntax:**
```bash
wai shipit [path] [--non-interactive] [--push]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- `--non-interactive` - Skip confirmation prompts
- `--push` - Push to remote after commit

**Examples:**
```bash
# Interactive shipit (prompts for commit message)
wai shipit

# Non-interactive with push
wai shipit --non-interactive --push

# Specific project
wai shipit /home/user/my-project
```

**Workflow:**
1. Runs `closeout` command (AI updates WAI-State files)
2. Stages changed files: `git add WAI-Spoke/ CLAUDE.md` (and others)
3. Prompts for commit message (or uses default)
4. Creates commit with "Co-Authored-By: AI" footer
5. Optionally pushes to remote

**Default Commit Message:**
```
Session closeout: [Brief summary of work]

[Optional details]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Git Operations:**
- Runs `git status` to check working tree
- Runs `git add` for relevant files
- Runs `git commit` with message
- Optionally runs `git push` if `--push` flag used

**Related Commands:** closeout, time

---

### `time`

Show current session token usage estimate and context capacity warning.

**Purpose:** Estimate tokens used in current AI session and warn if approaching context window limit.

**Syntax:**
```bash
wai time [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Check current session token usage
wai time
```

**Output:**
```
Session Token Usage Estimate

Estimated tokens used: 45,230 / 200,000 (22.6%)
Remaining capacity: 154,770 tokens

Status: Healthy - Plenty of capacity remaining
```

**Warning Threshold:**
- Green (< 80%): Healthy capacity
- Yellow (80-90%): Approaching limit, consider closeout
- Red (> 90%): Nearing limit, closeout recommended

**Output (approaching limit):**
```
Session Token Usage Estimate

Estimated tokens used: 165,000 / 200,000 (82.5%)
Remaining capacity: 35,000 tokens

⚠️ WARNING: Approaching 80% capacity (160K tokens)
Recommendation: Run 'wai closeout' and start a fresh session
```

**Notes:**
- Provides rough estimate based on session log analysis
- Actual token count may vary by model
- Conservative estimates (tends to overestimate)

**Related Commands:** closeout, shipit, stats

---

### `stats`

Show session analytics and metrics for the current spoke.

**Purpose:** Display comprehensive session statistics, decision tracking, and activity analytics.

**Syntax:**
```bash
wai stats [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Show stats for current project
wai stats

# Show stats for specific project
wai stats /home/user/my-project
```

**Output Includes:**
- Total session count
- Last session timestamp and user
- Decision count and high-impact decisions (impact >= 8)
- Session focus areas
- Average session duration (if tracked)
- Conversation log size
- Signals count (high-impact learnings)

**Example Output:**
```
=== Session Analytics ===

Project: my-app
Sessions: 47
Last session: 2026-01-20 15:30 UTC by Claude Sonnet 4.5

=== Decisions ===

High-impact decisions: 12
Total decisions: 38

Recent high-impact (impact >= 8):
  - Switched from REST to GraphQL API (impact: 9, 2026-01-15)
  - Adopted TypeScript for type safety (impact: 10, 2026-01-10)

=== Activity ===

Conversation log: 1,250 entries
Signals: 15 high-impact learnings
```

**Related Commands:** time, closeout

---

### `sync`

Upgrade spoke structure to latest version and prepare for hub synchronization.

**Purpose:** Update spoke structure from older versions (e.g., v2.0 to v2.1), migrate files, and sync metadata with hub.

**Syntax:**
```bash
wai sync [--all]
```

**Arguments:**
- None (operates on current spoke)

**Flags:**
- `--all` - Upgrade all registered spokes in hub

**Examples:**
```bash
# Sync current spoke
wai sync

# Sync all spokes registered with hub
wai sync --all
```

**Upgrade Operations:**
- Migrates legacy `__seed/` to `WAI-Spoke/`
- Updates structure version in WAI-State.json
- Adds missing files (WAI-Signals.jsonl, .gitignore, etc.)
- Updates CLAUDE.md with latest IDE instructions
- Validates WAI-State.json schema

**Version Migrations:**
- 2.0 → 2.1: Adds WAI-Signals.jsonl, updates analytics schema
- Future versions: Automatic backward-compatible upgrades

**Related Commands:** absorbe, init

---

## Baseline Tracking

Baseline mode enables controlled pre/post comparison of AI-assisted changes for research and benchmarking.

### `baseline enable`

Enable baseline tracking mode for a spoke.

**Purpose:** Activate baseline mode to snapshot current state for later comparison. Used for measuring AI effectiveness.

**Syntax:**
```bash
wai baseline enable [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Enable baseline mode for current project
wai baseline enable

# Enable for specific project
wai baseline enable /home/user/my-project
```

**What It Does:**
1. Creates `WAI-Spoke/baseline/` directory
2. Creates `baseline-state.json` with initial snapshot:
   - File checksums (SHA-256)
   - Directory structure
   - Timestamp
   - Mode: enabled
3. Sets baseline mode flag in WAI-State.json

**Baseline State Structure:**
```json
{
  "enabled": true,
  "created_at": "2026-01-20T15:30:00Z",
  "snapshots": {
    "src/main.py": {
      "checksum": "abc123...",
      "size": 1024,
      "modified": "2026-01-20T10:00:00Z"
    }
  }
}
```

**Notes:**
- Must be run BEFORE making changes to measure
- Records immutable snapshot for comparison
- Does not affect normal development workflow

**Related Commands:** baseline disable, baseline status, baseline run

---

### `baseline disable`

Disable baseline tracking and lock baseline data.

**Purpose:** Finalize baseline mode, lock baseline data, and optionally create final comparison report.

**Syntax:**
```bash
wai baseline disable [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Disable baseline mode
wai baseline disable

# Disable for specific project
wai baseline disable /home/user/my-project
```

**What It Does:**
1. Sets `baseline-state.json` mode to disabled
2. Locks baseline data (prevents modification)
3. Generates final comparison report (if changes detected)
4. Updates WAI-State.json baseline metadata

**Final Report Includes:**
- Files modified, added, deleted
- Total lines changed
- Change density (lines changed per file)
- Duration (time between enable and disable)

**Notes:**
- Run this AFTER completing AI-assisted changes
- Baseline data persists for future reference
- Can re-enable baseline mode later for new comparison

**Related Commands:** baseline enable, baseline run

---

### `baseline status`

Show current baseline mode status and metadata.

**Purpose:** Display whether baseline mode is active, snapshot details, and tracked changes.

**Syntax:**
```bash
wai baseline status [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Check baseline status
wai baseline status

# Check specific project
wai baseline status /home/user/my-project
```

**Output (baseline enabled):**
```
=== Baseline Mode: ENABLED ===

Created: 2026-01-20 15:30 UTC
Tracked files: 47
Baseline snapshot: locked

Next steps:
  1. Make AI-assisted changes
  2. Run 'wai baseline run' to compare
  3. Run 'wai baseline disable' to finalize
```

**Output (baseline disabled):**
```
=== Baseline Mode: DISABLED ===

Baseline mode is not active.

To start tracking:
  wai baseline enable
```

**Output (baseline completed):**
```
=== Baseline Mode: COMPLETED ===

Created: 2026-01-20 15:30 UTC
Finalized: 2026-01-20 18:45 UTC
Duration: 3h 15m

Tracked files: 47
Modified: 12 files
Added: 3 files
Deleted: 1 file
Total changes: 234 lines

Last comparison: 2026-01-20 18:40 UTC (IDE: Claude Code, Model: GPT-5)
```

**Related Commands:** baseline enable, baseline disable, baseline run

---

### `baseline run`

Run automated baseline comparison between initial snapshot and current state.

**Purpose:** Generate diff report showing changes since baseline was enabled. Used for measuring AI effectiveness and code quality.

**Syntax:**
```bash
wai baseline run [path] [--ide IDE_NAME] [--model MODEL_NAME] [--notes NOTES]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- `--ide IDE_NAME` - IDE/tool name (e.g., "Claude Code", "Cursor")
- `--model MODEL_NAME` - AI model name (e.g., "GPT-5", "Claude Sonnet 4.5")
- `--notes NOTES` - Optional notes for this comparison run

**Examples:**
```bash
# Basic comparison
wai baseline run

# With metadata for research tracking
wai baseline run --ide "Claude Code" --model "GPT-5"

# With notes
wai baseline run --ide "Cursor" --model "Claude Opus 4.5" --notes "Refactoring authentication module"

# Specific project
wai baseline run /home/user/my-project --ide "Codex CLI" --model "GPT-5.5"
```

**What It Does:**
1. Compares current file state to baseline snapshot
2. Generates diff report (files changed, lines added/removed/modified)
3. Calculates change metrics (density, complexity, etc.)
4. Records comparison metadata (timestamp, IDE, model, notes)
5. Appends run to `baseline-runs.jsonl` for trend analysis

**Output:**
```
=== Baseline Comparison Report ===

Run: 2026-01-20 18:40 UTC
IDE: Claude Code
Model: GPT-5
Notes: Refactoring authentication module

Files modified: 12
Files added: 3
Files deleted: 1
Total lines changed: 234 (+180, -54)

Top changed files:
  src/auth/login.py: +45 -12 (57 lines)
  src/auth/middleware.py: +38 -8 (46 lines)
  tests/test_auth.py: +52 -15 (67 lines)

Change density: 4.98 lines/file
Duration since baseline: 3h 10m

Report saved to WAI-Spoke/baseline/runs/run-2026-01-20T18-40-00.json
```

**Use Cases:**
- Measure AI-assisted refactoring effectiveness
- Compare different AI models/IDEs on same task
- Track code quality evolution over sessions
- Research: quantify AI impact on development

**Notes:**
- Can run multiple times (tracks history)
- Each run records metadata for comparison
- Does not modify code, only analyzes

**Related Commands:** baseline enable, baseline disable, baseline status

---

## Template Management

Create reusable project templates from existing spokes for rapid initialization.

### `template create`

Create a reusable template from an existing spoke.

**Purpose:** Package a spoke's WAI-Spoke/ structure as a template for initializing new projects with predefined patterns.

**Syntax:**
```bash
wai template create <name> [--path PATH] [--description TEXT]
```

**Arguments:**
- `name` (required): Template name (alphanumeric, dashes, underscores)

**Flags:**
- `--path PATH` - Spoke path to template (default: current directory)
- `--description TEXT` or `-d TEXT` - Template description

**Examples:**
```bash
# Create template from current directory
wai template create my-template

# Create from specific project
wai template create web-app-template --path /home/user/projects/my-web-app

# With description
wai template create react-app -d "React app with TypeScript and Vite" --path ./my-react-app
```

**What It Does:**
1. Reads WAI-Spoke/ structure from source project
2. Extracts reusable patterns (WAI-Guide.md, foundation structure)
3. Sanitizes project-specific data (names, paths, session logs)
4. Saves template to hub `templates/` directory
5. Registers template in hub templates registry

**Template Structure:**
```
hub/
└── templates/
    └── my-template/
        ├── template-metadata.json
        ├── WAI-Guide.md
        ├── WAI-State.json (sanitized)
        └── WAI-State.md (sanitized)
```

**Template Metadata:**
```json
{
  "name": "my-template",
  "description": "My project template",
  "version": "2.1",
  "created_at": "2026-01-20T15:30:00Z",
  "source_project": "my-web-app"
}
```

**Related Commands:** template list, template apply

---

### `template list`

List all available templates in the hub.

**Purpose:** Display registered templates with metadata for selection.

**Syntax:**
```bash
wai template list
```

**Arguments:**
- None

**Flags:**
- None

**Examples:**
```bash
wai template list
```

**Output:**
```
Available Templates (3):

  react-app
    Description: React app with TypeScript and Vite
    Version: 2.1
    Created: 2026-01-15 10:30 UTC

  python-api
    Description: FastAPI backend with PostgreSQL
    Version: 2.1
    Created: 2026-01-18 14:20 UTC

  data-pipeline
    Description: ETL pipeline with Airflow
    Version: 2.1
    Created: 2026-01-20 09:00 UTC
```

**Related Commands:** template create, template apply

---

### `template apply`

Apply a template to initialize a new project.

**Purpose:** Initialize a new spoke using a predefined template, inheriting patterns and structure.

**Syntax:**
```bash
wai template apply <name> <target_path>
```

**Arguments:**
- `name` (required): Template name
- `target_path` (required): Path to new project directory

**Flags:**
- None

**Examples:**
```bash
# Apply template to new project
wai template apply react-app ./my-new-app

# Apply to absolute path
wai template apply python-api /home/user/projects/new-api

# Apply to existing directory (adds WAI-Spoke/)
wai template apply data-pipeline ./existing-project
```

**What It Does:**
1. Validates template exists in hub
2. Creates target directory if needed
3. Copies template files to `target_path/WAI-Spoke/`
4. Personalizes project metadata (name, created date)
5. Initializes session state for new project
6. Creates CLAUDE.md with IDE instructions

**Personalization:**
- Updates project name in WAI-State.json
- Resets session count to 0
- Clears session logs
- Sets created timestamp
- Preserves foundation structure and patterns from template

**Notes:**
- Target directory can be empty or existing project
- Does not overwrite existing WAI-Spoke/ (fails with warning)
- Use `--force` flag to overwrite (not yet implemented)

**Related Commands:** template create, init

---

### `template delete`

Delete a template from the hub.

**Purpose:** Remove a template permanently from the hub templates directory.

**Syntax:**
```bash
wai template delete <name> [--force]
```

**Arguments:**
- `name` (required): Template name to delete

**Flags:**
- `--force` or `-f` - Skip confirmation prompt

**Examples:**
```bash
# Delete with confirmation
wai template delete old-template

# Force delete without prompt
wai template delete old-template --force
wai template delete old-template -f
```

**Confirmation:**
```
Delete template 'old-template'? This cannot be undone. [y/N]:
```

**Notes:**
- Permanently deletes template directory from hub
- Cannot be undone (no recycle bin)
- Does not affect projects created from this template

**Related Commands:** template create, template list

---

## IDE Integration

Configure IDE-specific Wheelwright integration for seamless AI session continuity.

### `configure-ide detect`

Detect IDEs currently in use for the project.

**Purpose:** Auto-detect IDE configuration files (VS Code, Cursor, JetBrains, etc.) to determine active development environment.

**Syntax:**
```bash
wai configure-ide detect [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Detect IDEs in current project
wai configure-ide detect

# Detect in specific project
wai configure-ide detect /home/user/my-project
```

**Detection Signals:**
- `.vscode/` directory → VS Code
- `.cursor/` directory → Cursor
- `.idea/` directory → JetBrains IDEs (IntelliJ, PyCharm, etc.)
- `.claude/` directory → Claude Code
- `*.code-workspace` files → VS Code workspaces

**Output:**
```
Detected IDEs:

  ✓ VS Code (.vscode/ found)
  ✓ Claude Code (.claude/ found)

No configuration found for:
  Cursor
  JetBrains IDEs
```

**Related Commands:** configure-ide setup, configure-ide list

---

### `configure-ide list`

List all supported IDE integrations.

**Purpose:** Display available IDE integrations and their capabilities.

**Syntax:**
```bash
wai configure-ide list [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
wai configure-ide list
```

**Output:**
```
Supported IDE Integrations:

  VS Code
    Config file: .vscode/settings.json
    Capabilities: context injection, CLAUDE.md support
    Status: Detected

  Cursor
    Config file: .cursor/settings.json
    Capabilities: context injection, inline prompts
    Status: Not detected

  Claude Code
    Config file: .claude/CLAUDE.md
    Capabilities: native Wheelwright support
    Status: Detected

  JetBrains IDEs
    Config files: .idea/**, *.iml
    Capabilities: context injection
    Status: Not detected
```

**Related Commands:** configure-ide detect, configure-ide capabilities

---

### `configure-ide setup`

Setup IDE configuration files for Wheelwright integration.

**Purpose:** Generate or update IDE-specific configuration for Wheelwright context injection and session continuity.

**Syntax:**
```bash
wai configure-ide setup [ide_name] [path] [--force]
```

**Arguments:**
- `ide_name` (optional): IDE name (default: setup all detected IDEs)
- `path` (optional): Project path (default: current directory)

**Flags:**
- `--force` - Overwrite existing configuration files

**Examples:**
```bash
# Setup all detected IDEs
wai configure-ide setup

# Setup specific IDE
wai configure-ide setup "VS Code"
wai configure-ide setup Cursor

# Setup with path
wai configure-ide setup "Claude Code" /home/user/my-project

# Force overwrite existing config
wai configure-ide setup --force
```

**What It Does:**
1. Detects or validates IDE
2. Creates/updates IDE config directory (`.vscode/`, `.cursor/`, etc.)
3. Generates IDE-specific settings:
   - Context file paths (WAI-Guide.md, WAI-State.json)
   - Prompt templates
   - Keyboard shortcuts (if supported)
4. Creates root-level `CLAUDE.md` with project instructions
5. Updates WAI-State.json with IDE metadata

**Generated Files:**
- **VS Code:** `.vscode/settings.json` (file associations, context paths)
- **Cursor:** `.cursor/settings.json` (AI context paths)
- **Claude Code:** `CLAUDE.md` (project instructions)
- **JetBrains:** `.idea/wheelwright.xml` (context configuration)

**CLAUDE.md Contents:**
- Project overview
- Path to WAI-Spoke/ directory
- Session start protocol
- Command reference

**Related Commands:** configure-ide detect, configure-ide capabilities

---

### `configure-ide capabilities`

Show detailed capabilities for an IDE integration.

**Purpose:** Display what features are supported for a specific IDE (context injection, shortcuts, etc.).

**Syntax:**
```bash
wai configure-ide capabilities [ide_name] [path]
```

**Arguments:**
- `ide_name` (optional): IDE name (default: show all detected IDEs)
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Show capabilities for all detected IDEs
wai configure-ide capabilities

# Show capabilities for specific IDE
wai configure-ide capabilities "VS Code"
wai configure-ide capabilities Cursor

# Specific project
wai configure-ide capabilities "Claude Code" /home/user/my-project
```

**Output:**
```
IDE Capabilities: VS Code

Context Injection:
  ✓ CLAUDE.md support (automatic)
  ✓ File watcher for WAI-Spoke/ changes
  ✓ Workspace recommendations

Keyboard Shortcuts:
  ✗ Not supported (VS Code limitation)

AI Integration:
  ~ Copilot compatible (requires extension)
  ✓ Chat context from files

Limitations:
  - Cannot auto-inject context into Copilot
  - Requires manual context file inclusion
```

**Related Commands:** configure-ide list, configure-ide setup

---

### `configure-ide optimize`

Get optimization suggestions for IDE configuration.

**Purpose:** Analyze current IDE setup and suggest improvements for better Wheelwright integration.

**Syntax:**
```bash
wai configure-ide optimize [path]
```

**Arguments:**
- `path` (optional): Project path (default: current directory)

**Flags:**
- None

**Examples:**
```bash
# Get optimization suggestions
wai configure-ide optimize

# Specific project
wai configure-ide optimize /home/user/my-project
```

**Output:**
```
IDE Optimization Suggestions:

VS Code:
  ✓ CLAUDE.md configured correctly
  ⚠️ Recommendation: Add .vscode/extensions.json for extension suggestions
  ⚠️ Recommendation: Enable file watchers in settings.json

Claude Code:
  ✓ Native Wheelwright support detected
  ✓ CLAUDE.md up to date

Cursor:
  ✗ Not configured - Run 'wai configure-ide setup Cursor'

General:
  ⚠️ Consider adding .editorconfig for consistency
  ✓ .gitignore properly excludes session logs
```

**Related Commands:** configure-ide setup, configure-ide capabilities

---

## Interactive Menus

When run without arguments, WAI-CLI provides context-aware interactive menus.

### Main Framework Menu

Displayed when running `wai` from the framework directory itself.

**Trigger:** Run `wai` from `C:\Development\framework` (or wherever framework is installed)

**Menu:**
```
============================================================
Framework Menu
============================================================

Select an object to manage:

1. Spoke (this project)
2. Hub (central repository)
3. Projects (registered spokes)
4. Groups (project collections)
5. Help
6. Exit
```

**Options:**
- **1. Spoke** → Opens Spoke Actions Menu
- **2. Hub** → Opens Hub Actions Menu
- **3. Projects** → Opens Projects Actions Menu
- **4. Groups** → Opens Groups Actions Menu
- **5. Help** → Displays help information, returns to menu
- **6. Exit** → Exits CLI

**Navigation:**
- Selecting any option executes action and returns to menu (loop-back design)
- Press Ctrl+C to exit at any time

---

### Spoke Actions Menu

Displayed when selecting "Spoke" from Framework Menu, or running `wai` from a spoke directory.

**Trigger:**
- Select "Spoke" in Framework Menu
- Run `wai` from any initialized spoke project

**Menu:**
```
--- Spoke Actions ---

1. Show status
2. Sync with hub
3. Generate closeout
4. Output context
5. Back
```

**Options:**
- **1. Show status** → Runs `wai status` (displays spoke details)
- **2. Sync with hub** → Runs `wai sync` (upgrades structure, prepares sync)
- **3. Generate closeout** → Runs `wai closeout` (session closeout instructions)
- **4. Output context** → Runs `wai context` (outputs WAI files for LLM paste)
- **5. Back** → Returns to main Framework Menu (or exits if launched from spoke)

**Use Case:**
- Quick access to common spoke operations without remembering command syntax
- Ideal for new users learning the CLI

---

### Hub Actions Menu

Displayed when selecting "Hub" from Framework Menu, or running `wai` from hub directory.

**Trigger:**
- Select "Hub" in Framework Menu
- Run `wai` from hub directory

**Menu:**
```
--- Hub Actions ---

1. Locate/show hub
2. Create new hub
3. Back
```

**Options:**
- **1. Locate/show hub** → Runs `wai hub locate` (auto-discover and display hub path)
- **2. Create new hub** → Runs `wai hub create` (interactive hub creation)
- **3. Back** → Returns to main Framework Menu

**Use Case:**
- Hub setup and discovery without command memorization
- First-time hub creation workflow

---

### Projects Actions Menu

Displayed when selecting "Projects" from Framework Menu.

**Menu:**
```
--- Projects Actions ---

1. List all projects
2. Add new projects
3. List by group
4. Back
```

**Options:**
- **1. List all projects** → Runs `wai projects list` (show all registered projects)
- **2. Add new projects** → Runs `wai projects add` (interactive project discovery)
- **3. List by group** → Prompts for group name, runs `wai projects list --group GROUP`
- **4. Back** → Returns to main Framework Menu

**Use Case:**
- Managing multiple projects without remembering command syntax
- Quick project registration workflow

---

### Groups Actions Menu

Displayed when selecting "Groups" from Framework Menu.

**Menu:**
```
--- Groups Actions ---

1. List all groups
2. Create new group
3. Add spoke to group
4. Remove spoke from group
5. Delete group
6. Back
```

**Options:**
- **1. List all groups** → Runs `wai group list -v` (detailed group listing)
- **2. Create new group** → Prompts for name/description, runs `wai group create`
- **3. Add spoke to group** → Prompts for group/spoke, runs `wai group add-spoke`
- **4. Remove spoke from group** → Prompts for group/spoke, runs `wai group remove-spoke`
- **5. Delete group** → Prompts for group name, runs `wai group delete`
- **6. Back** → Returns to main Framework Menu

**Use Case:**
- Organizing projects into groups without command syntax
- Batch operations on related projects

---

### Uninitialized Menu

Displayed when running `wai` from a directory that is NOT initialized as a spoke or hub.

**Trigger:** Run `wai` from any directory without `WAI-Spoke/` or hub structure

**Menu:**
```
--- Initialize Wheelwright ---

This directory is not initialized.

1. Initialize as spoke (project)
2. Locate or create hub
3. Exit
```

**Options:**
- **1. Initialize as spoke** → Runs `wai init` (interactive spoke initialization)
- **2. Locate or create hub** → Opens Hub Actions Menu
- **3. Exit** → Exits CLI

**Use Case:**
- First-time setup workflow
- Guides new users through initialization process

---

## Planned Commands

The following commands are documented in the roadmap but not yet implemented in the CLI.

### `spoke`

> **⚠️ NOT YET IMPLEMENTED**

**Planned Purpose:** Manage spoke-specific operations (list spokes, add spoke alias, remove spoke).

**Expected Syntax:**
```bash
wai spoke list          # List all registered spokes
wai spoke add <name>    # Add spoke to current wheel
wai spoke remove <name> # Remove spoke from wheel
```

**Status:** Not yet implemented. Current workaround:
- Use `wai projects list` to list registered spokes
- Use `wai projects add` to register projects
- Use hub registry for spoke management

**Tracked in:** Framework development roadmap

---

### `help`

> **⚠️ NOT YET IMPLEMENTED**

**Planned Purpose:** Display comprehensive help information without exiting to `--help` flag.

**Expected Syntax:**
```bash
wai help               # General help
wai help <command>     # Command-specific help
```

**Status:** Not yet implemented as a dedicated command. Current workaround:
- Use `wai --help` for general help
- Use `wai <command> --help` for command-specific help
- Use interactive menus (run `wai` without arguments)
- Read this document: `docs/CLI_REFERENCE.md`

**Tracked in:** Framework development roadmap

---

## Common Workflows

### First-Time Setup

```bash
# 1. Initialize project as spoke
cd /home/user/my-project
wai init

# 2. Create hub (suggested: ../hub)
wai hub create

# 3. Register project with hub
wai projects add

# 4. Verify setup
wai status
```

### Daily Development Session

```bash
# 1. Start session (AI loads context from WAI-Spoke/)
# AI reads WAI-Guide.md, WAI-State.json, WAI-State.md

# 2. Work with AI on tasks...

# 3. Check token usage periodically
wai time

# 4. End session with closeout + commit
wai shipit
```

### Multi-Project Management

```bash
# 1. Create hub (once)
wai hub create ~/wheelwright-hub

# 2. Initialize multiple projects
cd ~/projects/project1 && wai init
cd ~/projects/project2 && wai init
cd ~/projects/project3 && wai init

# 3. Register all with hub
wai projects add --scan ~/projects

# 4. Organize into groups
wai group create clients
wai group add-spoke clients project1
wai group add-spoke clients project2

wai group create internal
wai group add-spoke internal project3

# 5. List by group
wai projects list --group clients
```

### Baseline Comparison Workflow

```bash
# 1. Enable baseline before changes
wai baseline enable

# 2. Make AI-assisted changes...

# 3. Run comparison
wai baseline run --ide "Claude Code" --model "GPT-5" --notes "Refactoring auth module"

# 4. Review report, continue changes...

# 5. Run another comparison
wai baseline run --ide "Claude Code" --model "GPT-5" --notes "Added unit tests"

# 6. Finalize when done
wai baseline disable
```

### Template Creation and Reuse

```bash
# 1. Create template from existing project
cd ~/projects/my-react-app
wai template create react-starter -d "React + TypeScript + Vite template"

# 2. List available templates
wai template list

# 3. Apply to new project
wai template apply react-starter ~/projects/new-client-app

# 4. Verify new project initialized
cd ~/projects/new-client-app
wai status
```

---

## Environment Variables

### `WHEELWRIGHT_HUB_PATH`

Explicitly set hub location to override auto-discovery.

**Format:**
```bash
export WHEELWRIGHT_HUB_PATH="/home/user/wheelwright-hub"
```

**Purpose:**
- Skip auto-discovery and use specified hub path
- Useful for CI/CD environments
- Highest priority in hub discovery (+15 points)

**Example:**
```bash
export WHEELWRIGHT_HUB_PATH=~/wheelwright-hub
wai hub locate
# Output: Found hub at /home/user/wheelwright-hub (score: 27)
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid command, operation failed) |
| 130 | User cancelled (Ctrl+C) |

---

## Getting Help

### In-CLI Help
```bash
# General help
wai --help

# Command-specific help
wai hub --help
wai baseline enable --help
wai group create --help
```

### Interactive Mode
```bash
# Launch interactive menu
wai
```

### Documentation
- **This reference:** `docs/CLI_REFERENCE.md`
- **Quick start:** `docs/QUICKSTART.md`
- **Spokes guide:** `docs/SPOKES.md`
- **README:** `README.md`

### Reporting Issues

- GitHub Issues: https://github.com/your-org/wheelwright-framework/issues
- Include WAI-CLI version (`wai version`)
- Include command output and error messages

---

## Version History

### v2.0.1 (Current)
- Spoke structure version: 2.1
- All commands documented in this reference

### Future Versions
- v2.1.0: Planned `spoke` command group
- v2.1.0: Planned `hub status` command
- v2.2.0: Planned dedicated `help` command

---

**End of CLI Reference**

For more information, visit the Wheelwright Framework documentation or run `wai --help`.
