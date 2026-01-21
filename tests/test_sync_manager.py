"""
Unit Tests for SyncManager

Tests version comparison, KB sync, and metadata management.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from wai_cli.sync_manager import SyncManager


class TestVersionComparison(unittest.TestCase):
    """Test semantic version comparison logic."""

    def setUp(self):
        """Create temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_version_less_than(self):
        """Test v1 < v2."""
        result = self.manager._compare_versions("1.0.0", "1.2.0")
        self.assertEqual(result, -1)

        result = self.manager._compare_versions("1.0.0", "2.0.0")
        self.assertEqual(result, -1)

        result = self.manager._compare_versions("1.2.3", "1.2.4")
        self.assertEqual(result, -1)

    def test_version_greater_than(self):
        """Test v1 > v2."""
        result = self.manager._compare_versions("2.0.0", "1.9.9")
        self.assertEqual(result, 1)

        result = self.manager._compare_versions("1.3.0", "1.2.0")
        self.assertEqual(result, 1)

        result = self.manager._compare_versions("1.2.5", "1.2.4")
        self.assertEqual(result, 1)

    def test_version_equal(self):
        """Test v1 == v2."""
        result = self.manager._compare_versions("1.2.3", "1.2.3")
        self.assertEqual(result, 0)

        result = self.manager._compare_versions("0.0.0", "0.0.0")
        self.assertEqual(result, 0)

        result = self.manager._compare_versions("10.5.2", "10.5.2")
        self.assertEqual(result, 0)

    def test_version_padding(self):
        """Test version comparison with different lengths."""
        result = self.manager._compare_versions("1.0", "1.0.0")
        self.assertEqual(result, 0)

        result = self.manager._compare_versions("1.2", "1.2.1")
        self.assertEqual(result, -1)

        result = self.manager._compare_versions("2.0.1", "2.0")
        self.assertEqual(result, 1)

    def test_invalid_version_format(self):
        """Test handling of invalid version strings."""
        # Should treat invalid versions as equal (return 0)
        result = self.manager._compare_versions("invalid", "1.0.0")
        self.assertEqual(result, 0)

        result = self.manager._compare_versions("1.0.0", "not-a-version")
        self.assertEqual(result, 0)


class TestKBVersionDetection(unittest.TestCase):
    """Test KB version detection from hub and spoke."""

    def setUp(self):
        """Create temporary directories and files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_get_hub_kb_version_exists(self):
        """Test getting hub KB version when manifest exists."""
        manifest = {
            "version": "1.5.0",
            "updated": "2025-01-01"
        }
        manifest_file = self.hub_path / 'knowledge' / 'kb-manifest.json'
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)

        version = self.manager._get_hub_kb_version()
        self.assertEqual(version, "1.5.0")

    def test_get_hub_kb_version_missing(self):
        """Test getting hub KB version when manifest doesn't exist."""
        version = self.manager._get_hub_kb_version()
        self.assertEqual(version, "0.0.0")

    def test_get_hub_kb_version_corrupted(self):
        """Test getting hub KB version when manifest is corrupted."""
        manifest_file = self.hub_path / 'knowledge' / 'kb-manifest.json'
        with open(manifest_file, 'w') as f:
            f.write("invalid json {")

        version = self.manager._get_hub_kb_version()
        self.assertEqual(version, "0.0.0")

    def test_get_spoke_kb_version_exists(self):
        """Test getting spoke KB version when sync file exists."""
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.3.0",
            "hub_kb_version": "1.5.0",
            "last_sync": None,
            "sync_status": "never_synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        version = self.manager._get_spoke_kb_version()
        self.assertEqual(version, "1.3.0")

    def test_get_spoke_kb_version_missing(self):
        """Test getting spoke KB version when sync file doesn't exist."""
        version = self.manager._get_spoke_kb_version()
        self.assertEqual(version, "0.0.0")

    def test_get_spoke_kb_version_corrupted(self):
        """Test getting spoke KB version when sync file is corrupted."""
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            f.write("corrupted json")

        version = self.manager._get_spoke_kb_version()
        self.assertEqual(version, "0.0.0")


