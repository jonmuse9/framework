"""
Integration Tests for Multi-Spoke Sync (--all flag)

Tests batch synchronization of multiple spokes with hub.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path

from wai_cli.commands.sync import _sync_all_spokes, _sync_single_spoke
from wai_cli.utils.registry import load_registry, add_project


class TestMultiSpokeSync(unittest.TestCase):
    """Test multi-spoke sync functionality."""

    def setUp(self):
        """Create temporary hub and multiple spokes."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke1_path = Path(self.temp_dir) / 'spoke1'
        self.spoke2_path = Path(self.temp_dir) / 'spoke2'
        self.spoke3_path = Path(self.temp_dir) / 'spoke3'

        # Create hub directory structure
        self.hub_path.mkdir(parents=True)
        (self.hub_path / 'registry').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        # Create hub registry
        registry = {
            "version": "2.0",
            "description": "Test hub registry",
            "projects": [],
            "groups": {}
        }
        registry_file = self.hub_path / 'registry' / 'wheel-projects.json'
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        # Create hub KB manifest
        hub_manifest = {
            "version": "1.5.0",
            "updated": "2025-01-21"
        }
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f, indent=2)

        # Create hub KB files
        (self.hub_path / 'knowledge' / 'pattern-test.md').write_text("# Test Pattern")

        # Create spokes with WAI-Spoke structure
        for spoke_path in [self.spoke1_path, self.spoke2_path, self.spoke3_path]:
            spoke_path.mkdir(parents=True)
            wai_dir = spoke_path / 'WAI-Spoke'
            wai_dir.mkdir(parents=True)

            # Create spoke KB sync file
            spoke_sync = {
                "version": "1.0",
                "spoke_kb_version": "1.0.0",
                "hub_kb_version": "1.0.0",
                "last_sync": None,
                "sync_status": "never_synced",
                "sync_history": []
            }
            with open(wai_dir / 'WAI-KB-Sync.json', 'w') as f:
                json.dump(spoke_sync, f, indent=2)

            # Create WAI-State.json
            state = {
                "wheelwright": {
                    "version": "2.1",
                    "spoke_structure_version": "2.1"
                }
            }
            with open(wai_dir / 'WAI-State.json', 'w') as f:
                json.dump(state, f, indent=2)

        # Register spokes in hub
        add_project(self.hub_path, self.spoke1_path, "spoke1", "Test spoke 1")
        add_project(self.hub_path, self.spoke2_path, "spoke2", "Test spoke 2")
        add_project(self.hub_path, self.spoke3_path, "spoke3", "Test spoke 3")

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_sync_all_spokes_success(self):
        """Test successful sync of all registered spokes."""
        # Sync all spokes
        _sync_all_spokes(self.hub_path)

        # Verify all spokes were synced
        for spoke_path in [self.spoke1_path, self.spoke2_path, self.spoke3_path]:
            # Check KB was downloaded
            spoke_kb_dir = spoke_path / 'WAI-Spoke' / 'hub-knowledge'
            self.assertTrue(spoke_kb_dir.exists())
            self.assertTrue((spoke_kb_dir / 'kb-manifest.json').exists())
            self.assertTrue((spoke_kb_dir / 'pattern-test.md').exists())

            # Check sync metadata was updated
            sync_file = spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
            with open(sync_file, 'r') as f:
                sync_data = json.load(f)

            self.assertEqual(sync_data['spoke_kb_version'], "1.5.0")
            self.assertEqual(sync_data['hub_kb_version'], "1.5.0")
            self.assertEqual(sync_data['sync_status'], 'synced')

        # Verify registry was updated with sync timestamps
        registry = load_registry(self.hub_path)
        for project in registry['projects']:
            self.assertIn('last_synced_at', project)
            self.assertEqual(project['last_sync_status'], 'success')

    def test_sync_all_spokes_one_fails(self):
        """Test that one spoke failure doesn't stop others."""
        # Remove WAI-Spoke from spoke2 to cause failure
        shutil.rmtree(self.spoke2_path / 'WAI-Spoke')

        # Sync all spokes
        _sync_all_spokes(self.hub_path)

        # Verify spoke1 and spoke3 were synced successfully
        for spoke_path in [self.spoke1_path, self.spoke3_path]:
            spoke_kb_dir = spoke_path / 'WAI-Spoke' / 'hub-knowledge'
            self.assertTrue(spoke_kb_dir.exists())

        # Verify spoke2 failed (no hub-knowledge directory)
        spoke2_kb_dir = self.spoke2_path / 'WAI-Spoke' / 'hub-knowledge'
        self.assertFalse(spoke2_kb_dir.exists())

        # Verify registry reflects success/failure
        registry = load_registry(self.hub_path)
        for project in registry['projects']:
            if project['name'] == 'spoke2':
                self.assertEqual(project['last_sync_status'], 'failed')
            else:
                self.assertEqual(project['last_sync_status'], 'success')

    def test_sync_all_spokes_spoke_path_not_found(self):
        """Test handling when registered spoke path doesn't exist."""
        # Delete spoke3 directory
        shutil.rmtree(self.spoke3_path)

        # Sync all spokes
        _sync_all_spokes(self.hub_path)

        # Verify spoke1 and spoke2 were synced successfully
        for spoke_path in [self.spoke1_path, self.spoke2_path]:
            spoke_kb_dir = spoke_path / 'WAI-Spoke' / 'hub-knowledge'
            self.assertTrue(spoke_kb_dir.exists())

    def test_sync_all_spokes_empty_registry(self):
        """Test handling when no spokes are registered."""
        # Clear registry
        registry = {
            "version": "2.0",
            "description": "Empty registry",
            "projects": [],
            "groups": {}
        }
        registry_file = self.hub_path / 'registry' / 'wheel-projects.json'
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

        # Sync should complete without errors
        _sync_all_spokes(self.hub_path)

    def test_sync_all_spokes_invalid_registry(self):
        """Test handling when registry is corrupted."""
        # Corrupt registry
        registry_file = self.hub_path / 'registry' / 'wheel-projects.json'
        registry_file.write_text("invalid json {{{")

        # Sync should fail gracefully
        _sync_all_spokes(self.hub_path)


