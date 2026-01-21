"""
Smart closeout processor for Wheelwright sessions.

Handles end-of-session processing including:
- File scanning and reconciliation
- Content rebalancing
- Signal extraction
- Analytics recording
- Log cleanup
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .session import SessionManager
from .rebalancer import FileRebalancer
from .metrics import MetricsTracker
from .quality_gates import QualityGates
from .utils.input import print_success, print_error, print_info, print_warning, safe_confirm
from .integrations.manager import IDEManager
import os
import subprocess


class CloseoutProcessor:
    """Processes session closeout comprehensively."""

    def __init__(self, spoke_dir: Path):
        """Initialize closeout processor."""
        self.spoke_dir = spoke_dir
        self.wai_spoke_dir = spoke_dir / 'WAI-Spoke'

        # Initialize components
        self.session = SessionManager(spoke_dir)
        self.rebalancer = FileRebalancer(self.wai_spoke_dir)
        self.metrics = MetricsTracker(self.wai_spoke_dir)
        self.quality_gates = QualityGates(spoke_dir)

    def process_closeout(self, interactive: bool = True) -> Dict[str, Any]:
        """
        Execute complete closeout workflow.

        Args:
            interactive: If True, prompts user for confirmations

        Returns:
            Dict with closeout summary
        """
        print_info("\n🔄 Processing Session Closeout...\n")

        results = {
            'steps_completed': [],
            'warnings': [],
            'errors': [],
            'session_summary': {},
            'quality_gates': {}
        }

        # Step 0: Run Quality Gates (unless truly minor changes)
        print_info("  Step 0/10: Running quality gates...")
        gate_results = self.quality_gates.run_all_gates(skip_minor=True)
        results['quality_gates'] = gate_results

        if gate_results.get('skip_reason'):
            print_info(f"    ⚠️  {gate_results['skip_reason']}")
            results['steps_completed'].append(f"Quality gates: {gate_results['skip_reason']}")
        elif not gate_results['passed']:
            # Quality gates failed
            print_warning("    ⚠️  Quality gates failed!")

            for blocker in gate_results.get('blockers', []):
                print_error(f"      ✗ BLOCKER: {blocker}")

            for warning in gate_results.get('warnings', []):
                print_warning(f"      ⚠️  {warning}")

            if interactive and gate_results.get('blockers'):
                print_info("\n  Quality gate blockers detected. Continue anyway?")
                if not safe_confirm("Proceed with closeout despite blockers?", default=False):
                    results['errors'].append("Closeout aborted due to quality gate failures")
                    return results

            results['steps_completed'].append(f"Quality gates: Failed with {len(gate_results.get('blockers', []))} blockers")
        else:
            print_success("    ✓ All quality gates passed")
            results['steps_completed'].append("Quality gates: Passed")

        # Step 1: Process seed folders and clean up sprawl
        print_info("  Step 1/10: Processing seed folders and cleanup...")
        seed_result = self._process_seed_and_cleanup(interactive)
        results['steps_completed'].append(seed_result['summary'])
        results['warnings'].extend(seed_result.get('warnings', []))

        # Step 2: Reconcile WAI-Hub-Learnings.md if exists
        print_info("  Step 2/10: Reconciling hub learnings...")
        learnings_reconciled = self._reconcile_hub_learnings()
        if learnings_reconciled:
            results['steps_completed'].append("Reconciled hub learnings into WAI-Guide.md")

        # Step 3: Run file rebalancer
        print_info("  Step 3/10: Rebalancing file content...")
        rebalance_result = self.rebalancer.rebalance()
        if rebalance_result['rebalanced']:
            results['steps_completed'].append(f"Rebalanced files: {len(rebalance_result['actions'])} actions")
        else:
            results['steps_completed'].append("Files balanced: no action needed")

        # Step 4: Extract session summary
        print_info("  Step 4/10: Extracting session summary...")
        session_summary = self.session.extract_session_summary()
        results['session_summary'] = session_summary
        results['steps_completed'].append(f"Extracted summary: {session_summary['turns']} turns")

        # Step 5: Extract high-impact signals
        print_info("  Step 5/10: Extracting high-impact signals...")
        signals_extracted = self._extract_signals()
        if signals_extracted > 0:
            results['steps_completed'].append(f"Extracted {signals_extracted} high-impact signals")
        else:
            results['steps_completed'].append("No new signals to extract")

        # Step 6: Record analytics
        print_info("  Step 6/10: Recording session analytics...")
        self._record_analytics(session_summary)
        results['steps_completed'].append("Recorded session analytics")

        # Step 7: Update session state and clear log
        print_info("  Step 7/10: Finalizing closeout...")
        self._finalize_closeout(session_summary)
        results['steps_completed'].append("Finalized: state updated, log cleared")

        # Step 8: Refresh integrations and optionally re-brief active session
        print_info("  Step 8/10: Refreshing integrations...")
        integration_status = self._refresh_integrations()
        results['integration_status'] = integration_status
        results['steps_completed'].append(f"Integrations refreshed: {integration_status['updated']} updated")

        # Step 9: Check sync health
        print_info("  Step 9/10: Checking sync health...")
        sync_health = self._check_sync_health()
        if sync_health:
            results['sync_health'] = sync_health
            if sync_health['status'] in ['stale', 'outdated']:
                warning_msg = f"Sync recommended: {sync_health['status']}"
                if sync_health['pending_signals'] > 0:
                    warning_msg += f" ({sync_health['pending_signals']} pending signals)"
                results['warnings'].append(warning_msg)
                results['steps_completed'].append(f"Sync health: {sync_health['status']} - sync recommended")
            else:
                results['steps_completed'].append(f"Sync health: {sync_health['status']}")
        else:
            results['steps_completed'].append("Sync health: No hub found")

        print_success("\n✓ Closeout Complete!\n")

        return results

    def _process_seed_and_cleanup(self, interactive: bool) -> Dict[str, Any]:
        """Process seed folders and auto-archive unknown items."""
        from .spoke_update import SpokeUpdateProcessor

        updater = SpokeUpdateProcessor(self.spoke_dir)
        plan = updater.plan_update()

        ingest_count = len(plan.get("ingest_files", []))
        ref_count = len(plan.get("reference_files", []))
        unknown_count = len(plan.get("unknown_items", []))

        if interactive and (ingest_count or ref_count or unknown_count):
            print_info(f"    Seed ingest: {ingest_count} file(s)")
            print_info(f"    Seed reference: {ref_count} file(s)")
            print_info(f"    Unknown items: {unknown_count}")
            print_info("    Running update to ingest and archive.")

        results = updater.run_update()
        summary_parts = []
        if results["ingested"]:
            summary_parts.append(f"ingested {len(results['ingested'])}")
            if interactive and results.get("ingest_notes"):
                print_info("    Ingested files:")
                for note in results["ingest_notes"]:
                    targets = ", ".join(note.get("applied_to", []))
                    preview = note.get("preview", "")
                    print_info(f"      - {note.get('file')} → {targets}")
                    if preview:
                        print_info(f"        preview: {preview}")
        if results["archived_reference"]:
            summary_parts.append(f"archived {len(results['archived_reference'])} reference")
        if results["archived_unknown"]:
            summary_parts.append(f"archived {len(results['archived_unknown'])} unknown")

        summary = "Seed/update: " + (", ".join(summary_parts) if summary_parts else "no changes")
        return {
            "summary": summary,
            "warnings": results.get("warnings", [])
        }

    def _reconcile_hub_learnings(self) -> bool:
        """
        Reconcile WAI-Hub-Learnings.md into WAI-Guide.md.

        Returns:
            True if learnings were reconciled
        """
        learnings_file = self.wai_spoke_dir / 'WAI-Hub-Learnings.md'
        guide_file = self.wai_spoke_dir / 'WAI-Guide.md'

        if not learnings_file.exists():
            return False

        # Read learnings content
        learnings_content = learnings_file.read_text()

        # Read existing guide
        guide_content = guide_file.read_text()

        # Add hub learnings section if not exists
        hub_section_header = "\n## Hub Learnings\n\n"
        if hub_section_header not in guide_content:
            guide_content += hub_section_header

        # Extract just the patterns (skip header and instructions)
        import re
        pattern_sections = re.findall(r'## (Pattern|Decision|Insight|Warning).*?(?=##|$)', learnings_content, re.DOTALL)

        # Append new patterns to guide
        for section in pattern_sections:
            guide_content += f"\n## {section}\n"

        # Write updated guide
        guide_file.write_text(guide_content)

        # Delete learnings file (reconciled)
        learnings_file.unlink()

        print_success("  ✓ Reconciled hub learnings into WAI-Guide.md")

        return True

    def _extract_signals(self) -> int:
        """
        Extract high-impact signals from session.

        Returns:
            Number of signals extracted
        """
        # For now, return 0 - this will be enhanced in Phase 4
        # to actually analyze conversation log for patterns
        return 0

    def _record_analytics(self, session_summary: Dict[str, Any]) -> None:
        """Record session completion in analytics."""
        # Calculate session duration (placeholder - will be real in session tracking)
        session_data = {
            'session_id': 'manual-closeout',  # Will be real session ID
            'turns': session_summary.get('turns', 0),
            'tokens_estimate': 0,  # Will be calculated from log
            'duration_seconds': 0,  # Will be real duration
            'time_together_seconds': 0,  # Placeholder
            'time_ai_alone_seconds': 0,  # Placeholder
        }

        self.metrics.record_session_end(session_data)

    def _finalize_closeout(self, session_summary: Dict[str, Any]) -> None:
        """Finalize closeout by updating state and clearing log."""
        state_file = self.wai_spoke_dir / 'WAI-State.json'

        with open(state_file, 'r') as f:
            state = json.load(f)

        # Move current_session to last_closeout
        current_session = state.get('_session_state', {}).get('current_session')

        if current_session:
            state['_session_state']['last_closeout'] = {
                **current_session,
                'closed_at': datetime.now().isoformat(),
                'summary': session_summary.get('summary', 'Session complete'),
                'key_topics': session_summary.get('key_topics', []),
                'files_modified': session_summary.get('files_modified', [])
            }

        # Clear current session
        state['_session_state']['current_session'] = None
        state['_session_state']['protocol_completed'] = False
        state['_session_state']['requires_review'] = False

        # Save state
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        # Clear conversation log
        self.session.clear_log()

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print closeout summary."""
        print_info("\n" + "=" * 60)
        print_success("  Session Closeout Summary")
        print_info("=" * 60 + "\n")

        session_summary = results['session_summary']

        print_info(f"  Turns: {session_summary.get('turns', 0)}")
        print_info(f"  Summary: {session_summary.get('summary', 'N/A')[:100]}...")

        if session_summary.get('key_topics'):
            print_info(f"  Key topics: {', '.join(session_summary['key_topics'])}")

        if session_summary.get('files_modified'):
            print_info(f"  Files modified: {len(session_summary['files_modified'])}")

        print_info("\n  Steps completed:")
        for step in results['steps_completed']:
            print_success(f"    ✓ {step}")

        if results['warnings']:
            print_info("\n  Warnings:")
            for warning in results['warnings']:
                print_warning(f"    ⚠️  {warning}")

        # Show sync health if needs attention
        sync_health = results.get('sync_health')
        if sync_health and sync_health['status'] in ['stale', 'outdated', 'never_synced']:
            print_info("\n  Sync Health:")
            print_warning(f"    ⚠️  Status: {sync_health['status']}")
            if sync_health['pending_signals'] > 0:
                print_warning(f"    ⚠️  {sync_health['pending_signals']} pending signals ready for upload")
            if sync_health['kb_version_drift']:
                print_warning(f"    ⚠️  KB drift: {sync_health['kb_version_drift']}")
            print_info(f"    → Run 'WAI sync' to synchronize with hub")

        if results['errors']:
            print_info("\n  Errors:")
            for error in results['errors']:
                print_error(f"    ✗ {error}")

        print_info("\n" + "=" * 60)
        print_info("  WAI-Spoke/ folder ready for hub learning")

        integration_status = results.get('integration_status')
        if integration_status:
            print_info("  Integrations verified and refreshed")
            updated = integration_status.get('updated', 0)
            print_info(f"  Integration files updated: {updated}")

            statuses = integration_status.get('statuses', {})
            if statuses:
                print_info("  Integration status:")
                for name, status in statuses.items():
                    print_info(f"    - {name}: {status}")

            if integration_status.get('session_refreshed'):
                print_info("  Codex session refreshed - integrations active")
            else:
                print_info("  Start new session with fresh context")
        else:
            print_info("  Start new session with fresh context")

        print_info("=" * 60 + "\n")

    def _refresh_integrations(self) -> Dict[str, Any]:
        """Refresh integration files and optionally re-brief active session."""
        manager = IDEManager(self.spoke_dir)
        updated = 0
        statuses = {}

        for ide in manager.all_integrations:
            config_path = ide.config_file_path
            generated = ide.generate_config()
            current = config_path.read_text() if config_path.exists() else None

            if current != generated:
                ide.write_config(generated)
                updated += 1
                statuses[ide.name] = "updated"
            else:
                statuses[ide.name] = "up_to_date"

        session_refreshed = False
        hook_output = ""
        hook_path = self.spoke_dir / "WAI-Spoke" / "hooks" / "session-start.sh"
        if hook_path.exists():
            env = os.environ.copy()
            env["WAI_PROJECT_DIR"] = str(self.spoke_dir)
            result = subprocess.run(
                [str(hook_path)],
                cwd=self.spoke_dir,
                env=env,
                capture_output=True,
                text=True
            )
            hook_output = (result.stdout or "").strip()
            session_refreshed = True

        return {
            "updated": updated,
            "statuses": statuses,
            "session_refreshed": session_refreshed,
            "briefing_emitted": bool(hook_output)
        }

    def _check_sync_health(self) -> Optional[Dict[str, Any]]:
        """
        Check sync health with hub.

        Returns:
            Sync health dict or None if no hub found
        """
        from .hub import HubManager
        from .sync_manager import SyncManager

        # Find hub
        hub_manager = HubManager()
        hub_path = hub_manager.auto_discover_hub(self.spoke_dir, verbose=False)

        if not hub_path:
            return None

        try:
            sync_manager = SyncManager(hub_path, self.spoke_dir)
            health = sync_manager.calculate_sync_health()
            return health
        except Exception:
            # Silently skip if sync health check fails
            return None


def generate_closeout() -> None:
    """Generate session closeout (legacy function for backward compatibility)."""
    print_warning("\n⚠️  Using legacy closeout stub.")
    print_info("Use CloseoutProcessor for full functionality.\n")
