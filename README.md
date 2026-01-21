# Wheelwright Framework

**Build AI wheels that roll forward forever.**

Your AI remembers everything. Every decision. Every insight. Every conversation.
Your wheel never stops rolling - it only grows smarter.

Works with ChatGPT, Claude, Gemini, Copilot - **any AI you use**.

---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> *"We aren't reinventing the wheel - we're evolving it faster than one person ever could."*

---

## What is Wheelwright?

Wheelwright gives your AI assistants **perfect memory** across all your work sessions. Never lose context, never repeat explanations, always move forward.

**The beauty of Wheelwright:** Your AI partner remembers where you left off - whether you're brainstorming ideas, writing code, or shipping features. Switch between Claude, ChatGPT, or any LLM without losing a single detail. Your wheel keeps rolling.

### WAI Files - "This is the WAI"

WAI (pronounced "way") stands for **Wheelwright AI**.

Your Spoke-Project's `WAI-Spoke/` directory contains:
- **WAI-State.json** - Technical state, foundation, session tracking
- **WAI-State.md** - Strategic vision and evolution log
- **WAI-Guide.md** - Instructions for AI assistants
- **WAI-Signals.jsonl** - High-impact learnings log

*"This is the WAI"* - The files that carry context forward. 🎯

---

## Token Efficiency: More Than Meets the Eye

**Wheelwright isn't just about going rogue with AI on your own - it's about being smarter, faster, and more efficient with your time and money.**

### The Problem: 50-80% Token Waste

Most AI-assisted development suffers from **premature implementation waste**:

```
You: "Add user authentication"
AI: *immediately writes 500 lines of code*
You: "Wait, I meant OAuth not JWT"
AI: *rewrites everything*
You: "Actually, use our existing auth service"
AI: *starts over again*

Result: 1,500+ tokens wasted, 2 hours lost, frustration high
```

**This is the #1 problem in long-running AI projects** - and it costs real money.

### The Solution: ADAPTIVE Workflow

Wheelwright automatically prevents token waste through **intelligent complexity assessment**:

**Complex Tasks** (multi-file OR >6 steps) → **STRICT Mode with Gates:**
1. **Discussion** - Explore requirements, alternatives, risks WITHOUT code
2. **Planning** - Get approval on structured plan BEFORE implementation
3. **Implementation** - Execute with automatic checkpointing

**Simple Tasks** (single file AND ≤5 steps) → **YOLO Mode:**
- AI proceeds autonomously
- No gates, maximum speed
- Retroactive logging

```
You: "Add user authentication"
AI: "I see several approaches. Let's discuss before implementing:
     - Option A: OAuth with existing provider
     - Option B: JWT with custom implementation
     - Option C: Integrate with your auth service
     Which aligns with the architecture?"

You: "Option C - use existing auth service"
AI: "Perfect. Here's the plan... [shows structured plan]"
You: "PLAN ACCEPTED"
AI: *implements correctly the first time*

Result: Zero rework, saves 1,000+ tokens, done in 30 minutes
```

### The Value: Time + Money

**Token efficiency means:**
- ✅ **50-80% fewer tokens** - Save real money on API costs
- ✅ **Zero rework cycles** - Get it right the first time
- ✅ **Faster completion** - Discussion → Plan → Done (no revisions)
- ✅ **Automatic checkpointing** - Large tasks pause every 3-5 steps for verification
- ✅ **Context compression** - `'Compact'` command keeps sessions lean

**Cost comparison:**
```
Without Token Efficiency:
- Feature implementation: ~15,000 tokens (with 2-3 rework cycles)
- Cost: ~$0.45 per feature (GPT-4)
- Time: 3-4 hours (including rework)

With Token Efficiency:
- Feature implementation: ~5,000 tokens (correct first time)
- Cost: ~$0.15 per feature (GPT-4)
- Time: 1 hour (no rework)

Savings per feature: $0.30 + 2-3 hours
Over 100 features: $30 saved + 200-300 hours saved
```

### How It Works: Automatic Intelligence