class TestKBVersionMismatch(unittest.TestCase):
    """Test KB version mismatch detection."""

    def setUp(self):
        """Create temporary directories and files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_version_mismatch_update_needed(self):
        """Test when hub has newer version."""
        # Setup hub version
        hub_manifest = {"version": "2.0.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        # Setup spoke version
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "1.0.0",
            "hub_kb_version": "1.0.0"
        }
        with open(self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f)

        needs_update, hub_v, spoke_v = self.manager.check_kb_version_mismatch()

        self.assertTrue(needs_update)
        self.assertEqual(hub_v, "2.0.0")
        self.assertEqual(spoke_v, "1.0.0")

    def test_version_mismatch_no_update_needed(self):
        """Test when versions are the same."""
        # Setup hub version
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        # Setup spoke version
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0"
        }
        with open(self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f)

        needs_update, hub_v, spoke_v = self.manager.check_kb_version_mismatch()

        self.assertFalse(needs_update)
        self.assertEqual(hub_v, "1.5.0")
        self.assertEqual(spoke_v, "1.5.0")

    def test_version_mismatch_spoke_newer(self):
        """Test when spoke has newer version (shouldn't happen, but handle it)."""
        # Setup hub version
        hub_manifest = {"version": "1.0.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        # Setup spoke version
        spoke_sync = {
            "version": "1.0",
            "spoke_kb_version": "2.0.0",
            "hub_kb_version": "1.0.0"
        }
        with open(self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
            json.dump(spoke_sync, f)

        needs_update, hub_v, spoke_v = self.manager.check_kb_version_mismatch()

        self.assertFalse(needs_update)
        self.assertEqual(hub_v, "1.0.0")
        self.assertEqual(spoke_v, "2.0.0")


class TestSyncMetadataUpdate(unittest.TestCase):
    """Test sync metadata updates."""

    def setUp(self):
        """Create temporary directories and files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_update_metadata_creates_file(self):
        """Test creating metadata file if it doesn't exist."""
        self.manager.update_kb_sync_metadata('download', '1.0.0')

        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        self.assertTrue(sync_file.exists())

        with open(sync_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['hub_kb_version'], '1.0.0')
        self.assertEqual(data['sync_status'], 'synced')
        self.assertIsNotNone(data['last_sync'])

    def test_update_metadata_adds_history(self):
        """Test adding sync history entries."""
        self.manager.update_kb_sync_metadata('download', '1.0.0')
        self.manager.update_kb_sync_metadata('download', '1.1.0')

        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(len(data['sync_history']), 2)
        self.assertEqual(data['sync_history'][0]['hub_version'], '1.0.0')
        self.assertEqual(data['sync_history'][1]['hub_version'], '1.1.0')

    def test_update_metadata_limits_history(self):
        """Test that sync history is limited to 50 entries."""
        # Add 60 sync entries
        for i in range(60):
            self.manager.update_kb_sync_metadata('download', f'{i}.0.0')

        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'r') as f:
            data = json.load(f)

        # Should only keep last 50
        self.assertEqual(len(data['sync_history']), 50)
        self.assertEqual(data['sync_history'][0]['hub_version'], '10.0.0')
        self.assertEqual(data['sync_history'][-1]['hub_version'], '59.0.0')

    def test_update_metadata_recovers_from_corruption(self):
        """Test recovery from corrupted metadata file."""
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            f.write("corrupted json {{{")

        # Should recreate metadata file
        self.manager.update_kb_sync_metadata('download', '1.0.0')

        self.assertTrue(sync_file.exists())
        with open(sync_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['hub_kb_version'], '1.0.0')


class TestSignalUpload(unittest.TestCase):
    """Test signal upload functionality."""

    def setUp(self):
        """Create temporary directories and files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'signals' / 'by-spoke').mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_upload_signals_no_file(self):
        """Test upload when signals file doesn't exist."""
        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 0)
        self.assertEqual(result['duplicates_skipped'], 0)
        self.assertEqual(result['signals_total'], 0)

    def test_upload_signals_empty_file(self):
        """Test upload when signals file is empty."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
        signals_file.write_text('')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 0)
        self.assertEqual(result['signals_total'], 0)

    def test_upload_signals_high_impact(self):
        """Test upload of high-impact signals (impact >= 8)."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Test Pattern",
                "impact": 9,
                "context": "High impact pattern"
            }],
            "flags": {}
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 1)
        self.assertEqual(result['duplicates_skipped'], 0)
        self.assertEqual(result['signals_total'], 1)

        # Verify signal uploaded to hub
        hub_signals_file = self.hub_path / 'signals' / 'by-spoke' / self.spoke_path.name / 'signals.jsonl'
        self.assertTrue(hub_signals_file.exists())

        with open(hub_signals_file, 'r') as f:
            uploaded_signal = json.loads(f.read().strip())

        self.assertIn('uploaded_to_hub_at', uploaded_signal)
        self.assertEqual(uploaded_signal['offers'][0]['topic'], 'Test Pattern')

    def test_upload_signals_ready_for_hub_flag(self):
        """Test upload of signals with ready_for_hub flag."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Flagged Pattern",
                "impact": 5,
                "context": "Low impact but flagged"
            }],
            "flags": {
                "ready_for_hub": True
            }
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 1)
        self.assertEqual(result['signals_total'], 1)

    def test_upload_signals_low_impact_not_flagged(self):
        """Test that low impact signals without flag are not uploaded."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Low Impact Pattern",
                "impact": 5,
                "context": "Low impact, not flagged"
            }],
            "flags": {}
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 0)
        self.assertEqual(result['signals_total'], 1)

    def test_upload_signals_already_uploaded(self):
        """Test that already uploaded signals are skipped."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Already Uploaded",
                "impact": 9,
                "context": "Already uploaded"
            }],
            "flags": {},
            "uploaded_to_hub_at": "2025-01-21T11:00:00Z"
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 0)
        self.assertEqual(result['signals_total'], 1)

    def test_upload_signals_duplicate_detection(self):
        """Test duplicate signal detection."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal1 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Duplicate Pattern",
                "impact": 9,
                "context": "Same content"
            }],
            "flags": {}
        }

        signal2 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Duplicate Pattern",
                "impact": 9,
                "context": "Same content"
            }],
            "flags": {}
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal1) + '\n')
            f.write(json.dumps(signal2) + '\n')

        result = self.manager.upload_signals()

        # First signal uploaded, second detected as duplicate
        self.assertEqual(result['signals_uploaded'], 1)
        self.assertEqual(result['duplicates_skipped'], 1)
        self.assertEqual(result['signals_total'], 2)

    def test_upload_signals_malformed_line(self):
        """Test handling of malformed signal lines."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        valid_signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Valid Pattern",
                "impact": 9,
                "context": "Valid signal"
            }],
            "flags": {}
        }

        with open(signals_file, 'w') as f:
            f.write("malformed json {{\n")
            f.write(json.dumps(valid_signal) + '\n')

        result = self.manager.upload_signals()

        # Should skip malformed line and upload valid signal
        self.assertEqual(result['signals_uploaded'], 1)
        self.assertEqual(result['signals_total'], 1)

    def test_upload_signals_updates_spoke_file(self):
        """Test that spoke signals file is updated with upload timestamps."""
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Test Pattern",
                "impact": 9,
                "context": "Test"
            }],
            "flags": {}
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal) + '\n')

        result = self.manager.upload_signals()

        self.assertEqual(result['signals_uploaded'], 1)

        # Read spoke signals file and verify uploaded_to_hub_at added
        with open(signals_file, 'r') as f:
            updated_signal = json.loads(f.read().strip())

        self.assertIn('uploaded_to_hub_at', updated_signal)

    def test_extract_max_impact_top_level(self):
        """Test extracting impact from top-level field."""
        signal = {"impact": 10}
        impact = self.manager._extract_max_impact(signal)
        self.assertEqual(impact, 10)

    def test_extract_max_impact_offers(self):
        """Test extracting maximum impact from offers array."""
        signal = {
            "offers": [
                {"impact": 5},
                {"impact": 9},
                {"impact": 7}
            ]
        }
        impact = self.manager._extract_max_impact(signal)
        self.assertEqual(impact, 9)

    def test_extract_max_impact_no_impact(self):
        """Test extracting impact when no impact field exists."""
        signal = {"offers": [{"topic": "test"}]}
        impact = self.manager._extract_max_impact(signal)
        self.assertEqual(impact, 0)

    def test_calculate_signal_hash_consistency(self):
        """Test that identical signals produce same hash."""
        signal1 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Test",
                "context": "Content"
            }]
        }

        signal2 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{
                "type": "pattern",
                "topic": "Test",
                "context": "Content"
            }]
        }

        hash1 = self.manager._calculate_signal_hash(signal1)
        hash2 = self.manager._calculate_signal_hash(signal2)

        self.assertEqual(hash1, hash2)

    def test_calculate_signal_hash_different(self):
        """Test that different signals produce different hashes."""
        signal1 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{"type": "pattern", "topic": "Test1", "context": "Content1"}]
        }

        signal2 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{"type": "pattern", "topic": "Test2", "context": "Content2"}]
        }

        hash1 = self.manager._calculate_signal_hash(signal1)
        hash2 = self.manager._calculate_signal_hash(signal2)

        self.assertNotEqual(hash1, hash2)


class TestSyncHealthCalculation(unittest.TestCase):
    """Test sync health calculation."""

    def setUp(self):
        """Create temporary directories and files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hub_path = Path(self.temp_dir) / 'hub'
        self.spoke_path = Path(self.temp_dir) / 'spoke'

        self.hub_path.mkdir(parents=True)
        self.spoke_path.mkdir(parents=True)
        (self.spoke_path / 'WAI-Spoke').mkdir(parents=True)
        (self.hub_path / 'knowledge').mkdir(parents=True)

        self.manager = SyncManager(self.hub_path, self.spoke_path)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir)

    def test_sync_health_never_synced(self):
        """Test health when never synced."""
        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'never_synced')
        self.assertIsNone(health['days_since_last_sync'])
        self.assertIsNone(health['kb_version_drift'])
        self.assertEqual(health['pending_signals'], 0)
        self.assertIsNotNone(health['last_check'])

    def test_sync_health_healthy(self):
        """Test health when recently synced and up to date."""
        # Create sync metadata with recent sync
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['days_since_last_sync'], 0)
        self.assertIsNone(health['kb_version_drift'])
        self.assertEqual(health['pending_signals'], 0)

    def test_sync_health_stale_by_time(self):
        """Test health when synced > 30 days ago."""
        from datetime import timedelta

        # Create sync metadata with old sync (45 days ago)
        last_sync_time = datetime.now(timezone.utc) - timedelta(days=45)
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest (same version)
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'stale')
        self.assertEqual(health['days_since_last_sync'], 45)
        self.assertIsNone(health['kb_version_drift'])

    def test_sync_health_stale_by_minor_version(self):
        """Test health when minor version drift exists."""
        # Create sync metadata with recent sync but old version
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.3.0",
            "hub_kb_version": "1.3.0",
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest with newer minor version
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'stale')
        self.assertEqual(health['kb_version_drift'], '2 minor versions behind')

    def test_sync_health_outdated_by_time(self):
        """Test health when synced > 90 days ago."""
        from datetime import timedelta

        # Create sync metadata with very old sync (100 days ago)
        last_sync_time = datetime.now(timezone.utc) - timedelta(days=100)
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'outdated')
        self.assertEqual(health['days_since_last_sync'], 100)

    def test_sync_health_outdated_by_major_version(self):
        """Test health when major version drift exists."""
        # Create sync metadata with recent sync but old major version
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest with newer major version
        hub_manifest = {"version": "3.0.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        self.assertEqual(health['status'], 'outdated')
        self.assertEqual(health['kb_version_drift'], '2 major versions behind')

    def test_sync_health_pending_signals(self):
        """Test counting pending signals."""
        # Create sync metadata
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest
        hub_manifest = {"version": "1.5.0"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        # Create signals file with pending signals
        signals_file = self.spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'

        signal1 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{"type": "pattern", "topic": "Test1", "impact": 9, "context": "Test"}],
            "flags": {}
        }

        signal2 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{"type": "pattern", "topic": "Test2", "impact": 5, "context": "Test"}],
            "flags": {"ready_for_hub": True}
        }

        signal3 = {
            "timestamp": "2025-01-21T12:00:00Z",
            "by": "Claude Sonnet 4.5",
            "offers": [{"type": "pattern", "topic": "Test3", "impact": 9, "context": "Test"}],
            "flags": {},
            "uploaded_to_hub_at": "2025-01-21T11:00:00Z"
        }

        with open(signals_file, 'w') as f:
            f.write(json.dumps(signal1) + '\n')
            f.write(json.dumps(signal2) + '\n')
            f.write(json.dumps(signal3) + '\n')

        health = self.manager.calculate_sync_health()

        # Should count 2 pending signals (high impact + flagged, but not uploaded)
        self.assertEqual(health['pending_signals'], 2)

    def test_sync_health_corrupted_metadata(self):
        """Test health when metadata file is corrupted."""
        # Create corrupted sync file
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            f.write("corrupted json {{{")

        health = self.manager.calculate_sync_health()

        # Should treat as never synced
        self.assertEqual(health['status'], 'never_synced')
        self.assertIsNone(health['days_since_last_sync'])

    def test_sync_health_patch_version_drift(self):
        """Test health with patch version drift."""
        # Create sync metadata
        sync_data = {
            "version": "1.0",
            "spoke_kb_version": "1.5.0",
            "hub_kb_version": "1.5.0",
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sync_status": "synced"
        }
        sync_file = self.spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        # Create hub manifest with patch version bump
        hub_manifest = {"version": "1.5.3"}
        with open(self.hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
            json.dump(hub_manifest, f)

        health = self.manager.calculate_sync_health()

        # Patch version drift shouldn't trigger stale status alone
        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['kb_version_drift'], '3 patch versions behind')


if __name__ == '__main__':
    unittest.main()
