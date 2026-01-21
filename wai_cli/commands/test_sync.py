import json
from pathlib import Path
from datetime import datetime, timezone

from wai_cli.commands.sync import sync_spoke, _check_sync_health
from wai_cli.sync_manager import SyncManager


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
