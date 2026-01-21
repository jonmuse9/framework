"""
Shipit Command - Closeout + Git Commit in one operation.

This module handles the 'shipit' command which combines a full closeout
with automatic git commit workflow.
"""

from pathlib import Path
from git import Repo
from git import exc as git_exc

from ..closeout import CloseoutProcessor
from ..bootstrap import refresh_bootstrap
from ..utils.input import safe_confirm, print_info, print_error, print_success, print_warning
from ..utils.paths import normalize_path, check_spoke_initialized


def cmd_shipit(args):
    """
    Execute shipit command - closeout + git commit.

    This command performs a complete closeout followed by an automated
    git commit workflow. It:
    1. Runs full closeout processing
    2. Refreshes bootstrap (if framework repo)
    3. Auto-stages WAI files
    4. Optionally stages other modified files
    5. Closes associated Lugs
    6. Updates CHANGELOG.md
    7. Generates commit message from session summary
    8. Creates commit and optionally pushes to remote

    Args:
        args: Argument namespace with:
            - path: Path to spoke directory
            - non_interactive: Skip confirmation prompts
            - skip_quality_gates: Skip quality gate checks
            - no_push: Don't push to remote after commit
    """
    try:
        spoke_path = normalize_path(args.path)

        # Check if spoke exists
        if not check_spoke_initialized(spoke_path):
            print_error(f"No spoke found at {spoke_path}")
            print_info("Run 'WAI init' to initialize a spoke first.")
            return

        # Check if this is a git repository
        try:
            repo = Repo(spoke_path, search_parent_directories=True)
        except git_exc.InvalidGitRepositoryError:
            print_error("Not a git repository.")
            print_info("Initialize git first: git init")
            return

        # Step 1: Run full closeout
        print_info("\n🚀 Shipit: Closeout + Git Commit\n")
        print_info("=" * 60)

        processor = CloseoutProcessor(spoke_path)
        results = processor.process_closeout(
            interactive=not args.non_interactive,
            skip_quality_gates=args.skip_quality_gates
        )

        # Check if closeout was aborted
        if results.get('errors') and any('aborted' in e.lower() for e in results['errors']):
            print_error("\nShipit aborted due to closeout errors.")
            return

        # Step 1.5: Refresh bootstrap (framework repo only)
        framework_root = Path(__file__).resolve().parent.parent.parent
        if spoke_path.resolve() == framework_root.resolve():
            print_info("\n  Refreshing bootstrap folder...")
            refresh_bootstrap(framework_root, verbose=True)

        # Step 2: Git workflow using GitPython
        print_info("\n" + "=" * 60)
        print_info("  Git Commit Workflow")
        print_info("=" * 60 + "\n")

        if not repo.is_dirty(untracked_files=True):
            print_info("  Working tree clean - nothing to commit.\n")
            return

        # Show what changed
        print_info("  Changed files:")
        for item in repo.index.diff(None) + repo.index.diff("HEAD"):
            print_info(f"    M {item.a_path}")
        for f in repo.untracked_files:
            print_info(f"    ?? {f}")
        print_info("")

        # Stage WAI state files and Lugs
        wai_files = [
            'WAI-Spoke/WAI-State.json',
            'WAI-Spoke/WAI-State.md',
            'WAI-Spoke/WAI-Guide.md',
            'WAI-Spoke/WAI-Signals.jsonl',
            'WAI-Spoke/lugs.jsonl',
            'WAI-Spoke/lugs-closed.jsonl',
            'WAI-Spoke/lug-sessions.jsonl',
            'WAI-Spoke/WAI-Point.json'
        ]

        files_to_commit = []
        for wai_file in wai_files:
            if (spoke_path / wai_file).exists():
                # Check if file is modified or untracked
                is_modified = any(item.a_path == wai_file for item in repo.index.diff(None))
                is_untracked = wai_file in repo.untracked_files
                if is_modified or is_untracked:
                    files_to_commit.append(wai_file)

        if files_to_commit:
            print_info("  Auto-staging WAI files:")
            for f in files_to_commit:
                print_info(f"    + {f}")
                repo.index.add([f])
            print_info("")

        # Ask about other files
        unstaged_files = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
        unstaged_files = [f for f in unstaged_files if not f.startswith('WAI-Spoke/')]

        if unstaged_files and not args.non_interactive:
            print_info("  Other modified files:")
            for f in unstaged_files:
                print_info(f"    {f}")
            print_info("")

            print_info("  The following files are modified or untracked but were not automatically staged by the Framework.")
            print_info("  You can choose to include them in this commit.")

            if safe_confirm("  Stage these files too?", default=True):
                for f in unstaged_files:
                    repo.index.add([f])
                    print_info(f"    + {f}")
                print_info("")

        # Get Lugs for this session to close
        session_state = processor.session.get_state()
        session_id = session_state.get('session_id')
        closed_lugs_info = []

        if session_id:
            from ..lugs import LugManager
            lug_manager = LugManager(spoke_path)
            session_lugs = lug_manager.get_session_lugs(session_id)

            if session_lugs:
                print_info(f"  Found {len(session_lugs)} Lugs associated with this session.")
                for lug in session_lugs:
                    if lug.status == 'open':
                        if args.non_interactive or safe_confirm(f"  Close Lug {lug.id} ({lug.title})?", default=True):
                            lug_manager.close_lug(lug.id, summary=results.get('session_summary', {}).get('summary', 'Closed via shipit'))
                            closed_lugs_info.append(f"{lug.id} ({lug.title})")

                # Ensure lug files are staged after closing
                repo.index.add(['WAI-Spoke/lugs.jsonl', 'WAI-Spoke/lugs-closed.jsonl'])

        # Update Changelog
        try:
            from ..changelog import ChangelogGenerator
            generator = ChangelogGenerator(Path(spoke_path))
            generator.update_changelog_file()
            if (Path(spoke_path) / "CHANGELOG.md").exists():
                repo.index.add(["CHANGELOG.md"])
            print_info("    [shipit] CHANGELOG.md updated.")
        except Exception as e:
            print_warning(f"    [shipit] Failed to update changelog: {e}")

        # Generate commit message
        session_summary = results.get('session_summary', {})
        summary_text = session_summary.get('summary', 'Session closeout')
        key_topics = session_summary.get('key_topics', [])
        turns = session_summary.get('turns', 0)
        baseline_summary = _get_latest_baseline_summary(spoke_path)

        lugs_msg = ""
        if closed_lugs_info:
            lugs_msg = "\nClosed Lugs:\n" + "\n".join([f"- {info}" for info in closed_lugs_info])

        commit_msg = f"""Session closeout: {summary_text[:60]}

{summary_text}

Session turns: {turns}
{f'Key topics: {", ".join(key_topics)}' if key_topics else ''}
{lugs_msg}
{baseline_summary}

🤖 Generated with [Wheelwright AI](https://github.com/mario/wheelwright-ai)
Co-Authored-By: Wheelwright AI <noreply@wheelwright.ai>"""

        # Create commit
        commit = repo.index.commit(commit_msg)
        print_success(f"\n  ✓ Commit {commit.hexsha[:7]} created successfully!\n")

        # Show commit details
        print_info(repo.git.log("-1", "--stat"))

        # Push to remote by default (unless --no-push)
        if not args.no_push:
            print_info("  Pushing to remote...")
            try:
                origin = repo.remote(name='origin')
                origin.push()
                print_success("  ✓ Pushed to remote successfully!\n")
            except Exception as e:
                print_error(f"  Push failed: {e}")
        else:
            print_info("  To push to remote, run: git push\n")

        print_info("=" * 60)
        print_success("  Shipit Complete!")
        print_info("=" * 60 + "\n")

    except Exception as e:
        print_error(f"Shipit command failed: {e}")
        import traceback
        traceback.print_exc()


def _get_latest_baseline_summary(spoke_path: Path) -> str:
    """
    Return a one-line summary of the latest baseline run, if available.

    Args:
        spoke_path: Path to spoke directory

    Returns:
        Formatted baseline summary string or empty string if not available
    """
    log_path = spoke_path / 'WAI-Spoke' / 'WAI-Baseline-Log.jsonl'
    if not log_path.exists():
        return ""

    last_line = ""
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():
                last_line = line

    if not last_line:
        return ""

    try:
        import json
        entry = json.loads(last_line)
        savings = entry.get("savings", {})
        percent = savings.get("percent_saved")
        ide = entry.get("ide", "Unknown IDE")
        model = entry.get("model", "Unknown Model")
        timestamp = entry.get("timestamp", "Unknown time")
        if percent is None:
            return f"Baseline run: {timestamp} | IDE: {ide} | Model: {model}"
        return f"Baseline run: {timestamp} | IDE: {ide} | Model: {model} | Saved: {percent}%"
    except Exception:
        return ""
