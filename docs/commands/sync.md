# Sync Command - Detailed Reference

**Command:** `wai sync [--all] [--check]`

**Purpose:** Synchronize spoke with hub through comprehensive three-phase workflow: structure upgrade, knowledge base download, and signal upload.

---

## Table of Contents

- [Overview](#overview)
- [Command Flags](#command-flags)
- [Sync Workflow](#sync-workflow)
- [Health Monitoring](#health-monitoring)
- [Common Scenarios](#common-scenarios)
- [Troubleshooting](#troubleshooting)
- [Exit Codes](#exit-codes)
- [Advanced Usage](#advanced-usage)

---

## Overview

The `sync` command orchestrates hub-spoke synchronization to keep your projects current with centralized learnings and contribute their own insights back to the hub.

**What sync does:**
1. Upgrades spoke structure to latest version (if needed)
2. Downloads updated knowledge base from hub
3. Uploads high-impact signals to hub

**When to run sync:**
- After completing major features (to share learnings)
- Before starting new work (to get latest patterns)
- Every 30 days (to stay current)
- When `wai sync --check` recommends it

---

## Command Flags

### No Flags (Default)

**Syntax:**
```bash
wai sync
```

**Behavior:**
- Syncs current spoke with hub
- Performs all three phases (upgrade, download, upload)
- Displays progress and results
- Safe to run multiple times

**Example:**
```bash
cd ~/projects/my-app
wai sync

# Output:
# Checking spoke structure version...
#    ✓ Spoke structure is current (v2.1)
#
#     ✓ Spoke structure ready
#    Hub: /home/user/wheelwright-hub
#    Spoke: my-app
#
#     Checking hub KB...
#    KB update available: v1.0.0 -> v1.2.0
#    Downloading KB updates...
#    ✓ Downloaded 12 patterns, 8 learnings
#    ✓ Synced to v1.2.0
#
#     Scanning signals...
#    ✓ Uploaded 3 high-impact signal(s)
#    ℹ Skipped 2 duplicate(s)
#
#     ✓ Sync complete
```

---

### `--all` Flag

**Syntax:**
```bash
wai sync --all
```

**Behavior:**
- Syncs ALL registered spokes in hub
- Batch operation across multiple projects
- Continues on individual failures
- Updates registry with sync status
- Displays summary at end

**Use Cases:**
- Updating all projects after hub KB update
- Periodic maintenance across workspace
- CI/CD pipeline synchronization
- Team-wide knowledge distribution

**Example:**
```bash
wai sync --all

# Output:
# Loading hub registry...
#    Found 5 registered spoke(s)
#
#     Syncing all spokes with hub...
#    [1/5] project-a: ✓ Synced
#    [2/5] project-b: ✓ Synced
#    [3/5] project-c: ✗ Path not found
#    [4/5] project-d: ✓ Synced
#    [5/5] project-e: ✓ Synced
#
#     Summary: 4 succeeded, 1 failed
#
#     Failed spokes:
#       - project-c: Path not found
```

**Exit Code:**
- 0 if any spoke synced successfully
- 1 if all spokes failed

**Registry Updates:**
Each synced spoke gets registry metadata updated:
- `last_synced_at` - ISO timestamp
- `last_sync_status` - "success" or "failed"

---

### `--check` Flag

**Syntax:**
```bash
wai sync --check
```

**Behavior:**
- Checks sync health WITHOUT performing sync
- Displays status, KB drift, pending signals
- Exits with code 1 if sync recommended
- No modifications to spoke or hub

**Use Cases:**
- CI/CD health checks
- Automated sync scheduling decisions
- Pre-deployment verification
- Monitoring dashboards

**Example:**
```bash
wai sync --check

# Output:
# Checking sync health...
#    Hub: /home/user/wheelwright-hub
#    Spoke: my-project
#
#     Sync Health Report
#    ==================================================
#
#     Status: ⚠ STALE
#    Last sync: 35 days ago
#    KB version drift: 2 minor versions behind
#    Pending signals: 5 ready for upload
#
#    ==================================================
#
#     ⚠ Sync recommended
#    Run 'wai sync' to update KB and upload signals
```

**Exit Codes:**
- 0 - Healthy (no sync needed)
- 1 - Needs sync (stale, outdated, or never synced)

**Health Status Values:**

| Status | Meaning | Exit Code |
|--------|---------|-----------|
| `healthy` | Synced within 30 days, KB current | 0 |
| `stale` | 30-90 days since sync OR minor version drift | 1 |
| `outdated` | >90 days since sync OR major version drift | 1 |
| `never_synced` | Never synced with hub | 1 |

---

## Sync Workflow

### Phase 1: Structure Upgrade

**Purpose:** Ensure spoke has latest structure version before syncing.

**Operations:**
1. Detect current spoke structure version
2. Compare to target version (v2.1)
3. Auto-upgrade if outdated:
   - v1.0 (.WAI/) → v2.1 (WAI-Spoke/)
   - v2.0 (WAI-Spoke/) → v2.1 (adds signals support)
4. Migrate files preserving content
5. Update version metadata

**Supported Migrations:**

| From | To | Changes |
|------|-----|---------|
| v1.0 | v2.1 | Rename .WAI/ → WAI-Spoke/, add signals, update schema |
| v2.0 | v2.1 | Add WAI-Signals.jsonl, update analytics schema |

**Output:**
```
Checking spoke structure version...
   ✓ Spoke structure is current (v2.1)
```

Or if upgrade needed:
```
Checking spoke structure version...
   Detected v2.0 structure - auto-upgrading...
   ✓ Spoke upgraded to v2.1
```

---

### Phase 2: KB Download

**Purpose:** Download updated knowledge base from hub to spoke.

**Workflow:**
1. Check hub KB version (from hub/knowledge/kb-manifest.json)
2. Check spoke KB version (from WAI-Spoke/WAI-KB-Sync.json)
3. Compare versions using semantic versioning
4. If hub version > spoke version:
   - Backup existing spoke KB (to hub-knowledge.backup.[timestamp])
   - Copy hub/knowledge/ → WAI-Spoke/hub-knowledge/
   - Update WAI-KB-Sync.json with new version
   - Count patterns and learnings downloaded

**Version Comparison:**
- Major version drift (1.x.x → 2.x.x) - Critical update
- Minor version drift (1.1.x → 1.2.x) - Recommended update
- Patch version drift (1.1.1 → 1.1.2) - Minor update

**Output:**
```
Checking hub KB...
   KB update available: v1.0.0 -> v1.2.0
   Downloading KB updates...
   ✓ Downloaded 12 patterns, 8 learnings
   ✓ Synced to v1.2.0
```

Or if current:
```
Checking hub KB...
   ✓ KB is current (v1.2.0)
```

**Error Handling:**
- Hub KB not found → Skip KB sync, continue with signals
- Download fails → Rollback to backup, preserve previous version
- Corrupted manifest → Treat as v0.0.0, download full KB

---

### Phase 3: Signal Upload

**Purpose:** Upload high-impact signals from spoke to hub.

**Workflow:**
1. Read WAI-Signals.jsonl
2. Filter signals:
   - Impact >= 8 OR flags.ready_for_hub = true
   - Not already uploaded (no uploaded_to_hub_at field)
3. Calculate content hash for each signal
4. Check for duplicates in hub
5. Upload new signals:
   - Append to hub/signals/by-spoke/[spoke-name]/signals.jsonl
   - Add uploaded_to_hub_at timestamp to spoke signal
6. Update WAI-KB-Sync.json with upload metadata

**Signal Filtering Criteria:**

| Condition | Result |
|-----------|--------|
| impact >= 8 AND not uploaded | Upload |
| flags.ready_for_hub = true AND not uploaded | Upload |
| impact < 8 AND not flagged | Skip |
| already has uploaded_to_hub_at | Skip (already uploaded) |
| duplicate content hash | Skip (deduplicate) |

**Output:**
```
Scanning signals...
   ✓ Uploaded 3 high-impact signal(s)
   ℹ Skipped 2 duplicate(s)
```

Or if none:
```
Scanning signals...
   ℹ No high-impact signals ready for upload
```

**Deduplication:**
Signals are deduplicated by content hash (SHA256) of:
- timestamp
- by (author)
- offers (type, topic, context)

Identical signals across spokes are uploaded only once to hub.

---

## Health Monitoring

### Calculate Sync Health

Sync health is determined by multiple factors:

**Factors:**
1. **Days since last sync** (from WAI-KB-Sync.json last_sync)
2. **KB version drift** (spoke version vs hub version)
3. **Pending signals** (unuploaded high-impact signals)

**Health Status Logic:**

| Condition | Status |
|-----------|--------|
| Never synced | `never_synced` |
| Last sync >90 days OR major version drift | `outdated` |
| Last sync >30 days OR minor version drift | `stale` |
| Last sync ≤30 days AND KB current | `healthy` |

### Health Report Output

```
Sync Health Report
==================================================

    Status: ⚠ STALE
   Last sync: 35 days ago
   KB version drift: 2 minor versions behind
   Pending signals: 5 ready for upload

==================================================

    ⚠ Sync recommended
   Run 'wai sync' to update KB and upload signals
```

**Components:**
- **Status Symbol** - ✓ (healthy), ⚠ (stale), ✗ (outdated), ℹ (never synced)
- **Last Sync** - Days since last sync or "Never"
- **KB Version Drift** - How far behind hub KB (e.g., "2 minor versions behind")
- **Pending Signals** - Count of unuploaded high-impact signals
- **Recommendation** - Action to take based on status

---

## Common Scenarios

### Scenario 1: First Sync After Hub Creation

**Setup:**
- Hub created with `wai hub create`
- Spoke initialized with `wai init`
- Never synced before

**Command:**
```bash
wai sync
```

**Expected Output:**
```
Checking spoke structure version...
   ✓ Spoke structure is current (v2.1)

    ✓ Spoke structure ready
   Hub: /home/user/wheelwright-hub
   Spoke: my-project

    Checking hub KB...
   ⚠ Hub KB not found - skipping KB sync
     (Hub KB directory not found: /home/user/wheelwright-hub/knowledge)

    Scanning signals...
   ℹ No signals found

    ✓ Sync complete
```

**Explanation:** Hub exists but no KB yet (will be created when hub aggregates learnings from multiple spokes).

---

### Scenario 2: Regular Sync with Updates

**Setup:**
- Spoke last synced 45 days ago
- Hub has new KB version (v1.3.0)
- Spoke has 5 new high-impact signals

**Command:**
```bash
wai sync
```

**Expected Output:**
```
Checking spoke structure version...
   ✓ Spoke structure is current (v2.1)

    ✓ Spoke structure ready
   Hub: /home/user/wheelwright-hub
   Spoke: my-project

    Checking hub KB...
   KB update available: v1.2.0 -> v1.3.0
   Downloading KB updates...
   ✓ Downloaded 8 patterns, 5 learnings
   ✓ Synced to v1.3.0

    Scanning signals...
   ✓ Uploaded 5 high-impact signal(s)

    ✓ Sync complete
```

**Result:** Spoke receives latest patterns and shares its learnings.

---

### Scenario 3: Batch Sync All Spokes

**Setup:**
- Hub has 10 registered spokes
- 2 spokes moved to different paths
- 8 spokes need KB updates

**Command:**
```bash
wai sync --all
```

**Expected Output:**
```
Loading hub registry...
   Found 10 registered spoke(s)

    Syncing all spokes with hub...
   [1/10] project-a: ✓ Synced
   [2/10] project-b: ✗ Path not found
   [3/10] project-c: ✓ Synced
   [4/10] project-d: ✓ Synced
   [5/10] project-e: ✗ Path not found
   [6/10] project-f: ✓ Synced
   [7/10] project-g: ✓ Synced
   [8/10] project-h: ✓ Synced
   [9/10] project-i: ✓ Synced
   [10/10] project-j: ✓ Synced

    Summary: 8 succeeded, 2 failed

    Failed spokes:
      - project-b: Path not found
      - project-e: Path not found
```

**Next Steps:** Remove or update registry entries for moved projects.

---

### Scenario 4: Health Check in CI/CD

**Setup:**
- Automated CI/CD pipeline
- Check if sync needed before deployment

**Command:**
```bash
wai sync --check
```

**Expected Output (healthy):**
```
Checking sync health...
   Hub: /home/user/wheelwright-hub
   Spoke: my-project

    Sync Health Report
   ==================================================

    Status: ✓ HEALTHY
   Last sync: 5 days ago
   KB version: Up to date
   Pending signals: None

   ==================================================

    ✓ Spoke is synchronized with hub
   No sync needed at this time
```

**Exit Code:** 0 (CI passes)

**Expected Output (needs sync):**
```
Checking sync health...
   Hub: /home/user/wheelwright-hub
   Spoke: my-project

    Sync Health Report
   ==================================================

    Status: ⚠ STALE
   Last sync: 35 days ago
   KB version drift: 1 minor version behind
   Pending signals: 3 ready for upload

   ==================================================

    ⚠ Sync recommended
   Run 'wai sync' to update KB and upload signals
```

**Exit Code:** 1 (CI triggers sync job)

---

### Scenario 5: Legacy Spoke Upgrade

**Setup:**
- Spoke created with old framework (v1.0)
- Uses .WAI/ directory structure
- Never synced with hub

**Command:**
```bash
wai sync
```

**Expected Output:**
```
Checking spoke structure version...
   Detected v1.0 structure (.WAI/) - auto-upgrading...
   Migrating .WAI/ to WAI-Spoke/...
   ✓ Spoke upgraded to v2.1

    ✓ Spoke structure ready
   Hub: /home/user/wheelwright-hub
   Spoke: legacy-project

    Checking hub KB...
   KB update available: v0.0.0 -> v1.3.0
   Downloading KB updates...
   ✓ Downloaded 15 patterns, 12 learnings
   ✓ Synced to v1.3.0

    Scanning signals...
   ℹ No signals found

    ✓ Sync complete
```

**Result:** Legacy spoke upgraded and synced in one command.

---

## Troubleshooting

### Issue: "No hub found"

**Symptom:**
```
No hub found - cannot check sync health
```

**Causes:**
1. Hub not created yet
2. Hub path not discoverable
3. No registered connection between spoke and hub

**Solutions:**

**Create hub:**
```bash
wai hub create ~/wheelwright-hub
```

**Set environment variable:**
```bash
export WHEELWRIGHT_HUB_PATH=~/wheelwright-hub
wai sync
```

**Register spoke with hub:**
```bash
wai projects add
```

---

### Issue: "Hub KB not found"

**Symptom:**
```
⚠ Hub KB not found - skipping KB sync
  (Hub KB directory not found: /path/to/hub/knowledge)
```

**Causes:**
1. Hub created but no KB aggregated yet
2. KB directory deleted or moved

**Solutions:**

**Normal behavior for new hubs:**
- KB is created when hub first aggregates learnings from spokes
- Not an error, just informational
- Spoke sync continues with structure upgrade and signal upload

**If KB should exist but missing:**
```bash
# Manually create KB directory
mkdir -p ~/wheelwright-hub/knowledge

# Create initial manifest
cat > ~/wheelwright-hub/knowledge/kb-manifest.json << 'EOF'
{
  "version": "0.1.0",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

---

### Issue: "KB sync failed"

**Symptom:**
```
✗ KB sync failed: [Errno 13] Permission denied
  Previous KB version preserved
```

**Causes:**
1. Permission errors on hub/knowledge/ directory
2. Disk space issues
3. Corrupted hub KB files

**Solutions:**

**Fix permissions:**
```bash
chmod -R u+rw ~/wheelwright-hub/knowledge/
wai sync
```

**Check disk space:**
```bash
df -h ~/wheelwright-hub
```

**Restore from backup if corrupted:**
```bash
# Backups are in spoke/WAI-Spoke/hub-knowledge.backup.[timestamp]
cd ~/projects/my-project/WAI-Spoke
ls -la hub-knowledge.backup.*

# Restore latest backup to hub
latest=$(ls -t hub-knowledge.backup.* | head -1)
cp -r "$latest"/* ~/wheelwright-hub/knowledge/
```

---

### Issue: "No spoke structure found"

**Symptom:**
```
✗ No valid spoke structure found
Run 'WAI init' to initialize this project
```

**Causes:**
1. Running sync in non-Wheelwright project
2. WAI-Spoke/ directory deleted or moved

**Solutions:**

**Initialize spoke:**
```bash
wai init
wai sync
```

**Restore from git:**
```bash
git checkout WAI-Spoke/
wai sync
```

---

### Issue: Signals not uploading

**Symptom:**
```
Scanning signals...
   ℹ No high-impact signals ready for upload
```

**But you expect signals to upload.**

**Causes:**
1. Signals have impact < 8
2. Signals already uploaded (have uploaded_to_hub_at field)
3. Signals not marked ready_for_hub

**Diagnostics:**

**Check signals file:**
```bash
cat WAI-Spoke/WAI-Signals.jsonl
```

**Look for:**
- `"impact": 8` or higher
- `"flags": {"ready_for_hub": true}`
- No `"uploaded_to_hub_at"` field

**Solution:**

**Increase signal impact or flag for upload:**
```json
{
  "timestamp": "2025-01-21T10:00:00Z",
  "by": "Claude Sonnet 4.5",
  "offers": [{
    "type": "pattern",
    "topic": "Error handling",
    "impact": 9,
    "context": "Novel approach to error recovery"
  }],
  "flags": {
    "ready_for_hub": true,
    "has_high_impact_learnings": true
  }
}
```

---

### Issue: Duplicate signals skipped

**Symptom:**
```
Scanning signals...
   ✓ Uploaded 2 high-impact signal(s)
   ℹ Skipped 5 duplicate(s)
```

**Causes:**
1. Same signals exist in hub (from this or another spoke)
2. Content hash collision (rare)

**Explanation:**
This is **normal behavior**. Hub deduplicates signals by content hash to avoid storing identical learnings multiple times.

**Content Hash Includes:**
- Signal timestamp
- Signal author (by)
- Offers content (type, topic, context)

**If signals seem unique but still skipped:**
- Check hub/signals/by-spoke/[spoke-name]/signals.jsonl
- Compare content hashes
- Ensure signals have distinct topics or contexts

---

### Issue: Batch sync fails for all spokes

**Symptom:**
```
Summary: 0 succeeded, 10 failed

Failed spokes:
  - project-a: No spoke structure found
  - project-b: No spoke structure found
  ...
```

**Causes:**
1. Registry paths outdated (projects moved)
2. Registry corrupted
3. Permissions issues

**Solutions:**

**Rescan and re-register projects:**
```bash
# From directory containing projects
wai projects add --scan .

# Or manually remove outdated entries
# Edit ~/wheelwright-hub/registry/wheel-projects.json
```

**Verify registry:**
```bash
wai projects list
```

---

## Exit Codes

| Code | Condition | Description |
|------|-----------|-------------|
| 0 | Success | Sync completed successfully OR health check shows healthy |
| 1 | Needs sync / Failed | Health check shows sync needed OR sync operation failed |
| 130 | Cancelled | User cancelled with Ctrl+C |

**Examples:**

```bash
# Success
wai sync
echo $?  # 0

# Health check - healthy
wai sync --check
echo $?  # 0

# Health check - needs sync
wai sync --check
echo $?  # 1

# Sync failed
wai sync
echo $?  # 1
```

**CI/CD Usage:**
```bash
# Check health, exit 1 if sync needed
wai sync --check || {
  echo "Sync needed, running sync..."
  wai sync || exit 1
}
```

---

## Advanced Usage

### Automated Sync Scheduling

**Cron job (daily check, sync if needed):**
```bash
# Add to crontab
0 9 * * * cd ~/projects/my-app && wai sync --check || wai sync
```

**Git hook (post-merge sync):**
```bash
# .git/hooks/post-merge
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
wai sync --check || wai sync
```

---

### Conditional Sync in Scripts

**Check health first, sync only if needed:**
```bash
#!/bin/bash

if ! wai sync --check; then
  echo "Sync recommended, syncing now..."
  wai sync
else
  echo "Spoke is healthy, no sync needed"
fi
```

---

### Multi-Hub Scenarios

**Different projects with different hubs:**
```bash
# Project A uses hub-personal
export WHEELWRIGHT_HUB_PATH=~/wheelwright-hub-personal
cd ~/projects/personal-project
wai sync

# Project B uses hub-work
export WHEELWRIGHT_HUB_PATH=~/wheelwright-hub-work
cd ~/projects/work-project
wai sync
```

---

### Sync Metadata Inspection

**View sync history:**
```bash
# WAI-KB-Sync.json contains sync history
cat WAI-Spoke/WAI-KB-Sync.json | jq '.sync_history[-5:]'

# Output shows last 5 syncs:
# [
#   {
#     "timestamp": "2025-01-15T10:30:00Z",
#     "type": "download",
#     "hub_version": "1.2.0",
#     "spoke_version": "1.2.0"
#   },
#   ...
# ]
```

**Check uploaded signals:**
```bash
# Signals with uploaded_to_hub_at timestamp
grep uploaded_to_hub_at WAI-Spoke/WAI-Signals.jsonl
```

---

## Best Practices

1. **Sync regularly** - Every 30 days minimum to stay current
2. **Check before sync** - Use `--check` to see what will change
3. **Sync after milestones** - Share learnings when features complete
4. **Monitor health** - Integrate `--check` into CI/CD pipelines
5. **Batch sync wisely** - Use `--all` during off-hours for large workspaces
6. **Review signals** - Ensure high-impact signals have impact >= 8
7. **Keep hub accessible** - Use `$WHEELWRIGHT_HUB_PATH` for consistent discovery

---

## Related Commands

- `wai hub create` - Create hub for synchronization
- `wai projects add` - Register spokes with hub
- `wai closeout` - Process sessions and prepare signals
- `wai absorbe` - Migrate legacy structures before sync
- `wai status` - Check spoke and hub connection status

---

## See Also

- [CLI Reference](../CLI_REFERENCE.md) - Complete command reference
- [Hub Synchronization](../../README.md#hub-synchronization) - Overview and benefits
- [WAI-Guide.md](../../templates/WAI/WAI-Guide.md) - AI instructions for sync workflow

---

**End of Sync Command Reference**

For questions or issues, see [GitHub Issues](https://github.com/wheelwright-ai/framework/issues)
