# Changelog

All notable changes to the Wheelwright Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added - Hub Synchronization

#### New Sync Command Features
- **Hub KB Synchronization** - Download knowledge base updates from hub to spoke
  - Semantic version tracking (hub vs spoke KB versions)
  - Automatic backup before KB replacement
  - Pattern and learning download counts
  - Rollback on download failure

- **Signal Upload to Hub** - Share high-impact learnings with hub
  - Automatic filtering (impact >= 8 or ready_for_hub flag)
  - Content hash deduplication across spokes
  - Upload tracking with `uploaded_to_hub_at` timestamps
  - Spoke-specific signal organization in hub

- **Multi-Spoke Batch Sync** - `--all` flag for hub-wide synchronization
  - Sync all registered spokes in one command
  - Continue on individual failures with summary report
  - Registry updates with sync status and timestamps
  - Failed spoke reporting with error details

- **Sync Health Monitoring** - `--check` flag for health assessment
  - Health status calculation (healthy, stale, outdated, never_synced)
  - Days since last sync tracking
  - KB version drift detection (major/minor/patch)
  - Pending signals count
  - Exit codes for CI/CD integration (0=healthy, 1=needs sync)

#### SyncManager Class
- New `SyncManager` class in `wai_cli/sync_manager.py`
  - `check_kb_version_mismatch()` - Compare hub vs spoke KB versions
  - `download_kb_updates()` - Download and install hub KB updates
  - `upload_signals()` - Upload high-impact signals to hub
  - `calculate_sync_health()` - Comprehensive health metrics
  - `update_kb_sync_metadata()` - Track sync history
  - Private helper methods with full documentation

#### WAI-KB-Sync.json File
- New sync metadata file in WAI-Spoke directory
  - Hub KB version tracking
  - Spoke KB version tracking
  - Sync history (last 50 entries)
  - Sync status indicators
  - Read-only for AI assistants

#### Documentation
- **CLI Reference Updates** - Comprehensive sync command documentation
  - All flags documented (--all, --check)
  - Detailed examples for each scenario
  - Health status indicators table
  - Error handling reference
  - Exit codes documentation

- **New Sync Command Guide** - `docs/commands/sync.md` created
  - Detailed workflow explanations (3 phases)
  - Common scenarios with expected outputs
  - Comprehensive troubleshooting guide
  - Advanced usage patterns
  - Best practices section

- **README Hub Synchronization Section** - Overview and benefits
  - Knowledge base concept explained
  - Signal sharing guidelines
  - Sync workflow documentation
  - Health monitoring overview
  - Troubleshooting quick reference

- **WAI-Guide.md Updates** - AI instructions for hub sync
  - Sync trigger recommendations
  - Signal sharing criteria
  - Health state explanations
  - Closeout integration
  - Hub discovery methods

### Changed

#### Sync Command Enhancement
- Enhanced `wai sync` command from structure-only to full hub sync
  - Phase 1: Structure upgrade (existing functionality)
  - Phase 2: KB download (new)
  - Phase 3: Signal upload (new)

#### Signal Processing
- WAI-Signals.jsonl now supports upload tracking
  - `uploaded_to_hub_at` field added on upload
  - Content hash-based deduplication
  - Ready-for-hub flag support

#### Hub Directory Structure
- Hub now includes knowledge and signals directories:
  ```
  hub/
  ├── knowledge/           # Consolidated KB
  │   └── kb-manifest.json # Version tracking
  └── signals/             # Collected signals
      └── by-spoke/        # Per-spoke organization
  ```

### Technical Details

#### Version Comparison
- Semantic version comparison for KB version drift detection
- Supports major, minor, and patch version comparisons
- Graceful handling of malformed version strings

#### Deduplication Strategy
- Content hashing using SHA256
- Hash includes: timestamp, author, offers (type/topic/context)
- Prevents duplicate signals across spokes

#### Error Handling
- Automatic rollback on KB download failure
- Backup preservation before KB replacement
- Graceful degradation (continues if KB missing)
- Batch sync continues on individual failures

#### Exit Codes
- Standard exit code conventions (0=success, 1=failure)
- Health check mode uses exit codes for CI/CD integration
- User cancellation (Ctrl+C) returns exit code 130

### Compatibility

- Backward compatible with existing spokes (auto-upgrades structure)
- Works with v1.0 (.WAI/), v2.0, and v2.1 (WAI-Spoke/) structures
- No breaking changes to existing commands or workflows
- WAI-KB-Sync.json created automatically if missing

### Performance

- Efficient signal deduplication with hash-based lookup
- Batch sync parallelizes operations per spoke
- Sync history limited to last 50 entries (prevents bloat)
- Incremental KB updates (only downloads when needed)

---

## [2.0.1] - Previous Release

See git history for previous changes.

---

[Unreleased]: https://github.com/wheelwright-ai/framework/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/wheelwright-ai/framework/releases/tag/v2.0.1
