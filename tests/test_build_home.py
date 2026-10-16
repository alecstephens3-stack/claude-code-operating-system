import pytest

import build_home as bh


def note(status, title, summary="s"):
    return (f"---\ntype: project\ntitle: {title}\nsummary: {summary}\nstatus: {status}\n"
            f"tags: [project]\nlast-updated: 2026-10-01\n---\n")


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "a.md").write_text(note("archived", "Alpha"))
    (tmp_path / "projects" / "b.md").write_text(note("active", "Bravo"))
    (tmp_path / "projects" / "c.md").write_text(note("active", "Charlie board"))
    (tmp_path / "HOME.md").write_text(
        "# Home\nhand-written\n<!-- AUTO:projects -->\nold\n<!-- /AUTO:projects -->\ntail\n")
    return tmp_path


def test_blocks_sorted_by_status_then_title(vault):
    out = bh.build((vault / "HOME.md").read_text(), vault)
    lines = [l for l in out.splitlines() if l.startswith("- ")]
    assert [l.split("]")[0] for l in lines] == ["- [Bravo", "- [Charlie board", "- [Alpha"]


def test_text_outside_markers_is_kept(vault):
    out = bh.build((vault / "HOME.md").read_text(), vault)
    assert out.startswith("# Home\nhand-written\n") and out.endswith("tail\n")
    assert "old" not in out


def test_unreadable_note_still_listed(vault):
    (vault / "projects" / "d.md").write_text("---\ntitle: Bad: colon\n---\n")
    out = bh.build((vault / "HOME.md").read_text(), vault)
    assert "[d](projects/d.md): front matter missing or unreadable" in out


def test_check_mode_and_idempotence(vault):
    assert bh.main(["--vault", str(vault), "--check"]) == 1
    assert bh.main(["--vault", str(vault)]) == 0
    assert bh.main(["--vault", str(vault), "--check"]) == 0


def test_unknown_folder_fails(vault):
    with pytest.raises(SystemExit):
        bh.build("<!-- AUTO:nope -->\n<!-- /AUTO:nope -->", vault)