Wheelwright automatically assesses every request:

```python
# Behind the scenes on every user message:
files_affected = count_files_in_request()  # 1 file
estimated_steps = estimate_complexity()     # 3 steps

if files_affected >= 2 or estimated_steps >= 6:
    workflow_mode = "STRICT"  # Multi-stage gates required
else:
    workflow_mode = "YOLO"  # Autonomous, fast execution
```

**You don't configure anything** - AI automatically chooses the right mode based on complexity.

### Built-In Commands

During any session:
- **`'Time'`** - Check token usage estimate (warns at 80% capacity)
- **`'Compact'`** - Compress context, balance WAI files
- **`'Closeout'`** - Process session, auto-runs Compact
- **`'Shipit'`** - Closeout + git commit in one command

### Cross-Platform Consistency

Token efficiency works **identically** across all AI tools:
- ✅ Claude Code (via CLAUDE.md)
- ✅ Cursor (via .cursorrules)
- ✅ VS Code Copilot/Continue (via settings.json)
- ✅ ChatGPT/Gemini/Generic (via AI-INSTRUCTIONS.md)

**One framework, universal efficiency.**

### The Bottom Line

**Wheelwright = Session Continuity + Token Efficiency**

- **Session continuity** ensures AI never forgets your project
- **Token efficiency** ensures you never waste time or money

This isn't just about "AI memory" - it's about **intelligent, cost-effective AI partnership** that respects your time and budget.

---

### Understanding the Wheel

- **Hub** = Your centralized memory and project registry (stored at ~/wheelwright-hub/)
- **Spoke-Projects** (or **Spokes** for short) = Individual projects using Wheelwright (like your apps, research, writing projects)
- **Wheels** = The combination of your Hub and all Spoke-Projects working together
- **Spoke-Signals** = How a Spoke-Project tracks notable learnings (WAI-Signals.jsonl)
- **Framework** = The Wheelwright source code (this repo)

**How they work together:** Your Hub discovers and tracks all your Spoke-Projects. Each Spoke signals important learnings back to the Hub. The Hub consolidates this knowledge and teaches all Spokes - raising all boats by raising the tide. This continuous "rolling" forward means your AI never forgets.

### About Wheelwright

**Wheelwright** is an AI context persistence system that makes project memory permanent.

**wheelwright-ai** is the GitHub organization hosting:
- Wheelwright Framework (this repo) - core tooling
- Extensions (VS Code, browser, etc.)
- Documentation and examples

**wheelwright.ai** is the project website and documentation hub.

All three work together under the "Wheelwright" umbrella.

### Key Features

- **Token Efficiency (50-80% savings)** - ADAPTIVE workflow prevents premature implementation waste. Complex tasks require Discussion → Planning → Approval gates. Simple tasks run autonomously. Saves time AND money.
- **Automatic Checkpointing** - Large plans pause every 3-5 steps for verification. No more runaway implementations. Stay in control.
- **Context Compression** - `'Compact'` command balances WAI files and compresses context. Keep sessions lean and efficient.
- **Single Source of Truth** - Maintain perfect context across all project stages: ideation, development, implementation, and beyond
- **Session Continuity** - Conversation logging tracks every turn, enabling intelligent closeout and recovery from disruptions
- **LLM-Portable Memory** - Keep context and progress portable to any LLM - ChatGPT, Claude, Gemini, Copilot, whatever comes next
- **Beyond Code** - Use Wheelwright for writing, research, strategy, design - any knowledge work requiring sustained AI partnership
- **Smart Closeout & Shipit** - Process sessions into summaries, clear verbose logs, commit changes - all with simple commands
- **Hub Learning Ready** - Closeout ensures your Spoke-Project is clean and ready for hub knowledge collection
- **Framework for Frameworks** - Built to support other frameworks and tools as they emerge
- **Collective Learning** - The Hub learns from all your Spoke-Projects and teaches them, creating a rising tide that lifts all boats

---

## Installation

### Step 1: Clone the Framework

