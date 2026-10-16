import datetime as dt

import pytest

import lint_frontmatter as lf

TODAY = dt.date(2026, 10, 17)
GOOD = """---
type: project
title: Order intake
summary: Orders land in the spreadsheet
status: active
client: Example Co.
tags: [project]
last-updated: 2026-10-12
---
See [[other]].
"""
OTHER = GOOD.replace("Order intake", "Other").replace("See [[other]].", "")


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "note.md").write_text(GOOD)
    (tmp_path / "other.md").write_text(OTHER)
    return tmp_path


def run(vault):
    return lf.lint(vault, lf.load_schema(), TODAY)


def test_clean_vault_has_no_findings(vault):
    assert run(vault) == ([], [])


@pytest.mark.parametrize("old, new, code", [
    ("---\ntype", "type", "MISSING"),
    ("title: Order intake", "title: Call: notes", "UNPARSEABLE"),
    ("summary: Orders land in the spreadsheet\n", "", "FIELD"),
    ("type: project", "type: memo", "TYPE"),
    ("status: active", "status: doing", "STATUS"),
    ("last-updated: 2026-10-12", "last-updated: 12/10/2026", "DATE"),
    ("tags: [project]", "tags: project", "TAGS"),
    ("[[other]]", "[[nowhere]]", "LINK"),
    ("client: Example Co.\n", "", "FIELD"),
])
def test_each_error_is_reported(vault, old, new, code):
    note = vault / "note.md"
    note.write_text(note.read_text().replace(old, new, 1))
    errors, _ = run(vault)
    assert any(e.startswith(code) for e in errors), errors


def test_stale_active_note_warns_but_does_not_error(vault):
    note = vault / "note.md"
    note.write_text(note.read_text().replace("2026-10-12", "2026-01-02"))
    errors, warns = run(vault)
    assert errors == []
    assert any(w.startswith("STALE") for w in warns)


def test_summary_period_warns(vault):
    note = vault / "note.md"
    note.write_text(note.read_text().replace("spreadsheet\n", "spreadsheet.\n", 1))
    assert any(w.startswith("SUMMARY") for w in run(vault)[1])


def test_link_with_alias_and_heading_resolves(vault):
    note = vault / "note.md"
    note.write_text(note.read_text().replace("[[other]]", "[[other#Section|the other note]]"))
    assert run(vault)[0] == []


def test_main_exit_codes_and_quiet(vault, capsys):
    assert lf.main([str(vault), "--today", "2026-10-17", "--quiet"]) == 0
    assert capsys.readouterr().out == ""
    (vault / "bad.md").write_text("no front matter")
    assert lf.main([str(vault), "--today", "2026-10-17"]) == 1
    assert "MISSING" in capsys.readouterr().out
