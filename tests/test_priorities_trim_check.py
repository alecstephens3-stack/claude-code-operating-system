import priorities_trim_check as pt

OLD = """## This week
- Review screen: fix OPS-12 before the walkthrough. Notes: vault/meetings/2026-10-01-walkthrough.md
- Contract signed for $4,500, copy at https://example.com/signed
- Ask the office manager (manager@example.com) for the export.
"""


def test_nothing_dropped_when_everything_survives():
    assert pt.dropped(OLD, OLD) == {}


def test_reports_each_kind_that_only_the_archive_keeps():
    new = "## This week\n- Review screen: walkthrough Thursday.\n"
    gone = pt.dropped(OLD, new)
    assert gone["tickets"] == ["OPS-12"]
    assert gone["files"] == ["vault/meetings/2026-10-01-walkthrough.md"]
    assert gone["money"] == ["$4,500"]
    assert gone["links"] == ["https://example.com/signed"]
    assert gone["emails"] == ["manager@example.com"]


def test_exit_code_and_message(tmp_path, capsys):
    old, new = tmp_path / "old.md", tmp_path / "new.md"
    old.write_text(OLD)
    new.write_text(OLD.replace("OPS-12", "the bug"))
    assert pt.main([str(old), str(new)]) == 1
    assert "tickets only in the archive: OPS-12" in capsys.readouterr().out
    new.write_text(OLD)
    assert pt.main([str(old), str(new)]) == 0