```bash
# Clone the framework repository
git clone https://github.com/wheelwright-ai/framework.git wheelwright
cd wheelwright

# Make the CLI executable
chmod +x WAI

# Optional: Add to your PATH for global access
echo 'export PATH="$PATH:$(pwd)"' >> ~/.bashrc
source ~/.bashrc
```

### Step 2: Initialize Your First Spoke-Project

Start by adding Wheelwright to an existing project (or create a new one):

```bash
# Navigate to your project
cd ~/projects/my-awesome-project

# Initialize Wheelwright context
WAI-CLI init

# Or initialize from anywhere
WAI-CLI init ~/projects/my-awesome-project
```

This creates a `WAI-Spoke/` directory containing your project's memory:
- `WAI-State.json` - Machine-readable project state and foundation
- `WAI-State.md` - Human-readable strategic context and vision
- `WAI-Guide.md` - Instructions that teach AI assistants about your project
- `WAI-Signals.jsonl` - High-impact learnings ready for Hub collection
- `WAI-KB-Sync.json` - Hub synchronization status

### GPT Bootstrap (Single-File Mode)

If you are working in a GPT session without the CLI, use the bootstrap folder:

1) Open `bootstrap/README.md` and `bootstrap/WAI-Minimal.template.md`.
2) Ask GPT to fill the template into ONE file (save as `WAI-Minimal.md`).
3) After initializing Wheelwright locally, move it to:
   `WAI-Spoke/seed/ingest/WAI-Minimal.md`
4) Run `WAI-CLI closeout` (or `WAI shipit`) to reconcile it into the full WAI files.

The bootstrap folder is refreshed on every Shipit for the framework.

### Step 3: Create Your Hub (After 1+ Spoke-Projects)

Once you have one or more Spoke-Projects, create a Hub to centralize learning:

```bash
# Create your personal Hub
WAI hub create

# Or specify a custom location
WAI hub create ~/wheelwright-hub
```

Your Hub becomes the central memory and registry for all your Spoke-Projects, enabling collective learning across everything you build.

---

## Using the Wheelwright CLI

The `WAI` command-line interface orchestrates your Hub, Spoke-Projects, and the Framework. Here's what it enables:

### Project Management
- **Initialize projects** - Add Wheelwright context to new or existing work
- **Check status** - View current wheel state, session info, and health metrics
- **Generate context** - Output formatted context for pasting into any LLM
- **Session closeout** - Prepare state files for session end with proper handoff

### Hub Operations
- **Create Hub** - Establish your centralized memory and project registry
- **Hub status** - Monitor Hub health, sync status, and connected Spoke-Projects
- **Locate Hub** - Find where your Hub lives on the filesystem
- **Project scanning** - Discover existing Spoke-Projects automatically
- **Bulk sync** - Synchronize all Spoke-Projects with the Hub at once

### Spoke System
- **List spokes** - View available capabilities (meta-consultation, document-analysis, code-review)
- **Add spokes** - Extend your wheel with specialized AI capabilities
- **Remove spokes** - Disable capabilities you no longer need

### Synchronization
- **Sync individual wheels** - Push Spoke-Signals to Hub, pull Hub learnings
- **Sync all wheels** - Update every Spoke-Project with latest Hub knowledge
- **Track sync history** - Monitor when and what was synchronized

### Command Glossary

