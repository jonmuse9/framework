from pathlib import Path
import json
import pytest

from wai_cli.hub import HubManager, get_hub_kb_version, get_hub_kb_hash


def _write_hub(hub_path: Path, project_path: Path, include_registry: bool) -> None:
    (hub_path / "registry").mkdir(parents=True, exist_ok=True)
    (hub_path / "hub-profile.json").write_text("{}\n")
    if include_registry:
        (hub_path / "registry" / "wheel-projects.json").write_text(
            "{\n"
            '  "version": "2.0",\n'
            '  "projects": [\n'
            f'    {{"path": "{project_path}"}}\n'
            "  ]\n"
            "}\n"
        )


def test_auto_discover_prefers_hub_with_project_registry(tmp_path: Path) -> None:
    project_path = tmp_path / "condoshield-crm"
    project_path.mkdir()

    default_hub = tmp_path / "wheelwright-hub"
    default_hub.mkdir()
    _write_hub(default_hub, project_path, include_registry=False)

    preferred_hub = tmp_path / "wheelwright-ai" / "hub"
    _write_hub(preferred_hub, project_path, include_registry=True)

    manager = HubManager()
    discovered = manager.auto_discover_hub(project_path, verbose=False)

    assert discovered == preferred_hub


def test_create_kb_structure(tmp_path: Path) -> None:
    """Test KB structure creation."""
    hub_path = tmp_path / "test-hub"
    manager = HubManager()

    manager._create_kb_structure(hub_path)

    # Verify directories
    assert (hub_path / "knowledge").exists()
    assert (hub_path / "knowledge" / "patterns").exists()
    assert (hub_path / "knowledge" / "decisions").exists()
    assert (hub_path / "knowledge" / "learnings").exists()

    # Verify kb-manifest.json
    manifest_path = hub_path / "kb-manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    assert manifest["version"] == "1.0.0"
    assert manifest["patterns_count"] == 0
    assert manifest["decisions_count"] == 0
    assert manifest["learnings_count"] == 0
    assert manifest["content_hash"] == ""
    assert "last_updated" in manifest


def test_create_signal_structure(tmp_path: Path) -> None:
    """Test signal structure creation."""
    hub_path = tmp_path / "test-hub"
    manager = HubManager()

    manager._create_signal_structure(hub_path)

    # Verify directories
    assert (hub_path / "signals").exists()
    assert (hub_path / "signals" / "by-spoke").exists()
    assert (hub_path / "signals" / "aggregated").exists()
    assert (hub_path / "signals" / "aggregated" / "by-type").exists()


def test_get_hub_kb_version_success(tmp_path: Path) -> None:
    """Test getting KB version from manifest."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()

    manifest = {
        "version": "1.0.0",
        "last_updated": "2026-01-21T12:00:00",
        "patterns_count": 0,
        "decisions_count": 0,
        "learnings_count": 0,
        "content_hash": ""
    }

    with open(hub_path / "kb-manifest.json", 'w') as f:
        json.dump(manifest, f)

    version = get_hub_kb_version(hub_path)
    assert version == "1.0.0"


def test_get_hub_kb_version_missing_file(tmp_path: Path) -> None:
    """Test getting KB version when file doesn't exist."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()

    with pytest.raises(FileNotFoundError):
        get_hub_kb_version(hub_path)


def test_get_hub_kb_version_invalid_json(tmp_path: Path) -> None:
    """Test getting KB version with invalid JSON."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()

    with open(hub_path / "kb-manifest.json", 'w') as f:
        f.write("invalid json{")

    with pytest.raises(ValueError, match="Invalid JSON"):
        get_hub_kb_version(hub_path)


def test_get_hub_kb_version_missing_version_field(tmp_path: Path) -> None:
    """Test getting KB version when version field is missing."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()

    manifest = {
        "last_updated": "2026-01-21T12:00:00"
    }

    with open(hub_path / "kb-manifest.json", 'w') as f:
        json.dump(manifest, f)

    with pytest.raises(ValueError, match="missing 'version' field"):
        get_hub_kb_version(hub_path)


def test_get_hub_kb_hash_empty_kb(tmp_path: Path) -> None:
    """Test KB hash with empty knowledge directory."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()
    (hub_path / "knowledge").mkdir()
    (hub_path / "knowledge" / "patterns").mkdir()
    (hub_path / "knowledge" / "decisions").mkdir()
    (hub_path / "knowledge" / "learnings").mkdir()

    hash_value = get_hub_kb_hash(hub_path)
    # Empty KB should return the hash of empty content
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64  # SHA-256 hex string


def test_get_hub_kb_hash_with_content(tmp_path: Path) -> None:
    """Test KB hash with content."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()
    (hub_path / "knowledge").mkdir()
    (hub_path / "knowledge" / "patterns").mkdir()

    # Add a pattern file
    pattern_file = hub_path / "knowledge" / "patterns" / "test-pattern.json"
    with open(pattern_file, 'w') as f:
        json.dump({"name": "test", "type": "pattern"}, f)

    hash1 = get_hub_kb_hash(hub_path)
    assert isinstance(hash1, str)
    assert len(hash1) == 64

    # Add another file - hash should change
    pattern_file2 = hub_path / "knowledge" / "patterns" / "test-pattern2.json"
    with open(pattern_file2, 'w') as f:
        json.dump({"name": "test2", "type": "pattern"}, f)

    hash2 = get_hub_kb_hash(hub_path)
    assert hash2 != hash1


def test_get_hub_kb_hash_missing_kb(tmp_path: Path) -> None:
    """Test KB hash when knowledge directory doesn't exist."""
    hub_path = tmp_path / "test-hub"
    hub_path.mkdir()

    hash_value = get_hub_kb_hash(hub_path)
    assert hash_value == ""


def test_hub_creation_includes_kb_and_signals(tmp_path: Path) -> None:
    """Test that hub creation includes KB and signal structures."""
    hub_path = tmp_path / "test-hub"
    manager = HubManager()

    manager._create_hub_structure(hub_path)

    # Verify all hub components exist
    assert (hub_path / "hub-profile.json").exists()
    assert (hub_path / "registry").exists()
    assert (hub_path / "registry" / "wheel-projects.json").exists()

    # Verify KB structure
    assert (hub_path / "knowledge").exists()
    assert (hub_path / "knowledge" / "patterns").exists()
    assert (hub_path / "knowledge" / "decisions").exists()
    assert (hub_path / "knowledge" / "learnings").exists()
    assert (hub_path / "kb-manifest.json").exists()

    # Verify signal structure
    assert (hub_path / "signals").exists()
    assert (hub_path / "signals" / "by-spoke").exists()
    assert (hub_path / "signals" / "aggregated").exists()
    assert (hub_path / "signals" / "aggregated" / "by-type").exists()
