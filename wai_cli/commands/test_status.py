import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from wai_cli.commands.status import show_status


def _write_state(path: Path, hub_path: str) -> None:
    state = {
        "wheelwright": {
            "hub_path": hub_path
        },
        "_project_foundation": {
            "completed": False
        },
        "wheel": {},
        "_session_state": {
            "last_modified_by": "test",
            "session_count": 0
        }
    }
    path.write_text(json.dumps(state, indent=2) + "\n")


def _write_hub(hub_path: Path, project_path: Path) -> None:
    (hub_path / "registry").mkdir(parents=True)
    (hub_path / "hub-profile.json").write_text("{}\n")
    (hub_path / "registry" / "wheel-projects.json").write_text(
        "{\n"
        '  "version": "2.0",\n'
        '  "projects": [\n'
        f'    {{"path": "{project_path}"}}\n'
        "  ]\n"
        "}\n"
    )


def test_status_updates_hub_path(tmp_path: Path) -> None:
    project_path = tmp_path / "condoshield-crm"
    spoke_dir = project_path / "WAI-Spoke"
    spoke_dir.mkdir(parents=True)

    bad_hub = tmp_path / "wheelwright-hub"
    bad_hub.mkdir()
    (bad_hub / "hub-profile.json").write_text("{}\n")

    good_hub = tmp_path / "wheelwright-ai" / "hub"
    _write_hub(good_hub, project_path)

    state_path = spoke_dir / "WAI-State.json"
    _write_state(state_path, str(bad_hub))

    show_status(str(project_path))

    updated = state_path.read_text()
    assert str(good_hub) in updated


def test_status_shows_sync_health_healthy(tmp_path: Path, capsys) -> None:
    """Test that status command shows sync health when healthy."""
    project_path = tmp_path / "project"
    spoke_dir = project_path / "WAI-Spoke"
    spoke_dir.mkdir(parents=True)

    hub_path = tmp_path / "hub"
    _write_hub(hub_path, project_path)
    (hub_path / "knowledge").mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.5.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata with recent sync
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.5.0",
        "hub_kb_version": "1.5.0",
        "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sync_status": "synced"
    }
    sync_file = spoke_dir / 'WAI-KB-Sync.json'
    with open(sync_file, 'w') as f:
        json.dump(sync_data, f)

    state_path = spoke_dir / "WAI-State.json"
    _write_state(state_path, str(hub_path))

    show_status(str(project_path))

    captured = capsys.readouterr()
    assert 'Sync Health:' in captured.out
    assert 'healthy' in captured.out


def test_status_shows_sync_health_stale(tmp_path: Path, capsys) -> None:
    """Test that status command shows sync health when stale."""
    project_path = tmp_path / "project"
    spoke_dir = project_path / "WAI-Spoke"
    spoke_dir.mkdir(parents=True)

    hub_path = tmp_path / "hub"
    _write_hub(hub_path, project_path)
    (hub_path / "knowledge").mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.5.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata with old sync (45 days ago)
    last_sync_time = datetime.now(timezone.utc) - timedelta(days=45)
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.5.0",
        "hub_kb_version": "1.5.0",
        "last_sync": last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sync_status": "synced"
    }
    sync_file = spoke_dir / 'WAI-KB-Sync.json'
    with open(sync_file, 'w') as f:
        json.dump(sync_data, f)

    state_path = spoke_dir / "WAI-State.json"
    _write_state(state_path, str(hub_path))

    show_status(str(project_path))

    captured = capsys.readouterr()
    assert 'Sync Health:' in captured.out
    assert 'stale' in captured.out
    assert "Run 'WAI sync' to update" in captured.out


def test_status_shows_sync_health_with_pending_signals(tmp_path: Path, capsys) -> None:
    """Test that status command shows pending signals count."""
    project_path = tmp_path / "project"
    spoke_dir = project_path / "WAI-Spoke"
    spoke_dir.mkdir(parents=True)

    hub_path = tmp_path / "hub"
    _write_hub(hub_path, project_path)
    (hub_path / "knowledge").mkdir()

    # Create hub manifest
    hub_manifest = {"version": "1.5.0"}
    with open(hub_path / 'knowledge' / 'kb-manifest.json', 'w') as f:
        json.dump(hub_manifest, f)

    # Create sync metadata
    sync_data = {
        "version": "1.0",
        "spoke_kb_version": "1.5.0",
        "hub_kb_version": "1.5.0",
        "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sync_status": "synced"
    }
    sync_file = spoke_dir / 'WAI-KB-Sync.json'
    with open(sync_file, 'w') as f:
        json.dump(sync_data, f)

    # Create signals file with pending signal
    signals_file = spoke_dir / 'WAI-Signals.jsonl'
    signal = {
        "timestamp": "2025-01-21T12:00:00Z",
        "by": "Claude Sonnet 4.5",
        "offers": [{"type": "pattern", "topic": "Test", "impact": 9, "context": "Test"}],
        "flags": {}
    }
    with open(signals_file, 'w') as f:
        f.write(json.dumps(signal) + '\n')

    state_path = spoke_dir / "WAI-State.json"
    _write_state(state_path, str(hub_path))

    show_status(str(project_path))

    captured = capsys.readouterr()
    assert 'Sync Health:' in captured.out
    assert 'Pending signals: 1' in captured.out