```bash
# Core Commands
WAI-CLI init [path]                    # Initialize Wheelwright in a project
WAI-CLI status                         # Show current spoke state and health
WAI absorbe / update               # Process seed folders, archive sprawl
WAI context                        # Output context for LLM paste
WAI version                        # Show Wheelwright version

# Session Management
WAI closeout                       # Generate session closeout
WAI shipit                         # Closeout + git commit
WAI time                           # Show token usage estimate
WAI stats                          # Show session analytics
WAI sync [--all]                   # Upgrade spoke structure

# Hub Management
WAI hub create [path]              # Create your personal Hub
WAI hub locate                     # Find Hub location on filesystem

# Project Management
WAI projects add [--scan PATH...]  # Register projects with hub
WAI projects list [--group NAME]   # List registered projects

# Group Management
WAI group create <name>            # Create project group
WAI group list [-v]                # List all groups
WAI group add-spoke <group> <spoke> # Add spoke to group
WAI group remove-spoke <group> <spoke> # Remove spoke from group
WAI group delete <name>            # Delete a group

# Baseline Tracking
WAI baseline enable                # Enable baseline mode
WAI baseline disable               # Disable and lock baseline
WAI baseline status                # Show baseline status
WAI baseline run                   # Run baseline comparison

# Template Management
WAI template create <name>         # Create reusable template
WAI template list                  # List available templates
WAI template apply <name> <path>   # Apply template to project
WAI template delete <name>         # Delete a template

# IDE Integration
WAI configure-ide detect           # Detect IDEs in use
WAI configure-ide list             # List supported IDEs
WAI configure-ide setup [ide]      # Setup IDE configuration
WAI configure-ide capabilities     # Show IDE capabilities
WAI configure-ide optimize         # Get optimization suggestions

# Interactive Mode
WAI                                # Launch interactive menu (context-aware)
```

**Not Yet Implemented:**
- `WAI hub status` - Show Hub health and metrics (use `WAI projects list` instead)
- `WAI spoke list/add/remove` - Spoke management (use `WAI projects` commands)
- `WAI help` - Dedicated help command (use `WAI --help` or interactive mode)

---

## The Beauty of Session Continuity

### Before Wheelwright

```
You: "Let's add authentication to the app"
AI: "Sure! What kind of auth?"
You: "We discussed this yesterday - JWT with refresh tokens"
AI: "Okay, what database are you using?"
You: "PostgreSQL... like we've been using this whole project"
AI: "Got it. Should I use bcrypt for passwords?"
You: *sighs* "Yes, we already set that up in session 1..."
```

**Every new session = starting from scratch.**

### With Wheelwright

```
You: "Let's add authentication to the app"
AI: *reads WAI-Spoke/* "I see we're using PostgreSQL with bcrypt.
    Based on our architecture decisions (WAI-State.json:147),
    I'll implement JWT with refresh tokens as discussed.
    Should I follow the pattern we established in the user service?"
You: "Perfect."
```

**Every new session = picking up exactly where you left off.**

### What Makes This Magic?

1. **AI reads your wheel context** before responding
2. **Understands project foundation** - identity, boundaries, approach
3. **Sees decision history** - knows why things are the way they are
4. **Tracks evolution** - understands how the project has changed
5. **Learns from patterns** - applies Hub knowledge from your other projects
6. **Signals breakthroughs** - shares high-impact learnings back to the Hub

### Switch LLMs Without Friction

Start with Claude in the morning:
```bash
# Copy context for Claude
WAI context | pbcopy
```

Continue with ChatGPT in the afternoon:
```bash
# Same context, different AI
WAI context | pbcopy
```

**Both AIs see the same foundation, decisions, and progress.** Your wheel keeps rolling.

### From Idea to Implementation - One Continuous Memory

```
Session 1 (Ideation)
└─ AI helps brainstorm features
   └─ Records decisions in WAI-State.json

Session 2 (Planning)
└─ AI recalls Session 1 decisions
   └─ Proposes architecture
   └─ Updates evolution log

Session 3 (Development)
└─ AI knows the plan from Session 2
   └─ Writes code matching architecture
   └─ Signals breakthrough patterns to Hub

Session 4 (Different Project)
└─ AI applies Hub learnings from Session 3
   └─ Your wheel is teaching other wheels
```

**This is why we call it "rolling forward" - context never resets.**

---

## Automatic Discovery: The Critical Feature

**WAI must be seen and loaded automatically** - this isn't optional, it's what makes session continuity actually work.

### Why Automatic Discovery Matters

When you start an AI session in VS Code, Claude Code, Cursor, or any AI-powered IDE, the AI needs to **see your `WAI-Spoke/` folder immediately** - before you type a single prompt. Without this:

- ❌ AI starts with zero context
- ❌ You have to manually paste context every session
- ❌ Session continuity breaks down
- ❌ WAI becomes just another manual workflow

