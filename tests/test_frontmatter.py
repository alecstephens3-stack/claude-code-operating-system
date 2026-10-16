import pytest

import frontmatter as fm


def test_reads_scalars_lists_and_quotes():
    text = '---\ntype: project\ntitle: "Call notes: pricing"\ntags: [a, "b c"]\n---\nbody\n'
    assert fm.parse(text) == {"type": "project", "title": "Call notes: pricing", "tags": ["a", "b c"]}


def test_no_block_is_none():
    assert fm.parse("# Just a heading\n") is None


def test_empty_list():
    assert fm.parse("---\ntags: []\n---\n") == {"tags": []}


def test_trailing_comment_is_dropped():
    assert fm.parse("---\nstatus: active # live\n---\n") == {"status": "active"}


@pytest.mark.parametrize("block, needle", [
    ("title: Call notes: pricing", "unquoted colon"),
    ("title: \"open quote", "never closed"),
    ("type: a\ntype: b", "duplicate"),
    ("parent:\n  child: x", "indented"),
    ("just words", "expected"),
])
def test_unreadable_blocks_raise(block, needle):
    with pytest.raises(fm.FrontmatterError, match=needle):
        fm.parse(f"---\n{block}\n---\n")


def test_unclosed_block_raises():
    with pytest.raises(fm.FrontmatterError, match="never closed"):
        fm.parse("---\ntype: project\n")


def test_notes_skips_hidden_and_listed_dirs(tmp_path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "archives").mkdir()
    (tmp_path / "archives" / "old.md").write_text("x")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "cfg.md").write_text("x")
    assert [p.name for p in fm.notes(tmp_path, {"archives"})] == ["a.md"]
