import datetime as dt
import json

import pytest

import check_context_budget as cb

TODAY = dt.date(2026, 10, 17)


def config(**over):
    cfg = {
        "warn_at": 0.8,
        "layers": [
            {"name": "main", "path": "CLAUDE.md", "limit": 100, "unit": "bytes", "why": "w", "fix": "f"},
            {"name": "index", "path": "mem/{project_key}/INDEX.md", "limit": 10, "unit": "lines",
             "why": "w", "fix": "f"},
        ],
        "reset": {"path": "prio.md", "pattern": "Last reset: (\\d{4}-\\d{2}-\\d{2})", "max_age_days": 7},
    }
    cfg.update(over)
    return cfg


@pytest.fixture
def root(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x" * 10)
    (tmp_path / "prio.md").write_text("Last reset: 2026-10-12\n")
    return tmp_path


def test_quiet_when_everything_fits(root):
    assert cb.report(config(), root, "session", TODAY) == ""
    assert cb.report(config(), root, "text", TODAY) == ""


def test_warns_near_the_limit(root):
    (root / "CLAUDE.md").write_text("x" * 85)
    out = cb.report(config(), root, "session", TODAY)
    assert "CONTEXT BUDGET WARNING" in out and "main: 85 of 100 bytes (85%)" in out
    assert "main file is at 85%" in cb.report(config(), root, "text", TODAY)


def test_counts_lines_and_resolves_project_key(root):
    key = str(root.resolve()).replace("/", "-")
    index = root / "mem" / key / "INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text("line\n" * 9)
    rows = {r["name"]: r for r in cb.rows(config(), root)}
    assert rows["index"]["value"] == 9
    assert "index: 9 of 10 lines" in cb.report(config(), root, "session", TODAY)


def test_missing_file_is_skipped_not_an_error(root):
    rows = {r["name"]: r for r in cb.rows(config(), root)}
    assert rows["index"]["value"] is None
    assert "missing" in cb.report(config(), root, "table", TODAY)


def test_overdue_or_missing_reset_is_reported(root):
    (root / "prio.md").write_text("Last reset: 2026-10-01\n")
    assert "16 days" in cb.report(config(), root, "session", TODAY)
    (root / "prio.md").write_text("no header\n")
    assert "not had its weekly reset recorded" in cb.report(config(), root, "text", TODAY)


def test_main_with_config_file(root, tmp_path, capsys):
    cfg = tmp_path / "budget.json"
    cfg.write_text(json.dumps(config()))
    assert cb.main(["--config", str(cfg), "--root", str(root), "--today", "2026-10-17"]) == 0
    assert "priorities last reset: 5 days ago" in capsys.readouterr().out