With automatic discovery:

- ✅ AI loads context before responding
- ✅ Understands project foundation from first message
- ✅ Applies Hub learnings automatically
- ✅ True session continuity - zero manual steps

### How AI Tools Discover WAI

Popular AI assistants automatically discover WAI through standard integration points:

#### Claude Code
```json
// Claude Code automatically reads project instructions
// Place instructions in: CLAUDE.md
// WAI templates include this by default

// Your CLAUDE.md points to WAI-Spoke/ folder:
"IMPORTANT: Read WAI-Spoke/ folder first to understand project context."
```

#### Codex CLI
```markdown
// Codex CLI reads project instructions
// Place instructions in: AGENTS.md
// WAI templates include this by default
```

#### VS Code Extensions (Copilot, Codeium, etc.)
```json
// .vscode/settings.json - WAI creates this automatically
{
  "ai.context.files": [
    "WAI-Spoke/WAI-Guide.md",
    "WAI-Spoke/WAI-State.json",
    "WAI-Spoke/WAI-State.md"
  ],
  "ai.instructions": "WAI-Spoke/WAI-Guide.md"
}
```

#### Cursor IDE
```json
// .cursorrules - WAI generates on init
// Cursor automatically loads this file
// Contains: "Read WAI-Spoke/WAI-Guide.md for complete project context"
```

#### Windsurf, Zed, and Others
```markdown
// .ai/instructions.md or similar conventions
// WAI detects your IDE and creates appropriate files
// Standard pattern: Point to WAI-Spoke/ as source of truth
```

### The WAI Automatic Setup

When you run `WAI-CLI init`, the framework:

1. **Detects your environment** - VS Code? Claude Code? Cursor? Other?
2. **Creates integration files** - `.vscode/settings.json`, `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, etc.
3. **Points AI to `WAI-Spoke/`** - Each integration file references `WAI-Spoke/WAI-Guide.md`
4. **Configures auto-loading** - AI tools read context on session start

### What Gets Loaded Automatically

When an AI tool starts a session in your project:

```
Session Start
    ↓
AI Tool Detects Integration File (CLAUDE.md, AGENTS.md, .cursorrules, etc.)
    ↓
Reads WAI-Spoke/WAI-Guide.md
    ↓
Loads WAI-Spoke/WAI-State.json (foundation, decisions, constraints)
    ↓
Loads WAI-Spoke/WAI-State.md (strategic context, vision)
    ↓
Checks WAI-Spoke/WAI-KB-Sync.json (Hub learnings available?)
    ↓
AI is now FULLY CONTEXT-AWARE before first response
```

### Verifying Automatic Loading

You can test if your AI tool is loading WAI correctly:

**Start a new session and ask:**
```
"What is this project about and what are the current boundaries?"
```

**If WAI is loading correctly, AI will respond with:**
- Project name and one-liner from `WAI-State.json`
- In-scope and out-of-scope boundaries
- Current phase and next actions
- Recent decisions and rationale

**If AI asks "What project?" → WAI isn't loading automatically** - check your integration files.

### Supported AI Tools

WAI auto-configures for:

| Tool | Integration File | Auto-Generated |
|------|------------------|----------------|
| **Codex CLI** | `AGENTS.md` | ✅ Yes |
| **Claude Code** | `CLAUDE.md` | ✅ Yes |
| **VS Code** (Copilot, Codeium, Continue) | `.vscode/settings.json` | ✅ Yes |
| **Cursor** | `.cursorrules` | ✅ Yes |
| **Windsurf** | `.windsurfrules` | ✅ Yes |
| **Zed** | `.zed/settings.json` | ✅ Yes |
| **GitHub Copilot Workspace** | `.github/copilot-instructions.md` | ✅ Yes |
| **Aider** | `.aider.conf.yml` | ✅ Yes |
| **Web LLMs** | Use `WAI-CLI context` command | Manual copy |

### Manual Override (When Needed)

For AI tools not yet supported, you can manually configure:

```bash
# Generate context for copy/paste
WAI context

