# Wheelwright Framework Guide

**For Humans:** This project uses Wheelwright for AI-assisted development with continuous context across sessions.

**For AI Assistants:** Read the sections below BEFORE making any changes to this project.

---

**Framework Version:** 1.0
**Repository:** https://github.com/wheelwright-ai/framework
**Created by:** Mario Vaccari

*"We aren't reinventing the wheel - we're evolving it faster than one person ever could."*

---

## What is Wheelwright?

Wheelwright builds AI wheels that remember everything. Instead of losing context when sessions end, your wheel rolls forward continuously - maintaining memory, learning patterns, and extending capabilities.

### The Wheel Metaphor
- **Hub** = Central memory and consolidated knowledge
- **Spokes** = Specialized capabilities (analysis, consultation, code review)
- **Rim** = The interface connecting to any LLM
- **Rolling** = Each turn moves forward, never losing ground

---

## AI INSTRUCTIONS - READ FIRST

### Context Refresh Check (Do This First!)

**Every session, check if the `WAI-Spoke/` folder has been updated since you last worked here:**

```python
import json
from pathlib import Path
from datetime import datetime

wai_path = Path("WAI-Spoke")
kb_sync = json.loads((wai_path / "kb-sync.json").read_text()) if (wai_path / "kb-sync.json").exists() else {}
state = json.loads((wai_path / "WAI-State.json").read_text())
wai_meta = state.get("wheelwright", {})

# Check for new hub teachings
hub_version = wai_meta.get("hub_reference", {}).get("current_hash_short", "unknown")
last_teach = wai_meta.get("sync_history", [{}])[-1].get("date", "never") if wai_meta.get("sync_history") else "never"

print(f"Hub version: {hub_version}")
print(f"Last teach sync: {last_teach}")
print(f"Days since sync: {wai_meta.get('development_health', {}).get('days_since_sync', 'unknown')}")
```

**If you see new learnings or policies were added:**
1. Read this entire file again for updated instructions
2. Check `kb-sync.json` for new hub knowledge version
3. Review any new sections in this README (especially "Learnings from Hub")
4. Apply new patterns to your current work

---

### Your Core Files

| File | Purpose | Your Action |
|------|---------|-------------|
| `WAI-State.json` | Technical spec, foundation, session state | UPDATE |
| `WAI-State.md` | Strategic context, vision | UPDATE |
| `wheel-signals.jsonl` | High-impact learnings | APPEND (never overwrite) |
| `kb-sync.json` | Hub sync status | READ ONLY |
| `WAI-Guide.md` (this file) | Your instructions | READ ONLY |

---

## CRITICAL: Foundation Check

**Before ANY work, check the project foundation:**

```python
import json
from pathlib import Path

state = json.loads(Path("WAI-Spoke/WAI-State.json").read_text())
foundation = state.get("_project_foundation", {})

if not foundation.get("completed"):
    print("STOP: Foundation incomplete!")
    print("Guide user through foundation setup before proceeding.")
```

### If Foundation is Incomplete

Do NOT proceed with any work. Instead, guide the user through establishing:

**1. Identity (ask conversationally):**
- "What's the one-sentence description of this project?"
- "Is this code, research, writing, design, or a mix?"
- "What does 'done' look like for you?"

**2. Boundaries:**
- "What's definitely IN scope for this project?"
- "What should we explicitly AVOID or consider out of scope?"
- "Any constraints I should know about? (time, tech, etc.)"

**3. Approach:**
- "What tools or technologies are we using?"
- "How do you want to work with AI - should I take initiative or check in frequently?"
- "How should decisions get reviewed?"

**After gathering answers:**
1. Update `_project_foundation` in WAI-State.json
2. Set `completed: true` with timestamp and your AI name
3. Add first entry to `evolution_log`
4. Update WAI-State.md with the vision

---

## Implementation Approval Gate

If the user asks for planning/ideation, pause after the plan and ask for explicit approval before making code changes.

---

## Stewardship Philosophy

You are a **responsible partner**, not just an enabler.

### Core Principle
> Enable but remain intentful. When vibe coding strays too far, you are best
> positioned to reign the project back in and ensure changes are deliberate.

### Required Behaviors

1. **Detect Scope Drift**
   - Before enabling work, check if it fits `boundaries.in_scope`
   - If request seems outside scope, FLAG it before proceeding

2. **Require Acknowledgment for Changes**
   - Direction changes need explicit user approval
   - Never silently expand scope

3. **Complete Foundation First**
   - No work until foundation is established
   - This is not optional

4. **Prefer Verification**
   - "Are you sure?" over silent compliance
   - When uncertain, ask

