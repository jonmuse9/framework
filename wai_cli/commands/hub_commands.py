"""
Hub management commands for Wheelwright CLI

This module contains all hub-related command handlers including:
- Hub creation and discovery
- Hub learn/teach cycles (knowledge distribution)
- Hub subsumption (merging multiple hubs)
- Hub candidate management
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from ..hub import HubManager, HubCandidate
from ..init import init_spoke
from ..utils.input import print_info, print_success, print_error, safe_input, safe_confirm
from ..utils.paths import normalize_path
from ..utils.registry import load_registry


def cmd_hub(cli, args):
    """Handle hub commands."""
    if args.hub_command == 'create':
        hub_create(cli, args)
    elif args.hub_command == 'locate':
        hub_locate(cli)
    else:
        print_info("Hub commands: create, locate")


def hub_create(cli, args):
    """Create new hub."""
    hub_manager = HubManager()

    if args.path:
        try:
            hub_path = normalize_path(args.path)
            hub_manager.prompt_create_hub(default_path=hub_path)
        except Exception as e:
            print_error(f"Hub creation failed: {e}")
    else:
        # Interactive with default ../hub
        try:
            cwd = Path.cwd()
            default_path = (cwd.parent / 'hub').resolve()
            hub_manager.prompt_create_hub(default_path=default_path, framework_path=cwd)
        except Exception as e:
            print_error(f"Hub creation failed: {e}")


def hub_locate(cli):
    """Locate hub."""
    hub_manager = HubManager()
    cwd = Path.cwd()

    hub_path = hub_manager.auto_discover_hub(cwd, verbose=True)

    if hub_path:
        print_success(f"\nHub found at: {hub_path}")
    else:
        print_info("\nNo hub found.")
        print_info("Run 'WAI hub create' to create a new hub.")


def hub_locate_with_candidates(cli):
    """Locate hub and show all candidates with selection options."""
    hub_manager = HubManager()
    cwd = Path.cwd()

    print_info("\n🔍 Scanning for hub candidates...\n")

    # Get all candidates (modify auto_discover to return all)
    candidates = get_all_hub_candidates(cli, cwd)

    if not candidates:
        print_info("  No hub candidates found.")
        print_info("  Run 'Create' to initialize a new hub.")
        return

    # Show all candidates
    print_info(f"  Found {len(candidates)} hub candidate(s):\n")
    for i, candidate in enumerate(candidates, 1):
        print_info(f"  [{i}] {candidate.path} (score: {candidate.score})")
        for reason in candidate.reasons[:3]:  # Show top 3 reasons
            print_info(f"      {reason}")
        print_info("")

    if len(candidates) == 1:
        print_success(f"  Using hub: {candidates[0].path}")
        return

    # Multiple candidates - prompt for selection
    print_info("  Multiple hub candidates found. What would you like to do?\n")
    print_info("  1. Use highest-scored hub (recommended)")
    print_info("  2. Select specific hub")
    print_info("  3. Cancel\n")

    choice = safe_input("  Choice", default="1")

    if choice == "1":
        selected = candidates[0]
        print_success(f"\n  Selected: {selected.path}")
    elif choice == "2":
        idx = safe_input(f"  Select hub (1-{len(candidates)})", default="1")
        try:
            selected = candidates[int(idx) - 1]
            print_success(f"\n  Selected: {selected.path}")
        except (ValueError, IndexError):
            print_info("\n  Invalid selection.")
            return
    else:
        return

    # Ask about other candidates
    if len(candidates) > 1:
        print_info(f"\n  Other candidates found:")
        for candidate in candidates[1:]:
            print_info(f"    - {candidate.path}")

        action = safe_input("\n  Action for other hubs? (ignore/subsume/skip)", default="skip")

        if action == "ignore":
            print_info("\n  Ignoring other hubs...")
            hub_ignore_candidates(cli, [c.path for c in candidates[1:]], selected.path)
        elif action == "subsume":
            print_info("\n  Subsuming other hubs into primary...")
            for candidate in candidates[1:]:
                hub_subsume(cli, source_hub=candidate.path, target_hub=selected.path)


def get_all_hub_candidates(cli, current_path: Path) -> List:
    """Get all hub candidates with scoring."""
    hub_manager = HubManager()

    # Use internal methods to get all candidates
    candidates = []

    # Environment variable
    env_hub = os.environ.get('WHEELWRIGHT_HUB_PATH')
    if env_hub:
        try:
            env_path = normalize_path(env_hub)
            if env_path.exists():
                candidate = HubCandidate(env_path)
                candidate.add_score(15, "From $WHEELWRIGHT_HUB_PATH")
                candidates.append(candidate)
        except Exception:
            pass

    # Parent folder scan
    parent_candidates = hub_manager._scan_parent_folder(current_path)
    candidates.extend(parent_candidates)

    # Score all candidates
    for candidate in candidates:
        hub_manager._score_candidate(candidate)

    # Sort by score
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Return ALL candidates (not filtered by score)
    # This allows user to see and choose even low-scored options
    return candidates


def hub_trigger_teach(cli, hub_path: Path):
    """Trigger teach event - hub learns from spokes (called by 'Learn' menu option)."""
    print_info("\n📚 Learn Event - Hub Learns from Spoke Projects\n")

    # Load and show registered spokes
    try:
        registry = load_registry(hub_path)
        spokes = registry.get('projects', [])  # Registry uses 'projects' not 'spokes'

        if not spokes:
            print_info("  No spokes registered in hub.")
            print_info("  Add spokes first: Main Menu → Spokes → Add Projects")
            return

        print_info("  📊 Preview of what will happen:")
        print_info("")
        print_info(f"  Hub: {hub_path.name}")
        print_info(f"  Spokes to scan: {len(spokes)}")
        print_info("")
        for spoke in spokes[:5]:  # Show first 5
            spoke_name = spoke.get('preferred_name', spoke.get('path', 'Unknown'))
            print_info(f"    • {spoke_name}")
        if len(spokes) > 5:
            print_info(f"    ... and {len(spokes) - 5} more")
        print_info("")
        print_info("  Actions:")
        print_info("    1. Scan each spoke's WAI-Signals.jsonl")
        print_info("    2. Extract high-impact learnings (impact ≥8)")
        print_info("    3. Update hub knowledge base")
        print_info("    4. Record learn timestamp")
        print_info("")

        if not safe_confirm("  Proceed with learning from spokes?", default=False):
            print_info("  Cancelled.")
            return

        # Actually perform the learning
        print_info("\n  📚 Hub learning from spokes...")
        print_info("")

        # Create knowledge base directory if it doesn't exist
        kb_dir = hub_path / 'knowledge-base'
        kb_dir.mkdir(exist_ok=True)

        total_new_signals = 0
        spoke_results = []

        for spoke in spokes:
            spoke_path = Path(spoke.get('path', ''))
            spoke_name = spoke.get('preferred_name', spoke_path.name)

            # Look for WAI-Signals.jsonl in the spoke
            signals_file = spoke_path / 'WAI-Spoke' / 'WAI-Signals.jsonl'
            if not signals_file.exists():
                spoke_results.append((spoke_name, 0, "No signals file"))
                continue

            try:
                # Read spoke signals
                new_signals = []

                # 1. Standard signals
                if signals_file.exists():
                    with open(signals_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    signal = json.loads(line)
                                    if signal.get('impact', 0) >= 8:
                                        new_signals.append(signal)
                                except: pass

                # 2. Promote significant Lugs
                closed_lugs_file = spoke_path / 'WAI-Spoke' / 'lugs-closed.jsonl'
                if closed_lugs_file.exists():
                    with open(closed_lugs_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    # Use a simplified parser or LugManager if available,
                                    # but direct JSON for speed during hub sync
                                    lug_data = json.loads(line)
                                    # Map minified keys if necessary, but here we assume impact/priority
                                    # are stored in lugs.jsonl logic
                                    impact = lug_data.get('i', 0) if 'i' in lug_data else lug_data.get('impact_score', 0)
                                    priority = lug_data.get('p', '') if 'p' in lug_data else lug_data.get('priority', '')

                                    if (impact >= 8 or priority == 'high'):
                                        new_signals.append({
                                            'type': 'lug_promotion',
                                            'id': lug_data.get('id', 'unknown'),
                                            'title': lug_data.get('title', 'Untitled Lug'),
                                            'summary': lug_data.get('summary', ''),
                                            'impact': impact,
                                            'timestamp': lug_data.get('closed_at', datetime.now().isoformat()),
                                            'origin_spoke': spoke_name
                                        })
                                except: pass

                if new_signals:
                    # Append to hub knowledge
                    target_file = kb_dir / f"{spoke_name}-signals.jsonl"

                    existing_ids = set()
                    if target_file.exists():
                        with open(target_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                try:
                                    s = json.loads(line)
                                    if 'id' in s: existing_ids.add(s['id'])
                                except: pass

                    added = 0
                    with open(target_file, 'a', encoding='utf-8') as f:
                        for signal in new_signals:
                            if signal.get('id') not in existing_ids:
                                f.write(json.dumps(signal) + "\n")
                                added += 1

                    spoke_results.append((spoke_name, added, "Updated"))
                    total_new_signals += added
                else:
                    spoke_results.append((spoke_name, 0, "No high-impact signals"))

            except Exception as e:
                spoke_results.append((spoke_name, 0, f"Error: {e}"))

        # Generate Hub Index (Map)
        from ..hub_indexer import HubIndexer
        try:
            print_info("  🗺️  Regenerating Hub Index...")
            indexer = HubIndexer(hub_path)
            index_path = indexer.generate_index()
            print_success(f"     Index updated: {index_path.name}")
        except Exception as e:
            print_error(f"     Failed to generate index: {e}")

        # Display results
        print_info("  Results by spoke:")
        print_info("")
        for spoke_name, count, status in spoke_results:
            if count > 0:
                print_success(f"    ✓ {spoke_name}: {count} new signal(s) - {status}")
            else:
                print_info(f"      {spoke_name}: {count} new signals - {status}")

        print_info("")
        if total_new_signals > 0:
            print_success(f"  ✓ Learn complete! Added {total_new_signals} new signal(s) to hub knowledge base")

            # Update hub profile with last learn timestamp
            profile_path = hub_path / 'hub-profile.json'
            if profile_path.exists():
                try:
                    profile = json.loads(profile_path.read_text())
                    profile['last_learn_run'] = datetime.now().isoformat()
                    profile_path.write_text(json.dumps(profile, indent=2))
                except:
                    pass
        else:
            print_info(f"  ✓ Learn complete! No new signals found (all spokes already absorbed)")

        print_info("")
        print_info("  📝 Next: To apply these learnings in an active AI session:")
        print_info("     1. If AI is already working on a spoke project:")
        print_info("        - Say 'Closeout' to end current session")
        print_info("        - Start new session to load updated WAI-Guide.md")
        print_info("     2. Hub knowledge is now available in hub/knowledge-base/")
        print_info("     3. Run 'Teach' to distribute to specific spokes")

    except Exception as e:
        print_error(f"  Error loading registry: {e}")


def hub_trigger_learn(cli, hub_path: Path):
    """Trigger learn event - spokes learn from hub (called by 'Teach' menu option)."""
    print_info("\n🎓 Teach Event - Hub Distributes Knowledge to Spokes\n")

    # Auto-Learn first: Ensure we have latest signals
    print_info("  🔄 Auto-Learn: Gathering latest signals from spokes first...")
    hub_trigger_teach(cli, hub_path)

    # Load and show registered spokes
    try:
        registry = load_registry(hub_path)
        spokes = registry.get('projects', [])  # Registry uses 'projects' not 'spokes'

        if not spokes:
            print_info("  No spokes registered in hub.")
            print_info("  Add spokes first: Main Menu → Spokes → Add Projects")
            return

        def ensure_spoke_workspace(spoke_path: Path):
            spoke_dir = spoke_path / 'WAI-Spoke'
            created_spoke = False
            workspace_created = []

            if not spoke_dir.exists():
                try:
                    init_spoke(spoke_path, is_framework=False, verbose=False)
                    created_spoke = True
                except Exception as exc:
                    return False, created_spoke, workspace_created, f"Init failed: {exc}"

            templates_dir = Path(__file__).parent.parent.parent / 'templates' / 'WAI'
            if not templates_dir.exists():
                return False, created_spoke, workspace_created, "Templates directory not found"

            workspace_files = ['WAI-Workspace.cmd', 'wai-shell.sh', 'wai-cli-launch.sh']

            def parse_version(value: str) -> tuple:
                if not value:
                    return (0, 0, 0)
                try:
                    parts = [int(p) for p in value.strip().split(".")]
                    while len(parts) < 3:
                        parts.append(0)
                    return tuple(parts[:3])
                except Exception:
                    return (0, 0, 0)

            def extract_version(path: Path) -> tuple:
                try:
                    text = path.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    return (0, 0, 0)
                for line in text.splitlines()[:10]:
                    if "WAI_WORKSPACE_VERSION" in line:
                        raw = line.split("=", 1)[-1].strip().strip('"').strip("'")
                        return parse_version(raw)
                return (0, 0, 0)

            for filename in workspace_files:
                src = templates_dir / filename
                dst = spoke_dir / filename
                if not src.exists():
                    continue

                needs_update = False
                if not dst.exists():
                    needs_update = True
                else:
                    src_version = extract_version(src)
                    dst_version = extract_version(dst)
                    if src_version > dst_version:
                        needs_update = True

                if needs_update:
                    try:
                        dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
                        workspace_created.append(filename)
                    except Exception as exc:
                        return False, created_spoke, workspace_created, f"Failed to write {filename}: {exc}"

            return True, created_spoke, workspace_created, None

        # Check if hub has knowledge to share
        kb_dir = hub_path / 'knowledge-base'
        has_knowledge = kb_dir.exists() and any(kb_dir.glob('*.jsonl'))

        print_info("  📊 Preview of what will happen:")
        print_info("")
        print_info(f"  Hub: {hub_path.name}")
        print_info(f"  Spokes to update: {len(spokes)}")
        print_info("")
        for spoke in spokes[:5]:  # Show first 5
            spoke_name = spoke.get('preferred_name', spoke.get('path', 'Unknown'))
            print_info(f"    • {spoke_name}")
        if len(spokes) > 5:
            print_info(f"    ... and {len(spokes) - 5} more")
        print_info("")
        print_info("  Actions:")
        print_info("    1. Ensure each spoke has WAI-Spoke and workspace files")
        if has_knowledge:
            print_info("    2. Read hub knowledge base patterns")
            print_info("    3. Update each spoke's WAI-Guide.md")
            print_info("    4. Add relevant best practices and learnings")
            print_info("    5. Record teach timestamp")
        print_info("")

        if not has_knowledge:
            print_info("  ⚠️  Hub knowledge base is empty.")
            print_info("  Proceeding will bootstrap WAI-Spoke + workspace files only.")

        if not safe_confirm("  Proceed with distributing knowledge to spokes?", default=False):
            print_info("  Cancelled.")
            return

        # Actually perform the teaching
        print_info("\n  🎓 Hub teaching to spokes...")
        print_info("")

        total_updated = 0
        total_bootstrapped = 0
        spoke_updates = []

        # Read all hub knowledge base files
        kb_patterns = []
        for kb_file in kb_dir.glob('*.jsonl'):
            try:
                with open(kb_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                signal = json.loads(line)
                                # Extract high-impact patterns
                                for offer in signal.get('offers', []):
                                    if offer.get('impact', 0) >= 8:
                                        kb_patterns.append({
                                            'type': offer.get('type', 'pattern'),
                                            'topic': offer.get('topic', 'Unknown'),
                                            'context': offer.get('context', ''),
                                            'impact': offer.get('impact', 8),
                                            'source': kb_file.stem
                                        })
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

        if has_knowledge and not kb_patterns:
            print_error("  No patterns found in knowledge base to distribute.")
            return

        if has_knowledge:
            print_info(f"  Found {len(kb_patterns)} high-impact pattern(s) from hub knowledge base")
            print_info(f"  (Patterns = learnings, best practices, and insights to share)")
            print_info("")

        # Update each spoke
        for spoke in spokes:
            spoke_path = Path(spoke.get('path', ''))
            spoke_name = spoke.get('preferred_name', spoke_path.name)
            wai_spoke_dir = spoke_path / 'WAI-Spoke'

            bootstrap_status = ""
            ok, created_spoke, workspace_created, bootstrap_error = ensure_spoke_workspace(spoke_path)
            if not ok:
                spoke_updates.append((spoke_name, 0, f"Bootstrap failed: {bootstrap_error}", bootstrap_status))
                continue

            if created_spoke or workspace_created:
                total_bootstrapped += 1
                parts = []
                if created_spoke:
                    parts.append("initialized")
                if workspace_created:
                    parts.append("workspace files")
                bootstrap_status = f"bootstrapped ({', '.join(parts)})"

            if not has_knowledge:
                spoke_updates.append((spoke_name, 0, "Bootstrap only (no hub knowledge)", bootstrap_status))
                continue

            try:
                # Create a hub-learnings file that closeout will reconcile
                learnings_file = wai_spoke_dir / 'WAI-Hub-Learnings.md'

                # Generate learnings content
                content = f"# Hub Learnings - {datetime.now().strftime('%Y-%m-%d')}\n\n"
                content += "These patterns were distributed from the hub knowledge base.\n"
                content += "Run closeout to integrate these into your WAI-Guide.md\n\n"

                # Group by type
                patterns_by_type = {}
                for pattern in kb_patterns:
                    ptype = pattern['type']
                    if ptype not in patterns_by_type:
                        patterns_by_type[ptype] = []
                    patterns_by_type[ptype].append(pattern)

                # Write patterns
                for ptype, patterns in patterns_by_type.items():
                    content += f"## {ptype.title()}\n\n"
                    for pattern in patterns:
                        content += f"### {pattern['topic']}\n"
                        if pattern['context']:
                            content += f"{pattern['context']}\n"
                        content += f"\n*Impact: {pattern['impact']} | Source: {pattern['source']}*\n\n"

                # Write the file
                learnings_file.write_text(content)
                spoke_updates.append((spoke_name, len(kb_patterns), "✓ Updated", bootstrap_status))
                total_updated += 1

            except Exception as e:
                spoke_updates.append((spoke_name, 0, f"Error: {str(e)[:30]}", bootstrap_status))

        # Display results
        print_info("  Results by spoke:")
        print_info("")
        for spoke_name, count, status, bootstrap_status in spoke_updates:
            if bootstrap_status:
                status = f"{status} | {bootstrap_status}"
            # Don't add another checkmark if status already has one
            if count > 0 or "Updated" in status:
                print_success(f"    {spoke_name}: {count} pattern(s) - {status}")
            else:
                print_info(f"      {spoke_name}: {count} patterns - {status}")

        print_info("")
        if total_updated > 0:
            print_success(f"  ✓ Teach complete! Updated {total_updated} spoke(s) with hub knowledge")
            if total_bootstrapped > 0:
                print_info(f"  ✓ Bootstrapped {total_bootstrapped} spoke(s) with workspace files")

            # Update hub profile with last teach timestamp
            profile_path = hub_path / 'hub-profile.json'
            if profile_path.exists():
                try:
                    profile = json.loads(profile_path.read_text())
                    profile['last_teach_run'] = datetime.now().isoformat()
                    profile_path.write_text(json.dumps(profile, indent=2))
                except:
                    pass

            print_info("")
            print_info("  📝 IMPORTANT - Next Steps:")
            print_info("     1. If AI is currently working on one of the updated spokes:")
            print_info("        a. Say 'Closeout' to end the current session")
            print_info("        b. Closeout will reconcile WAI-Hub-Learnings.md into WAI-Guide.md")
            print_info("        c. Start a new session to load the updated guidance")
            print_info("")
            print_info("     2. New files created in each spoke:")
            print_info("        • WAI-Spoke/WAI-Hub-Learnings.md (temporary - for closeout)")
            print_info("")
            print_info("     3. After closeout, patterns will be in:")
            print_info("        • WAI-Spoke/WAI-Guide.md (permanent)")
            print_info("")
            print_info("  💡 This enables seamless learning on the fly!")
        else:
            if total_bootstrapped > 0:
                print_success(f"  ✓ Bootstrapped {total_bootstrapped} spoke(s) with workspace files")
            else:
                print_info(f"  No spokes were updated.")

    except Exception as e:
        print_error(f"  Error loading registry: {e}")


def hub_ignore_candidates(cli, ignore_paths: list, primary_hub: Path):
    """Add hub paths to ignore list in primary hub profile."""
    try:
        profile_path = primary_hub / 'hub-profile.json'
        if not profile_path.exists():
            print_error("  Hub profile not found.")
            return

        profile = json.loads(profile_path.read_text())

        # Add ignore list to profile
        if 'hub_config' not in profile:
            profile['hub_config'] = {}

        if 'ignored_hubs' not in profile['hub_config']:
            profile['hub_config']['ignored_hubs'] = []

        # Add new ignore paths
        for path in ignore_paths:
            path_str = str(path)
            if path_str not in profile['hub_config']['ignored_hubs']:
                profile['hub_config']['ignored_hubs'].append(path_str)
                print_success(f"  Added to ignore list: {path}")

        # Save updated profile
        profile_path.write_text(json.dumps(profile, indent=2))
        print_success("\n  Ignore list updated!")

    except Exception as e:
        print_error(f"  Failed to update ignore list: {e}")


def hub_subsume(cli, source_hub: Path, target_hub: Path):
    """Merge source hub into target hub."""
    print_info(f"\n🔄 Subsuming {source_hub.name} → {target_hub.name}\n")

    # Load both registries
    try:
        source_registry_path = source_hub / 'registry' / 'wheel-projects.json'
        target_registry_path = target_hub / 'registry' / 'wheel-projects.json'

        if not source_registry_path.exists():
            print_error(f"  Source registry not found: {source_registry_path}")
            return

        source_registry = json.loads(source_registry_path.read_text())
        target_registry = json.loads(target_registry_path.read_text()) if target_registry_path.exists() else {"version": "2.0", "projects": [], "groups": {}}

        # Merge projects
        source_projects = source_registry.get('projects', [])
        target_projects = target_registry.get('projects', [])
        target_paths = {p['path'] for p in target_projects}

        added_count = 0
        duplicate_count = 0

        for project in source_projects:
            if project['path'] not in target_paths:
                target_projects.append(project)
                added_count += 1
                print_success(f"  ✓ Added: {project.get('name', 'Unknown')}")
            else:
                duplicate_count += 1
                print_info(f"  ⊙ Skipped duplicate: {project.get('name', 'Unknown')}")

        # Merge groups
        source_groups = source_registry.get('groups', {})
        target_groups = target_registry.get('groups', {})

        for group_name, group_data in source_groups.items():
            if group_name not in target_groups:
                target_groups[group_name] = group_data
                print_success(f"  ✓ Added group: {group_name}")
            else:
                # Merge spokes in existing group
                existing_spokes = set(target_groups[group_name].get('spokes', []))
                new_spokes = group_data.get('spokes', [])
                for spoke in new_spokes:
                    if spoke not in existing_spokes:
                        target_groups[group_name].setdefault('spokes', []).append(spoke)

        # Update target registry
        target_registry['projects'] = target_projects
        target_registry['groups'] = target_groups

        # Save merged registry
        target_registry_path.parent.mkdir(parents=True, exist_ok=True)
        target_registry_path.write_text(json.dumps(target_registry, indent=2))

        print_info(f"\n  Summary:")
        print_info(f"    Projects added: {added_count}")
        print_info(f"    Duplicates skipped: {duplicate_count}")
        print_info(f"    Groups merged: {len(source_groups)}")

        # Ask about deleting source hub
        if safe_confirm(f"\n  Delete source hub ({source_hub})?", default=False):
            try:
                shutil.rmtree(source_hub)
                print_success(f"  ✓ Deleted: {source_hub}")
            except Exception as e:
                print_error(f"  Failed to delete source hub: {e}")
        else:
            print_info(f"  Source hub preserved: {source_hub}")

        print_success("\n  ✓ Subsume complete!")

    except Exception as e:
        print_error(f"  Subsume failed: {e}")
        import traceback
        traceback.print_exc()
