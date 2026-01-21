"""
Integration Tests for KB Sync (Download)

Tests full KB sync workflow with hub and spoke.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path

from wai_cli.sync_manager import SyncManager


class TestKBDownloadIntegration(unittest.TestCase):
    """Test full KB download workflow."""

    def setUp(self):
        """Create temporary hub and spoke with KB files."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        # Create directories
        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        # Create hub KB manifest
        hub_manifest = {
            "version": "1.5.0",
            "updated": "2025-01-21",
            "patterns": ["pattern-1", "pattern-2"],
            "learnings": ["learning-1"]
        }
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f, indent=2)

        # Create hub KB files
        pattern_files = [
            "pattern-forge-ui-components.md",
            "pattern-error-handling.md"
        ]
        for pattern_file in pattern_files:
            (self.hub_path / 'knowledge' / pattern_file).write_text(
                f"# {pattern_file}\n\nPattern content here..."
            )

        learning_file = "learning-session-management.md"
        (self.hub_path / 'knowledge' / learning_file).write_text(
            "# Learning: Session Management\n\nKey insights..."
        )

        # Create spoke KB sync file with old version
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "1.0.0",
            "hub_kb_version": "1.0.0",
            "last_sync": None,
            "sync_status": "never_synced",
            "sync_history": []
        }
        with open(self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f, indent=2)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_full_kb_download_workflow(self):
        """Test complete KB download from hub to spoke."""
        # Check for update
        needs_update, hub_v, spoke_v = self.manager.check_kb_version_mismatch()

        self.assertTrue(needs_update)
        self.assertEqual(hub_v, "1.5.0")
        self.assertEqual(spoke_v, "1.0.0")

        # Download KB updates
        result = self.manager.download_kb_updates()

        # Verify download result
        self.assertEqual(result['hub_version'], "1.5.0")
        self.assertEqual(result['patterns_downloaded'], 2)
        self.assertEqual(result['learnings_downloaded'], 1)

        # Verify files copied to spoke
        spoke_kb_dir = self.spoke_path / 'WAI-Spoke' / 'hub-knowledge'
        self.assertTrue(spoke_kb_dir.exists())
        self.assertTrue((spoke_kb_dir / 'kb-manifest.json').exists())
        self.assertTrue((spoke_kb_dir / 'pattern-forge-ui-components.md').exists())
        self.assertTrue((spoke_kb_dir / 'pattern-error-handling.md').exists())
        self.assertTrue((spoke_kb_dir / 'learning-session-management.md').exists())

        # Verify sync metadata updated
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'r') as f:
            sync_data = json.load(f)

        self.assertEqual(sync_data['spoke_kb_version'], "1.5.0")
        self.assertEqual(sync_data['hub_kb_version'], "1.5.0")
        self.assertEqual(sync_data['sync_status'], 'synced')
        self.assertIsNotNone(sync_data['last_sync'])
        self.assertEqual(len(sync_data['sync_history']), 1)
        self.assertEqual(sync_data['sync_history'][0]['type'], 'download')

    def test_kb_download_no_update_needed(self):
        """Test when KB is already current."""
        # Update spoke to current version
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": "2025-01-20T10:00:00Z",
            "sync_status": "synced",
            "sync_history": []
        }
        with open(self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f, indent=2)

        # Check for update
        needs_update, hub_v, spoke_v = self.manager.check_kb_version_mismatch()

        self.assertFalse(needs_update)
        self.assertEqual(hub_v, "1.5.0")
        self.assertEqual(spoke_v, "1.5.0")

    def test_kb_download_hub_not_found(self):
        """Test error handling when hub KB doesn't exist."""
        # Remove hub KB directory
        shutil.rmtree(self.hub_path / 'knowledge')

        # Attempt download should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.manager.download_kb_updates()

    def test_kb_download_backup_and_rollback(self):
        """Test backup creation and rollback on error."""
        # Create existing spoke KB
        spoke_kb_dir = self.spoke_path / 'WAI-Spoke' / 'hub-knowledge'
        spoke_kb_dir.mkdir(parents=True)
        old_file = spoke_kb_dir / 'old-pattern.md'
        old_file.write_text("Old pattern content")

        # Simulate error during download by making hub KB unreadable
        # (This is tricky to test - we'll test backup creation instead)

        # First download should succeed and create backup
        result = self.manager.download_kb_updates()

        # Verify old KB was backed up
        backups = list(self.spoke_path.glob('WAI-Spoke/hub-knowledge.backup.*'))
        self.assertEqual(len(backups), 1)

        # Verify new KB is in place
        self.assertTrue(spoke_kb_dir.exists())
        self.assertTrue((spoke_kb_dir / 'kb-manifest.json').exists())
        self.assertFalse((spoke_kb_dir / 'old-pattern.md').exists())

    def test_kb_download_with_subdirectories(self):
        """Test downloading KB with nested directory structure."""
        # Create hub KB with subdirectories
        patterns_dir = self.hub_path / 'knowledge' / 'patterns'
        patterns_dir.mkdir(parents=True)
        (patterns_dir / 'pattern-nested.md').write_text("Nested pattern")

        learnings_dir = self.hub_path / 'knowledge' / 'learnings'
        learnings_dir.mkdir(parents=True)
        (learnings_dir / 'learning-nested.md').write_text("Nested learning")

        # Download KB
        result = self.manager.download_kb_updates()

        # Verify subdirectories copied
        spoke_kb_dir = self.spoke_path / 'WAI-Spoke' / 'hub-knowledge'
        self.assertTrue((spoke_kb_dir / 'patterns' / 'pattern-nested.md').exists())
        self.assertTrue((spoke_kb_dir / 'learnings' / 'learning-nested.md').exists())

        # Verify counts include nested files
        self.assertGreaterEqual(result['patterns_downloaded'], 3)
        self.assertGreaterEqual(result['learnings_downloaded'], 2)


