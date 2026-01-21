import json
from pathlib import Path

from wai_cli.baseline_helpers import get_latest_baseline_summary


def test_get_latest_baseline_summary(tmp_path: Path) -> None:
    spoke_dir = tmp_path / "spoke"
    wai_spoke = spoke_dir / "WAI-Spoke"
    wai_spoke.mkdir(parents=True)

    log_entry = {
        "timestamp": "2026-01-02T00:00:00Z",
        "ide": "Codex CLI",
        "model": "GPT-5",
        "savings": {"percent_saved": 68.6}
    }
    log_path = wai_spoke / "WAI-Baseline-Log.jsonl"
    log_path.write_text(json.dumps(log_entry) + "\n")

    summary = get_latest_baseline_summary(spoke_dir)

    assert "Codex CLI" in summary
    assert "GPT-5" in summary
    assert "68.6%" in summary
