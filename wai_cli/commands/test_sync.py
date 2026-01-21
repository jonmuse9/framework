import json
from pathlib import Path
from datetime import datetime, timezone

from wai_cli.commands.sync import sync_spoke, _check_sync_health
from wai_cli.sync_manager import SyncManager
from wai_cli.hub import HubManager


def test_sync_spoke_handles_missing_hub(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    sync_spoke(all_spokes=False)


def test_sync_spoke_check_flag_no_hub(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test sync --check when no hub is found."""
    import pytest

    # Don't create WAI-Spoke so auto-discovery won't find a hub
    monkeypatch.chdir(tmp_path)

    # _check_sync_health will exit with code 1 if WAI-Spoke doesn't exist
    with pytest.raises(SystemExit) as exc_info:
        sync_spoke(all_spokes=False, check_only=True)

    # Should exit with code 1
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    # Should indicate missing spoke structure
    assert 'No spoke structure found' in captured.out or 'No hub found' in captured.out


def test_check_sync_health_never_synced(tmp_path: Path, monkeypatch) -> None:
    """Test _check_sync_health when never synced."""
    import sys

    # Create hub and spoke directories
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()

    monkeypatch.chdir(spoke_path)

    # Should exit with code 1 (needs sync)
    try:
        _check_sync_health(hub_path, spoke_path)
        assert False, "Should have exited"
    except SystemExit as e:
        assert e.code == 1


def test_check_sync_health_healthy(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test _check_sync_health when healthy."""
    import sys

    # Create hub and spoke directories
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()

    # Create sync metadata with recent sync
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.5.0",
        "hub_kb_version": "1.5.0",
        "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sync_status": "synced"
    }
    sync_file = spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
    with open(sync_file, 'w') as f:
        json.dump(sync_data, f)

    # Create hub manifest
    hub_manifest = {"version": "1.5.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    monkeypatch.chdir(spoke_path)

    # Should exit with code 0 (healthy)
    try:
        _check_sync_health(hub_path, spoke_path)
        assert False, "Should have exited"
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    assert 'HEALTHY' in captured.out
    assert 'No sync needed' in captured.out


def test_check_sync_health_stale(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test _check_sync_health when stale."""
    import sys
    from datetime import timedelta

    # Create hub and spoke directories
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()

    # Create sync metadata with old sync (45 days ago)
    last_sync_time = datetime.now(timezone.utc) - timedelta(days=45)
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.5.0",
        "hub_kb_version": "1.5.0",
        "last_sync": last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sync_status": "synced"
    }
    sync_file = spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json'
    with open(sync_file, 'w') as f:
        json.dump(sync_data, f)

    # Create hub manifest
    hub_manifest = {"version": "1.5.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    monkeypatch.chdir(spoke_path)

    # Should exit with code 1 (needs sync)
    try:
        _check_sync_health(hub_path, spoke_path)
        assert False, "Should have exited"
    except SystemExit as e:
        assert e.code == 1

    captured = capsys.readouterr()
    assert 'STALE' in captured.out
    assert 'Sync recommended' in captured.out


def test_sync_spoke_with_no_spoke_structure(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test sync when no spoke structure exists."""
    # Create empty directory with no WAI-Spoke
    monkeypatch.chdir(tmp_path)

    # Should detect no spoke structure and exit
    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    assert 'No valid spoke structure found' in captured.out or 'Run \'WAI init\'' in captured.out


def test_sync_spoke_with_v1_structure(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test auto-upgrade from v1.0 structure."""
    spoke_path = tmp_path / 'spoke'
    spoke_path.mkdir()

    # Create v1.0 structure (.WAI/)
    old_wai_dir = spoke_path / '.WAI'
    old_wai_dir.mkdir()
    state_file = old_wai_dir / 'WAI-State.json'
    state_file.write_text('{"version": "1.0"}')

    monkeypatch.chdir(spoke_path)

    # Should auto-upgrade
    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    # Verify upgrade was attempted
    assert 'auto-upgrading' in captured.out or 'upgraded' in captured.out or 'Spoke structure' in captured.out


def test_sync_spoke_kb_sync_success(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test successful sync with hub KB."""
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.0.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    monkeypatch.chdir(spoke_path)

    # Mock hub discovery to return the hub path
    def mock_discover(self, path, verbose=False):
        return hub_path

    monkeypatch.setattr(HubManager, 'auto_discover_hub', mock_discover)

    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    assert 'Sync complete' in captured.out


def test_sync_spoke_signal_upload_with_no_signals(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test sync when there are no signals to upload."""
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()
    (hub_path / 'signals').mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.0.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.0.0",
        "hub_kb_version": "1.0.0"
    }
    with open(spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
        json.dump(sync_data, f)

    # No signals file created

    monkeypatch.chdir(spoke_path)

    # Mock hub discovery
    def mock_discover(self, path, verbose=False):
        return hub_path

    monkeypatch.setattr(HubManager, 'auto_discover_hub', mock_discover)

    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    assert 'No signals found' in captured.out or 'Sync complete' in captured.out


def test_sync_spoke_signal_upload_all_duplicates(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test sync when all signals are duplicates."""
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()
    (hub_path / 'signals').mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.0.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.0.0",
        "hub_kb_version": "1.0.0"
    }
    with open(spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
        json.dump(sync_data, f)

    # Create signal that's already uploaded
    signal = {
        "timestamp": "2025-01-21T12:00:00Z",
        "by": "Claude Sonnet 4.5",
        "offers": [{"type": "pattern", "topic": "Test", "impact": 9, "context": "Test"}],
        "flags": {"ready_for_hub": True},
        "uploaded_to_hub_at": "2025-01-21T11:00:00Z"
    }

    signals_file = spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
    with open(signals_file, 'w') as f:
        f.write(json.dumps(signal) + '\n')

    monkeypatch.chdir(spoke_path)

    # Mock hub discovery
    def mock_discover(self, path, verbose=False):
        return hub_path

    monkeypatch.setattr(HubManager, 'auto_discover_hub', mock_discover)

    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    assert 'already uploaded' in captured.out or 'Sync complete' in captured.out


def test_sync_spoke_signal_upload_success(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test successful signal upload."""
    hub_path = tmp_path / 'hub'
    spoke_path = tmp_path / 'spoke'
    hub_path.mkdir()
    spoke_path.mkdir()
    (spoke_path / 'WAI-Spoke').mkdir()
    (hub_path / 'knowledge').mkdir()
    (hub_path / 'signals').mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.0.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.0.0",
        "hub_kb_version": "1.0.0"
    }
    with open(spoke_path / 'WAI-Spoke' / 'WAI-KB-Sync.json', 'w') as f:
        json.dump(sync_data, f)

    # Create new signal ready for upload
    signal = {
        "timestamp": "2025-01-21T12:00:00Z",
        "by": "Claude Sonnet 4.5",
        "offers": [{"type": "pattern", "topic": "Test", "impact": 9, "context": "Test"}],
        "flags": {"ready_for_hub": True}
    }

    signals_file = spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
    with open(signals_file, 'w') as f:
        f.write(json.dumps(signal) + '\n')

    monkeypatch.chdir(spoke_path)

    # Mock hub discovery
    def mock_discover(self, path, verbose=False):
        return hub_path

    monkeypatch.setattr(HubManager, 'auto_discover_hub', mock_discover)

    sync_spoke(all_spokes=False, check_only=False)

    captured = capsys.readouterr()
    assert 'Uploaded' in captured.out or 'high-impact signal' in captured.out
