"""
Sync Command

Synchronize spoke with hub (upgrade structure, download KB, upload signals).
"""

from pathlib import Path
from ..upgrader import SpokeUpgrader
from ..hub import HubManager
from ..sync_manager import SyncManager


SPOKE_STRUCTURE_VERSION = "2.1"


def sync_spoke(all_spokes: bool = False, check_only: bool = False) -> None:
    """
    Sync spoke(s) with hub.

    Workflow:
    1. Auto-upgrade spoke structure if needed
    2. Download KB updates from hub
    3. Upload high-impact signals to hub

    Args:
        all_spokes: Sync all registered spokes
        check_only: Check sync health without performing sync
    """
    # Find hub
    hub_manager = HubManager()
    hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

    if not hub_path:
        if check_only:
            print(f"\n    No hub found - cannot check sync health")
            return
        print(f"\n    No hub found - upgrade operates on current project only")

    if all_spokes:
        if not hub_path:
            print(f"\n    ✗ Cannot sync all spokes: No hub found")
            print(f"   Run this command from a hub-connected project or use 'WAI hub discover'")
            return

        _sync_all_spokes(hub_path)
        return

    # Sync current spoke
    project_path = Path('.').resolve()

    # Check only mode - display sync health and exit
    if check_only:
        _check_sync_health(hub_path, project_path)
        return

    # Auto-upgrade spoke structure if needed
    print(f"\n    Checking spoke structure version...")
    version = SpokeUpgrader.detect_version(project_path)

    if version == 'unknown':
        print(f"   ✗ No valid spoke structure found")
        print(f"   Run 'WAI init' to initialize this project")
        return
    elif version == '1.0':
        print(f"   Detected v1.0 structure (.WAI/) - auto-upgrading...")
        if SpokeUpgrader.upgrade_spoke(project_path, version, verbose=True):
            print(f"   ✓ Spoke upgraded to v{SPOKE_STRUCTURE_VERSION}")
        else:
            print(f"   ✗ Upgrade failed - cannot proceed with sync")
            return
    else:
        print(f"   ✓ Spoke structure is current (v{version})")

    wai_dir = project_path / 'WAI-Spoke'

    print(f"\n    ✓ Spoke structure ready")

    # Phase 2: KB Sync (Download)
    if hub_path:
        print(f"   Hub: {hub_path}")
        print(f"   Spoke: {project_path.name}")
        print(f"\n    Checking hub KB...")

        try:
            sync_manager = SyncManager(hub_path, project_path)
            needs_update, hub_version, spoke_version = sync_manager.check_kb_version_mismatch()

            if needs_update:
                print(f"   KB update available: v{spoke_version} -> v{hub_version}")
                print(f"   Downloading KB updates...")

                result = sync_manager.download_kb_updates()

                print(f"   ✓ Downloaded {result['patterns_downloaded']} patterns, {result['learnings_downloaded']} learnings")
                print(f"   ✓ Synced to v{result['hub_version']}")
            else:
                print(f"   ✓ KB is current (v{spoke_version})")

        except FileNotFoundError as e:
            print(f"   ⚠ Hub KB not found - skipping KB sync")
            print(f"     ({e})")
        except IOError as e:
            print(f"   ✗ KB sync failed: {e}")
            print(f"     Previous KB version preserved")
        except Exception as e:
            print(f"   ⚠ KB sync error: {e}")
    else:
        print(f"   No hub found - KB sync skipped")
        print(f"   Spoke: {project_path.name}")

    # Phase 3: Signal Upload
    if hub_path:
        print(f"\n    Scanning signals...")

        try:
            if 'sync_manager' not in locals():
                sync_manager = SyncManager(hub_path, project_path)

            signal_result = sync_manager.upload_signals()

            if signal_result['signals_total'] == 0:
                print(f"   ℹ No signals found")
            elif signal_result['signals_uploaded'] == 0:
                if signal_result['duplicates_skipped'] > 0:
                    print(f"   ℹ All {signal_result['signals_total']} signal(s) already uploaded")
                else:
                    print(f"   ℹ No high-impact signals ready for upload")
            else:
                print(f"   ✓ Uploaded {signal_result['signals_uploaded']} high-impact signal(s)")
                if signal_result['duplicates_skipped'] > 0:
                    print(f"   ℹ Skipped {signal_result['duplicates_skipped']} duplicate(s)")

        except IOError as e:
            print(f"   ✗ Signal upload failed: {e}")
        except Exception as e:
            print(f"   ⚠ Signal upload error: {e}")

    print(f"\n    ✓ Sync complete")