# Or create a custom integration file
echo "Read WAI-Spoke/WAI-Guide.md for project context" > .your-ai-tool-config
```

**The goal:** Every AI tool should load WAI automatically. If your tool isn't listed, [open an issue](https://github.com/wheelwright-ai/framework/issues) and we'll add support.

---

## Hub Synchronization

**Keep all your spokes synchronized with the latest learnings.**

The hub acts as a central knowledge repository that collects patterns from all your projects and distributes them back. This creates a continuous learning loop where each project benefits from insights gained in others.

### What is the Knowledge Base (KB)?

The hub's knowledge base contains consolidated patterns, learnings, and best practices aggregated from all connected spokes. When you sync, your spoke downloads the latest KB and uploads its own high-impact signals.

**Knowledge Base Structure:**
```
hub/
└── knowledge/
    ├── kb-manifest.json      # Version and metadata
    ├── patterns/             # Reusable patterns
    │   ├── error-handling.md
    │   ├── api-design.md
    │   └── testing.md
    └── learnings/            # Cross-project insights
        ├── performance.md
        └── architecture.md
```

### What are Signals?

Signals are high-impact learnings (impact >= 8) that your spoke shares back to the hub. They capture breakthrough insights, architectural decisions, and patterns worth spreading to other projects.

**Signal Flow:**
```
Spoke (Your Project)
    ↓ Work produces insights
WAI-Signals.jsonl (impact >= 8)
    ↓ wai sync uploads
hub/signals/by-spoke/[project-name]/
    ↓ Hub processes and consolidates
hub/knowledge/ (KB updated)
    ↓ wai sync downloads
All Spokes (Updated KB)
```

### Sync Workflow

**Automatic Three-Phase Sync:**

1. **Structure Upgrade** - Auto-upgrades spoke to latest version (v2.1)
2. **KB Download** - Downloads updated patterns and learnings from hub
3. **Signal Upload** - Uploads your high-impact signals to hub

**Running Sync:**
```bash
# Sync current spoke
wai sync

# Check if sync is needed (no changes)
wai sync --check

# Sync all registered spokes
wai sync --all
```

### When to Sync

**Recommended Sync Frequency:**
- **After major milestones** - Share breakthrough patterns
- **Before starting new features** - Get latest hub learnings
- **Every 30 days** - Keep KB current (automatic health checks warn you)
- **After closeout** - Signals are logged, ready to share

**Health Monitoring:**
```bash
# Check sync health without syncing
wai sync --check

# Output shows status and recommendations:
#   ✓ healthy - No action needed
#   ⚠ stale - Sync recommended
#   ✗ outdated - Sync strongly recommended
#   ℹ never_synced - First sync needed
```

### Knowledge Base Benefits

**Why sync with the hub KB?**

1. **Cross-Project Learning** - Patterns from one project help all projects
2. **Consolidated Best Practices** - Hub aggregates and refines learnings
3. **Avoid Reinventing** - Reuse solutions from your past projects
4. **Continuous Improvement** - KB grows smarter with each sync
5. **Team Consistency** - Shared hub keeps teams aligned

**Example Pattern Sharing:**
```
Project A discovers efficient error handling pattern
    ↓ Signals to hub (impact: 9)
Hub adds to KB as reusable pattern
    ↓ Next sync distributes to all spokes
Project B, C, D receive error handling pattern
    ↓ Apply pattern in their contexts