class TestSingleSpokeSync(unittest.TestCase):
    """Test single spoke sync helper function."""

    def setUp(self):
        """Create temporary hub and spoke."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        # Create hub
        self.hub_path.mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        # Create hub KB manifest
        hub_manifest = {
            "version": "1.5.0",
            "updated": "2025-01-21"
        }
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f, indent=2)

        # Create spoke with WAI-Spoke structure
        self.spoke_path.mkdir(parents=True)
        wai_dir = self.spoke_path / 'WAI-Spoke'
        wai_dir.mkdir(parents=True)

        # Create spoke KB sync file
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "1.0.0",
            "hub_kb_version": "1.0.0",
            "last_sync": None,
            "sync_status": "never_synced",
            "sync_history": []
        }
        with open(wai_dir / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f, indent=2)

        # Create WAI-State.json
        state = {
            "wheelwright": {
                "version": "2.1",
                "spoke_structure_version": "2.1"
            }
        }
        with open(wai_dir / 'WAI-State.json', 'w') as f:
            json.dump(state, f, indent=2)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_sync_single_spoke_success(self):
        """Test successful single spoke sync."""
        result = _sync_single_spoke(self.hub_path, self.spoke_path)

        self.assertTrue(result['success'])
        self.assertNotIn('error', result)

        # Verify KB was downloaded
        spoke_kb_dir = self.spoke_path / 'WAI-Spoke' / 'hub-knowledge'
        self.assertTrue(spoke_kb_dir.exists())

    def test_sync_single_spoke_no_structure(self):
        """Test sync fails when spoke has no WAI-Spoke structure."""
        # Remove WAI-Spoke
        shutil.rmtree(self.spoke_path / 'WAI-Spoke')

        result = _sync_single_spoke(self.hub_path, self.spoke_path)

        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('No spoke structure', result['error'])

    def test_sync_single_spoke_upgrade_v1(self):
        """Test sync auto-upgrades v1.0 spoke structure."""
        # Create v1.0 structure
        shutil.rmtree(self.spoke_path / 'WAI-Spoke')
        old_wai_dir = self.spoke_path / '.WAI'
        old_wai_dir.mkdir(parents=True)

        # Create v1.0 state file
        state = {
            "framework_version": "1.0",
            "project_name": "test-spoke"
        }
        with open(old_wai_dir / 'state.json', 'w') as f:
            json.dump(state, f, indent=2)

        result = _sync_single_spoke(self.hub_path, self.spoke_path)

        # Should succeed after upgrade
        self.assertTrue(result['success'])

        # Verify structure was upgraded
        self.assertTrue((self.spoke_path / 'WAI-Spoke').exists())
        self.assertFalse(old_wai_dir.exists())

    def test_sync_single_spoke_kb_sync_error(self):
        """Test handling of KB sync errors."""
        # Remove hub KB to cause error
        shutil.rmtree(self.hub_path / 'knowledge')

        result = _sync_single_spoke(self.hub_path, self.spoke_path)

        # Should succeed (KB sync error is not fatal in batch mode)
        self.assertTrue(result['success'])

    def test_sync_single_spoke_with_signals(self):
        """Test spoke sync with signal upload."""
        # Create signals file
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
        signal = {
            "timestamp": "2025-01-21T10:00:00Z",
            "by": "claude",
            "impact": 9,
            "offers": [{
                "type": "pattern",
                "topic": "test-pattern",
                "context": "Test context",
                "impact": 9
            }],
            "flags": {
                "ready_for_hub": True
            }
        }
        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        # Create hub signals directory
        (self.hub_path / 'signals' / 'by-spoke').mkdir(parents=True)

        result = _sync_single_spoke(self.hub_path, self.spoke_path)

        self.assertTrue(result['success'])

        # Verify signal was uploaded
        hub_signals_file = self.hub_path / 'signals' / 'by-spoke' / 'spoke' / 'signals.jsonl'
        self.assertTrue(hub_signals_file.exists())


if __name__ == '__main__':
    unittest.main()