def _sync_all_spokes(hub_path: Path) -> None:
    """
    Sync all registered spokes with hub.

    Args:
        hub_path: Path to hub directory
    """
    from ..utils.registry import load_registry, update_project
    from ..utils.exceptions import RegistryError
    from datetime import datetime, timezone

    print(f"\n    Loading hub registry...")

    # Load registry
    try:
        registry = load_registry(hub_path)
    except RegistryError as e:
        print(f"   ✗ Failed to load registry: {e}")
        return

    projects = registry.get('projects', [])

    if not projects:
        print(f"   ℹ No spokes registered in hub")
        print(f"   Use 'WAI group add-spoke' to register projects")
        return

    print(f"   Found {len(projects)} registered spoke(s)")
    print(f"\n    Syncing all spokes with hub...")

    success_count = 0
    failed_count = 0
    failed_spokes = []

    for i, project in enumerate(projects, 1):
        project_path_str = project.get('path')
        project_name = project.get('name', 'unknown')

        if not project_path_str:
            print(f"   [{i}/{len(projects)}] {project_name}: ✗ Invalid project entry (no path)")
            failed_count += 1
            failed_spokes.append((project_name, "Invalid project entry"))
            continue

        project_path = Path(project_path_str)

        if not project_path.exists():
            print(f"   [{i}/{len(projects)}] {project_name}: ✗ Path not found")
            failed_count += 1
            failed_spokes.append((project_name, "Path not found"))
            continue

        # Sync this spoke
        print(f"   [{i}/{len(projects)}] {project_name}: ", end='', flush=True)

        try:
            result = _sync_single_spoke(hub_path, project_path)

            if result['success']:
                print(f"✓ Synced")
                success_count += 1

                # Update registry with sync timestamp
                try:
                    update_project(
                        hub_path,
                        project_name,
                        last_synced_at=datetime.now(timezone.utc).isoformat(),
                        last_sync_status='success'
                    )
                except Exception:
                    # Don't fail if registry update fails
                    pass

            else:
                print(f"✗ {result['error']}")
                failed_count += 1
                failed_spokes.append((project_name, result['error']))

                # Update registry with failure status
                try:
                    update_project(
                        hub_path,
                        project_name,
                        last_synced_at=datetime.now(timezone.utc).isoformat(),
                        last_sync_status='failed'
                    )
                except Exception:
                    pass

        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            failed_count += 1
            failed_spokes.append((project_name, f"Unexpected error: {e}"))

    # Print summary
    print(f"\n    Summary: {success_count} succeeded, {failed_count} failed")

    if failed_spokes:
        print(f"\n    Failed spokes:")
        for name, error in failed_spokes:
            print(f"      - {name}: {error}")