Entire wheel benefits from one project's insight
```

### Signal Sharing Guidelines

**What to signal (impact >= 8):**
- Architectural breakthroughs
- Performance optimizations (significant gains)
- Novel problem-solving approaches
- Critical bugs avoided through patterns
- Cross-domain applicable solutions

**What NOT to signal:**
- Common knowledge (everyone knows this)
- Obvious patterns (standard practices)
- Project-specific implementation details
- Minor refactorings (impact < 8)
- Routine fixes without novel insight

### Sync Health States

| Health | Description | Action |
|--------|-------------|--------|
| **Healthy** | Synced within 30 days, KB current | Continue working |
| **Stale** | 30-90 days since sync OR minor version drift | Run `wai sync` soon |
| **Outdated** | >90 days since sync OR major version drift | Run `wai sync` now |
| **Never Synced** | First sync pending | Run `wai sync` to connect |

### Troubleshooting Sync Issues

**Common Issues:**

| Issue | Solution |
|-------|----------|
| "No hub found" | Run `wai hub create` or set `$WHEELWRIGHT_HUB_PATH` |
| "Hub KB not found" | Hub created but no KB yet - will be created on first aggregation |
| "KB sync failed" | Previous version preserved, check hub/knowledge/ permissions |
| Duplicate signals skipped | Normal - hub deduplicates by content hash |
| No signals uploaded | No high-impact signals ready (impact < 8 or already uploaded) |

**For detailed troubleshooting, see:** [docs/commands/sync.md](docs/commands/sync.md)

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Wheelwright Framework (this repository)                    │
│  - Core source code (WAI CLI, Python modules)              │
│  - Wheel templates (WAI-State.json, WAI-Guide.md, etc.)   │
│  - Spoke loader + built-in spokes                           │
│  - Hub creation and management tooling                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ User runs: WAI hub create
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Hub (~/wheelwright-hub/ or custom location)                │
│  - Centralized memory and project registry                  │
│  - hub-profile.json (your preferences)                      │
│  - .WAI-registry/ (discovered Spoke-Projects)              │
│  - learnings/ (cross-project patterns)                      │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
      ┌──────────┐      ┌──────────┐      ┌──────────┐
      │ Project A│      │ Project B│      │ Project C│
      │ (Spoke)  │      │ (Spoke)  │      │ (Spoke)  │
      │  WAI-Spoke/  │      │  WAI-Spoke/  │      │  WAI-Spoke/  │
      └──────────┘      └──────────┘      └──────────┘
```

### The Wheel in Motion

1. **You work with AI** - Any LLM reads your `WAI-Spoke/` context
2. **AI updates state** - Session info, decisions, insights logged
3. **Signals flow to Hub** - High-impact learnings (impact >= 8) shared via `WAI-Signals.jsonl`
4. **Hub learns and teaches** - Patterns consolidated, distributed to other Spoke-Projects
5. **All boats rise** - Your next project starts smarter because of this one

### Built-in Session Commands

During any AI session with Wheelwright, these commands optimize efficiency and continuity:

| Command | AI Response |
|---------|-------------|
| `'Time'` | Estimates token usage with 60%/80%/90% capacity warnings |
| `'Compact'` | Compresses context, balances WAI files (auto-runs before closeout/shipit) |
| `'Rules'` | Lists active behavioral guidelines and project protocols |
| `'Closeout'` | Runs Compact, processes session, extracts learnings, clears conversation log |
| `'Shipit'` | Runs Closeout + git commit in one command (ready for push) |

---

## Project Structure

### Your Spoke-Project

```
your-project/
├── WAI-Spoke/                    # Wheelwright context directory
│   ├── WAI-State.json       # Machine-readable state, foundation, decisions
│   ├── WAI-State.md         # Human-readable strategic context
│   ├── WAI-Guide.md         # AI instructions and behavioral guidelines
│   ├── WAI-Signals.jsonl   # High-impact learnings ready for Hub
│   └── WAI-KB-Sync.json          # Hub synchronization status
└── ... your project files
```

### Your Hub

```
wheelwright-hub/
├── WAI-Spoke/                    # Hub's own Wheelwright context
├── .WAI-registry/           # Spoke-Project tracking and metadata
│   ├── wheels/               # Individual wheel metadata
│   └── wheel-projects.json   # Complete registry
├── hub-profile.json          # Your AI collaboration preferences
└── learnings/                # Cross-project consolidated patterns
    ├── ide/                  # IDE configurations and workflows
    ├── languages/            # Language-specific patterns
    └── workflows/            # Development workflow patterns
```

---

## Universal Application

Wheelwright isn't just for code. Build wheels for **any knowledge work**:

