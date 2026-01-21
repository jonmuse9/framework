"""
Update Command

Update spoke by absorbing seed files and archiving unknown items.
"""

from ..spoke_update import SpokeUpdateProcessor
from ..init import check_spoke_initialized
from ..utils.input import print_info, print_success, print_error, print_warning, safe_confirm
from ..utils.paths import normalize_path


def cmd_update(args):
    """
    Handle update command.

    Absorbs seed files from WAI-Spoke into canonical files and archives
    unknown items for review.

    Args:
        args: Argument namespace with 'path' attribute

    Process:
        1. Plan update (scan for ingest/reference files and unknown items)
        2. Show preview to user
        3. Confirm and execute update
        4. Report results
    """
    try:
        spoke_path = normalize_path(args.path)

        if not check_spoke_initialized(spoke_path):
            print_error(f"No spoke found at {spoke_path}")
            print_info("Run 'WAI init' to initialize a spoke first.")
            return

        updater = SpokeUpdateProcessor(spoke_path)
        plan = updater.plan_update()

        ingest_files = plan.get("ingest_files", [])
        reference_files = plan.get("reference_files", [])
        unknown_items = plan.get("unknown_items", [])

        print_info("\nAbsorbe Preview:")
        print_info(f"  Seed ingest files: {len(ingest_files)}")
        print_info(f"  Seed reference files: {len(reference_files)}")
        print_info(f"  Unknown items to archive: {len(unknown_items)}")

        if not (ingest_files or reference_files or unknown_items):
            print_info("  Nothing to update.")
            return

        if not safe_confirm("Proceed with update?", default=True):
            print_info("Absorbe cancelled.")
            return

        results = updater.run_update()
        print_success("\nAbsorbe complete.")
        print_info(f"  Ingested: {len(results['ingested'])}")
        print_info(f"  Archived reference: {len(results['archived_reference'])}")
        print_info(f"  Archived unknown: {len(results['archived_unknown'])}")

        if results.get("ingest_notes"):
            print_info("\n  Ingest details:")
            for note in results["ingest_notes"]:
                targets = ", ".join(note.get("applied_to", []))
                preview = note.get("preview", "")
                print_info(f"   - {note.get('file')} → {targets}")
                if preview:
                    print_info(f"     preview: {preview}")

        for warning in results.get("warnings", []):
            print_warning(f"  Warning: {warning}")

    except Exception as e:
        print_error(f"Absorbe failed: {e}")