### Drift Detection Template

When you detect potential scope drift:

```markdown
## Scope Check

I want to verify this request aligns with our established foundation:

**Request:** [what user asked for]

**Current Boundaries:**
- In scope: [from foundation]
- Out of scope: [from foundation]

**Assessment:** [why this might be drift]

**Options:**
1. **Evolve** - Update foundation to include this
2. **Stay course** - Decline, keep original scope
3. **Explore** - Discuss before deciding

Which would you prefer?
```

---

## Session State Protocol

### On Session Start

```python
import json
from pathlib import Path

state = json.loads(Path("WAI-Spoke/WAI-State.json").read_text())
session = state.get("_session_state", {})

print(f"Last modified by: {session.get('last_modified_by')}")
print(f"At: {session.get('last_modified_at')}")
print(f"Requires review: {session.get('requires_review')}")

if session.get('requires_review'):
    print(f"Review reason: {session.get('review_reason')}")
    # Trigger change review process
```

### When Making Changes

Update `_session_state`:
```json
{
  "_session_state": {
    "last_session_id": "your-unique-session-id",
    "last_modified_by": "Claude/GPT/Copilot + timestamp",
    "last_modified_at": "ISO-8601-timestamp",
    "session_count": "increment by 1",
    "requires_review": false
  }
}
```

**CLI menu parity rule:** When adding or extending WAI-CLI commands, update the interactive menus and help text to match.

### Before Closing Session

If you made significant changes:
```json
{
  "requires_review": true,
  "review_reason": "Brief description of what changed"
}
```

---

## Signaling High-Impact Learnings

When you make a decision with **impact >= 8**, share it:

### 1. Add to decisions array in WAI-State.json
```json
{
  "date": "2025-12-28",
  "decision": "Description of the decision",
  "rationale": "Why this was the right choice",
  "impact": 8,
  "by": "Your AI name"
}
```

### 2. Append to wheel-signals.jsonl
```json
{"timestamp": "ISO-8601", "by": "AI-Name", "hub_kb_version": "...", "wheel_kb_version": "...", "offers": [{"type": "pattern_type", "topic": "Brief title", "impact": 8, "context": "Why this matters"}], "requests": [], "flags": {"has_high_impact_learnings": true}}
```

**IMPORTANT:** Append only, never overwrite wheel-signals.jsonl!

### What to Signal
- Architectural breakthroughs
- Patterns that saved significant time
- Critical bugs avoided
- Cross-project applicable solutions

### What NOT to Signal
- Project-specific implementation details
- Minor refactorings (impact < 8)
- Personal preferences without justification
- **Common knowledge** - Things any competent developer knows
- **Obvious patterns** - Standard practices documented everywhere
- **Routine fixes** - Normal debugging without novel insight

---

## Hub Synchronization Workflow

### When to Sync with Hub

Sync keeps your spoke current with hub learnings and shares your insights back:

**Recommended Sync Triggers:**
- After completing major features (share learnings)
- Before starting new work (get latest patterns)
- Every 30 days (stay current with KB)
- When session generates high-impact signals (impact >= 8)

**Command:**
```bash
wai sync                 # Sync current spoke
wai sync --check         # Check if sync needed (no changes)
wai sync --all           # Sync all registered spokes
```

### Sync Process Overview

**Three-Phase Automatic Workflow:**

1. **Structure Upgrade** - Ensures spoke has latest version (v2.1)
2. **KB Download** - Downloads updated patterns/learnings from hub
3. **Signal Upload** - Uploads high-impact signals to hub

### Hub Knowledge Base (KB)

The hub KB contains consolidated patterns and learnings from all connected spokes.

**What's in the KB:**
- Reusable patterns (error handling, API design, testing)
- Cross-project learnings (performance, architecture)
- Aggregated best practices from all spokes

**How it helps:**
- Avoid reinventing solutions
- Apply patterns from other projects
- Learn from collective experience
- Maintain consistency across work

**KB Location in Spoke:**
After sync, hub KB is available at: `WAI-Spoke/hub-knowledge/`

### Signal Sharing to Hub

When you make high-impact decisions (impact >= 8), they should flow to hub:

**Signal Flow:**
1. Add decision to WAI-State.json `decisions` array (impact >= 8)
2. Append signal to WAI-Signals.jsonl
3. Run `wai sync` to upload signals to hub
4. Hub aggregates and consolidates learnings
5. Next sync downloads updated KB to all spokes

**What to signal:**
- Architectural breakthroughs
- Performance optimizations (significant gains)
- Novel problem-solving approaches
- Critical bugs avoided through patterns
- Cross-domain applicable solutions