### Software Development
- Full-stack applications
- API design and implementation
- Microservices architectures
- Open-source projects

### Writing & Content
- Books and long-form content
- Technical documentation
- Research papers
- Blog series

### Strategy & Planning
- Business strategy development
- Product roadmaps
- Organizational design
- Decision frameworks

### Research & Analysis
- Academic research
- Market analysis
- Competitive intelligence
- Data investigations

### Design
- UI/UX design systems
- Software architecture
- System design
- Information architecture

**Any project requiring sustained AI partnership benefits from continuous context.**

---

## Configuration

### Environment Variables

```bash
# Set your Hub location
export WHEELWRIGHT_HUB_PATH=~/wheelwright-hub

# Set Framework location (if not in PATH)
export WHEELWRIGHT_FRAMEWORK_PATH=~/projects/wheelwright-ai/framework

# Enable automatic synchronization
export WHEELWRIGHT_AUTO_SYNC=true
```

### Hub Profile Customization

Edit `hub-profile.json` to personalize AI interactions:

```json
{
  "work_style": {
    "preferred_ais": ["Claude", "ChatGPT", "GitHub Copilot"],
    "coding_preferences": {
      "languages": ["Python", "TypeScript", "Go"],
      "patterns": ["functional", "clean-code", "test-driven"]
    },
    "collaboration_style": "collaborative"
  },
  "project_defaults": {
    "auto_sync": true,
    "signal_threshold": 8
  }
}
```

---

## Philosophy: AI as Responsible Partner

Wheelwright implements a unique **stewardship philosophy**:

> AI should enable but remain intentful. When work strays from the established
> foundation, the AI should detect drift and require explicit acknowledgment.

### Core Behaviors

1. **Detect Scope Drift** - Before enabling work, AI checks if it fits project boundaries
2. **Require Acknowledgment** - Direction changes need explicit user approval
3. **Complete Foundation First** - AI guides setup before diving into work
4. **Prefer Verification** - "Are you sure?" over silent compliance

### Why This Matters

Traditional AI assistants are **order-takers** - they do what you ask, even if it contradicts yesterday's decisions.

Wheelwright-enabled AI is a **responsible partner** - it remembers the plan, detects when you're drifting, and asks "Are you sure this aligns with our foundation?"

**Result:** Less wasted effort, more intentional evolution, better outcomes.

---

## Migrating from SCF

If you used the Session Continuity Framework (SCF), migration is straightforward:

```bash
# Run the migration script
python migrate-scf-to-wheelwright.py

# Rename your SCF hub
mv ~/scf-hub ~/wheelwright-hub

# Update environment variables
sed -i 's/SCF_HUB_PATH/WHEELWRIGHT_HUB_PATH/g' ~/.bashrc
```

The migration preserves all context, decisions, and learnings.

---

## Contributing

We welcome contributions! Wheelwright is built for the community.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/wheelwright-ai/framework.git
cd framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Roadmap

- [ ] VS Code extension for automatic context loading
- [ ] Browser extension for web-based LLMs
- [ ] Cloud sync (wheelwright.cloud)
- [ ] Spoke marketplace for community-contributed capabilities
- [ ] Team Hub sharing and collaboration
- [ ] Enterprise features (SSO, audit logs, compliance)

---

## Support

- **Documentation:** [wheelwright.ai/docs](https://wheelwright.ai/docs)
- **GitHub Issues:** [wheelwright-ai/framework/issues](https://github.com/wheelwright-ai/framework/issues)
- **Discussions:** [wheelwright-ai/framework/discussions](https://github.com/wheelwright-ai/framework/discussions)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Credits

Wheelwright Framework was originally developed as the Session Continuity Framework (SCF).

Created by **Mario Vaccari**

[wheelwright.ai](https://wheelwright.ai) | [GitHub](https://github.com/wheelwright-ai) | [Twitter](https://twitter.com/wheelwright_ai)

---

**Roll forward. Never lose ground.**

*Wheelwright Framework - Build AI wheels that roll forward forever*