def _sync_single_spoke(hub_path: Path, spoke_path: Path) -> dict:
    """
    Sync a single spoke with hub.

    Returns dict with 'success' (bool) and 'error' (str if failed).

    Args:
        hub_path: Path to hub directory
        spoke_path: Path to spoke project

    Returns:
        Dict with keys:
            - success: bool
            - error: str (if success is False)
    """
    # Auto-upgrade spoke structure if needed
    version = SpokeUpgrader.detect_version(spoke_path)

    if version == 'unknown':
        return {
            'success': False,
            'error': 'No spoke structure found'
        }
    elif version == '1.0':
        # Auto-upgrade
        if not SpokeUpgrader.upgrade_spoke(spoke_path, version, verbose=False):
            return {
                'success': False,
                'error': 'Upgrade failed'
            }

    wai_dir = spoke_path / 'WAI-Spoke'

    if not wai_dir.exists():
        return {
            'success': False,
            'error': 'WAI-Spoke directory not found'
        }

    # Phase 2: KB Sync (Download)
    try:
        sync_manager = SyncManager(hub_path, spoke_path)
        needs_update, hub_version, spoke_version = sync_manager.check_kb_version_mismatch()

        if needs_update:
            try:
                sync_manager.download_kb_updates()
            except FileNotFoundError:
                # Hub KB not found - not a critical error for batch sync
                pass
            except IOError as e:
                return {
                    'success': False,
                    'error': f'KB sync failed: {e}'
                }

    except Exception as e:
        return {
            'success': False,
            'error': f'KB check failed: {e}'
        }

    # Phase 3: Signal Upload
    try:
        signal_result = sync_manager.upload_signals()
        # Signal upload is informational - don't fail on errors
    except Exception:
        # Continue even if signal upload fails
        pass

    return {'success': True}


def _check_sync_health(hub_path: Path, spoke_path: Path) -> None:
    """
    Check and display sync health without performing sync.

    Args:
        hub_path: Path to hub directory
        spoke_path: Path to spoke project

    Exit codes:
        0: Healthy
        1: Needs sync (stale, outdated, or never synced)
    """
    import sys

    print(f"\n    Checking sync health...")
    print(f"   Hub: {hub_path}")
    print(f"   Spoke: {spoke_path.name}")

    wai_dir = spoke_path / 'WAI-Spoke'

    if not wai_dir.exists():
        print(f"\n    ✗ No spoke structure found")
        print(f"   Run 'WAI init' to initialize this project")
        sys.exit(1)

    try:
        sync_manager = SyncManager(hub_path, spoke_path)
        health = sync_manager.calculate_sync_health()

        print(f"\n    Sync Health Report")
        print(f"   " + "=" * 50)

        # Status with appropriate symbol
        status_symbol = {
            'healthy': '✓',
            'stale': '⚠',
            'outdated': '✗',
            'never_synced': 'ℹ'
        }.get(health['status'], '?')

        print(f"\n    Status: {status_symbol} {health['status'].upper()}")

        # Days since last sync
        if health['days_since_last_sync'] is not None:
            print(f"   Last sync: {health['days_since_last_sync']} days ago")
        else:
            print(f"   Last sync: Never")

        # KB version drift
        if health['kb_version_drift']:
            print(f"   KB version drift: {health['kb_version_drift']}")
        else:
            print(f"   KB version: Up to date")

        # Pending signals
        if health['pending_signals'] > 0:
            print(f"   Pending signals: {health['pending_signals']} ready for upload")
        else:
            print(f"   Pending signals: None")

        print(f"\n   " + "=" * 50)

        # Recommendation
        if health['status'] == 'healthy':
            print(f"\n    ✓ Spoke is synchronized with hub")
            print(f"   No sync needed at this time")
            sys.exit(0)
        elif health['status'] == 'stale':
            print(f"\n    ⚠ Sync recommended")
            print(f"   Run 'WAI sync' to update KB and upload signals")
            sys.exit(1)
        elif health['status'] == 'outdated':
            print(f"\n    ✗ Sync strongly recommended")
            print(f"   Spoke is significantly behind hub")
            print(f"   Run 'WAI sync' to update KB and upload signals")
            sys.exit(1)
        elif health['status'] == 'never_synced':
            print(f"\n    ℹ First sync needed")
            print(f"   Run 'WAI sync' to synchronize with hub")
            sys.exit(1)

    except Exception as e:
        print(f"\n    ✗ Failed to check sync health: {e}")
        sys.exit(1)