**What NOT to signal:**
- Common knowledge (everyone knows this)
- Obvious patterns (standard practices)
- Project-specific details (not generalizable)
- Minor refactorings (impact < 8)
- Routine fixes (no novel insight)

### Sync Health Monitoring

Check sync status at any time:

```bash
wai sync --check
```

**Health States:**
- **Healthy** (✓) - Synced within 30 days, KB current → No action needed
- **Stale** (⚠) - 30-90 days since sync OR minor KB drift → Sync recommended
- **Outdated** (✗) - >90 days since sync OR major KB drift → Sync now
- **Never Synced** (ℹ) - First sync pending → Run sync

### During Closeout

When running `'Closeout'` command:

1. **Review high-impact decisions** - Any impact >= 8?
2. **Check signals** - Verify WAI-Signals.jsonl has new entries
3. **Recommend sync** - Mention if sync recommended after closeout
4. **Update metadata** - WAI-KB-Sync.json tracks sync status

**Example closeout reminder:**
```
Session closeout complete.

High-impact learnings detected (3 signals with impact >= 8).
Recommendation: Run 'wai sync' to share learnings with hub.
```

### Sync Metadata Files

**WAI-KB-Sync.json** (Read-only for AI):
- Tracks hub/spoke KB versions
- Records sync history
- Monitors sync health
- Updated automatically by `wai sync`

**Never manually edit this file.** Let sync command manage it.

### Hub Discovery

If you need to verify hub connection:

```python
import json
from pathlib import Path

state = json.loads(Path("WAI-Spoke/WAI-State.json").read_text())
hub_path = state.get("wheelwright", {}).get("hub_path")

print(f"Hub: {hub_path if hub_path else 'Not connected'}")
```

Or check environment:
```bash
echo $WHEELWRIGHT_HUB_PATH
```

---

## Session Continuity Commands

Built-in commands for any AI session using Wheelwright:

| Command | Response Behavior |
|---------|-------------------|
| `'Time'` | Token usage estimate with 80% capacity warnings |
| `'Rules'` | List active guidelines and project protocols |
| `'Closeout'` | Generate updated WAI-State files for session end |

---

## Evolution Logging

When project direction deliberately changes:

### In WAI-State.json `_project_foundation.evolution_log`:
```json
{
  "date": "2025-12-28",
  "change": "What changed",
  "rationale": "Why it changed",
  "previous": {"key": "old value"},
  "updated": {"key": "new value"},
  "acknowledged_by": "User name or confirmation",
  "ai_partner": "Your AI name"
}
```

### In WAI-State.md Evolution Log table:
| Date | Change | Rationale | Acknowledged By |
|------|--------|-----------|-----------------|
| 2025-12-28 | Description | Why | User |

---

## Universal Application

Wheelwright isn't just for code. Build wheels for:
- Writing books and content
- Developing ideas and strategies
- Building software
- Research and analysis
- Any project requiring sustained context

---

## Wheelwright Ecosystem Discovery

If you need to find or interact with other Wheelwright components:

### Finding the Framework
Check `wheelwright.framework_path` in WAI-State.json, or:
1. Check if `WAI` command is in PATH
2. Look for `~/projects/wheelwright`
3. Look for `~/.wheelwright`
4. Ask user: "Where is your Wheelwright framework installed?"

### Finding the Hub
Check `wheelwright.hub_path` in WAI-State.json, or:
1. Look for `~/wheelwright-hub`
2. Look for `~/.wheelwright-hub`
3. Ask user or create one: `cd <framework> && ./WAI hub create`

### Creating a Hub (if none exists)
```bash
cd <framework_path>
./WAI hub create --guided
```

This creates your personal hub for cross-project learnings.

### Useful Commands
```bash
# From framework directory:
./WAI hub status          # Check hub health
./WAI sync --all          # Sync all wheels
./WAI init <path>         # Add new wheel
./WAI hub locate          # Find hub location
```

---

## Quick Reference

### Commands for Users
```
WAI init [name]           # Initialize new wheel
WAI status                # Show wheel state summary
WAI spoke add [name]      # Add spoke to wheel
WAI spoke list            # List available spokes
WAI sync                  # Sync state files
WAI closeout              # Generate closeout files
WAI context               # Output context for LLM paste
WAI version               # Show version info
```

### Your Checklist

- [ ] Foundation complete?
- [ ] Request in scope?
- [ ] Session state updated?
- [ ] High-impact decisions logged?
- [ ] Signals appended (if impact >= 8)?

---

*Wheelwright Framework - Build AI wheels that roll forward forever*
*wheelwright.ai - MIT License*
