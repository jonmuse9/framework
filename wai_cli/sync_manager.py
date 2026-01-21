"""
Hub-Spoke Knowledge Base Synchronization Manager

Orchestrates KB synchronization between hub and spokes with version tracking.
"""

import json
import shutil
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime, timezone


class SyncManager:
    """Orchestrates hub-spoke synchronization."""

    def __init__(self, hub_path: Path, spoke_path: Path):
        """
        Initialize SyncManager.

        Args:
            hub_path: Path to hub directory
            spoke_path: Path to spoke project root
        """
        self.hub_path = hub_path
        self.spoke_path = spoke_path
        self.spoke_wai_dir = spoke_path / 'WAI-Spoke'
        self.hub_kb_dir = hub_path / 'knowledge'
        self.spoke_hub_kb_dir = self.spoke_wai_dir / 'hub-knowledge'

    def check_kb_version_mismatch(self) -> Tuple[bool, str, str]:
        """
        Compare hub vs spoke KB versions.

        Returns:
            Tuple of (needs_update, hub_version, spoke_version)

        Examples:
            >>> manager = SyncManager(hub_path, spoke_path)
            >>> needs_update, hub_v, spoke_v = manager.check_kb_version_mismatch()
            >>> if needs_update:
            ...     print(f"Update available: {spoke_v} -> {hub_v}")
        """
        hub_version = self._get_hub_kb_version()
        spoke_version = self._get_spoke_kb_version()

        needs_update = self._compare_versions(spoke_version, hub_version) < 0

        return needs_update, hub_version, spoke_version

    def download_kb_updates(self) -> Dict[str, Any]:
        """
        Download updated KB from hub to spoke.

        Workflow:
        1. Verify hub KB exists
        2. Create/clean spoke hub-knowledge directory
        3. Copy hub/knowledge/ -> spoke/WAI-Spoke/hub-knowledge/
        4. Update spoke's WAI-KB-Sync.json

        Returns:
            Dict with keys:
                - patterns_downloaded: int
                - learnings_downloaded: int
                - hub_version: str

        Raises:
            FileNotFoundError: If hub KB directory doesn't exist
            IOError: If download fails

        Examples:
            >>> result = manager.download_kb_updates()
            >>> print(f"Downloaded {result['patterns_downloaded']} patterns")
        """
        # Verify hub KB exists
        if not self.hub_kb_dir.exists():
            raise FileNotFoundError(f"Hub KB directory not found: {self.hub_kb_dir}")

        # Get hub version
        hub_version = self._get_hub_kb_version()

        # Create/clean spoke hub-knowledge directory
        if self.spoke_hub_kb_dir.exists():
            # Backup existing KB before replacing
            backup_dir = self.spoke_wai_dir / f'hub-knowledge.backup.{int(datetime.now(timezone.utc).timestamp())}'
            shutil.move(str(self.spoke_hub_kb_dir), str(backup_dir))

        self.spoke_hub_kb_dir.mkdir(parents=True, exist_ok=True)

        # Copy hub KB to spoke
        patterns_downloaded = 0
        learnings_downloaded = 0

        try:
            # Copy entire knowledge directory
            for item in self.hub_kb_dir.iterdir():
                dest = self.spoke_hub_kb_dir / item.name

                if item.is_file():
                    shutil.copy2(str(item), str(dest))

                    # Count patterns and learnings
                    if 'pattern' in item.name.lower():
                        patterns_downloaded += 1
                    elif 'learning' in item.name.lower():
                        learnings_downloaded += 1

                elif item.is_dir():
                    shutil.copytree(str(item), str(dest))

                    # Count files in subdirectories
                    for subitem in dest.rglob('*'):
                        if subitem.is_file():
                            if 'pattern' in subitem.name.lower():
                                patterns_downloaded += 1
                            elif 'learning' in subitem.name.lower():
                                learnings_downloaded += 1

            # Update sync metadata
            self.update_kb_sync_metadata('download', hub_version)

            return {
                'patterns_downloaded': patterns_downloaded,
                'learnings_downloaded': learnings_downloaded,
                'hub_version': hub_version
            }

        except Exception as e:
            # Rollback on error
            if self.spoke_hub_kb_dir.exists():
                shutil.rmtree(str(self.spoke_hub_kb_dir))

            # Restore backup if exists
            backup_dir = max(
                [d for d in self.spoke_wai_dir.glob('hub-knowledge.backup.*')],
                default=None,
                key=lambda d: d.stat().st_mtime
            )
            if backup_dir:
                shutil.move(str(backup_dir), str(self.spoke_hub_kb_dir))

            raise IOError(f"Failed to download KB updates: {e}") from e

    def update_kb_sync_metadata(self, sync_type: str, hub_version: Optional[str] = None) -> None:
        """
        Update WAI-KB-Sync.json with sync history.

        Args:
            sync_type: Type of sync operation ('download', 'upload', 'check')
            hub_version: Hub KB version (optional, will be queried if not provided)

        Examples:
            >>> manager.update_kb_sync_metadata('download', '1.2.0')
        """
        kb_sync_file = self.spoke_wai_dir / 'WAI-KB-Sync.json'

        # Load or create sync metadata
        if kb_sync_file.exists():
            try:
                with open(kb_sync_file, 'r', encoding='utf-8') as f:
                    sync_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Corrupted file - recreate from template
                sync_data = self._create_default_sync_metadata()
        else:
            sync_data = self._create_default_sync_metadata()

        # Get versions
        if hub_version is None:
            hub_version = self._get_hub_kb_version()

        # For download, spoke version should match hub version
        # For other sync types, get current spoke version
        if sync_type == 'download':
            spoke_version = hub_version
            sync_data['sync_status'] = 'synced'
        else:
            spoke_version = self._get_spoke_kb_version()

        # Update metadata
        sync_data['hub_kb_version'] = hub_version
        sync_data['spoke_kb_version'] = spoke_version
        sync_data['last_sync'] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Add to sync history
        if 'sync_history' not in sync_data:
            sync_data['sync_history'] = []

        sync_data['sync_history'].append({
            'timestamp': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'type': sync_type,
            'hub_version': hub_version,
            'spoke_version': spoke_version
        })

        # Keep only last 50 sync history entries
        if len(sync_data['sync_history']) > 50:
            sync_data['sync_history'] = sync_data['sync_history'][-50:]

        # Write updated metadata
        with open(kb_sync_file, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def _get_hub_kb_version(self) -> str:
        """
        Get KB version from hub's kb-manifest.json.

        Returns:
            Version string (e.g., "1.2.0")
        """
        manifest_file = self.hub_kb_dir / 'kb-manifest.json'

        if not manifest_file.exists():
            return "0.0.0"

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            return manifest.get('version', '0.0.0')
        except (json.JSONDecodeError, IOError):
            return "0.0.0"

    def _get_spoke_kb_version(self) -> str:
        """
        Get spoke's current KB version from WAI-KB-Sync.json.

        Returns:
            Version string (e.g., "1.2.0")
        """
        kb_sync_file = self.spoke_wai_dir / 'WAI-KB-Sync.json'

        if not kb_sync_file.exists():
            return "0.0.0"

        try:
            with open(kb_sync_file, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
            return sync_data.get('spoke_kb_version', '0.0.0')
        except (json.JSONDecodeError, IOError):
            return "0.0.0"

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two semantic version strings.

        Args:
            v1: First version (e.g., "1.2.0")
            v2: Second version (e.g., "1.3.0")

        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2

        Examples:
            >>> manager._compare_versions("1.0.0", "1.2.0")
            -1
            >>> manager._compare_versions("2.0.0", "1.9.9")
            1
            >>> manager._compare_versions("1.2.3", "1.2.3")
            0
        """
        try:
            # Parse version strings
            v1_parts = [int(x) for x in v1.split('.')]
            v2_parts = [int(x) for x in v2.split('.')]

            # Pad to same length
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            # Compare
            for p1, p2 in zip(v1_parts, v2_parts):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1

            return 0

        except (ValueError, AttributeError):
            # Invalid version format - treat as equal
            return 0

    def _create_default_sync_metadata(self) -> Dict[str, Any]:
        """
        Create default sync metadata structure.

        Returns:
            Dict with default sync metadata
        """
        return {
            "version": "1.0",
            "spoke_kb_version": "0.0.0",
            "hub_kb_version": "0.0.0",
            "last_sync": None,
            "sync_status": "never_synced",
            "sync_history": [],
            "_instructions": {
                "for_llms": "This file tracks synchronization between this spoke and its hub. Read only.",
                "sync_statuses": ["never_synced", "synced", "pending_push", "pending_pull", "conflict"]
            }
        }

    def upload_signals(self) -> Dict[str, Any]:
        """
        Upload high-impact signals from spoke to hub.

        Workflow:
        1. Read spoke's WAI-Signals.jsonl
        2. Filter for flags.ready_for_hub = true and impact >= 8
        3. Skip already-uploaded signals (check uploaded_to_hub_at)
        4. Check for duplicates by content hash
        5. Copy to hub/signals/by-spoke/[spoke-name]/signals.jsonl
        6. Append to aggregated collections
        7. Update spoke signals with uploaded_to_hub_at timestamp

        Returns:
            Dict with keys:
                - signals_uploaded: int
                - duplicates_skipped: int
                - signals_total: int

        Raises:
            FileNotFoundError: If spoke signals file doesn't exist
            IOError: If upload fails

        Examples:
            >>> result = manager.upload_signals()
            >>> print(f"Uploaded {result['signals_uploaded']} signals")
        """
        signals_file = self.spoke_wai_dir / 'WAI-Signals.jsonl'

        # Check if signals file exists
        if not signals_file.exists():
            # No signals to upload - not an error
            return {
                'signals_uploaded': 0,
                'duplicates_skipped': 0,
                'signals_total': 0
            }

        # Read and filter signals
        signals_to_upload: List[Dict[str, Any]] = []
        all_signals: List[str] = []
        signals_total = 0

        try:
            with open(signals_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    all_signals.append(line)

                    try:
                        signal = json.loads(line)
                        signals_total += 1

                        # Filter criteria:
                        # 1. Has flags.ready_for_hub = true OR impact >= 8
                        # 2. Not already uploaded (no uploaded_to_hub_at field)
                        flags = signal.get('flags', {})
                        impact = self._extract_max_impact(signal)
                        already_uploaded = 'uploaded_to_hub_at' in signal

                        # Check if signal should be uploaded
                        ready_for_hub = flags.get('ready_for_hub', False)
                        high_impact = impact >= 8

                        if (ready_for_hub or high_impact) and not already_uploaded:
                            signals_to_upload.append({
                                'line_num': line_num,
                                'signal': signal,
                                'original_line': line
                            })

                    except json.JSONDecodeError as e:
                        # Skip malformed signals
                        print(f"   Warning: Skipping malformed signal at line {line_num}: {e}")
                        continue

        except IOError as e:
            raise IOError(f"Failed to read signals file: {e}") from e

        # If no signals to upload, return early
        if not signals_to_upload:
            return {
                'signals_uploaded': 0,
                'duplicates_skipped': 0,
                'signals_total': signals_total
            }

        # Create hub signals directory structure
        spoke_name = self.spoke_path.name
        hub_signals_dir = self.hub_path / 'signals' / 'by-spoke' / spoke_name
        hub_signals_dir.mkdir(parents=True, exist_ok=True)

        hub_signals_file = hub_signals_dir / 'signals.jsonl'

        # Load existing hub signals for deduplication
        existing_hashes = self._load_existing_signal_hashes(hub_signals_file)

        # Upload signals
        signals_uploaded = 0
        duplicates_skipped = 0
        updated_signal_lines = []

        try:
            # Open hub signals file for appending
            with open(hub_signals_file, 'a', encoding='utf-8') as hub_f:
                for item in signals_to_upload:
                    signal = item['signal']

                    # Calculate content hash for deduplication
                    content_hash = self._calculate_signal_hash(signal)

                    # Check for duplicates
                    if content_hash in existing_hashes:
                        duplicates_skipped += 1
                        continue

                    # Mark signal as uploaded
                    signal['uploaded_to_hub_at'] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                    # Append to hub signals file
                    hub_f.write(json.dumps(signal, ensure_ascii=False) + '\n')

                    # Track uploaded signal
                    existing_hashes.add(content_hash)
                    signals_uploaded += 1

                    # Store updated signal line
                    updated_signal_lines.append({
                        'line_num': item['line_num'],
                        'signal': signal
                    })

            # Update spoke signals file with uploaded_to_hub_at timestamps
            if updated_signal_lines:
                self._update_spoke_signals_with_timestamps(signals_file, all_signals, updated_signal_lines)

            # Update sync metadata
            self.update_kb_sync_metadata('signal_upload')

            return {
                'signals_uploaded': signals_uploaded,
                'duplicates_skipped': duplicates_skipped,
                'signals_total': signals_total
            }

        except Exception as e:
            raise IOError(f"Failed to upload signals: {e}") from e

    def _extract_max_impact(self, signal: Dict[str, Any]) -> int:
        """
        Extract maximum impact value from signal.

        Checks:
        - signal.impact (if single value)
        - signal.offers[].impact (if array of offers)

        Args:
            signal: Signal dictionary

        Returns:
            Maximum impact value (default: 0)
        """
        # Check top-level impact
        if 'impact' in signal:
            return signal['impact']

        # Check offers array
        offers = signal.get('offers', [])
        if offers:
            max_impact = max((offer.get('impact', 0) for offer in offers), default=0)
            return max_impact

        return 0

    def _calculate_signal_hash(self, signal: Dict[str, Any]) -> str:
        """
        Calculate content hash for signal deduplication.

        Uses offers content, timestamp, and by field for hashing.

        Args:
            signal: Signal dictionary

        Returns:
            SHA256 hash string
        """
        # Build content string for hashing
        hash_parts = []

        # Include timestamp
        if 'timestamp' in signal:
            hash_parts.append(str(signal['timestamp']))

        # Include author
        if 'by' in signal:
            hash_parts.append(str(signal['by']))

        # Include offers
        if 'offers' in signal:
            # Sort offers by topic for consistent hashing
            sorted_offers = sorted(signal['offers'], key=lambda o: o.get('topic', ''))
            for offer in sorted_offers:
                hash_parts.append(offer.get('type', ''))
                hash_parts.append(offer.get('topic', ''))
                hash_parts.append(offer.get('context', ''))

        # Create hash
        content = '|'.join(hash_parts)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _load_existing_signal_hashes(self, hub_signals_file: Path) -> set:
        """
        Load hashes of existing signals from hub.

        Args:
            hub_signals_file: Path to hub signals JSONL file

        Returns:
            Set of signal hashes
        """
        hashes = set()

        if not hub_signals_file.exists():
            return hashes

        try:
            with open(hub_signals_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        signal = json.loads(line)
                        content_hash = self._calculate_signal_hash(signal)
                        hashes.add(content_hash)
                    except json.JSONDecodeError:
                        # Skip malformed signals
                        continue

        except IOError:
            # File read error - return empty set
            pass

        return hashes

    def _update_spoke_signals_with_timestamps(
        self,
        signals_file: Path,
        all_signals: List[str],
        updated_signal_lines: List[Dict[str, Any]]
    ) -> None:
        """
        Update spoke signals file with uploaded_to_hub_at timestamps.

        Args:
            signals_file: Path to spoke signals file
            all_signals: All signal lines (original)
            updated_signal_lines: List of updated signals with line numbers

        Raises:
            IOError: If file update fails
        """
        try:
            # Create mapping of line_num -> updated signal
            updates_map = {item['line_num']: item['signal'] for item in updated_signal_lines}

            # Rewrite signals file with updates
            with open(signals_file, 'w', encoding='utf-8') as f:
                for line_num, original_line in enumerate(all_signals, 1):
                    if line_num in updates_map:
                        # Write updated signal
                        f.write(json.dumps(updates_map[line_num], ensure_ascii=False) + '\n')
                    else:
                        # Write original line
                        f.write(original_line + '\n')

        except IOError as e:
            raise IOError(f"Failed to update spoke signals file: {e}") from e

    def calculate_sync_health(self) -> Dict[str, Any]:
        """
        Calculate sync health metrics.

        Returns:
            Dict with keys:
                - status: "healthy" | "stale" | "outdated" | "never_synced"
                - days_since_last_sync: int or None
                - kb_version_drift: str or None (e.g., "2 versions behind")
                - pending_signals: int
                - last_check: timestamp

        Examples:
            >>> manager = SyncManager(hub_path, spoke_path)
            >>> health = manager.calculate_sync_health()
            >>> if health['status'] != 'healthy':
            ...     print(f"Sync recommended: {health['status']}")
        """
        kb_sync_file = self.spoke_wai_dir / 'WAI-KB-Sync.json'

        # Load sync metadata
        sync_data = None
        if kb_sync_file.exists():
            try:
                with open(kb_sync_file, 'r', encoding='utf-8') as f:
                    sync_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Corrupted file - treat as never synced
                sync_data = None

        # Calculate days since last sync
        days_since_last_sync = None
        last_sync = sync_data.get('last_sync') if sync_data else None

        if last_sync:
            try:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                delta = now - last_sync_dt
                days_since_last_sync = delta.days
            except (ValueError, AttributeError):
                # Invalid timestamp - treat as never synced
                last_sync = None

        # Calculate KB version drift
        kb_version_drift = None
        if sync_data and self.hub_kb_dir.exists():
            try:
                hub_version = self._get_hub_kb_version()
                spoke_version = sync_data.get('spoke_kb_version', '0.0.0')

                comparison = self._compare_versions(spoke_version, hub_version)

                if comparison < 0:
                    # Spoke is behind hub - calculate drift
                    hub_parts = [int(x) for x in hub_version.split('.')]
                    spoke_parts = [int(x) for x in spoke_version.split('.')]

                    # Pad to same length
                    max_len = max(len(hub_parts), len(spoke_parts))
                    hub_parts.extend([0] * (max_len - len(hub_parts)))
                    spoke_parts.extend([0] * (max_len - len(spoke_parts)))

                    # Determine drift type
                    if hub_parts[0] > spoke_parts[0]:
                        # Major version drift
                        major_diff = hub_parts[0] - spoke_parts[0]
                        kb_version_drift = f"{major_diff} major version{'s' if major_diff > 1 else ''} behind"
                    elif hub_parts[1] > spoke_parts[1]:
                        # Minor version drift
                        minor_diff = hub_parts[1] - spoke_parts[1]
                        kb_version_drift = f"{minor_diff} minor version{'s' if minor_diff > 1 else ''} behind"
                    else:
                        # Patch version drift
                        patch_diff = hub_parts[2] - spoke_parts[2]
                        kb_version_drift = f"{patch_diff} patch version{'s' if patch_diff > 1 else ''} behind"
            except (ValueError, AttributeError, FileNotFoundError):
                # Can't determine drift - skip
                kb_version_drift = None

        # Count pending signals
        pending_signals = 0
        signals_file = self.spoke_wai_dir / 'WAI-Signals.jsonl'

        if signals_file.exists():
            try:
                with open(signals_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            signal = json.loads(line)

                            # Check if signal is ready for hub and not uploaded
                            flags = signal.get('flags', {})
                            impact = self._extract_max_impact(signal)
                            already_uploaded = 'uploaded_to_hub_at' in signal

                            ready_for_hub = flags.get('ready_for_hub', False)
                            high_impact = impact >= 8

                            if (ready_for_hub or high_impact) and not already_uploaded:
                                pending_signals += 1
                        except json.JSONDecodeError:
                            # Skip malformed signals
                            continue
            except IOError:
                # Can't read signals - assume 0 pending
                pass

        # Determine health status
        if last_sync is None:
            status = "never_synced"
        elif days_since_last_sync is not None:
            # Check for version drift
            has_major_drift = kb_version_drift and 'major' in kb_version_drift
            has_minor_drift = kb_version_drift and 'minor' in kb_version_drift

            if days_since_last_sync > 90 or has_major_drift:
                status = "outdated"
            elif days_since_last_sync > 30 or has_minor_drift:
                status = "stale"
            else:
                status = "healthy"
        else:
            status = "healthy"

        return {
            'status': status,
            'days_since_last_sync': days_since_last_sync,
            'kb_version_drift': kb_version_drift,
            'pending_signals': pending_signals,
            'last_check': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
