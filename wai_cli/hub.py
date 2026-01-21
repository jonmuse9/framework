"""
Hub Discovery and Management

Intelligent hub discovery with scoring, verification, and creation.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from .utils.paths import (
    normalize_path,
    is_valid_hub_location,
    suggest_hub_locations,
    ensure_directory
)
from .utils.input import safe_input, safe_confirm, print_info, print_success, print_warning
from .utils.exceptions import InvalidHubError, PathNotFoundError


class HubCandidate:
    """Hub discovery candidate with scoring."""

    def __init__(self, path: Path):
        self.path = path
        self.score = 0
        self.reasons: List[str] = []

    def add_score(self, points: int, reason: str):
        """Add points with reasoning."""
        self.score += points
        self.reasons.append(f"+{points}: {reason}")

    def __repr__(self):
        return f"HubCandidate({self.path}, score={self.score})"


class HubManager:
    """Hub discovery and management."""

    def auto_discover_hub(
        self,
        current_path: Path,
        verbose: bool = False
    ) -> Optional[Path]:
        """
        Auto-discover hub with intelligent scoring.

        Priority:
        1. $WHEELWRIGHT_HUB_PATH environment variable
        2. Parent folder scan (../hub, ../WAI-Hub, ../*hub*)
        3. Common paths (~/wheelwright-hub, etc.)

        Scoring factors:
        - Has hub-profile.json: +10
        - Has registry/wheel-projects.json: +5
        - Has WAI-Spoke/: +3 (deduct - likely a spoke, not hub)
        - Modified last 30 days: +2
        - Name exactly "hub": +1

        Args:
            current_path: Path to start search from (usually framework folder)
            verbose: Print discovery progress

        Returns:
            Path to discovered hub or None

        Examples:
            >>> hub = HubManager().auto_discover_hub(Path("/home/user/projects/framework"))
            /home/user/projects/hub
        """
        candidates: List[HubCandidate] = []

        # Priority 1: Environment variable
        env_hub = os.environ.get('WHEELWRIGHT_HUB_PATH')
        if env_hub:
            try:
                env_path = normalize_path(env_hub)
                if env_path.exists():
                    candidate = HubCandidate(env_path)
                    candidate.add_score(15, "From $WHEELWRIGHT_HUB_PATH")
                    candidates.append(candidate)
                    if verbose:
                        print_info(f"Found env hub: {env_path}")
            except Exception:
                pass

        # Priority 2: Parent folder scan
        parent_candidates = self._scan_parent_folder(current_path)
        candidates.extend(parent_candidates)

        if verbose and parent_candidates:
            print_info(f"Found {len(parent_candidates)} candidates in parent folder")

        # Priority 3: Suggested locations
        suggested = suggest_hub_locations(framework_path=current_path)
        for path in suggested:
            if path.exists() and not any(c.path == path for c in candidates):
                candidate = HubCandidate(path)
                candidate.add_score(1, "Suggested location")
                candidates.append(candidate)

        # Score all candidates
        for candidate in candidates:
            self._score_candidate(candidate)
            if self._candidate_has_project(candidate.path, current_path):
                candidate.add_score(12, "Registry contains current project")

        # Sort by score (highest first)
        candidates.sort(key=lambda c: c.score, reverse=True)

        if verbose and candidates:
            print_info(f"\nHub candidates (scored):")
            for i, candidate in enumerate(candidates[:5], 1):
                print_info(f"  {i}. {candidate.path} (score: {candidate.score})")
                for reason in candidate.reasons:
                    print_info(f"     {reason}")

        # Return best candidate if score >= 10 (has hub-profile.json)
        if candidates and candidates[0].score >= 10:
            return candidates[0].path

        return None

    def _scan_parent_folder(self, current_path: Path) -> List[HubCandidate]:
        """
        Scan parent folder for hub candidates.

        Looks for:
        - ../hub
        - ../WAI-Hub
        - ../*hub* (any folder with "hub" in name)

        Args:
            current_path: Current working directory

        Returns:
            List of hub candidates
        """
        candidates = []
        parent = current_path.parent

        if not parent.exists() or parent == current_path:
            return candidates

        # Scan parent directory
        try:
            for item in parent.iterdir():
                if not item.is_dir():
                    continue

                # Skip hidden folders
                if item.name.startswith('.'):
                    continue

                # Check if name contains "hub"
                name_lower = item.name.lower()
                if 'hub' in name_lower:
                    candidate = HubCandidate(item)

                    # Exact match "hub" gets bonus
                    if name_lower == 'hub':
                        candidate.add_score(5, "Name exactly 'hub'")
                    else:
                        candidate.add_score(3, f"Name contains 'hub' ({item.name})")

                    candidates.append(candidate)

                # Check for nested hubs within sibling repos (e.g., repo/hub)
                nested_hub = item / 'hub'
                if nested_hub.exists() and nested_hub.is_dir():
                    candidate = HubCandidate(nested_hub)
                    candidate.add_score(4, f"Nested hub in {item.name}/hub")
                    candidates.append(candidate)

                nested_wai_hub = item / 'WAI-Hub'
                if nested_wai_hub.exists() and nested_wai_hub.is_dir():
                    candidate = HubCandidate(nested_wai_hub)
                    candidate.add_score(4, f"Nested hub in {item.name}/WAI-Hub")
                    candidates.append(candidate)

        except PermissionError:
            pass  # Can't read parent directory

        return candidates

    def _candidate_has_project(self, hub_path: Path, project_path: Path) -> bool:
        """Return True if hub registry lists the given project path."""
        try:
            registry = hub_path / 'registry' / 'wheel-projects.json'
            if not registry.exists():
                return False
            data = json.loads(registry.read_text())
            for project in data.get('projects', []):
                path = project.get('path')
                if not path:
                    continue
                try:
                    if Path(path).resolve() == project_path.resolve():
                        return True
                except Exception:
                    if path == str(project_path):
                        return True
        except Exception:
            return False
        return False

    def _score_candidate(self, candidate: HubCandidate) -> None:
        """
        Score a hub candidate based on structure and metadata.

        Scoring:
        - Has hub-profile.json: +10
        - Has registry/wheel-projects.json: +5
        - Has WAI-Spoke/: -5 (likely a spoke, not hub)
        - Modified last 30 days: +2
        - Name exactly "hub": +1 (already added in scan)

        Args:
            candidate: HubCandidate to score
        """
        path = candidate.path

        # Check for hub-profile.json
        if (path / 'hub-profile.json').exists():
            candidate.add_score(10, "Has hub-profile.json")

        # Check for registry/wheel-projects.json
        if (path / 'registry' / 'wheel-projects.json').exists():
            candidate.add_score(5, "Has registry/wheel-projects.json")

        # Check for WAI-Spoke/ (deduct - likely a spoke)
        if (path / 'WAI-Spoke').exists():
            candidate.add_score(-5, "Has WAI-Spoke/ (likely a spoke, not hub)")

        # Check modification time
        try:
            # Check modification time of hub-profile.json if exists
            profile_file = path / 'hub-profile.json'
            if profile_file.exists():
                mtime = datetime.fromtimestamp(profile_file.stat().st_mtime)
                if datetime.now() - mtime < timedelta(days=30):
                    candidate.add_score(2, "Modified in last 30 days")
        except Exception:
            pass

    def verify_hub_structure(self, path: Path) -> Tuple[bool, Optional[str]]:
        """
        Verify valid hub structure.

        Required:
        - hub-profile.json exists
        - registry/ directory exists
        - registry/wheel-projects.json exists (or can be created)

        Args:
            path: Path to verify

        Returns:
            Tuple of (valid: bool, error_message: Optional[str])

        Examples:
            >>> valid, error = HubManager().verify_hub_structure(Path("/home/user/hub"))
            (True, None)
        """
        if not path.exists():
            return False, f"Path does not exist: {path}"

        if not path.is_dir():
            return False, f"Path is not a directory: {path}"

        # Check hub-profile.json
        hub_profile = path / 'hub-profile.json'
        if not hub_profile.exists():
            return False, f"Missing hub-profile.json at {path}"

        # Check registry directory
        registry_dir = path / 'registry'
        if not registry_dir.exists():
            return False, f"Missing registry/ directory at {path}"

        if not registry_dir.is_dir():
            return False, f"registry/ is not a directory at {path}"

        # Check wheel-projects.json (optional - will be created if needed)
        registry_file = registry_dir / 'wheel-projects.json'
        if not registry_file.exists():
            # Warning but not error - can be created
            pass

        return True, None

    def prompt_create_hub(
        self,
        default_path: Optional[Path] = None,
        framework_path: Optional[Path] = None
    ) -> Path:
        """
        Interactive hub creation with default ../hub.

        Args:
            default_path: Default hub path (usually ../hub)
            framework_path: Path to framework (for ../hub calculation)

        Returns:
            Path to created hub

        Raises:
            PathNotFoundError: If creation fails

        Examples:
            >>> hub_path = HubManager().prompt_create_hub(
            ...     framework_path=Path("/home/user/projects/framework")
            ... )
        """
        print_info("\n=== Hub Setup ===\n")

        # Calculate default if not provided
        if default_path is None and framework_path is not None:
            default_path = (framework_path.parent / 'hub').resolve()

        # Get suggestions
        suggestions = suggest_hub_locations(framework_path)

        # Show suggestions
        print_info("Suggested hub locations:")
        for i, suggestion in enumerate(suggestions[:3], 1):
            exists_marker = " (exists)" if suggestion.exists() else ""
            default_marker = " (default)" if suggestion == default_path else ""
            print_info(f"  {i}. {suggestion}{exists_marker}{default_marker}")

        # Prompt for path
        default_str = str(default_path) if default_path else None
        prompt = "\nHub location"

        hub_path_str = safe_input(
            prompt,
            default=default_str,
            validator=lambda s: len(s) > 0,
            max_length=500
        )

        if hub_path_str is None:
            raise PathNotFoundError("Hub creation cancelled by user")

        # Normalize path
        try:
            hub_path = normalize_path(hub_path_str)
        except Exception as e:
            raise PathNotFoundError(f"Invalid path: {e}")

        # Validate location
        valid, error = is_valid_hub_location(hub_path)
        if not valid:
            raise PathNotFoundError(error or "Invalid hub location")

        # Create hub structure
        self._create_hub_structure(hub_path)

        print_success(f"Hub created at {hub_path}")

        return hub_path

    def _create_hub_structure(self, hub_path: Path) -> None:
        """
        Create hub directory structure.

        Creates:
        - hub_path/
        - hub_path/hub-profile.json
        - hub_path/registry/
        - hub_path/registry/wheel-projects.json
        - hub_path/knowledge/ (KB structure)
        - hub_path/signals/ (signal aggregation)

        Args:
            hub_path: Path to create hub at

        Raises:
            PathNotFoundError: If creation fails
        """
        import json

        # Create directories
        ensure_directory(hub_path)
        ensure_directory(hub_path / 'registry')

        # Create hub-profile.json
        hub_profile = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "name": hub_path.name,
            "description": "Wheelwright Hub - Central learning repository"
        }

        hub_profile_path = hub_path / 'hub-profile.json'
        with open(hub_profile_path, 'w', encoding='utf-8') as f:
            json.dump(hub_profile, f, indent=2, ensure_ascii=False)
            f.write('\n')

        # Create wheel-projects.json
        registry = {
            "version": "2.0",
            "projects": [],
            "groups": {}
        }

        registry_path = hub_path / 'registry' / 'wheel-projects.json'
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            f.write('\n')

        # Create KB and signal structures
        self._create_kb_structure(hub_path)
        self._create_signal_structure(hub_path)

    def _create_kb_structure(self, hub_path: Path) -> None:
        """
        Create knowledge base directory structure.

        Creates:
        - hub_path/knowledge/
        - hub_path/knowledge/patterns/
        - hub_path/knowledge/decisions/
        - hub_path/knowledge/learnings/
        - hub_path/kb-manifest.json

        Args:
            hub_path: Path to hub root

        Raises:
            PathNotFoundError: If creation fails
        """
        try:
            # Create knowledge directories
            kb_path = hub_path / 'knowledge'
            ensure_directory(kb_path)
            ensure_directory(kb_path / 'patterns')
            ensure_directory(kb_path / 'decisions')
            ensure_directory(kb_path / 'learnings')

            # Create kb-manifest.json
            manifest = {
                "version": "1.0.0",
                "last_updated": datetime.now().isoformat(),
                "patterns_count": 0,
                "decisions_count": 0,
                "learnings_count": 0,
                "content_hash": ""
            }

            manifest_path = hub_path / 'kb-manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
                f.write('\n')

        except PermissionError as e:
            raise PathNotFoundError(f"Permission denied creating KB structure: {e}")
        except Exception as e:
            raise PathNotFoundError(f"Failed to create KB structure: {e}")

    def _create_signal_structure(self, hub_path: Path) -> None:
        """
        Create signal aggregation directory structure.

        Creates:
        - hub_path/signals/
        - hub_path/signals/by-spoke/
        - hub_path/signals/aggregated/
        - hub_path/signals/aggregated/by-type/

        Args:
            hub_path: Path to hub root

        Raises:
            PathNotFoundError: If creation fails
        """
        try:
            # Create signals directories
            signals_path = hub_path / 'signals'
            ensure_directory(signals_path)
            ensure_directory(signals_path / 'by-spoke')
            ensure_directory(signals_path / 'aggregated')
            ensure_directory(signals_path / 'aggregated' / 'by-type')

        except PermissionError as e:
            raise PathNotFoundError(f"Permission denied creating signal structure: {e}")
        except Exception as e:
            raise PathNotFoundError(f"Failed to create signal structure: {e}")

    def get_or_create_hub(
        self,
        current_path: Path,
        auto_discover: bool = True,
        verbose: bool = False
    ) -> Path:
        """
        Get existing hub or prompt to create one.

        Workflow:
        1. Try auto-discovery if enabled
        2. If found, verify structure
        3. If not found, prompt user to create

        Args:
            current_path: Current working directory (usually framework)
            auto_discover: Attempt auto-discovery first
            verbose: Print discovery progress

        Returns:
            Path to hub (existing or newly created)

        Examples:
            >>> hub = HubManager().get_or_create_hub(Path.cwd())
        """
        discovered_hub = None

        # Try auto-discovery
        if auto_discover:
            if verbose:
                print_info("Searching for existing hub...")

            discovered_hub = self.auto_discover_hub(current_path, verbose=verbose)

            if discovered_hub:
                # Verify structure
                valid, error = self.verify_hub_structure(discovered_hub)

                if valid:
                    if verbose:
                        print_success(f"Found valid hub at {discovered_hub}")
                    return discovered_hub
                else:
                    print_warning(f"Found hub at {discovered_hub} but invalid: {error}")
                    discovered_hub = None

        # Prompt to create hub
        if discovered_hub is None:
            print_info("\nNo valid hub found.")

            # Ask user
            create = safe_confirm("Create new hub?", default=True)

            if not create:
                raise InvalidHubError("Hub is required to proceed")

            # Prompt for location and create
            hub_path = self.prompt_create_hub(framework_path=current_path)
            return hub_path

        return discovered_hub


def get_hub_kb_version(hub_path: Path) -> str:
    """
    Get KB version from kb-manifest.json.

    Args:
        hub_path: Path to hub root

    Returns:
        Version string (e.g., "1.0.0")

    Raises:
        FileNotFoundError: If kb-manifest.json does not exist
        ValueError: If manifest is invalid or missing version

    Examples:
        >>> version = get_hub_kb_version(Path("/home/user/hub"))
        "1.0.0"
    """
    manifest_path = hub_path / 'kb-manifest.json'

    if not manifest_path.exists():
        raise FileNotFoundError(f"kb-manifest.json not found at {hub_path}")

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        version = manifest.get('version')
        if not version:
            raise ValueError("kb-manifest.json missing 'version' field")

        return version

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in kb-manifest.json: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read kb-manifest.json: {e}")


def get_hub_kb_hash(hub_path: Path) -> str:
    """
    Calculate content hash for KB change detection.

    Hashes all content in knowledge/ directory to detect changes.
    Uses SHA-256 hash of concatenated file contents sorted by path.

    Args:
        hub_path: Path to hub root

    Returns:
        SHA-256 hash string (hex)

    Examples:
        >>> hash_value = get_hub_kb_hash(Path("/home/user/hub"))
        "a3f5c8b2..."
    """
    import hashlib

    kb_path = hub_path / 'knowledge'

    if not kb_path.exists():
        return ""

    # Collect all files in knowledge/ directory
    files = []
    try:
        for pattern in ['patterns', 'decisions', 'learnings']:
            pattern_path = kb_path / pattern
            if pattern_path.exists():
                files.extend(sorted(pattern_path.glob('**/*')))
    except Exception:
        return ""

    # Calculate hash of all file contents
    hasher = hashlib.sha256()

    for file_path in sorted(files):
        if not file_path.is_file():
            continue

        try:
            # Hash relative path
            rel_path = file_path.relative_to(kb_path)
            hasher.update(str(rel_path).encode('utf-8'))

            # Hash file content
            with open(file_path, 'rb') as f:
                hasher.update(f.read())
        except Exception:
            # Skip files that can't be read
            continue

    return hasher.hexdigest()