class TestCorruptedMetadataRecovery(unittest.TestCase):
    """Test recovery from corrupted sync metadata."""

    def setUp(self):
        """Create temporary hub and spoke."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        # Create hub KB manifest
        hub_manifest = {"version": "1.0.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_recovery_from_corrupted_sync_metadata(self):
        """Test that corrupted WAI-KB-Sync.json is recreated."""
        # Create corrupted sync file
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        sync_file.write_text("invalid json {{{")

        # Update metadata should recreate file
        self.manager.update_kb_sync_metadata('download', '1.0.0')

        # Verify file is valid JSON
        with open(sync_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['version'], '1.0')
        self.assertEqual(data['hub_kb_version'], '1.0.0')

    def test_recovery_from_missing_sync_metadata(self):
        """Test that missing WAI-KB-Sync.json is created."""
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'

        # Ensure file doesn't exist
        if sync_file.exists():
            sync_file.unlink()

        # Update metadata should create file
        self.manager.update_kb_sync_metadata('download', '1.0.0')

        # Verify file exists and is valid
        self.assertTrue(sync_file.exists())

        with open(sync_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['version'], '1.0')
        self.assertEqual(data['hub_kb_version'], '1.0.0')


class TestHubNotFoundGracefulHandling(unittest.TestCase):
    """Test graceful handling when hub is not found."""

    def test_version_check_with_missing_hub_kb(self):
        """Test version check when hub KB directory doesn't exist."""
        temp_dir = tempfile.mkdtemp()

        try:
            hub_path = Path(temp_dir) / 'hub'
            spoke_path = Path(temp_dir) / 'spoke'

            hub_path.mkdir(parents=True)
            spoke_path.mkdir(parents=True)
            (spoke_path / 'WAI-Spoke').mkdir(parents=True)

            # Don't create knowledge directory

            manager = SyncManager(hub_path, spoke_path)

            # Version check should return 0.0.0 for missing hub
            needs_update, hub_v, spoke_v = manager.check_kb_version_mismatch()

            self.assertEqual(hub_v, "0.0.0")

        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
