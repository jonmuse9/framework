"""
Sync Command

Synchronize spoke with hub (upgrade structure, download KB, upload signals).
"""

from pathlib import Path
from ..upgrader import SpokeUpgrader
from ..hub import HubManager
from ..sync_manager import SyncManager


SPOKE_STRUCTURE_VERSION = "2.1"


def sync_spoke(all_spokes: bool = False) -> None:
    """
    Sync spoke(s) with hub.

    Workflow:
    1. Auto-upgrade spoke structure if needed
    2. Download KB updates from hub
    3. Upload high-impact signals to hub

    Args:
        all_spokes: Sync all registered spokes (not yet implemented)
    """
    # Find hub
    hub_manager = HubManager()
    hub_path = hub_manager.auto_discover_hub(Path.cwd(), verbose=False)

    if not hub_path:
        print(f"\n    No hub found - upgrade operates on current project only")

    if all_spokes:
        print(f"\n    Upgrading all spokes...")
        print(f"   Feature coming soon")
        return

    # Sync current spoke
    project_path = Path('.').resolve()

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
